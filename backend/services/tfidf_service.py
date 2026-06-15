"""
tfidf_service.py — Sparse TF-IDF vectorizer for chunk text + queries.

Replaces the GPT4All / nomic embedding pipeline for retrieval. The
quantized nomic GGUF model has two real-world problems on this stack:

  1. ``llama.cpp`` is not thread-safe. Concurrent calls produce
     OSError access violations and GGML_ASSERT aborts that can take
     the whole process down.
  2. Per-batch latency is 1-3 s on GPU and noticeably more on CPU,
     which became the dominant bottleneck once the chunk pipeline was
     otherwise optimized.

For our retrieval surface — short chunk render-text bodies and
short user queries — TF-IDF over a per-snapshot vocabulary is both
faster (microseconds per query) AND tends to be more accurate when
the user is searching for keyword fragments embedded in URLs or
body text. Sparse matrices keep memory cost trivial even with
thousands of chunks.

Storage model (per user request):
  * The TF-IDF document matrix lives as a standalone ``.npz`` file
    on disk (``scipy.sparse.save_npz``) keyed by snapshot id, NOT
    inside the kuzu vector DB. Sparse-matrix files load in tens of
    milliseconds and let cosine-similarity queries run as a single
    sparse-matvec — no per-row deserialization, no DB roundtrip.
  * ``ChunkInstance.embedding`` (kuzu schema) keeps a dense 1024-d
    L2-normalized projection so legacy callers that read the column
    keep working. The "real" retrieval index is the sparse file.

Optional GPU acceleration:
  * If ``cupy`` + ``cupyx.scipy.sparse`` are available, the sparse
    matrix can be moved to device for matvec. Falls back to CPU
    silently when GPU isn't installed — TF-IDF on CPU is already
    sub-millisecond for queries on thousands of docs.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Optional GPU sparse backend
# ---------------------------------------------------------------------------
#
# ``cupyx.scipy.sparse`` provides device-side sparse matvec that's
# 5-50x faster than scipy's CPU implementation on large vocabularies.
# We import it lazily and fall back to CPU silently if unavailable —
# cupy requires a CUDA install which most user setups won't have.

_GPU_AVAILABLE: Optional[bool] = None  # tri-state: None=untested, True/False after probe


def _probe_gpu() -> bool:
    """Return True if ``cupyx.scipy.sparse`` can be imported AND a
    device is reachable. GPU is the DEFAULT — set
    ``WFH_TFIDF_GPU=0`` to force CPU (useful on machines without
    CUDA or for quick offline tests).

    The first ``cupy`` device init costs ~3-4 s, so the very first
    GPU matvec in a process pays that. Subsequent calls are
    sub-millisecond and dramatically beat scipy on large matrices.
    """
    global _GPU_AVAILABLE
    if _GPU_AVAILABLE is not None:
        return _GPU_AVAILABLE
    # Default ON per user request. Only disable when the env var
    # explicitly says "0".
    if os.environ.get("WFH_TFIDF_GPU", "1") == "0":
        _GPU_AVAILABLE = False
        return False
    try:
        import cupy  # type: ignore
        import cupyx.scipy.sparse  # type: ignore  # noqa: F401
        cupy.cuda.runtime.getDeviceCount()  # raises if no driver
        _GPU_AVAILABLE = True
        logger.info("TF-IDF: cupy GPU sparse backend available (CUDA on)")
    except Exception as e:
        _GPU_AVAILABLE = False
        logger.info("TF-IDF: GPU unavailable (%s); CPU scipy.sparse fallback", e)
    return _GPU_AVAILABLE


# ---------------------------------------------------------------------------
# URL tokenization
# ---------------------------------------------------------------------------
#
# The user wants URLs to surface as searchable tokens — e.g.
# ``/blog/our-bodies-know`` should match the query "bodies know".
# We split URLs into plain text by stripping the scheme/host and
# turning every ``/`` and ``-`` (also ``_`` and ``.`` while we're at
# it — they all separate words inside URL slugs) into spaces, then
# url-decode anything percent-escaped. The result is concatenated
# back into the chunk's text body before vectorization.

_URL_SEP_RE = re.compile(r"[/\-_.]+")
_PERCENT_RE = re.compile(r"%[0-9A-Fa-f]{2}")


def tokenize_url(url: Optional[str]) -> str:
    """Split a URL into space-separated tokens for retrieval.

    Strips the scheme + host (those repeat across every URL on a
    site and would dominate IDF weights uselessly) and turns
    ``/``, ``-``, ``_``, ``.`` into spaces so multi-word slugs
    become tokens. Returns an empty string for falsy input or
    non-http(s) schemes.
    """
    if not url:
        return ""
    try:
        parts = urlsplit(url)
    except Exception:
        return ""
    if parts.scheme not in ("http", "https", ""):
        return ""

    # Keep host words (e.g. "noetic.org" → "noetic org") since
    # site names are often meaningful for retrieval.
    host = (parts.hostname or "").replace(".", " ")
    path = parts.path or ""
    query = parts.query or ""

    body = " ".join(p for p in (host, path, query) if p)
    body = _URL_SEP_RE.sub(" ", body)
    # %20 etc. → space; other percent escapes go to spaces too —
    # we don't need exact byte-accurate decoding, just word breaks.
    body = _PERCENT_RE.sub(" ", body)
    return re.sub(r"\s+", " ", body).strip()


def expand_urls_in_text(text: str) -> str:
    """Replace bare URLs inside ``text`` with their tokenized form.

    Used after the chunk renderer has produced its ``rendered_text``
    so any anchor URLs that survived the render now contribute
    actual searchable words to the TF-IDF vector.
    """
    if not text:
        return text

    def _swap(m):
        return " " + tokenize_url(m.group(0)) + " "

    # Match absolute and relative URLs greedily up to the first whitespace or
    # control char — generous enough for chunk-render output where
    # URLs appear in plain text, not pre-tokenized.
    return re.sub(r"(?:https?://|/)\S+", _swap, text)


# ---------------------------------------------------------------------------
# TF-IDF
# ---------------------------------------------------------------------------


@dataclass
class TfidfFitResult:
    """Summary returned by :meth:`TfidfService.fit` for logging."""

    document_count: int
    vocabulary_size: int
    nnz: int  # total non-zero entries across the matrix
    fit_time_ms: float = 0.0


#: ``None`` = NO vocabulary cap. Per the user's "token-complete"
#: requirement, every token from every scanned DOM gets a column
#: index — including URL slugs and sparse tokens that occur in
#: only a handful of documents. Sparse storage means the matrix
#: cost is O(nnz) anyway, so capping vocab is purely lossy.
DEFAULT_MAX_FEATURES = None


class TfidfService:
    """Sparse TF-IDF vectorizer with cosine-similarity helpers.

    Vocabulary is built lazily — call :meth:`fit` over the document
    corpus once, then :meth:`vectorize` and :meth:`query_similarities`
    for retrieval. The fit is fast enough (sub-second for thousands
    of chunks) that callers can re-fit per snapshot to avoid stale
    IDF weights leaking across pages.

    Persistence: the fitted ``(matrix, vocabulary, idf)`` triple
    serializes to a single ``.npz`` file via :meth:`save_to_file` /
    :meth:`load_from_file`. That's the canonical retrieval index —
    callers that just want sparse cosine over a snapshot's chunks
    load the file and run a single sparse matvec, no DB needed.
    """

    def __init__(
        self,
        *,
        min_df: int = 1,
        max_df: float = 1.0,
        ngram_range: Tuple[int, int] = (1, 2),
        max_features: Optional[int] = DEFAULT_MAX_FEATURES,
        sublinear_tf: bool = True,
        use_gpu: Optional[bool] = None,
    ):
        # sklearn imports kept lazy so this module doesn't blow up on
        # boxes that don't have scikit-learn installed (e.g. the
        # legacy nomic-only tests).
        from sklearn.feature_extraction.text import TfidfVectorizer

        # ngram_range=(1, 2) gives unigrams + bigrams which captures
        # short multi-word terms ("space swimming", "tarot reading")
        # that dominate slug-based queries without inflating vocab
        # the way trigrams would.
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            token_pattern=r"(?u)\b\w+\b",
            min_df=min_df,
            max_df=max_df,
            ngram_range=ngram_range,
            max_features=max_features,
            sublinear_tf=sublinear_tf,
            norm="l2",
        )
        self._fitted = False
        self._matrix = None  # sparse CSR — matches corpus order
        # ``use_gpu=None`` → auto-detect; True → force; False → never.
        if use_gpu is None:
            self._use_gpu = _probe_gpu()
        else:
            self._use_gpu = bool(use_gpu) and _probe_gpu()
        self._gpu_matrix = None  # cached cupyx.scipy.sparse.csr_matrix

    # ------------------------------------------------------------------
    # Fit / transform
    # ------------------------------------------------------------------

    def fit(self, corpus: Sequence[str]) -> TfidfFitResult:
        import time
        if not corpus:
            self._fitted = False
            self._matrix = None
            self._gpu_matrix = None
            return TfidfFitResult(0, 0, 0, 0.0)

        # Expand any URLs inside each doc before fitting so URL
        # slugs contribute real tokens rather than monolithic
        # ``http://...`` strings that no query would ever match.
        prepared = [expand_urls_in_text(t or "") for t in corpus]

        t0 = time.time()
        self._matrix = self._vectorizer.fit_transform(prepared)
        self._fitted = True
        self._gpu_matrix = None  # invalidate stale GPU copy
        elapsed_ms = (time.time() - t0) * 1000.0

        return TfidfFitResult(
            document_count=len(prepared),
            vocabulary_size=len(self._vectorizer.vocabulary_),
            nnz=int(self._matrix.nnz),
            fit_time_ms=elapsed_ms,
        )

    def vectorize(self, text: str):
        """Return a 1-row sparse CSR matrix for one document/query."""
        if not self._fitted:
            raise RuntimeError("TfidfService.vectorize called before fit()")
        return self._vectorizer.transform([expand_urls_in_text(text or "")])

    # ------------------------------------------------------------------
    # Cosine similarity helpers
    # ------------------------------------------------------------------

    def _ensure_gpu_matrix(self):
        """Lazily copy the doc matrix to device. Returns the cupy CSR
        view (or ``None`` if GPU is disabled / unavailable)."""
        if not self._use_gpu or self._matrix is None:
            return None
        if self._gpu_matrix is not None:
            return self._gpu_matrix
        try:
            import cupy  # type: ignore
            from cupyx.scipy.sparse import csr_matrix as _gpu_csr  # type: ignore
            self._gpu_matrix = _gpu_csr(self._matrix.astype(np.float32))
            return self._gpu_matrix
        except Exception as e:
            logger.warning("TF-IDF: GPU copy failed (%s); falling back to CPU", e)
            self._use_gpu = False
            return None

    def doc_query_similarities(self, query: str) -> np.ndarray:
        """Cosine similarity of ``query`` against every fitted doc.

        Uses the already-fitted matrix — no re-fit. Picks the GPU
        backend automatically when available (single sparse matvec
        is the bottleneck for thousand-chunk pages).
        """
        if not self._fitted:
            raise RuntimeError("doc_query_similarities called before fit()")
        q_vec = self.vectorize(query)  # CPU sparse (1, V)

        gpu_mat = self._ensure_gpu_matrix()
        if gpu_mat is not None:
            try:
                import cupy  # type: ignore
                from cupyx.scipy.sparse import csr_matrix as _gpu_csr  # type: ignore
                q_gpu = _gpu_csr(q_vec.astype(np.float32))
                sims_gpu = (gpu_mat @ q_gpu.T).toarray().ravel()
                return cupy.asnumpy(sims_gpu).astype(np.float32, copy=False)
            except Exception as e:
                logger.warning("TF-IDF: GPU matvec failed (%s); CPU fallback", e)
                self._use_gpu = False

        # CPU path: scipy sparse matvec.
        sims = (self._matrix @ q_vec.T).toarray().ravel()
        return sims.astype(np.float32, copy=False)

    def query_similarities(
        self,
        query: str,
        doc_texts: Sequence[str],
    ) -> np.ndarray:
        """One-shot ``query → similarities`` over an arbitrary doc set.

        Re-fits the vectorizer over the doc set so IDF reflects only
        the retrieval corpus, then runs cosine via :meth:`doc_query_similarities`.
        """
        if not doc_texts:
            return np.zeros((0,), dtype=np.float32)
        self.fit(doc_texts)
        return self.doc_query_similarities(query)

    def matrix(self):
        """Return the fitted document matrix (sparse CSR, L2-normalized)."""
        if not self._fitted:
            raise RuntimeError("TfidfService.matrix called before fit()")
        return self._matrix

    # ------------------------------------------------------------------
    # File-backed persistence
    # ------------------------------------------------------------------

    def save_to_file(self, path: str) -> None:
        """Persist (matrix + vocabulary + idf) to a single ``.npz``.

        Loadable by :meth:`load_from_file`. Roughly:
            data, indices, indptr   ← scipy.sparse.save_npz format
            vocab_terms             ← np.ndarray of strings
            vocab_indices           ← np.ndarray of column indices
            idf                     ← np.ndarray of weights
        """
        if not self._fitted:
            raise RuntimeError("save_to_file called before fit()")
        from scipy import sparse as sp
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        # Write the sparse doc matrix and the vocabulary in one .npz so
        # the file is self-contained — a query path can mmap-load this
        # alone, no separate vocab file to keep in sync.
        terms = np.array(list(self._vectorizer.vocabulary_.keys()), dtype=object)
        indices = np.array(
            [self._vectorizer.vocabulary_[t] for t in terms], dtype=np.int64,
        )
        idf = np.asarray(self._vectorizer.idf_, dtype=np.float32)

        m = self._matrix.tocsr()
        np.savez_compressed(
            path,
            matrix_data=m.data.astype(np.float32),
            matrix_indices=m.indices.astype(np.int32),
            matrix_indptr=m.indptr.astype(np.int32),
            matrix_shape=np.asarray(m.shape, dtype=np.int64),
            vocab_terms=terms,
            vocab_indices=indices,
            idf=idf,
        )

    @classmethod
    def load_from_file(cls, path: str) -> "TfidfService":
        """Reconstruct a :class:`TfidfService` from a saved ``.npz``.

        The vocabulary is rehydrated into the underlying sklearn
        vectorizer so subsequent ``vectorize(query)`` / ``doc_query_similarities``
        calls work without re-fitting.
        """
        from scipy import sparse as sp
        from sklearn.feature_extraction.text import TfidfVectorizer

        z = np.load(path, allow_pickle=True)
        terms = z["vocab_terms"]
        idx = z["vocab_indices"]
        vocab = {str(t): int(i) for t, i in zip(terms, idx)}
        idf = np.asarray(z["idf"], dtype=np.float32)

        svc = cls()
        # Manually rehydrate the underlying sklearn vectorizer with
        # the saved vocabulary + IDF weights so transform() works.
        svc._vectorizer = TfidfVectorizer(
            lowercase=True,
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
            sublinear_tf=True,
            norm="l2",
            vocabulary=vocab,
        )
        svc._vectorizer._tfidf = type("ShimTfIdf", (), {})()
        # sklearn stores idf_ on the underlying TfidfTransformer; this
        # rehydration path bypasses that — instead we set _tfidf.idf_
        # so the transformer's fit() was effectively done at save time.
        # Calling fit() over a 1-element corpus that contains every
        # vocabulary term is the cleanest way to populate it.
        svc._vectorizer.fit([" ".join(terms)])
        # Override the just-fitted IDF with the saved weights so we
        # don't depend on the rehydration corpus for IDF accuracy.
        svc._vectorizer._tfidf.idf_ = idf

        shape = tuple(int(x) for x in z["matrix_shape"])
        svc._matrix = sp.csr_matrix(
            (z["matrix_data"], z["matrix_indices"], z["matrix_indptr"]),
            shape=shape,
        )
        svc._fitted = True
        return svc

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def use_gpu(self) -> bool:
        return bool(self._use_gpu)


# ---------------------------------------------------------------------------
# ChunkInstance compatibility shim
# ---------------------------------------------------------------------------


@dataclass
class TfidfBatchResult:
    """Drop-in replacement for ``ChunkInstanceEmbedder.EmbeddingBatchResult``."""

    embedded_count: int
    unique_text_count: int
    page_embedding: Optional[np.ndarray] = None
    fit: TfidfFitResult = field(default_factory=lambda: TfidfFitResult(0, 0, 0, 0.0))


class ChunkInstanceVectorizer:
    """TF-IDF replacement for ``ChunkInstanceEmbedder``.

    Same surface area: ``embed_instances(instances)`` mutates each
    instance's ``.embedding`` in place. We project the L2-normalized
    sparse TF-IDF row to a fixed-size dense vector via random
    projection so the existing ``ChunkInstance.embedding LIST<DOUBLE>``
    schema keeps working without a migration. The dense projection
    preserves cosine similarity to within ε per the Johnson-
    Lindenstrauss lemma — good enough for the ChunkUmapNode-style
    color/position derivation downstream, and the actual retrieval
    pipeline always uses the sparse matrix directly when available.
    """

    #: Dense embedding dimensionality.
    #:
    #: Bumped to 1024 per user request: the random projection's
    #: cosine-preservation error scales as O(1/√d), so 1024 dims
    #: cuts the worst-case distortion ~4x relative to the previous
    #: 64. The trade-off is RAM (a 1024-d float32 row is 4 KB ×
    #: N_chunks = single-digit MB at most for thousand-chunk pages
    #: — negligible).
    #:
    #: NOTE: this dense projection is the LEGACY storage shape used
    #: by ``ChunkInstance.embedding LIST<DOUBLE>``. The authoritative
    #: retrieval index is the sparse ``.npz`` saved by
    #: :meth:`TfidfService.save_to_file`, which has the FULL
    #: vocabulary-sized dimensionality (typically 5-50 k cols).
    DENSE_DIM = 1024

    def __init__(self, dense_dim: int = DENSE_DIM):
        self.dense_dim = int(dense_dim)
        self.tfidf = TfidfService()
        self._projection: Optional[np.ndarray] = None
        # Last-fit text → dense vector cache so callers that ask
        # ``embed_query`` post-fit don't redo the full sparse-to-dense
        # roundtrip.
        self._dense_matrix: Optional[np.ndarray] = None

    def _build_projection(self, vocab_size: int) -> np.ndarray:
        """Random-projection matrix (vocab × dense_dim).

        Seeded so successive scans produce comparable embeddings
        across snapshots. Variance scaled by ``1/sqrt(dense_dim)``
        per Johnson-Lindenstrauss for length preservation.
        """
        rng = np.random.default_rng(20240426)
        return rng.normal(
            0.0,
            1.0 / np.sqrt(self.dense_dim),
            size=(vocab_size, self.dense_dim),
        ).astype(np.float32)

    def embed_instances(self, instances: Sequence) -> TfidfBatchResult:
        """Vectorize each instance, attach a dense embedding."""
        if not instances:
            return TfidfBatchResult(0, 0, None)

        # Deduplicate identical rendered_text so we vectorize each
        # unique string once even on heavy templated pages (mirrors
        # ChunkInstanceEmbedder's old dedup behavior).
        unique_texts: List[str] = []
        key_to_idx: dict = {}
        per_inst_idx: List[int] = []
        for inst in instances:
            t = getattr(inst, "rendered_text", "") or ""
            if t not in key_to_idx:
                key_to_idx[t] = len(unique_texts)
                unique_texts.append(t)
            per_inst_idx.append(key_to_idx[t])

        fit_result = self.tfidf.fit(unique_texts)
        if not self.tfidf.fitted:
            for inst in instances:
                inst.embedding = []
            return TfidfBatchResult(0, 0, None, fit_result)

        sparse = self.tfidf.matrix()  # (U, V)
        vocab = sparse.shape[1]
        if self._projection is None or self._projection.shape != (vocab, self.dense_dim):
            self._projection = self._build_projection(vocab)

        dense = (sparse @ self._projection)  # (U, dense_dim)
        if hasattr(dense, "toarray"):
            dense = dense.toarray()
        dense = np.asarray(dense, dtype=np.float32)

        # L2-normalize rows so downstream cosine-similarity is just
        # a dot product.
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        dense = dense / norms

        for inst, ui in zip(instances, per_inst_idx):
            inst.embedding = list(map(float, dense[ui].tolist()))

        page_vec = dense.mean(axis=0)
        page_norm = float(np.linalg.norm(page_vec))
        if page_norm > 0:
            page_vec = page_vec / page_norm

        self._dense_matrix = dense
        return TfidfBatchResult(
            embedded_count=len(instances),
            unique_text_count=len(unique_texts),
            page_embedding=page_vec.astype(np.float32),
            fit=fit_result,
        )

    def embed_query(self, query: str) -> np.ndarray:
        """Encode a query into the same dense space.

        Returns a ``(dense_dim,)`` float32 vector. Falls back to a
        zero vector if no fit has been performed yet — callers
        should re-run :meth:`embed_instances` over their corpus
        first.
        """
        if not self.tfidf.fitted or self._projection is None:
            return np.zeros((self.dense_dim,), dtype=np.float32)
        sparse = self.tfidf.vectorize(query)
        dense = (sparse @ self._projection)
        if hasattr(dense, "toarray"):
            dense = dense.toarray()
        v = np.asarray(dense, dtype=np.float32).ravel()
        n = float(np.linalg.norm(v))
        return v / n if n > 0 else v

    # ------------------------------------------------------------------
    # File-backed sparse index — primary retrieval surface
    # ------------------------------------------------------------------

    def save_sparse_index(
        self, path: str, instances: Optional[Sequence] = None,
    ) -> str:
        """Persist the sparse doc matrix + vocabulary to ``path``.

        When ``instances`` is supplied, the sparse matrix is re-fitted
        over per-instance texts so its rows align 1:1 with the
        instance list. Callers can then build a :class:`SparseTfidfIndex`
        directly: one matrix row per chunk-instance, no dedup mapping
        layer needed.

        When ``instances`` is omitted, the existing (dedup-aware)
        matrix is saved as-is — useful for callers that want vocabulary
        + IDF weights but not the per-instance alignment.

        Returns the resolved path.
        """
        if not path.endswith(".npz"):
            path = path + ".npz"
        if instances is not None:
            # Re-fit over per-instance texts. This uses a fresh TfidfService
            # so the previously-fitted (dedup) vocabulary isn't disturbed.
            inst_texts = [getattr(i, "rendered_text", "") or "" for i in instances]
            inst_svc = TfidfService()
            inst_svc.fit(inst_texts)
            inst_svc.save_to_file(path)
        else:
            self.tfidf.save_to_file(path)
        return path


# ---------------------------------------------------------------------------
# Standalone sparse retrieval index
# ---------------------------------------------------------------------------


class SparseTfidfIndex:
    """File-backed sparse retrieval index.

    Wraps a saved ``TfidfService`` ``.npz`` plus the chunk-id list
    that aligns with the matrix rows. Loaders that just want
    ``query → top-k chunk_ids`` use this directly:

        idx = SparseTfidfIndex.load("snapshots/snap_xyz/tfidf.npz",
                                    chunk_ids=["c1","c2",...])
        for cid, score in idx.search("dolphin science", k=10):
            ...

    No DB roundtrip; the entire query path is one sparse matvec
    plus an ``argpartition``.
    """

    def __init__(self, svc: TfidfService, row_ids: List[str]):
        if len(row_ids) != svc.matrix().shape[0]:
            raise ValueError(
                f"row_ids length ({len(row_ids)}) != matrix rows "
                f"({svc.matrix().shape[0]})"
            )
        self.svc = svc
        self.row_ids = list(row_ids)

    @classmethod
    def load(cls, npz_path: str, row_ids: Sequence[str]) -> "SparseTfidfIndex":
        svc = TfidfService.load_from_file(npz_path)
        return cls(svc, list(row_ids))

    def search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        sims = self.svc.doc_query_similarities(query)
        if sims.size == 0:
            return []
        k = min(k, sims.size)
        # argpartition is O(N) vs argsort's O(N log N); for large
        # corpora that's the difference between 1 ms and 50 ms per
        # query.
        cut = np.argpartition(-sims, k - 1)[:k]
        order = cut[np.argsort(-sims[cut])]
        return [(self.row_ids[i], float(sims[i])) for i in order]
