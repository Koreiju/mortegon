"""WebSocket frame vocabulary (Workstream W1; domain anchor §11.4).

The workspace's WebSocket carries a small typed-frame vocabulary. This
module defines:

  * ``FrameType``                  — the canonical string enum of types.
  * ``Provenance``                 — provenance class enum (§9.12).
  * ``next_frame_seq(scope)``      — monotonic per-scope sequence counter.
  * ``make_frame(...)``            — factory that stamps ``type`` +
                                     ``frame_seq`` + ``workspace_id`` (when
                                     known) onto an outgoing payload.
  * Helper builders for each frame type with the canonical body schema.

Existing scanner code emits dict payloads directly via
``backend/api/routes.py::_ws_push``. The new helpers in this module are
**additive**: they produce dicts in the same shape, so existing call
sites can opt in incrementally without breaking. New frame types
(``umap_canonical``, ``concept_index_update``, ``purge_workspace``) are
defined here so backend services and the frontend share a single source
of truth for the wire contract.

Per §11.4, the canonical frame envelope is:

    {
      "type": <FrameType>,
      "frame_seq": <monotone int per workspace>,
      "workspace_id": <str | None>,
      ...type-specific body...
    }

The frontend's ``cp/scanner.js::_processScanFrame`` dispatches by
``type``; out-of-order frames (lower ``frame_seq`` arriving after a
higher one) should be discarded by the client.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Frame type registry
# ---------------------------------------------------------------------------

class FrameType:
    """Canonical frame type strings (§11.4).

    Defined as class attributes rather than an Enum so existing code can
    use the literal string ("nodes", "done", ...) interchangeably with
    ``FrameType.NODES``. JSON serialisation is just the string value.
    """

    # --- Existing scanner-emitted types (already used by the codebase) ---
    STATS = "stats"
    LOG = "log"
    NODES = "nodes"  # legacy generic; new code prefers chunks_partial/instances
    CHUNK_ADDED = "chunk_added"
    CHUNK_REPLACED = "chunk_replaced"
    CHUNK_REMOVED = "chunk_removed"
    CHUNKS_PARTIAL = "chunks_partial"
    CHUNK_INSTANCES_PARTIAL = "chunk_instances_partial"
    INSTANCES_INDEXED = "instances_indexed"
    CACHED = "cached"
    DONE = "done"

    # --- New layout / concept / lifecycle types (W1 introduces wire schema) ---
    UMAP_CANONICAL = "umap_canonical"        # §11.5 — canonical 3D coords broadcast
    CONCEPT_INDEX_UPDATE = "concept_index_update"  # §11.6 — concept-side index update
    CONCEPT_CHANGED = "concept_changed"      # multi-tab sync — single concept changed
    EDGE_CHANGED = "edge_changed"            # multi-tab sync — single edge changed
    PURGE_WORKSPACE = "purge_workspace"      # §9.11 — reset / URL removal
    APPARITION_HINT = "apparition_hint"      # §8D.16 — top-K candidates for a focal

    # --- Agent + viewport telemetry frame types ---
    AGENT_TOKEN = "agent_token"              # W10 / §8D.8 — live SLM token stream
    AGENT_REVIEW = "agent_review"            # W24 / §8C.8 — RequestUserReviewAction
    SPINE_DELTA = "spine_delta"              # W35 / §8D.27 — client → server viewport
    EVOLUTION_LOG_DIFF = "evolution_log_diff"  # C5 / §8D.33 — log row append
    COMPUTE_GRAPH_LAYOUT = "compute_graph_layout"  # §6.6.4 — bisector node + UMAP-independent links
    ONTOLOGY_LAYOUT = "ontology_layout"      # §R.2 — full concept-ontology 6D projection

    @classmethod
    def all(cls) -> List[str]:
        return [
            cls.STATS, cls.LOG, cls.NODES,
            cls.CHUNK_ADDED, cls.CHUNK_REPLACED, cls.CHUNK_REMOVED,
            cls.CHUNKS_PARTIAL, cls.CHUNK_INSTANCES_PARTIAL,
            cls.INSTANCES_INDEXED, cls.CACHED, cls.DONE,
            cls.UMAP_CANONICAL, cls.CONCEPT_INDEX_UPDATE,
            cls.CONCEPT_CHANGED, cls.EDGE_CHANGED,
            cls.PURGE_WORKSPACE, cls.APPARITION_HINT,
            cls.AGENT_TOKEN, cls.AGENT_REVIEW, cls.SPINE_DELTA,
            cls.EVOLUTION_LOG_DIFF, cls.COMPUTE_GRAPH_LAYOUT,
            cls.ONTOLOGY_LAYOUT,
        ]


class Provenance:
    """Provenance flags for chunks in the projector (§9.12).

    ``scanner-emitted`` is the default. Graph and agent outputs are
    flagged when they project to 3D under the live output-projection
    pathway (§8D.19).
    """

    SCANNER_EMITTED = "scanner-emitted"
    GRAPH_OUTPUT = "graph-output"
    AGENT_OUTPUT = "agent-output"

    @classmethod
    def all(cls) -> List[str]:
        return [cls.SCANNER_EMITTED, cls.GRAPH_OUTPUT, cls.AGENT_OUTPUT]


# ---------------------------------------------------------------------------
# Frame-seq monotonic counter
# ---------------------------------------------------------------------------

_SEQ_LOCK = threading.Lock()
_SEQ_COUNTERS: Dict[str, int] = {}


def next_frame_seq(scope: str) -> int:
    """Return a monotonically-increasing integer for ``scope``.

    ``scope`` is typically a workspace_id or snapshot_id (stringified).
    Counters are per-scope, in-memory, monotonic but not persistent. On
    process restart counters reset; this is acceptable because the
    frontend only uses ``frame_seq`` for ordering within a single live
    WS connection (replay buffers and reconnect logic in ws_replay.py
    handle the cross-restart case separately).
    """
    with _SEQ_LOCK:
        n = _SEQ_COUNTERS.get(scope, 0) + 1
        _SEQ_COUNTERS[scope] = n
        return n


def reset_frame_seq(scope: str) -> None:
    """Reset the sequence counter for ``scope`` (e.g., on workspace purge)."""
    with _SEQ_LOCK:
        _SEQ_COUNTERS.pop(scope, None)


# ---------------------------------------------------------------------------
# Generic envelope factory
# ---------------------------------------------------------------------------

def make_frame(
    type_: str,
    *,
    workspace_id: Optional[str] = None,
    snapshot_id: Optional[int] = None,
    body: Optional[Dict[str, Any]] = None,
    seq_scope: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a typed frame envelope (§11.4).

    Parameters
    ----------
    type_ : str
        One of the :class:`FrameType` strings.
    workspace_id : str, optional
        Stamps the frame with its workspace context. Recommended for
        every frame; legacy frames may omit.
    snapshot_id : int, optional
        For scanner-emitted frames, the snapshot id (used to scope the
        sequence counter when ``seq_scope`` is not given).
    body : dict, optional
        Type-specific body keys, merged into the envelope.
    seq_scope : str, optional
        Override for the sequence counter scope. Defaults to
        ``workspace_id`` if set, otherwise ``str(snapshot_id)``.
    """
    if seq_scope is None:
        seq_scope = workspace_id or (str(snapshot_id) if snapshot_id is not None else "_global")
    frame: Dict[str, Any] = {
        "type": type_,
        "frame_seq": next_frame_seq(seq_scope),
    }
    if workspace_id is not None:
        frame["workspace_id"] = workspace_id
    if snapshot_id is not None:
        frame["snapshot_id"] = snapshot_id
    if body:
        frame.update(body)
    return frame


# ---------------------------------------------------------------------------
# Type-specific builders
#
# These are convenience wrappers around ``make_frame``. They exist to
# document the canonical body schema for each frame type and to provide
# a single place to extend when new fields land.
# ---------------------------------------------------------------------------

def build_umap_canonical(
    *,
    workspace_id: str,
    coords: Dict[str, List[float]],
    url_roots: Optional[Dict[str, Dict[str, Any]]] = None,
    removed_ids: Optional[List[str]] = None,
    provenance: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build a ``umap_canonical`` frame (§11.5).

    Per ``docs/code_constraints/ws_frames.md`` + §6.1 + §1.8: the
    canonical coord vector is **6D** — three position channels followed
    by three HSV channels. Legacy 3-vector payloads are migrated by the
    LayoutFrame loader; the wire schema is always 6.

    Parameters
    ----------
    coords : dict
        ``{ concept_node_id: [x, y, z, h, s, v] }``. The first three
        floats are the 3D world position; the last three are HSV
        channels normalised to [0, 1] for direct consumption by
        ``THREE.Color.setHSL(h, s, v)``. Keys may be chunk integer ids
        (scanner-emitted chunks) or composite
        ``graph__<graph_id>__<output_card_id>__<sample_id>`` ids for
        graph-output chunks.
    url_roots : dict, optional
        ``{ url: { "root_position": [x,y,z], "bounding_radius": r } }``
        for per-URL workspace placement (§9.5). Per-URL roots are
        position-only — colour state lives per-chunk.
    removed_ids : list[str], optional
        Ids the frontend should remove from the scene graph (graph
        outputs that the latest compile no longer produces; chunks the
        user explicitly removed).
    provenance : dict, optional
        ``{ id: <provenance class> }`` per §9.12. Required in the
        initial frame after a reconnect; optional incrementally.
        ``agent-output`` provenance triggers perimeter-rescale on the
        backend (§6.6.1) before this frame is built.
    """
    body: Dict[str, Any] = {"coords": coords}
    if url_roots is not None:
        body["url_roots"] = url_roots
    if removed_ids is not None:
        body["removed_ids"] = removed_ids
    if provenance is not None:
        body["provenance"] = provenance
    return make_frame(FrameType.UMAP_CANONICAL, workspace_id=workspace_id, body=body)


def build_compute_graph_layout(
    *,
    workspace_id: str,
    placement,                                       # ComputeGraphPlacement (layout_service)
    readouts: Optional[List[Dict[str, Any]]] = None,
    links: Optional[List[Any]] = None,               # list[ProjectorLink]
) -> Dict[str, Any]:
    """Build a ``compute_graph_layout`` frame (§6.6.4; contracts.md §3).

    The compute-graph projector overlay — emitted ALONGSIDE the per-node
    readout ``chunk_replaced`` deltas (§7.8.3) and **never folded into**
    ``umap_canonical``: the bisector node + the link network carry no
    UMAP-fit coupling (§18.34). ``placement`` is a ``ComputeGraphPlacement``;
    ``links`` a list of ``ProjectorLink``. Both are serialised to plain,
    **coordinate-free** link dicts here for the wire (links carry only
    ``src_id`` / ``dst_id`` / ``kind`` — never positions).
    """
    body: Dict[str, Any] = {
        "graph_id": getattr(placement, "graph_id", ""),
        "node": {
            "pos": list(getattr(placement, "pos", (0.0, 0.0, 0.0))),
            "hsv": list(getattr(placement, "hsv", (0.5, 0.5, 0.5))),
        },
        "settle_seq": int(getattr(placement, "settle_seq", 0)),
        "readouts": list(readouts or []),
        "links": [
            {
                "src_id": getattr(l, "src_id", ""),
                "dst_id": getattr(l, "dst_id", ""),
                "kind": getattr(l, "kind", ""),
            }
            for l in (links or [])
        ],
    }
    return make_frame(
        FrameType.COMPUTE_GRAPH_LAYOUT, workspace_id=workspace_id, body=body,
    )


def build_ontology_layout(
    *,
    workspace_id: str,
    coords: Dict[str, List[float]],
    names: Optional[Dict[str, str]] = None,
    type_hints: Optional[Dict[str, str]] = None,
    edges: Optional[List[Dict[str, str]]] = None,
    fitted: bool = False,
) -> Dict[str, Any]:
    """Build an ``ontology_layout`` frame (§R.2).

    The FULL database ontology projected into the projector's 6D
    (xyz+HSV) space: every workspace ConceptNode — foundation fixtures,
    python-native functional-object trees, user concepts, compiled-from-
    scans — keyed by concept_id, sitting alongside the chunk field.
    ``edges`` is the one-edge-table adjacency, **coordinate-free** (the
    §18.34 rule: link networks never couple to the UMAP fit). ``fitted``
    is True when the coords come from a real nomic-UMAP fit (False =
    hash-placeholder transient, §6.1)."""
    body: Dict[str, Any] = {
        "coords": dict(coords or {}),
        "names": dict(names or {}),
        "type_hints": dict(type_hints or {}),
        "edges": list(edges or []),
        "count": len(coords or {}),
        "fitted": bool(fitted),
    }
    return make_frame(
        FrameType.ONTOLOGY_LAYOUT, workspace_id=workspace_id, body=body,
    )


def build_concept_index_update(
    *,
    workspace_id: str,
    updates: Dict[str, Dict[str, Any]],
    removed_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a ``concept_index_update`` frame (§11.6).

    Parameters
    ----------
    updates : dict
        ``{ card_id: { embedding?, pagerank?, similar_to?, provenance? } }``.
        Frontend caches these for retrieval surfaces (§8D.16, §8D.22).
    removed_ids : list[str], optional
        Card ids that were deleted from the concept index.
    """
    body: Dict[str, Any] = {"updates": updates}
    if removed_ids is not None:
        body["removed_ids"] = removed_ids
    return make_frame(FrameType.CONCEPT_INDEX_UPDATE, workspace_id=workspace_id, body=body)


def build_concept_changed(
    *,
    workspace_id: str,
    concept_id: str,
    change: str,        # "created" | "updated" | "deleted"
    concept: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a ``concept_changed`` frame for multi-tab cache sync.

    Emitted on every concept-mutation REST call so that other tabs
    viewing the same workspace can reload the specific concept
    without polling. The ``concept`` field carries the full record
    for ``created``/``updated`` operations; absent for ``deleted``.
    """
    body: Dict[str, Any] = {"concept_id": concept_id, "change": change}
    if concept is not None:
        body["concept"] = concept
    return make_frame(FrameType.CONCEPT_CHANGED, workspace_id=workspace_id, body=body)


def build_edge_changed(
    *,
    workspace_id: str,
    edge_id: str,
    change: str,        # "created" | "deleted"
    edge: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an ``edge_changed`` frame for multi-tab edge-set sync.

    Emitted on every concept-edge create / delete REST call so that
    peer tabs viewing the same workspace can apply the wiring change
    without re-fetching the whole concept list. The ``edge`` field
    carries ``{ edge_id, source_id, target_id, edge_type, ... }`` for
    ``created``; absent for ``deleted``.
    """
    body: Dict[str, Any] = {"edge_id": edge_id, "change": change}
    if edge is not None:
        body["edge"] = edge
    return make_frame(FrameType.EDGE_CHANGED, workspace_id=workspace_id, body=body)


def build_purge_workspace(
    *,
    workspace_id: str,
    urls: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a ``purge_workspace`` frame (§9.11).

    Parameters
    ----------
    urls : list[str], optional
        If provided, scope the purge to these URLs only. If omitted,
        purges the entire workspace.
    """
    body: Dict[str, Any] = {}
    if urls is not None:
        body["urls"] = urls
    return make_frame(FrameType.PURGE_WORKSPACE, workspace_id=workspace_id, body=body)


def build_apparition_hint(
    *,
    workspace_id: str,
    focal_id: str,
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build an ``apparition_hint`` frame (§8D.16, §8D.43 triple product).

    Parameters
    ----------
    focal_id : str
        The concept node id the candidates are scored against.
    candidates : list[dict]
        ``[ { card_id, score, pagerank, tfidf_cos, nomic_cos, ... } ]``
        Top-K candidates by triple-product, descending by ``score``.
    """
    return make_frame(
        FrameType.APPARITION_HINT,
        workspace_id=workspace_id,
        body={"focal_id": focal_id, "candidates": candidates},
    )


def build_done(*, snapshot_id: int, workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """Build a ``done`` frame (scan completion marker)."""
    return make_frame(FrameType.DONE, workspace_id=workspace_id, snapshot_id=snapshot_id)


def build_agent_token(
    *,
    workspace_id: str,
    token: str,
    parameter_card_id: str = "",
) -> Dict[str, Any]:
    """Build an ``agent_token`` frame (W10 / §8D.8, §8D.28).

    One frame per token streamed from the meta-cognition SLM tick. The
    frontend appends each token to a per-parameter-card buffer so the
    user can watch the agent reason in real time.
    """
    return make_frame(
        FrameType.AGENT_TOKEN,
        workspace_id=workspace_id,
        body={"token": token, "parameter_card_id": parameter_card_id},
    )


def build_agent_review(
    *,
    workspace_id: str,
    entry: Dict[str, Any],
) -> Dict[str, Any]:
    """Build an ``agent_review`` frame (W24 / §8C.8).

    Carries a ``RequestUserReviewAction`` queue entry: ``{ review_id,
    prompt, card_ids, actor, ... }``. The frontend renders a
    yellow-bordered review card with accept / dismiss buttons.
    """
    return make_frame(
        FrameType.AGENT_REVIEW,
        workspace_id=workspace_id,
        body={"entry": entry},
    )


def build_evolution_log_diff(
    *,
    workspace_id: str,
    diff: Dict[str, Any],
) -> Dict[str, Any]:
    """Build an ``evolution_log_diff`` frame (C5 / §8D.33).

    Emitted every time the evolution log appends a row so any open
    log-viewer panel updates live (without polling the REST endpoint).
    ``diff`` is the wire-shaped ``EvolutionDiff.to_dict()`` payload.
    """
    return make_frame(
        FrameType.EVOLUTION_LOG_DIFF,
        workspace_id=workspace_id,
        body={"diff": diff},
    )


# ---------------------------------------------------------------------------
# Provenance helper
# ---------------------------------------------------------------------------

def stamp_provenance(frame: Dict[str, Any], provenance: str) -> Dict[str, Any]:
    """Add a top-level ``provenance`` flag to ``frame`` (§9.12).

    Mutates and returns the frame for chaining. No-op if the frame
    already carries a ``provenance`` key (don't clobber explicit
    settings from build helpers).
    """
    if "provenance" not in frame:
        frame["provenance"] = provenance
    return frame
