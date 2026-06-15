"""Apparition Service (Workstream W6; domain anchor §8D.16, §8D.22,
§8D.36, §8D.43).

Implements the triple-product apparition retrieval over the unified
Concept Index. Score for a candidate against a focal concept node:

    score = pagerank(candidate)
          · tfidf_cos(focal.rendered, candidate.rendered)
          · nomic_cos(focal.description, candidate.description)

Missing factors default to 1.0 (multiplicative identity per §8D.43)
so partial-signal cards still surface. The product semantics mean
candidates must score well across all three axes to rank high.

Five navigation modes (§8D.36):

  1. hover apparitions on a stuck card — focal = the hovered node
  2. empty-primitive radiation         — focal = an empty card with
                                          typed text in description
  3. DB-ontology recursion             — focal = a typed-graph node
                                          (Database, Module, etc.);
                                          structural edges dominate
  4. meta-cognition node retrieval     — focal = the node's local
                                          subgraph centroid (W10)
  5. closest-inverse function lookup   — focal = the desired output
                                          (§8D.7); inverse direction

All five share the scoring function; they differ only in *what is
the focal* and *which structural edges dominate*.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Score record
# ---------------------------------------------------------------------------

@dataclass
class ApparitionCandidate:
    card_id: str
    score: float
    pagerank: float
    tfidf_cos: float
    nomic_cos: float
    provenance: str = ""
    # §8D.1.3 compact representation: the halo phantom displays ONLY
    # the candidate's name (no score chip, no description preview).
    # We carry the name in the candidate dict so the frontend (and the
    # REPL viewer) can render the halo without a second concept-fetch.
    name: str = ""
    # §O.18 — cone-ray transport scalars for the 3D projector. radial +
    # along_ray derive from normalized similarity (closer-on-cone == more
    # similar); angular is camera-computed on the client (along the cone
    # surface normal). None when transport wasn't requested.
    transport: Optional[Dict[str, float]] = None
    # §8.1.1 / ConceptEdge.md SoftLink §2.2 — per-frequency-band scores when
    # the service is in multi-frequency mode (None in single-frequency mode).
    band_scores: Optional[Dict[str, float]] = None
    # §8.2.1.1 — True when this candidate was added by the ray-projection
    # coupling (a manifold-nearest projector chunk), not the triple-product
    # apparition search. Lets the halo render it as a ray-projected phantom.
    ray_projected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cos(a: Optional[List[float]], b: Optional[List[float]]) -> float:
    """Cosine similarity with multiplicative-identity fallback (§8D.43)."""
    if a is None or b is None:
        return 1.0
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    if va.size == 0 or vb.size == 0:
        return 1.0
    if va.size != vb.size:
        m = min(va.size, vb.size)
        va = va[:m]
        vb = vb[:m]
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return max(0.0, min(1.0, float(np.dot(va, vb)) / (na * nb)))


def _minmax(vals: List[float]) -> List[float]:
    """Min-max normalize a cosine list to [0,1] over its own space (§O.22).

    Independent cosine spaces sit at biased scales, so each axis must be
    normalized to [0,1] over its own distribution BEFORE the two are combined
    via max(). A flat list (all equal) maps to neutral 1.0.
    """
    if not vals:
        return []
    lo = min(vals)
    hi = max(vals)
    if hi - lo < 1e-12:
        return [1.0 for _ in vals]
    return [(v - lo) / (hi - lo) for v in vals]


def _jaccard(a, b, idf: Optional[Dict[str, float]] = None) -> float:
    """Jaccard overlap of two token/bigram sets (real IR). With an ``idf`` map
    it is the **IDF-weighted** Jaccard — a rare shared term contributes more
    than a ubiquitous one: ``Σ idf[t∈A∩B] / Σ idf[t∈A∪B]`` (terms absent from
    the map default to weight 1.0). Without ``idf`` it is the plain set
    overlap ``|A∩B| / |A∪B|``."""
    if not a or not b:
        return 0.0
    inter = a & b
    if not inter:
        return 0.0
    union = a | b
    if idf:
        wi = sum(idf.get(x, 1.0) for x in inter)
        wu = sum(idf.get(x, 1.0) for x in union)
        return (wi / wu) if wu > 0 else 0.0
    return len(inter) / float(len(union))


def _band_signals(
    tcos: float, ncos: float,
    phrase: Optional[float] = None, paragraph: Optional[float] = None,
    pattern: Optional[float] = None,
) -> Dict[str, float]:
    """§8.1.1 — per-frequency-band similarity signals for one candidate.

    The five bands are distinct granularity views of the card's content:
      * token     — term-level TF-IDF content cosine (``tcos``).
      * phrase    — bigram-set Jaccard (``phrase`` when the ConceptIndex slots
                    carry lexical bigram sets; else the token/document blend).
      * paragraph — unigram-token-set Jaccard (``paragraph`` likewise).
      * document  — document-level nomic semantic cosine (``ncos``).
      * pattern   — structural co-occurrence of content + semantics.
    The phrase/paragraph bands are REAL lexical signals (Jaccard over the slot
    token/bigram sets — no fitted model, no mock); they fall back to the
    geometric blend only when a slot predates the lexical-set upsert.
    """
    import math as _math
    t = max(0.0, float(tcos))
    n = max(0.0, float(ncos))
    blend = _math.sqrt(t * n)
    return {
        "token": t,
        "phrase": float(phrase) if phrase is not None else blend,
        "paragraph": float(paragraph) if paragraph is not None else blend,
        "document": n,
        # pattern band: literal shared-bucket membership when both cards carry
        # a structural pattern-hash (1.0 same family / 0.0 different); else the
        # content×semantic co-occurrence proxy for non-structural cards.
        "pattern": float(pattern) if pattern is not None else (t * n),
    }


def _multi_freq_modulation(
    band_signals: Dict[str, float], band_weights: Dict[str, float],
) -> float:
    """§8.1.1 — the band-weighted modulation factor for multi-frequency mode.

    ``M = weighted_avg(band_signals; band_weights) / flat_avg(band_signals)``.
    By construction **M = 1.0 when the band weights are flat**, so the
    multi-frequency score reduces EXACTLY to the single-frequency triple product
    until observed-utility events tilt a band — bands that produced more
    user-confirmed surfacings count for more (§8.1.1). Clamped to a gentle range
    so a heavily-weighted band tilts the ranking without inverting it.
    """
    bands = list(band_signals.keys())
    if not bands:
        return 1.0
    wsum = sum(float(band_weights.get(b, 1.0)) for b in bands)
    if wsum <= 0:
        return 1.0
    weighted = sum(float(band_weights.get(b, 1.0)) * band_signals[b] for b in bands) / wsum
    flat = sum(band_signals[b] for b in bands) / len(bands)
    if flat <= 1e-9:
        return 1.0
    m = weighted / flat
    return max(0.25, min(4.0, m))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

# §8.1.1 multi-frequency aggregation thresholds. Per
# ``docs/code_constraints/backend_services.md`` §1.9 + anti-goal §18.25,
# the service transitions from single-frequency (PageRank only) to
# multi-frequency (token + phrase + paragraph + document + pattern
# bands) once K=32 observed-utility events accumulate. ``get_mode()``
# reports the active mode for the frontend pin-chrome to render and
# for env-scenarios to assert.
MULTI_FREQUENCY_TRANSITION_THRESHOLD = 32

# The five frequency bands per §8.1.1. Each band carries its own
# TF-IDF projection (token-level vocabulary, phrase n-grams, paragraph
# centroids, document-level summaries, pattern-hash buckets). The
# multi-frequency aggregator weights them by their cumulative observed
# utility — bands that have produced more user-confirmed surfacings
# count for more in the next ranking.
FREQUENCY_BANDS = ("token", "phrase", "paragraph", "document", "pattern")


class ApparitionService:
    """Stateless query service over the Concept Index + Graph Editor.

    Per ``docs/object_model/ApparitionService.md`` + §1.9 must-hold:
    reports active mode (single-frequency vs multi-frequency) via
    ``get_mode()``. After K=32 observed-utility events the service
    transitions to multi-frequency aggregation across the five bands
    in :data:`FREQUENCY_BANDS`.
    """

    def __init__(self, concept_index=None, graph_editor=None):
        self._concept_index = concept_index
        self._graph_editor = graph_editor
        # §1.9 mode tracking: count observed utility events; transition
        # automatically once the threshold is reached.
        self._observed_utility_events: int = 0
        # Per-band cumulative utility weights; updated each time
        # ``record_utility_event`` is called with the band the surfaced
        # candidate came from. Initialised flat so an early multi-freq
        # query still produces a meaningful ranking.
        self._band_weights: Dict[str, float] = {b: 1.0 for b in FREQUENCY_BANDS}

    # -------------------------------------------------------------------
    # §1.9 mode reporting + utility-event recording
    # -------------------------------------------------------------------

    def get_mode(self) -> Dict[str, Any]:
        """Report the active ranking mode.

        Returns ``{"mode", "events", "threshold", "bands",
        "band_weights"}``. Pinned panels and env-scenarios read this to
        verify the §1.9 contract (anti-goal §18.25 — single-frequency
        PageRank persisting after the threshold).
        """
        mode = (
            "multi_frequency"
            if self._observed_utility_events >= MULTI_FREQUENCY_TRANSITION_THRESHOLD
            else "single_frequency"
        )
        return {
            "mode": mode,
            "events": int(self._observed_utility_events),
            "threshold": int(MULTI_FREQUENCY_TRANSITION_THRESHOLD),
            "bands": list(FREQUENCY_BANDS),
            "band_weights": dict(self._band_weights),
        }

    def record_utility_event(self, band: str = "token", weight: float = 1.0) -> None:
        """Record one observed-utility event for the given band.

        Called by the lifecycle dispatcher each time a surfaced halo
        candidate is committed (soft → hard link) or otherwise marks
        itself as useful (pin, compile, autoregressive walk). Drives
        the §1.9 mode transition + band-weight aggregation.
        """
        self._observed_utility_events += 1
        if band in self._band_weights:
            self._band_weights[band] = float(self._band_weights[band]) + float(weight)

    def reset_utility_events(self) -> None:
        """Reset the event counter (test/REPL hook; production purge
        uses the workspace purge path which constructs a fresh service).
        """
        self._observed_utility_events = 0
        self._band_weights = {b: 1.0 for b in FREQUENCY_BANDS}

    def rebind(self, *, concept_index=None, graph_editor=None) -> None:
        """Rebind the index + graph_editor references without losing
        per-process state (event counter, band weights).

        Lets ``get_apparition_service`` keep singleton semantics while
        also handling lazy late-binding when the concept index isn't
        ready at first call. The §1.9 utility-event counter survives
        rebinds — only an explicit ``reset_utility_events`` zeroes it.
        """
        if concept_index is not None:
            self._concept_index = concept_index
        if graph_editor is not None:
            self._graph_editor = graph_editor

    # §8D.1.3 compact-representation contract: halos display ONLY the
    # name. We resolve names from card_ids via the graph_editor at
    # candidate construction time so the response is self-contained
    # and the frontend (and REPL viewer) need no second fetch.
    def _name_for(self, card_id: str) -> str:
        if not self._graph_editor or not card_id:
            return ""
        try:
            node = self._graph_editor.get_concept(card_id)
            return (getattr(node, "name", "") or "") if node else ""
        except Exception:
            return ""

    # -------------------------------------------------------------------
    # Mode 1 — focal-centric apparition retrieval
    # -------------------------------------------------------------------

    def _is_panel_focal(self, focal_id: str, workspace_id: str = "") -> bool:
        """True if ``focal_id`` is an AGGREGATE panel (multi-field) rather than a
        singular-primitive node (§O.19). Panels score via the §O.22 deviation;
        singular nodes via the separated-axes triple product (§8.1)."""
        if not self._graph_editor or not focal_id:
            return False
        try:
            node = self._graph_editor.get_concept(focal_id)
            if not node:
                return False
            data = (getattr(node, "data", "") or "").strip()
            if not data:
                return False
            import json as _json
            try:
                obj = _json.loads(data)
                return isinstance(obj, dict) and len(obj) > 1
            except Exception:
                # Non-JSON indent-tree: ≥2 structural lines reads as a panel.
                return data.count("\n") >= 2
        except Exception:
            return False

    def apparitions_for_focal(
        self,
        focal_id: str,
        *,
        workspace_id: str = "",
        k: int = 10,
        exclude_self: bool = True,
        min_score: float = 0.0,
        ray_project: bool = False,
    ) -> List[ApparitionCandidate]:
        """Top-K candidates against ``focal_id``.

        Singular-primitive focal (§O.19) → separated-axes triple product
        ``pagerank · tfidf_cos · nomic_cos`` (§8.1 / §8D.43). Panel focal → the
        §O.22 deviation ``pagerank · max(minmax(nomic), minmax(tfidf))``, each
        cosine min-max normalized to [0,1] over its own space first.

        ``ray_project`` (§8.2.1.1) augments the result with the
        **manifold-nearest projector chunks** — the cards closest to the focal
        in the LayoutService 6D-UMAP manifold — appended as ray-projected
        soft-links (deduped against the triple-product set). This couples the
        imaginary's retrieval halo to the real's 3D manifold geometry.
        """
        if self._concept_index is None:
            return []
        focal_slot = self._concept_index.get_slot(focal_id, workspace_id)
        if focal_slot is None:
            return []
        all_slots = self._concept_index.list_slots(workspace_id)
        is_panel = self._is_panel_focal(focal_id, workspace_id)
        # Pass 1 — collect per-candidate cosines, with the §8D.1.3 name-guard
        # (a slot resolving to no name is never a valid halo candidate).
        rows = []  # (cid, slot, pr, tcos, ncos, name)
        for cid, slot in all_slots.items():
            if exclude_self and cid == focal_id:
                continue
            name = self._name_for(cid)
            if not (name or "").strip():
                continue
            pr = float(slot.pagerank or 1.0)
            if pr <= 0:
                pr = 1.0  # multiplicative identity
            tcos = _cos(focal_slot.embedding_tfidf, slot.embedding_tfidf)
            ncos = _cos(focal_slot.embedding_nomic, slot.embedding_nomic)
            rows.append((cid, slot, pr, tcos, ncos, name))
        if not rows:
            return []
        # Pass 2 — score per focal kind.
        if is_panel:
            T = _minmax([r[3] for r in rows])
            N = _minmax([r[4] for r in rows])
            scores = [rows[i][2] * max(N[i], T[i]) for i in range(len(rows))]
        else:
            scores = [r[2] * r[3] * r[4] for r in rows]
        # §8.1.1 — multi-frequency band aggregation once K=32 observed-utility
        # events accrue (anti-goal §18.25 — single-frequency PageRank must NOT
        # persist past the threshold). The modulation M reduces to 1.0 at flat
        # band weights, so single-frequency mode is bit-for-bit unchanged; a
        # band that has produced more user-confirmed surfacings re-weights the
        # ranking toward its granularity.
        mode_info = self.get_mode()
        multi = (mode_info.get("mode") == "multi_frequency")
        band_weights = mode_info.get("band_weights") or {}
        per_band: List[Optional[Dict[str, float]]] = [None] * len(rows)
        if multi:
            f_tok = getattr(focal_slot, "token_set", None)
            f_big = getattr(focal_slot, "bigram_set", None)
            f_pat = getattr(focal_slot, "pattern_hash", "") or ""
            # §8.1.1 — IDF weights so a rare shared token/bigram counts more in
            # the phrase/paragraph Jaccard than a ubiquitous one.
            tok_idf = big_idf = None
            try:
                _idf = self._concept_index.band_idf(workspace_id)
                tok_idf, big_idf = _idf.get("token"), _idf.get("bigram")
            except Exception:
                tok_idf = big_idf = None
            tilted: List[float] = []
            for i, (cid, slot, pr, tcos, ncos, name) in enumerate(rows):
                # Real lexical band signals: phrase = bigram-set Jaccard,
                # paragraph = unigram-token-set Jaccard (None ⇒ blend fallback),
                # both IDF-weighted.
                c_tok = getattr(slot, "token_set", None)
                c_big = getattr(slot, "bigram_set", None)
                phrase = _jaccard(f_big, c_big, big_idf) if (f_big and c_big) else None
                paragraph = _jaccard(f_tok, c_tok, tok_idf) if (f_tok and c_tok) else None
                # Pattern band = literal shared-bucket membership when BOTH
                # cards carry a structural pattern-hash; else None ⇒ the
                # co-occurrence proxy (non-structural cards aren't penalised).
                c_pat = getattr(slot, "pattern_hash", "") or ""
                pattern = (1.0 if f_pat == c_pat else 0.0) if (f_pat and c_pat) else None
                bs = _band_signals(tcos, ncos, phrase=phrase, paragraph=paragraph,
                                   pattern=pattern)
                per_band[i] = bs
                tilted.append(scores[i] * _multi_freq_modulation(bs, band_weights))
            scores = tilted
        results: List[ApparitionCandidate] = []
        for i, ((cid, slot, pr, tcos, ncos, name), score) in enumerate(zip(rows, scores)):
            if score < min_score:
                continue
            results.append(ApparitionCandidate(
                card_id=cid,
                score=float(score),
                pagerank=float(slot.pagerank or 0.0),
                tfidf_cos=float(tcos),
                nomic_cos=float(ncos),
                provenance=slot.provenance,
                name=name,
                band_scores=per_band[i],
            ))
        results.sort(key=lambda r: r.score, reverse=True)
        results = results[: max(0, int(k))]
        # §8.2.1.1 — ray-projection coupling: augment the triple-product halo
        # with the manifold-nearest projector chunks (deduped), appended as
        # ray-projected soft-links.
        if ray_project:
            have = {r.card_id for r in results}
            for c in self.manifold_nearest(focal_id, workspace_id=workspace_id, k=k):
                if c.card_id not in have:
                    results.append(c)
                    have.add(c.card_id)
        return results

    def manifold_nearest(
        self, focal_id: str, *, workspace_id: str = "", k: int = 6,
    ) -> List[ApparitionCandidate]:
        """§8.2.1.1 — the focal's manifold-nearest cards in the LayoutService
        6D-UMAP frame (Euclidean over the 3 position dims). Returned as
        ray-projected ``ApparitionCandidate``s whose ``transport`` places them
        on the §O.18 cone by manifold proximity (nearest ⇒ apex). Empty when no
        layout frame / focal coords exist (graceful — the halo just shows the
        triple-product set)."""
        try:
            from backend.services.layout_service import get_layout_service
            frame = get_layout_service().get_frame(workspace_id)
        except Exception:
            frame = None
        if frame is None or not getattr(frame, "coords", None):
            return []
        fc = frame.coords.get(focal_id)
        if not fc or len(fc) < 3:
            return []
        fx, fy, fz = float(fc[0]), float(fc[1]), float(fc[2])
        dists: List[tuple] = []
        for cid, c in frame.coords.items():
            if cid == focal_id or not c or len(c) < 3:
                continue
            dx, dy, dz = float(c[0]) - fx, float(c[1]) - fy, float(c[2]) - fz
            dists.append((cid, (dx * dx + dy * dy + dz * dz) ** 0.5))
        if not dists:
            return []
        dists.sort(key=lambda t: t[1])
        near = dists[: max(0, int(k))]
        maxd = max((d for _, d in near), default=0.0) or 1.0
        out: List[ApparitionCandidate] = []
        for cid, d in near:
            sim = max(0.0, min(1.0, 1.0 - d / maxd)) if maxd > 0 else 1.0
            out.append(ApparitionCandidate(
                card_id=cid, score=float(sim), pagerank=0.0,
                tfidf_cos=0.0, nomic_cos=0.0, provenance="ray-projected",
                name=self._name_for(cid),
                transport={"similarity": sim,
                           "radial": (1.0 - sim) * 40.0,
                           "along_ray": sim * 40.0},
                ray_projected=True,
            ))
        return out

    # -------------------------------------------------------------------
    # Mode 2 — empty-primitive radiation over typed text
    # -------------------------------------------------------------------

    def radiation_for_text(
        self,
        text: str,
        *,
        workspace_id: str = "",
        k: int = 10,
        min_score: float = 0.0,
    ) -> List[ApparitionCandidate]:
        """Top-K candidates for an empty card's typed text (no real focal yet).

        Treats the typed text as a synthetic description: embed via
        nomic, score every workspace card by triple product (with
        tfidf_cos defaulting to 1.0 since the empty has no rendered
        value yet).
        """
        if self._concept_index is None:
            return []
        # Embed the typed text as a synthetic description.
        nomic_vec = None
        try:
            svc = self._concept_index._get_embedding_service()
            if svc is not None:
                nomic_vec = [float(x) for x in svc.embed_query(text)]
        except Exception:
            nomic_vec = None
        all_slots = self._concept_index.list_slots(workspace_id)
        results: List[ApparitionCandidate] = []
        for cid, slot in all_slots.items():
            pr = float(slot.pagerank or 1.0)
            if pr <= 0:
                pr = 1.0
            ncos = _cos(nomic_vec, slot.embedding_nomic)
            # tfidf factor defaults to 1.0 (multiplicative identity);
            # empty has no rendered value yet.
            score = pr * 1.0 * ncos
            if score < min_score:
                continue
            results.append(ApparitionCandidate(
                card_id=cid,
                score=float(score),
                pagerank=float(slot.pagerank or 0.0),
                tfidf_cos=1.0,
                nomic_cos=float(ncos),
                provenance=slot.provenance,
                name=self._name_for(cid),
            ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: max(0, int(k))]

    # -------------------------------------------------------------------
    # Mode 3 — DB-ontology recursion (structural)
    # -------------------------------------------------------------------

    def ontology_neighbours(
        self,
        focal_id: str,
        *,
        workspace_id: str = "",
        k: int = 20,
        depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """Walk typed edges from focal up to ``depth`` and return the
        connected concept-graph subset (§8D.36.3).

        Returns ``[ { card_id, edge_type, distance } ]`` sorted by
        distance ascending. Used by the DB-ontology recursion view
        where structural edges dominate.
        """
        if self._graph_editor is None:
            return []
        visited: Dict[str, Dict[str, Any]] = {}
        frontier = [(focal_id, 0, "")]  # (id, distance, incoming edge_type)
        while frontier:
            curr_id, curr_dist, edge_t = frontier.pop(0)
            if curr_id in visited:
                continue
            if curr_id != focal_id:
                visited[curr_id] = {
                    "card_id": curr_id,
                    "edge_type": edge_t,
                    "distance": curr_dist,
                }
            if curr_dist >= depth:
                continue
            try:
                out_edges = self._graph_editor.list_concept_edges(
                    workspace_id=workspace_id,
                    source_id=curr_id,
                    limit=200,
                )
                for e in out_edges:
                    if e.target_id not in visited and e.target_id != focal_id:
                        frontier.append((e.target_id, curr_dist + 1, e.edge_type))
            except Exception:
                pass
        results = list(visited.values())
        results.sort(key=lambda r: r["distance"])
        return results[: max(0, int(k))]

    # -------------------------------------------------------------------
    # Mode 4 — meta-cognition retrieval over the local subgraph centroid
    # -------------------------------------------------------------------

    def apparitions_for_subgraph_centroid(
        self,
        focal_id: str,
        *,
        workspace_id: str = "",
        k: int = 10,
        radius: int = 2,
        exclude_self: bool = True,
    ) -> List[ApparitionCandidate]:
        """§8D.36 mode 4 — focal = centroid of the focal's local subgraph.

        Walks ``linked_nodes`` outward ``radius`` hops from ``focal_id``,
        averages the embeddings of the touched concept slots, and scores
        the rest of the workspace against that averaged signature via
        the triple product.

        This realises the spec's "meta-cognition node retrieval" mode:
        the agent perceives not just one parameter card but its whole
        wired neighbourhood, so the candidates it surfaces reflect the
        graph context, not a single record's embedding.
        """
        if self._concept_index is None:
            return []
        if self._graph_editor is None:
            # No graph walk → fall back to single-focal mode.
            return self.apparitions_for_focal(
                focal_id, workspace_id=workspace_id, k=k,
                exclude_self=exclude_self,
            )

        # Collect the focal + neighbours up to ``radius`` hops.
        seen: Dict[str, int] = {focal_id: 0}
        frontier: List[str] = [focal_id]
        for hop in range(1, max(1, int(radius)) + 1):
            next_frontier: List[str] = []
            for cid in frontier:
                try:
                    out_edges = self._graph_editor.list_concept_edges(
                        workspace_id=workspace_id, source_id=cid, limit=200,
                    )
                except Exception:
                    out_edges = []
                for e in out_edges or []:
                    if e.target_id not in seen:
                        seen[e.target_id] = hop
                        next_frontier.append(e.target_id)
            frontier = next_frontier
            if not frontier:
                break

        # Average the embeddings of every touched slot. Skip slots
        # without vectors so they don't dilute the centroid.
        nomic_acc: Optional[np.ndarray] = None
        tfidf_acc: Optional[np.ndarray] = None
        n_nomic = 0
        n_tfidf = 0
        for cid in seen:
            slot = self._concept_index.get_slot(cid, workspace_id)
            if slot is None:
                continue
            if slot.embedding_nomic:
                v = np.asarray(slot.embedding_nomic, dtype=np.float32)
                nomic_acc = v if nomic_acc is None else nomic_acc + v
                n_nomic += 1
            if slot.embedding_tfidf:
                v = np.asarray(slot.embedding_tfidf, dtype=np.float32)
                # TF-IDF dims may vary across slots (hash-bucket size);
                # only accumulate when shapes match the running accumulator.
                if tfidf_acc is None:
                    tfidf_acc = v
                    n_tfidf = 1
                elif v.size == tfidf_acc.size:
                    tfidf_acc = tfidf_acc + v
                    n_tfidf += 1
        nomic_centroid = (nomic_acc / max(1, n_nomic)).tolist() if nomic_acc is not None else None
        tfidf_centroid = (tfidf_acc / max(1, n_tfidf)).tolist() if tfidf_acc is not None else None

        # Score every workspace slot against the centroid.
        all_slots = self._concept_index.list_slots(workspace_id)
        results: List[ApparitionCandidate] = []
        for cid, slot in all_slots.items():
            if exclude_self and cid in seen:
                continue
            # §8D.1.3 — the halo phantom is NAME-ONLY. A slot that resolves to
            # no usable name (an orphaned/stale index entry, or a node deleted
            # from the graph whose index slot lingered) would render as a blank
            # phantom, so it is never a valid halo candidate — skip it.
            name = self._name_for(cid)
            if not (name or "").strip():
                continue
            pr = float(slot.pagerank or 1.0) or 1.0
            tcos = _cos(tfidf_centroid, slot.embedding_tfidf)
            ncos = _cos(nomic_centroid, slot.embedding_nomic)
            score = pr * tcos * ncos
            results.append(ApparitionCandidate(
                card_id=cid, score=float(score),
                pagerank=float(slot.pagerank or 0.0),
                tfidf_cos=float(tcos), nomic_cos=float(ncos),
                provenance=slot.provenance,
                name=name,
            ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: max(0, int(k))]

    # -------------------------------------------------------------------
    # Mode 5 — closest-inverse function lookup (§8D.7)
    # -------------------------------------------------------------------

    def closest_inverse(
        self,
        output_id: str,
        *,
        workspace_id: str = "",
        k: int = 10,
    ) -> List[ApparitionCandidate]:
        """Given an output concept node, surface input candidates whose
        forward-execution would produce something close to it (§8D.7).

        §R.6 / §7.7 — two tiers:

        1. **Recorded inverse first.** Inputs with a ``FORWARD_MAPPED_TO``
           edge into this output (the persisted forward-call state space)
           are ground truth — they rank ahead of any similarity score,
           most-recent first, ``provenance="recorded-mapping"``.
        2. **Nomic generalisation.** The triple-product against the
           output's description+rendering fills the remaining slots —
           inputs whose forward-execution *would likely* produce something
           close (the unmapped remainder of the state space).

        Filters out the output itself; total ≤ ``k``.
        """
        recorded: List[ApparitionCandidate] = []
        recorded_ids: set = set()
        try:
            from backend.services.forward_inverse_map import recorded_inverse_ids
            ge = self._graph_editor
            for iid in recorded_inverse_ids(
                ge, output_id, workspace_id=workspace_id, limit=k,
            ):
                if iid == output_id:
                    continue
                name = self._name_for(iid) or ""
                recorded.append(ApparitionCandidate(
                    card_id=iid,
                    score=1.0,            # ground truth — above any cosine
                    pagerank=1.0, tfidf_cos=1.0, nomic_cos=1.0,
                    provenance="recorded-mapping",
                    name=name,
                ))
                recorded_ids.add(iid)
                if len(recorded) >= k:
                    break
        except Exception:
            recorded = []
            recorded_ids = set()

        if len(recorded) >= int(k):
            return recorded[: int(k)]

        similar = self.apparitions_for_focal(
            output_id,
            workspace_id=workspace_id,
            k=k,
            exclude_self=True,
        )
        out = recorded + [c for c in similar if c.card_id not in recorded_ids]
        return out[: int(k)]


# ---------------------------------------------------------------------------
# Module-level singleton (§1.1 — singleton-via-accessor)
# ---------------------------------------------------------------------------

import threading as _threading

_APPARITION_SERVICE: Optional["ApparitionService"] = None
_APPARITION_SERVICE_LOCK = _threading.Lock()


def get_apparition_service(
    *,
    concept_index=None,
    graph_editor=None,
) -> "ApparitionService":
    """Return the process-wide ApparitionService.

    Per ``docs/code_constraints/backend_services.md`` §1.1: singletons
    via accessor. Lazy late-binding rebinds ``concept_index`` /
    ``graph_editor`` without resetting the §1.9 utility-event counter
    or the per-band weights — the multi-frequency mode transition
    survives across REST calls.
    """
    global _APPARITION_SERVICE
    with _APPARITION_SERVICE_LOCK:
        if _APPARITION_SERVICE is None:
            _APPARITION_SERVICE = ApparitionService(
                concept_index=concept_index, graph_editor=graph_editor,
            )
        else:
            _APPARITION_SERVICE.rebind(
                concept_index=concept_index, graph_editor=graph_editor,
            )
    return _APPARITION_SERVICE
