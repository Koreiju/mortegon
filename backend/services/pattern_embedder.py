"""
pattern_embedder.py — Phase 4: 768-dim nomic embeddings per labeled pattern.

Each ``PatternLabelRow`` from Phase 3 is paired with its chunk's
knowledge panel to produce one canonical ``text_source`` string; that
string is passed through ``EmbeddingService.embed_texts`` (nomic,
``search_document:`` prefix), yielding a 768-D vector stored alongside
the pattern in Kuzu.

Canonical ``text_source`` format (see handoff)::

    [role:card] [category:tarot_card] summary_sentence
    title: The Lovers | The Empress | The Hierophant
    subtitle: love reading | abundance | tradition
    url: /tarot-cards/major-arcana/lovers ; /tarot-cards/major-arcana/empress ; ...

The embeddings can then answer semantic queries ("find the tarot cards")
via a cosine lookup against the pattern store.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from backend.dom.trie_persistence import BuiltTrie, PatternRow
from backend.mapper.chunk_builder import Chunk
from backend.services.pattern_labeler import PatternLabelRow

logger = logging.getLogger(__name__)


NOMIC_DIM = 768

# Category → pretty short name, for the canonical text_source.
_CANONICAL_FIELDS: List[Tuple[str, str, str]] = [
    # (category_prefix, display_label, value_separator)
    ("text.title",           "title",     " | "),
    ("text.heading",         "heading",   " | "),
    ("text.subtitle",        "subtitle",  " | "),
    ("text.visible",         "text",      " | "),
    ("text.body",            "body",      " | "),
    ("text.caption",         "caption",   " | "),
    ("text.accessible",      "alt",       " | "),
    ("text.metadata",        "meta",      " | "),
    ("interactive.label",    "label",     " | "),
    ("interactive.buttons",  "button",    " | "),
    ("interactive.inputs",   "input",     " | "),
    ("interactive.forms",    "form",      " | "),
    ("interactive.links",    "cta",       " | "),
    ("urls.internal",        "url",       " ; "),
    ("urls.external",        "extern_url"," ; "),
    ("urls.link",            "url",       " ; "),
    ("media.images",         "image",     " ; "),
    ("media.video",          "video",     " ; "),
    ("media.audio",          "audio",     " ; "),
    ("json_data",            "json",      " | "),
]


@dataclass
class PatternEmbeddingRow:
    """A single row destined for the ``PatternEmbedding`` Kuzu table."""

    embedding_id: str
    pattern_id: str
    version_id: str
    text_source: str
    embedding: np.ndarray
    created_at: str = ""


# ---------------------------------------------------------------------------
# Canonical text_source construction
# ---------------------------------------------------------------------------


def build_text_source(label: PatternLabelRow,
                      chunk: Chunk,
                      *,
                      max_values_per_field: int = 6,
                      max_value_len: int = 140) -> str:
    """
    Build the deterministic embedding input for one labeled pattern.

    Mirrors the handoff's format exactly: a one-line header with
    ``[role:...] [category:...] summary`` followed by category→values
    lines. Only categories actually present in the chunk's knowledge
    panel show up — no empty buckets.
    """
    header = f"[role:{label.role}] [category:{label.category}] {label.summary}".strip()
    lines = [header]

    # Emit known categories in canonical order first, novel ones alphabetical.
    seen_keys: set = set()
    fields = chunk.content_fields or {}

    for key, display, sep in _CANONICAL_FIELDS:
        if key in fields and fields[key]:
            seen_keys.add(key)
            vals = [_sanitize(v, max_value_len) for v in fields[key][:max_values_per_field]]
            vals = [v for v in vals if v]
            if vals:
                lines.append(f"{display}: {sep.join(vals)}")

    for key in sorted(fields.keys()):
        if key in seen_keys:
            continue
        vals = [_sanitize(v, max_value_len) for v in fields[key][:max_values_per_field]]
        vals = [v for v in vals if v]
        if not vals:
            continue
        # Unknown categories get their raw name as the display label.
        lines.append(f"{key}: {' | '.join(vals)}")

    return "\n".join(lines)


def _sanitize(text: str, limit: int) -> str:
    text = (text or "").replace("\n", " ").replace("\r", " ").strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(vec))
    if n <= 0.0:
        return vec
    return vec / n


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Plain cosine similarity; safe against zero-norm inputs."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Main embedder
# ---------------------------------------------------------------------------


class PatternEmbedder:
    """Turn ``PatternLabelRow`` + ``Chunk`` pairs into embedding rows."""

    def __init__(self, embedder: Optional[Any] = None, dim: int = NOMIC_DIM):
        self._embedder = embedder
        self.dim = int(dim)

    @property
    def embedder(self) -> Any:
        if self._embedder is None:
            from backend.services.embedding_service import EmbeddingService
            self._embedder = EmbeddingService()
        return self._embedder

    # -- public API ----------------------------------------------------

    def embed_labeled_patterns(
        self,
        built: BuiltTrie,
        chunks: List[Chunk],
        labels: List[PatternLabelRow],
    ) -> List[PatternEmbeddingRow]:
        """One embedding row per ``PatternLabelRow`` whose pattern is a chunk root.

        Labels whose ``pattern_id`` cannot be matched to a chunk are
        skipped — without a knowledge panel there is no stable text
        source to embed.
        """
        chunk_by_pattern: Dict[str, Chunk] = {c.pattern: c for c in chunks}
        patterns_by_id: Dict[str, PatternRow] = built.by_pattern_id

        texts: List[str] = []
        meta: List[Tuple[PatternLabelRow, Chunk]] = []

        for label in labels:
            pat = patterns_by_id.get(label.pattern_id)
            if pat is None:
                continue
            chunk = chunk_by_pattern.get(pat.pattern)
            if chunk is None:
                continue
            text = build_text_source(label, chunk)
            texts.append(text)
            meta.append((label, chunk))

        if not texts:
            return []

        matrix = self.embedder.embed_texts(texts)
        if matrix is None or getattr(matrix, "size", 0) == 0:
            logger.warning("Embedder returned no vectors for %d texts", len(texts))
            return []

        if matrix.shape[1] > self.dim:
            matrix = matrix[:, : self.dim]
        if matrix.shape[1] != self.dim:
            raise ValueError(
                f"Expected embedding dim {self.dim}, got {matrix.shape[1]}"
            )

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rows: List[PatternEmbeddingRow] = []
        for vec, (label, chunk), text in zip(matrix, meta, texts):
            rows.append(
                PatternEmbeddingRow(
                    embedding_id=_embedding_id(label.pattern_id, label.version_id),
                    pattern_id=label.pattern_id,
                    version_id=label.version_id,
                    text_source=text,
                    embedding=np.asarray(vec, dtype=np.float32),
                    created_at=now,
                )
            )
        return rows

    def embed_query(self, query: str) -> np.ndarray:
        vec = np.asarray(self.embedder.embed_query(query), dtype=np.float32)
        if vec.shape[0] > self.dim:
            vec = vec[: self.dim]
        return vec

    # -- retrieval utility --------------------------------------------

    def rank_patterns(
        self,
        query: str,
        rows: List[PatternEmbeddingRow],
        *,
        top_k: int = 5,
    ) -> List[Tuple[PatternEmbeddingRow, float]]:
        """Cosine-rank persisted patterns against a natural-language query.

        Returns ``[(row, similarity), ...]`` sorted descending. Simple
        brute force — fine for hundreds of patterns per page.
        """
        if not rows:
            return []
        q = self.embed_query(query)
        matrix = np.stack([r.embedding for r in rows]).astype(np.float32)
        # Normalize both sides and take a single dot product.
        q_norm = _l2_normalize(q)
        row_norms = np.linalg.norm(matrix, axis=1)
        safe = np.where(row_norms == 0.0, 1.0, row_norms)
        matrix_n = matrix / safe[:, None]
        sims = matrix_n @ q_norm
        order = np.argsort(-sims)
        out: List[Tuple[PatternEmbeddingRow, float]] = []
        for idx in order[:top_k]:
            out.append((rows[int(idx)], float(sims[int(idx)])))
        return out


def _embedding_id(pattern_id: str, version_id: str) -> str:
    return hashlib.sha1(f"emb|{version_id}|{pattern_id}".encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------------------------
# Kuzu persistence
# ---------------------------------------------------------------------------


def persist_pattern_embeddings(conn, rows: Iterable[PatternEmbeddingRow]) -> None:
    """Write embedding rows idempotently, keyed on ``(pattern_id, version_id)``.

    Kuzu's Python binding accepts ``list[float]`` for FLOAT[N] columns,
    so we convert the ndarray on the way in.
    """
    rows = list(rows)
    if not rows:
        return
    for row in rows:
        vec = row.embedding.tolist() if hasattr(row.embedding, "tolist") else list(row.embedding)
        conn.execute(
            "MATCH (e:PatternEmbedding {embedding_id: $eid}) DETACH DELETE e",
            parameters={"eid": row.embedding_id},
        )
        conn.execute(
            "CREATE (e:PatternEmbedding {"
            "embedding_id: $embedding_id, pattern_id: $pattern_id, "
            "version_id: $version_id, text_source: $text_source, "
            "embedding: $embedding, created_at: $created_at})",
            parameters={
                "embedding_id": row.embedding_id,
                "pattern_id": row.pattern_id,
                "version_id": row.version_id,
                "text_source": row.text_source,
                "embedding": vec,
                "created_at": row.created_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
        try:
            conn.execute(
                "MATCH (e:PatternEmbedding {embedding_id: $eid}), "
                "(t:TriePattern {pattern_id: $pid}) "
                "MERGE (e)-[:EMBEDDING_OF]->(t)",
                parameters={"eid": row.embedding_id, "pid": row.pattern_id},
            )
        except Exception:
            # Test schema may omit EMBEDDING_OF.
            pass


def load_pattern_embeddings(conn, version_id: str) -> List[PatternEmbeddingRow]:
    res = conn.execute(
        "MATCH (e:PatternEmbedding {version_id: $vid}) RETURN "
        "e.embedding_id, e.pattern_id, e.version_id, e.text_source, "
        "e.embedding, e.created_at",
        parameters={"vid": version_id},
    )
    out: List[PatternEmbeddingRow] = []
    while res.has_next():
        r = res.get_next()
        vec = np.asarray(r[4], dtype=np.float32)
        out.append(
            PatternEmbeddingRow(
                embedding_id=r[0],
                pattern_id=r[1],
                version_id=r[2],
                text_source=r[3] or "",
                embedding=vec,
                created_at=r[5] or "",
            )
        )
    return out
