"""Concept Index Service (Workstream W5; domain anchor §11.6, §8D.17,
§8D.23.1, §8D.43).

Sibling to ``layout_service`` on the chunk side. Holds, for each
ConceptNode in the unified Database:

  * ``embedding_nomic``     — nomic vector over the description field
                              (§8D.40 functional declaration).
  * ``embedding_tfidf``     — TF-IDF vector over the rendered_value
                              field (§8D.43 external frequency).
  * ``pagerank``            — PageRank score over the typed-edge graph
                              (§8D.23).
  * ``similar_to``          — top-K nomic-nearest neighbours (cache for
                              the apparition surface).
  * ``provenance``          — record source class (§9.12).

Triggers (§11.6):

  1. Card-edit settled cascade — re-embed the focal card.
  2. Edge added/removed — push-update PageRank along affected paths.
  3. Batch SIMILAR_TO pass — scheduled cadence over all embeddings.
  4. Manual ``/api/recompute_concept_index``.

The triple-product retrieval (§8D.43) reads from the cached
ConceptIndex at query time and is implemented in
``apparition_service`` (W6).

Like the Layout Service, this is intentionally light on dependencies
and decoupled from ``routes.py`` via a ``broadcast`` callable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SIMILAR_TO_THRESHOLD = 0.65  # cosine ≥ this → SIMILAR_TO edge
DEFAULT_SIMILAR_TO_K = 10            # top-K similar neighbours per card
DEFAULT_PAGERANK_DAMPING = 0.85
DEFAULT_PAGERANK_ITERATIONS = 30

# §11.6 — scheduled cadence for the batch SIMILAR_TO + PageRank pass.
# Set to ``0`` to disable; honoured via WFH_CONCEPT_INDEX_CADENCE_SEC.
_CADENCE_DEFAULT_SEC = 300.0  # 5 min — bounded re-cost; per-edit hooks
                              # still upsert eagerly, so this is the
                              # "stable" recompute that catches drift.

INDEX_PERSIST_DIR = os.environ.get(
    "WFH_CONCEPT_INDEX_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "kuzu_db")),
)


# ---------------------------------------------------------------------------
# Index slot
# ---------------------------------------------------------------------------

@dataclass
class ConceptIndexSlot:
    """Per-card index record (§11.6 ConceptIndex slot)."""

    card_id: str = ""
    embedding_nomic: Optional[List[float]] = None
    embedding_tfidf: Optional[List[float]] = None
    pagerank: float = 0.0
    similar_to: List[str] = field(default_factory=list)
    provenance: str = "user-authored"
    updated_at: float = 0.0
    # §8.1.1 multi-frequency lexical bands — parameter-free granularity views of
    # the card's text used by ApparitionService's band aggregation: the unigram
    # token set (paragraph-level lexical overlap) + the bigram set (phrase-level
    # overlap). Real IR signals (Jaccard), not fitted models; not broadcast.
    token_set: Optional[frozenset] = None
    bigram_set: Optional[frozenset] = None
    # §8.1.1 pattern frequency band — the structural pattern-hash bucket
    # (generalised-xpath hash) this card belongs to; "" for non-structural
    # cards. ApparitionService scores shared-bucket membership.
    pattern_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "embedding_nomic": self.embedding_nomic,
            "embedding_tfidf": self.embedding_tfidf,
            "pagerank": float(self.pagerank or 0.0),
            "similar_to": list(self.similar_to or []),
            "provenance": self.provenance,
            "updated_at": float(self.updated_at or 0.0),
        }

    def to_broadcast_dict(self) -> Dict[str, Any]:
        """Wire-shaped sub-payload for ``concept_index_update`` frames.

        Embedding vectors are *not* broadcast — they're large and the
        frontend doesn't need them; the frontend uses ``pagerank +
        similar_to + provenance`` to render apparition halos. The
        backend keeps the vectors locally and serves them through the
        triple-product retrieval endpoint (W6).
        """
        return {
            "pagerank": float(self.pagerank or 0.0),
            "similar_to": list(self.similar_to or []),
            "provenance": self.provenance,
        }


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

import re as _re_lex
_LEX_TOKEN_RE = _re_lex.compile(r"[a-z0-9]+")


def _lexical_sets(text: str):
    """§8.1.1 — build the (unigram token set, bigram set) for a card's text.

    Parameter-free granularity views (no fitted vectorizer): the unigram set
    is the paragraph-level lexical fingerprint; the bigram set is the
    phrase-level fingerprint. ApparitionService scores the phrase + paragraph
    frequency bands as Jaccard overlap over these sets.
    """
    if not text:
        return (frozenset(), frozenset())
    toks = [t for t in _LEX_TOKEN_RE.findall(str(text).lower()) if len(t) >= 2]
    uni = frozenset(toks)
    bi = frozenset(f"{toks[i]}_{toks[i + 1]}" for i in range(len(toks) - 1)) \
        if len(toks) > 1 else frozenset()
    return (uni, bi)


def pattern_hash_from_data(data: str) -> str:
    """§8.1.1 — the structural pattern-hash bucket for a card, from its data
    block's ``pattern`` (the generalised xpath the scanner assigns each
    chunk_instance). Returns ``""`` for cards with no structural pattern.
    ApparitionService's ``pattern`` frequency band scores shared-bucket
    membership (focal + candidate in the same structural family)."""
    if not data:
        return ""
    try:
        obj = json.loads(data)
    except Exception:
        return ""
    if not isinstance(obj, dict):
        return ""
    pat = obj.get("pattern") or obj.get("generalized_xpath") or ""
    if not pat or not isinstance(pat, str):
        return ""
    import hashlib as _hl
    return _hl.sha1(pat.encode("utf-8")).hexdigest()[:12]


def _cos(a: Optional[List[float]], b: Optional[List[float]]) -> float:
    """Cosine similarity with safe fallback. Missing vectors → 1.0
    (the multiplicative-identity per §8D.43, so the missing factor
    doesn't suppress retrieval; the user/agent gets *some* signal)."""
    if a is None or b is None:
        return 1.0
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    if va.size == 0 or vb.size == 0:
        return 1.0
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    dot = float(np.dot(va, vb))
    # Pad shorter to longer if dims differ (defensive — should not
    # happen in normal operation).
    if va.size != vb.size:
        m = min(va.size, vb.size)
        dot = float(np.dot(va[:m], vb[:m]))
    return max(0.0, min(1.0, dot / (na * nb)))


# ---------------------------------------------------------------------------
# Concept Index Service
# ---------------------------------------------------------------------------

class ConceptIndexService:
    """Persistent ConceptIndex with PageRank + SIMILAR_TO neighbours.

    Construct once at app boot; share across requests. The
    ``broadcast(snapshot_id, frame)`` hook (see routes.py's
    ``_ws_push``) lets the service emit ``concept_index_update``
    frames as slots change.
    """

    def __init__(
        self,
        broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
        graph_editor: Optional[Any] = None,
        similar_threshold: float = DEFAULT_SIMILAR_TO_THRESHOLD,
        similar_k: int = DEFAULT_SIMILAR_TO_K,
        pagerank_damping: float = DEFAULT_PAGERANK_DAMPING,
        pagerank_iterations: int = DEFAULT_PAGERANK_ITERATIONS,
    ):
        self._broadcast = broadcast
        self._graph_editor = graph_editor   # backend.services.graph_editor.GraphEditor
        self.similar_threshold = float(similar_threshold)
        self.similar_k = int(similar_k)
        self.pagerank_damping = float(pagerank_damping)
        self.pagerank_iterations = int(pagerank_iterations)

        # In-memory ConceptIndex per workspace.
        # Keys: workspace_id (str) -> { card_id -> ConceptIndexSlot }.
        self._index: Dict[str, Dict[str, ConceptIndexSlot]] = {}
        self._lock = threading.Lock()

        # Optional: lazy-import embedding service so callers without it
        # still get pagerank + similar_to (just no fresh embeddings).
        self._embedding_service = None

        # §11.6 — scheduled-cadence state. ``_dirty_workspaces`` tracks
        # which workspaces accumulated upserts/removes since the last
        # full recompute; the timer fires periodically and replays them.
        #
        # RLock — start_cadence/stop_cadence/_cadence_fire all acquire
        # this lock and call one another (start_cadence → stop_cadence
        # before re-arming). A plain Lock would deadlock there.
        self._dirty_workspaces: set = set()
        self._cadence_lock = threading.RLock()
        self._cadence_timer: Optional[threading.Timer] = None
        self._cadence_seconds: float = 0.0

        self._ensure_storage_dir()

    # -------------------------------------------------------------------
    # Persistence (mirrors layout_service pattern)
    # -------------------------------------------------------------------

    def _ensure_storage_dir(self) -> None:
        try:
            os.makedirs(INDEX_PERSIST_DIR, exist_ok=True)
        except Exception:
            pass

    def _index_path(self, workspace_id: str) -> str:
        safe = workspace_id.replace("/", "_").replace("\\", "_") or "_default"
        return os.path.join(INDEX_PERSIST_DIR, f"concept_index_{safe}.json")

    def load_index(self, workspace_id: str = "") -> Dict[str, ConceptIndexSlot]:
        path = self._index_path(workspace_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            slots: Dict[str, ConceptIndexSlot] = {}
            for cid, raw in (d or {}).items():
                slots[cid] = ConceptIndexSlot(
                    card_id=cid,
                    embedding_nomic=raw.get("embedding_nomic"),
                    embedding_tfidf=raw.get("embedding_tfidf"),
                    pagerank=float(raw.get("pagerank", 0.0)),
                    similar_to=list(raw.get("similar_to", [])),
                    provenance=raw.get("provenance", "user-authored"),
                    updated_at=float(raw.get("updated_at", 0.0)),
                )
            with self._lock:
                self._index[workspace_id] = slots
            return slots
        except Exception:
            return {}

    def save_index(self, workspace_id: str = "") -> bool:
        with self._lock:
            slots = self._index.get(workspace_id) or {}
            data = {cid: s.to_dict() for cid, s in slots.items()}
        try:
            with open(self._index_path(workspace_id), "w", encoding="utf-8") as f:
                json.dump(data, f)
            return True
        except Exception:
            return False

    def _get_workspace_index(self, workspace_id: str) -> Dict[str, ConceptIndexSlot]:
        with self._lock:
            wi = self._index.get(workspace_id)
        if wi is not None:
            return wi
        return self.load_index(workspace_id)

    # -------------------------------------------------------------------
    # Embedding access
    # -------------------------------------------------------------------

    def _get_embedding_service(self):
        if self._embedding_service is not None:
            return self._embedding_service
        try:
            from backend.services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
            return self._embedding_service
        except Exception:
            return None

    def _embed_description(self, text: str) -> Optional[List[float]]:
        """Nomic embedding over a description string (§8D.40)."""
        if not text:
            return None
        svc = self._get_embedding_service()
        if svc is None:
            return None
        try:
            v = svc.embed_query(text)
            if v is None:
                return None
            return [float(x) for x in v]
        except Exception:
            return None

    def _embed_rendered(self, text: str) -> Optional[List[float]]:
        """TF-IDF / external-frequency vector over rendered_value (§8D.43).

        W18 — real TF-IDF projection: tokenise via the same lexer
        the GlobalTfidfStore uses, look up IDF weights from the
        store, and project to a fixed-dim signed hash vector so
        every concept node's rendered_value vector has comparable
        shape across vocab growth. The cosine over these vectors is
        the canonical ``tfidf_cos`` factor in the triple product
        (§8D.43).

        Falls back to the nomic embedding only if the TF-IDF store
        is unavailable (e.g., test runs without a corpus).
        """
        if not text:
            return None
        try:
            v = self._tfidf_hash_vector(text)
            if v is not None:
                return v
        except Exception:
            pass
        # Fallback: dense nomic so the slot still has a vector to
        # contribute to scoring.
        svc = self._get_embedding_service()
        if svc is None:
            return None
        try:
            v = svc.embed_query(text)
            if v is None:
                return None
            return [float(x) for x in v]
        except Exception:
            return None

    # ----- W18 TF-IDF projection -----

    # Fixed projection dimension; matches Kuzu schema's FLOAT[1024].
    _TFIDF_PROJECTION_DIM = 1024

    def _tfidf_hash_vector(self, text: str) -> Optional[List[float]]:
        """Project a text into a fixed-dim signed-hash TF-IDF vector.

        Tokenises using the same lexer as ``global_tfidf_store._tokens``,
        looks up IDF weights from the live store, and hashes each
        token into a column of the projection. Signed hashing (sign
        bit from a second hash) gives un-correlated dimensions in
        expectation, so cosine similarity over the projected vectors
        approximates true TF-IDF cosine.

        Returns None when the store is unavailable (caller falls back
        to the nomic embedding).
        """
        try:
            from backend.services.global_tfidf_store import get_default_store, _tokens
        except Exception:
            return None
        try:
            store = get_default_store()
        except Exception:
            return None
        tokens = _tokens(text or "")
        if not tokens:
            return None
        # Get IDF cache from the store. The store rebuilds IDF lazily
        # on first ``search`` call; for our use we approximate IDF
        # with log(N / df + 1) using the store's df vector if exposed,
        # else use 1.0 (pure TF) as a graceful fallback.
        N = max(1, getattr(store, "doc_count", 0) or 1)
        df_array = None
        try:
            # Force the store to publish its df cache if not present.
            if hasattr(store, "_ensure_query_cache"):
                with store._lock:  # type: ignore
                    idf_arr, _ = store._ensure_query_cache()
                df_array = idf_arr  # already IDF, not raw df
        except Exception:
            df_array = None

        import math
        dim = int(self._TFIDF_PROJECTION_DIM)
        # Allocate ndarray for the hash projection.
        v = np.zeros(dim, dtype=np.float32)
        # Count term frequencies.
        tf_counts: Dict[str, int] = {}
        for t in tokens:
            tf_counts[t] = tf_counts.get(t, 0) + 1

        for tok, count in tf_counts.items():
            # IDF lookup. If the store's vocab knows this token,
            # use its stored IDF; otherwise approximate with log(N+1).
            idf = float(math.log(N + 1.0) + 1.0)
            if df_array is not None:
                col = None
                try:
                    col = store._vocab.get(tok)  # type: ignore
                except Exception:
                    col = None
                if col is not None and col < df_array.size:
                    idf = float(df_array[col]) or idf
            # Fix: deterministic signed-hash projection.
            # Python's built-in ``hash()`` is randomised per process
            # (PYTHONHASHSEED is randomised unless explicitly fixed),
            # which means TF-IDF vectors stored in process A are
            # NOT comparable to vectors built in process B. Use a
            # stable cryptographic hash (blake2b, 8 bytes) so the
            # projection is reproducible across process restarts.
            digest = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            h1 = int.from_bytes(digest, "big", signed=False)
            col_idx = (h1 & 0x7FFFFFFF) % dim
            sign = 1.0 if ((h1 >> 31) & 1) == 0 else -1.0
            v[col_idx] += sign * float(count) * idf

        # L2-normalise so cosine is just the dot product.
        norm = float(np.linalg.norm(v))
        if norm < 1e-12:
            return None
        v = v / norm
        return [float(x) for x in v]

    # -------------------------------------------------------------------
    # Slot mutation (the per-card update path called on every settled
    # compile cascade via the /api/concepts PATCH handler in W4)
    # -------------------------------------------------------------------

    def upsert_slot(
        self,
        card_id: str,
        *,
        description: str = "",
        rendering: str = "",
        provenance: str = "user-authored",
        workspace_id: str = "",
        embedding_nomic: Optional[List[float]] = None,
        embedding_tfidf: Optional[List[float]] = None,
        pattern_hash: str = "",
    ) -> ConceptIndexSlot:
        """Update or create the index slot for ``card_id``.

        If embeddings are not supplied, compute them from the
        description / rendering text via the embedding service.
        Returns the resulting slot.
        """
        # Compute embeddings if not provided.
        nomic = embedding_nomic if embedding_nomic is not None else self._embed_description(description)
        tfidf = embedding_tfidf if embedding_tfidf is not None else self._embed_rendered(rendering)
        # §8.1.1 — lexical band sets over the card's combined text (the phrase +
        # paragraph frequency bands score Jaccard overlap of these).
        token_set, bigram_set = _lexical_sets(
            f"{description or ''} {rendering or ''}".strip()
        )
        with self._lock:
            wi = self._index.setdefault(workspace_id, {})
            existing = wi.get(card_id)
            if existing is None:
                slot = ConceptIndexSlot(
                    card_id=card_id,
                    embedding_nomic=nomic,
                    embedding_tfidf=tfidf,
                    pagerank=0.0,
                    similar_to=[],
                    provenance=provenance,
                    updated_at=time.time(),
                    token_set=token_set,
                    bigram_set=bigram_set,
                    pattern_hash=pattern_hash or "",
                )
                wi[card_id] = slot
            else:
                if nomic is not None:
                    existing.embedding_nomic = nomic
                if tfidf is not None:
                    existing.embedding_tfidf = tfidf
                if token_set:
                    existing.token_set = token_set
                if bigram_set:
                    existing.bigram_set = bigram_set
                if pattern_hash:
                    existing.pattern_hash = pattern_hash
                existing.provenance = provenance or existing.provenance
                existing.updated_at = time.time()
                slot = existing
        # Broadcast incremental update + mark the workspace dirty so
        # the scheduled cadence (§11.6) picks up this edit on its next
        # batch pass without us having to drive recompute eagerly.
        self._broadcast_updates(workspace_id, {card_id: slot})
        with self._cadence_lock:
            self._dirty_workspaces.add(workspace_id)
        return slot

    def remove_slot(self, card_id: str, workspace_id: str = "") -> bool:
        with self._lock:
            wi = self._index.get(workspace_id) or {}
            existed = card_id in wi
            wi.pop(card_id, None)
        if existed:
            self._broadcast_removed(workspace_id, [card_id])
            with self._cadence_lock:
                self._dirty_workspaces.add(workspace_id)
        return existed

    def get_slot(self, card_id: str, workspace_id: str = "") -> Optional[ConceptIndexSlot]:
        wi = self._get_workspace_index(workspace_id)
        return wi.get(card_id)

    def list_slots(self, workspace_id: str = "") -> Dict[str, ConceptIndexSlot]:
        return self._get_workspace_index(workspace_id)

    def band_idf(self, workspace_id: str = "") -> Dict[str, Dict[str, float]]:
        """§8.1.1 — inverse-document-frequency weights for the lexical bands.

        Returns ``{"token": {tok: idf}, "bigram": {bg: idf}}`` over the
        workspace's slot ``token_set`` / ``bigram_set`` fingerprints, with the
        smoothed ``idf = ln((N + 1) / (df + 1)) + 1``. ApparitionService's
        phrase/paragraph bands use these so a *rare* shared token/bigram counts
        more than a ubiquitous one (a real IDF-weighted Jaccard). Cached per
        workspace, invalidated when the slot count changes (cheap heuristic)."""
        import math as _math
        wi = self._get_workspace_index(workspace_id)
        n = len(wi)
        cache = getattr(self, "_band_idf_cache", None)
        if cache is None:
            cache = self._band_idf_cache = {}
        prev = cache.get(workspace_id)
        if prev is not None and prev[0] == n:
            return prev[1]
        tok_df: Dict[str, int] = {}
        big_df: Dict[str, int] = {}
        for slot in wi.values():
            for t in (slot.token_set or ()):
                tok_df[t] = tok_df.get(t, 0) + 1
            for b in (slot.bigram_set or ()):
                big_df[b] = big_df.get(b, 0) + 1
        nf = float(n)
        tok_idf = {t: _math.log((nf + 1.0) / (df + 1.0)) + 1.0 for t, df in tok_df.items()}
        big_idf = {b: _math.log((nf + 1.0) / (df + 1.0)) + 1.0 for b, df in big_df.items()}
        out = {"token": tok_idf, "bigram": big_idf}
        cache[workspace_id] = (n, out)
        return out

    # -------------------------------------------------------------------
    # SIMILAR_TO and PageRank (§8D.23, §11.6 batch triggers)
    # -------------------------------------------------------------------

    def recompute_similar_to(self, workspace_id: str = "") -> int:
        """Recompute SIMILAR_TO neighbour lists across the workspace.

        For each card, find top-K nomic-nearest others above the
        configured threshold. Updates ``slot.similar_to`` in place.
        Returns the number of cards whose neighbour list changed.
        """
        wi = self._get_workspace_index(workspace_id)
        if not wi:
            return 0
        # Snapshot ids and embeddings.
        ids = []
        embs = []
        for cid, slot in wi.items():
            if slot.embedding_nomic is None:
                continue
            ids.append(cid)
            embs.append(slot.embedding_nomic)
        if len(ids) < 2:
            return 0
        # Build the cosine matrix (full pairwise — fine for K up to a
        # few thousand cards; revisit with FAISS / approximate NN if
        # the workspace grows past that).
        M = np.array(embs, dtype=np.float32)
        norms = np.linalg.norm(M, axis=1, keepdims=True).clip(min=1e-12)
        Mn = M / norms
        sim = Mn @ Mn.T  # cosine matrix (since rows are unit-normalised)
        changed = 0
        changed_ids: List[str] = []
        for i, cid in enumerate(ids):
            row = sim[i].copy()
            row[i] = -1.0  # exclude self
            order = np.argsort(-row)
            picks = []
            for j in order[: self.similar_k * 2]:
                if row[j] < self.similar_threshold:
                    break
                picks.append(ids[j])
                if len(picks) >= self.similar_k:
                    break
            slot = wi[cid]
            if picks != slot.similar_to:
                slot.similar_to = picks
                changed += 1
                changed_ids.append(cid)
        # Broadcast a single update frame carrying all changed slots.
        if changed_ids:
            self._broadcast_updates(
                workspace_id,
                {cid: wi[cid] for cid in changed_ids},
            )
        return changed

    def recompute_pagerank(self, workspace_id: str = "") -> int:
        """Recompute PageRank over the typed-edge graph.

        Edges come from the graph_editor (if injected) — both
        explicit user/agent wirings and the batch SIMILAR_TO edges
        we maintain in ``slot.similar_to``. Returns the number of
        cards whose pagerank value changed by more than 1e-6.
        """
        wi = self._get_workspace_index(workspace_id)
        if not wi:
            return 0
        ids = list(wi.keys())
        n = len(ids)
        idx_of = {cid: i for i, cid in enumerate(ids)}
        # Build adjacency from SIMILAR_TO + explicit edges (if available).
        adj: List[List[int]] = [[] for _ in range(n)]
        for i, cid in enumerate(ids):
            slot = wi[cid]
            for tgt in (slot.similar_to or []):
                ti = idx_of.get(tgt)
                if ti is not None and ti != i:
                    adj[i].append(ti)
        # Pull explicit edges if graph_editor is wired.
        if self._graph_editor is not None:
            try:
                edges = self._graph_editor.list_concept_edges(
                    workspace_id=workspace_id, limit=100000,
                )
                for e in edges:
                    si = idx_of.get(e.source_id)
                    ti = idx_of.get(e.target_id)
                    if si is not None and ti is not None and si != ti:
                        adj[si].append(ti)
            except Exception:
                pass

        # Random-walk PageRank with damping.
        damp = self.pagerank_damping
        pr = np.ones(n, dtype=np.float32) / max(1, n)
        out_count = np.array([max(1, len(a)) for a in adj], dtype=np.float32)
        for _ in range(self.pagerank_iterations):
            pr_new = (1 - damp) / max(1, n) * np.ones(n, dtype=np.float32)
            for i, neighbors in enumerate(adj):
                share = damp * pr[i] / out_count[i] if neighbors else 0.0
                for j in neighbors:
                    pr_new[j] += share
            pr = pr_new

        # Write back, count changes.
        changed = 0
        changed_ids: List[str] = []
        with self._lock:
            for i, cid in enumerate(ids):
                slot = wi[cid]
                new_val = float(pr[i])
                if abs(slot.pagerank - new_val) > 1e-6:
                    slot.pagerank = new_val
                    slot.updated_at = time.time()
                    changed += 1
                    changed_ids.append(cid)
        if changed_ids:
            self._broadcast_updates(
                workspace_id,
                {cid: wi[cid] for cid in changed_ids},
            )
        return changed

    def recompute_all(self, workspace_id: str = "") -> Dict[str, int]:
        """Run the full scheduled pass: SIMILAR_TO + PageRank + save."""
        sim_changed = self.recompute_similar_to(workspace_id)
        pr_changed = self.recompute_pagerank(workspace_id)
        self.save_index(workspace_id)
        # The cadence tracks pending edits per workspace; once a full
        # recompute has run, the workspace is clean again.
        with self._cadence_lock:
            self._dirty_workspaces.discard(workspace_id)
        return {"similar_to_changed": sim_changed, "pagerank_changed": pr_changed}

    # -------------------------------------------------------------------
    # §11.6 — scheduled cadence
    # -------------------------------------------------------------------

    def start_cadence(self, interval_seconds: float = _CADENCE_DEFAULT_SEC) -> None:
        """Begin the scheduled batch recompute (§11.6).

        Per-edit hooks (``upsert_slot`` / ``remove_slot``) update each
        slot eagerly; the scheduled pass catches second-order drift:
        SIMILAR_TO neighbour shifts as embeddings move, PageRank ripple
        as edges accumulate, and the periodic on-disk save that lets
        the index survive process restart.

        ``interval_seconds <= 0`` disables; safe to call repeatedly
        (idempotent — restarts only if the interval changed).
        """
        seconds = float(interval_seconds)
        with self._cadence_lock:
            if self._cadence_timer is not None and seconds == self._cadence_seconds:
                return  # already running at this interval
            self.stop_cadence()
            if seconds <= 0:
                return
            self._cadence_seconds = seconds
            self._arm_cadence_timer()

    def stop_cadence(self) -> None:
        with self._cadence_lock:
            if self._cadence_timer is not None:
                try:
                    self._cadence_timer.cancel()
                except Exception:
                    pass
                self._cadence_timer = None

    def _arm_cadence_timer(self) -> None:
        if self._cadence_seconds <= 0:
            return
        t = threading.Timer(self._cadence_seconds, self._cadence_fire)
        t.daemon = True
        self._cadence_timer = t
        t.start()

    def _cadence_fire(self) -> None:
        """Run a recompute pass over each dirty workspace, then re-arm."""
        try:
            with self._cadence_lock:
                pending = list(self._dirty_workspaces)
            for ws in pending:
                try:
                    self.recompute_all(workspace_id=ws)
                except Exception as e:
                    logger.warning("ConceptIndex cadence recompute_all(ws=%r) failed: %s",
                                   ws, e)
        finally:
            with self._cadence_lock:
                # Re-arm only if cadence is still active (start_cadence
                # may have been called with 0 to disable).
                if self._cadence_seconds > 0:
                    self._arm_cadence_timer()

    # -------------------------------------------------------------------
    # Broadcast
    # -------------------------------------------------------------------

    def _broadcast_updates(
        self,
        workspace_id: str,
        slots: Dict[str, ConceptIndexSlot],
    ) -> None:
        if self._broadcast is None or not slots:
            return
        from backend.api.ws_frames import build_concept_index_update
        payload = build_concept_index_update(
            workspace_id=workspace_id or "_default",
            updates={cid: slot.to_broadcast_dict() for cid, slot in slots.items()},
        )
        # No specific snapshot_id for concept-index broadcasts; emit on
        # the magic "0" slot which the WS handler can route as a
        # workspace-wide channel. routes.py treats unmatched
        # snapshot_ids as drops, so this is best-effort.
        try:
            self._broadcast(0, payload)
        except Exception:
            pass

    def _broadcast_removed(self, workspace_id: str, ids: List[str]) -> None:
        if self._broadcast is None or not ids:
            return
        from backend.api.ws_frames import build_concept_index_update
        payload = build_concept_index_update(
            workspace_id=workspace_id or "_default",
            updates={},
            removed_ids=list(ids),
        )
        try:
            self._broadcast(0, payload)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_SVC: Optional[ConceptIndexService] = None
_SVC_LOCK = threading.Lock()


def get_concept_index_service(
    broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    graph_editor: Optional[Any] = None,
) -> ConceptIndexService:
    """Process-wide singleton for the Concept Index Service.

    First-caller pattern: subsequent fetches without args reuse the
    existing instance. New broadcast or graph_editor hooks update the
    cached singleton in place so late-binding wiring works.
    """
    global _SVC
    with _SVC_LOCK:
        if _SVC is None:
            _SVC = ConceptIndexService(broadcast=broadcast, graph_editor=graph_editor)
            # §11.6 — start the scheduled SIMILAR_TO + PageRank cadence
            # the moment the singleton is born. Honours the env override
            # so deployments can tune it (set to 0 to disable entirely).
            try:
                env_sec = os.environ.get("WFH_CONCEPT_INDEX_CADENCE_SEC")
                interval = float(env_sec) if env_sec is not None else _CADENCE_DEFAULT_SEC
                _SVC.start_cadence(interval)
            except Exception:
                _SVC.start_cadence(_CADENCE_DEFAULT_SEC)
        else:
            if broadcast is not None and _SVC._broadcast is None:
                _SVC._broadcast = broadcast
            if graph_editor is not None and _SVC._graph_editor is None:
                _SVC._graph_editor = graph_editor
    return _SVC
