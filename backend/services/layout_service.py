"""Layout Service (Workstream W2; domain anchor §9.4, §11.5).

Wraps the existing TruncatedSVD-based UMAP-like projection (from
``routes.py::recompute_umap``) into a service responsible for:

  * Full-set **6D canonical-coordinate** computation over the live
    TF-IDF chunk index (§6.1, §9.3). The 6-vector packs three position
    components ``(x, y, z)`` plus three colour-state components
    ``(h, s, v)`` per chunk; the colour state is the projector's
    ray-projection signal that lets phantoms in the halo render with
    the same hue as the chunk they project from (§8.2.1.2).
  * Per-URL post-processing: centroid translation, bounding-radius
    scale, hard collider repulsion (§9.5, §9.7).
  * **Perimeter-encompassing rescale** for chunks tagged with
    ``provenance == agent-output`` (§6.6.1). The geometric move from
    the workspace's interior to its outer envelope is the Imaginary →
    Real return path: emissions live on the perimeter.
  * Persistent LayoutFrame storage (in-memory cache + JSON file)
    keyed by stable integer chunk ids (§9.4). Legacy 3-vector files
    migrate on first load by padding HSV with zeros (the projector
    re-derives HSV from the TF-IDF index on the next refit).
  * Broadcast of ``umap_canonical`` WS frames to all subscribed
    frontends via the routes module's ``_ws_push`` (§11.5).

Triggers — per §11.5:

  1. Scan-end (mapper emits ``done`` → routes.on_stream hooks into
     ``LayoutService.recompute_and_broadcast``).
  2. Manual ``/api/recompute_umap`` REST call.
  3. Graph-state change-sets (W7 — peripheral concept-node outputs).

Constraints anchored by ``docs/code_constraints/backend_services.md``:

  * §1.8 — fit 6D (n_components=6) + apply perimeter rescale for
    ``provenance == agent-output``. Anti-goals §18.23, §1.2.2.
  * §2.2 — must not run UMAP with ``n_components=3`` (position only).

The service is intentionally light on dependencies: only numpy, scipy
and sklearn (already used by the inline ``/recompute_umap``). It does
*not* import frontend modules or graph_editor; the broadcast happens
through a small callable passed in at construction so we don't create
a cycle with ``routes.py``.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy import sparse as sp

logger = logging.getLogger("wfh.layout")

try:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    _HAVE_SKLEARN = True
except Exception:
    TruncatedSVD = None  # type: ignore
    normalize = None  # type: ignore
    _HAVE_SKLEARN = False

# §6.1 / §B.2 — the layout is the **UMAP**-linear-radial force-directed
# hybrid. UMAP's neighbour-preservation is load-bearing: §18.17 (outliers
# in geometry), §8.2.1.1 (manifold-nearest ray-projection) and §8.2.1.2
# (6D HSV jointly fit) all assume content-similar chunks land adjacent —
# which a linear projection (SVD/PCA) does NOT guarantee. We therefore use
# real ``umap-learn`` when available, degrading **loudly** (never silently,
# §13.4) to TruncatedSVD only when umap is unavailable or fails at runtime.
try:
    import umap  # umap-learn
    _HAVE_UMAP = True
except Exception:
    umap = None  # type: ignore
    _HAVE_UMAP = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TARGET_RADIUS = 40.0       # workspace bounding sphere radius
DEFAULT_COLLIDER_RADIUS = 1.6      # workspace-wide collider (§9.7)
# Safety multiplier (§9.7 / USER_REQUIREMENTS_VERBATIM B.3): user reported
# "Layout issues also in the 3D layouts with spacing too close together."
# Bumped from 1.15 → 2.2 so the centre-to-centre minimum is 2·R·safety =
# 2·1.6·2.2 = 7.04 units, leaving ~3.8 units of clear gap between rims of
# 1.6-radius billboards (vs the prior 0.5 units of clearance that produced
# the visible too-close pairs).
DEFAULT_COLLIDER_SAFETY = 2.2      # multiplier; 2·R · safety in §9.7
DEFAULT_COLLIDER_ITERATIONS = 8    # hard-correction passes
DEFAULT_SAFETY_GAP = 12.0          # inter-URL padding (§9.5) — doubled from 6.0 for clearer URL separation

# LayoutFrame persistence path; survives process restart per §11.5.
LAYOUT_FRAME_DIR = os.environ.get(
    "WFH_LAYOUT_FRAME_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "kuzu_db")),
)


# ---------------------------------------------------------------------------
# LayoutFrame record
# ---------------------------------------------------------------------------

@dataclass
class LayoutFrame:
    """The current canonical coordinate set for a workspace (§11.5).

    Keyed by stable chunk id (string form of the integer; composite
    ``graph__<gid>__<ocid>__<sid>`` for graph outputs per §8D.19).
    Provenance flags per id are §9.12.
    """

    workspace_id: str = ""
    coords: Dict[str, List[float]] = field(default_factory=dict)
    url_roots: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    provenance: Dict[str, str] = field(default_factory=dict)
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "coords": self.coords,
            "url_roots": self.url_roots,
            "provenance": self.provenance,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LayoutFrame":
        """Reconstruct a LayoutFrame from a persisted dict.

        Per ``persistence.md §1.5``: legacy 3-vector files migrate on
        first load by padding HSV with neutral 0.5 — the projector then
        re-derives HSV from the TF-IDF index on the next refit. This
        keeps the 6-vector invariant (§1.8) while accepting old data.
        """
        raw = d.get("coords") or {}
        coords: Dict[str, List[float]] = {}
        for k, v in raw.items():
            seq = list(map(float, v))
            if len(seq) >= 6:
                coords[k] = seq[:6]
            elif len(seq) == 3:
                # Legacy 3-vector: pad HSV with neutral mid-band so the
                # frontend always gets a valid (h, s, v) triple.
                coords[k] = seq + [0.5, 0.5, 0.5]
            else:
                # Partially shorter: pad up to 6 with zeros.
                coords[k] = seq + [0.0] * (6 - len(seq))
        return cls(
            workspace_id=d.get("workspace_id", ""),
            coords=coords,
            url_roots=d.get("url_roots") or {},
            provenance=d.get("provenance") or {},
            updated_at=float(d.get("updated_at", 0.0)),
        )


# ---------------------------------------------------------------------------
# Compute-graph projector overlay (§6.6.4) — UMAP-INDEPENDENT records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProjectorLink:
    """§6.6.4 (P.8/P.9) — one edge of the projector's UMAP-INDEPENDENT link
    network. Carries NO coordinates: coupling the link network to the UMAP
    fit is the §18.34 regression."""
    src_id: str
    dst_id: str
    kind: str           # "url_to_sample" | "input_to_graph" | "readout_to_graph"
    graph_id: str


@dataclass(frozen=True)
class ComputeGraphPlacement:
    """§6.6.4 (P.10) — the single collapsed compute-graph node, placed on the
    linear bisector between the (hidden) input and output centroids. Only this
    node is emitted; the two centroids never are (§18.34)."""
    graph_id: str
    pos: tuple          # (x, y, z) bisector midpoint
    hsv: tuple          # (h, s, v) carried from the input centroid
    settle_seq: int     # monotone per graph_id; orders out-of-order readout deltas


# ---------------------------------------------------------------------------
# Layout Service
# ---------------------------------------------------------------------------

class LayoutService:
    """Orchestrator for canonical 3D layout computation and broadcast.

    Construct once at app boot; share across requests. Worker threads
    call ``recompute_and_broadcast`` after scan-end; the manual
    ``/api/recompute_umap`` REST handler calls it on demand.
    """

    def __init__(
        self,
        broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
        target_radius: float = DEFAULT_TARGET_RADIUS,
        collider_radius: float = DEFAULT_COLLIDER_RADIUS,
        collider_safety: float = DEFAULT_COLLIDER_SAFETY,
        collider_iterations: int = DEFAULT_COLLIDER_ITERATIONS,
    ):
        # ``broadcast(snapshot_id, frame)`` is the wire-out hook —
        # routes.py passes ``_ws_push`` here. Decoupled so the service
        # can be tested without a live WS.
        self._broadcast = broadcast
        self.target_radius = float(target_radius)
        self.collider_radius = float(collider_radius)
        self.collider_safety = float(collider_safety)
        self.collider_iterations = int(collider_iterations)

        # In-memory LayoutFrame per workspace (key = workspace_id).
        # Empty workspace_id is the "default" workspace.
        self._frames: Dict[str, LayoutFrame] = {}
        # §R.2 — per-workspace ontology projection ({concept_id: 6-vector}).
        self._ontology_frames: Dict[str, Dict[str, List[float]]] = {}
        # Per-URL root_position and bounding_radius caches (§9.5).
        self._url_roots: Dict[str, Dict[str, Any]] = {}
        # §6.6.4 — monotone settle_seq per compute-graph (orders bisector
        # node re-places under out-of-order readout deltas, §7.8.3).
        self._compute_graph_seq: Dict[str, int] = {}
        self._lock = threading.Lock()

        self._ensure_storage_dir()

    # -------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------

    def _ensure_storage_dir(self) -> None:
        try:
            os.makedirs(LAYOUT_FRAME_DIR, exist_ok=True)
        except Exception:
            pass

    def _frame_path(self, workspace_id: str) -> str:
        safe = workspace_id.replace("/", "_").replace("\\", "_") or "_default"
        return os.path.join(LAYOUT_FRAME_DIR, f"layout_frame_{safe}.json")

    def load_frame(self, workspace_id: str = "") -> Optional[LayoutFrame]:
        """Load persisted LayoutFrame from disk (§11.5 initial-connection)."""
        path = self._frame_path(workspace_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            frame = LayoutFrame.from_dict(d)
            with self._lock:
                self._frames[workspace_id] = frame
            return frame
        except Exception:
            return None

    def save_frame(self, workspace_id: str = "") -> bool:
        with self._lock:
            frame = self._frames.get(workspace_id)
        if frame is None:
            return False
        try:
            path = self._frame_path(workspace_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(frame.to_dict(), f)
            return True
        except Exception:
            return False

    def get_frame(self, workspace_id: str = "") -> Optional[LayoutFrame]:
        with self._lock:
            f = self._frames.get(workspace_id)
        if f is not None:
            return f
        return self.load_frame(workspace_id)

    # -------------------------------------------------------------------
    # §6.6.4 — compute-graph projector overlay (bisector node + links)
    # -------------------------------------------------------------------

    def place_compute_graph_node(
        self, workspace_id: str, graph_id: str,
        input_ids: List[str], output_ids: List[str],
    ) -> ComputeGraphPlacement:
        """§6.6.4 (P.10) — place the collapsed compute-graph node on the
        linear BISECTOR between the input 6D-UMAP position centroid and the
        (dynamically-updated) readout-perimeter centroid. Neither centroid
        is emitted — only the node. ``settle_seq`` increases per ``graph_id``
        so the projector can re-place on out-of-order readout deltas
        (§7.8.3); the node slides as the output centroid moves."""
        frame = self.get_frame(workspace_id)
        coords = frame.coords if frame is not None else {}

        def _centroid(ids: List[str]) -> Optional[List[float]]:
            pts = [coords[i][:3] for i in ids
                   if i in coords and len(coords[i]) >= 3]
            if not pts:
                return None
            k = len(pts)
            return [sum(p[j] for p in pts) / k for j in range(3)]

        in_c = _centroid(input_ids)
        out_c = _centroid(output_ids)
        if in_c is not None and out_c is not None:
            pos = [(in_c[j] + out_c[j]) / 2.0 for j in range(3)]
        elif in_c is not None:
            pos = in_c
        elif out_c is not None:
            pos = out_c
        else:
            pos = [0.0, 0.0, 0.0]

        # HSV carried from the first input carrying one (passive rotation §7.8.3).
        hsv = [0.5, 0.5, 0.5]
        for i in input_ids:
            v = coords.get(i)
            if v is not None and len(v) >= 6:
                hsv = list(v[3:6])
                break

        with self._lock:
            seq = int(self._compute_graph_seq.get(graph_id, 0)) + 1
            self._compute_graph_seq[graph_id] = seq

        return ComputeGraphPlacement(
            graph_id=graph_id,
            pos=(pos[0], pos[1], pos[2]),
            hsv=(hsv[0], hsv[1], hsv[2]),
            settle_seq=seq,
        )

    def compute_projector_links(
        self, workspace_id: str, graph_id: str, *,
        input_ids: Optional[List[str]] = None,
        readout_ids: Optional[List[str]] = None,
        url_sample_map: Optional[Dict[str, List[str]]] = None,
    ) -> List[ProjectorLink]:
        """§6.6.4 (P.8/P.9) — build the UMAP-INDEPENDENT projector link
        network: root_url→chunk_sample, (input roots ∪ click-sticked
        inputs)→graph_node, every readout→graph_node. Pure adjacency —
        carries no coordinates (§18.34). ``workspace_id`` is accepted for
        symmetry/future scoping; the adjacency is supplied by the caller
        (the editor knows the graph's inputs/readouts/url roots)."""
        links: List[ProjectorLink] = []
        for url_root, sample_ids in (url_sample_map or {}).items():
            for sid in (sample_ids or []):
                links.append(ProjectorLink(
                    src_id=url_root, dst_id=sid,
                    kind="url_to_sample", graph_id=graph_id,
                ))
        for iid in (input_ids or []):
            links.append(ProjectorLink(
                src_id=iid, dst_id=graph_id,
                kind="input_to_graph", graph_id=graph_id,
            ))
        for rid in (readout_ids or []):
            links.append(ProjectorLink(
                src_id=rid, dst_id=graph_id,
                kind="readout_to_graph", graph_id=graph_id,
            ))
        return links

    def purge_workspace(self, workspace_id: str = "") -> bool:
        """§9.11 — drop the LayoutFrame for ``workspace_id`` and remove
        its persisted JSON. Used by ``POST /api/purge_workspace`` so a
        wiped workspace doesn't keep ghosts in 3D from prior scans.
        Also drops the §R.2 ontology projection (memory + side file).
        """
        with self._lock:
            existed = workspace_id in self._frames
            self._frames.pop(workspace_id, None)
            if hasattr(self, "_ontology_frames"):
                self._ontology_frames.pop(workspace_id, None)
        try:
            path = self._frame_path(workspace_id)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    existed = True
                except Exception:
                    pass
        except Exception:
            pass
        try:
            opath = self._ontology_path(workspace_id)
            if os.path.exists(opath):
                os.remove(opath)
        except Exception:
            pass
        return bool(existed)

    # -------------------------------------------------------------------
    # §R.2 — full-ontology 6D projection
    #
    # "Build out a fully functional new set of features that allows for
    #  the full database ontology mapped to our 3D umap GUI, which
    #  integrates our full set of DB functional-objects and scanned
    #  webpage chunk structures." (USER_REQUIREMENTS_VERBATIM.md §R.2)
    #
    # The CHUNK field projects via TF-IDF (§6.1); the CONCEPT ontology
    # projects via its sibling pipeline's nomic vectors (§2.3 — the two
    # progressive vectorization pipelines stay siblings: this method
    # CONSUMES ConceptIndexService slots, it never nests the services).
    # Concepts without a nomic vector yet ride the deterministic hash
    # placeholder (§6.1 transient) until the next recompute.
    # -------------------------------------------------------------------

    def _ontology_path(self, workspace_id: str) -> str:
        safe = workspace_id.replace("/", "_").replace("\\", "_") or "_default"
        return os.path.join(LAYOUT_FRAME_DIR, f"ontology_frame_{safe}.json")

    def get_ontology_coords(self, workspace_id: str = "") -> Dict[str, List[float]]:
        """Current ontology coords (memory first, then disk). Empty dict
        when no projection has run yet."""
        with self._lock:
            frames = getattr(self, "_ontology_frames", None)
            if frames is not None and workspace_id in frames:
                return dict(frames[workspace_id])
        try:
            path = self._ontology_path(workspace_id)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                coords = {k: [float(x) for x in v] for k, v in (d.get("coords") or {}).items()}
                with self._lock:
                    if not hasattr(self, "_ontology_frames"):
                        self._ontology_frames: Dict[str, Dict[str, List[float]]] = {}
                    self._ontology_frames[workspace_id] = coords
                return dict(coords)
        except Exception:
            pass
        return {}

    def recompute_ontology(
        self,
        workspace_id: str = "",
        *,
        concept_index=None,
        graph_editor=None,
        broadcast_frame: bool = True,
    ) -> Dict[str, Any]:
        """§R.2 — project EVERY workspace ConceptNode (foundation fixtures,
        python-native functional-object trees, user concepts, compiled-
        from-scans) into the projector's 6D (xyz+HSV) space.

        Pipeline: nomic slot vectors → L2-normalise → ``_embed_6d`` (real
        UMAP, loud SVD degradation §13.4) → sphere-fit + HSV-normalise
        (the same ``_project`` post-processing contract the chunk field
        uses) → hash-placeholder for vectorless concepts → persist +
        ``ontology_layout`` broadcast (dual-routed §18.1: frame returned
        AND pushed).

        Returns ``{coords, names, type_hints, edges, fitted, count}``.
        """
        import numpy as _np

        nodes = []
        try:
            if graph_editor is not None:
                nodes = graph_editor.list_concepts(
                    workspace_id=workspace_id, limit=10000) or []
        except Exception:
            nodes = []
        names: Dict[str, str] = {}
        type_hints: Dict[str, str] = {}
        for n in nodes:
            cid = getattr(n, "concept_id", "") or ""
            if not cid:
                continue
            names[cid] = getattr(n, "name", "") or ""
            type_hints[cid] = getattr(n, "type_hint", "") or ""

        # Concept-side nomic vectors from the SIBLING index service.
        slots = {}
        try:
            if concept_index is not None:
                slots = concept_index.list_slots(workspace_id=workspace_id) or {}
        except Exception:
            slots = {}

        vec_ids: List[str] = []
        vecs: List[List[float]] = []
        for cid in names:
            slot = slots.get(cid)
            v = getattr(slot, "embedding_nomic", None) if slot is not None else None
            if v:
                vec_ids.append(cid)
                vecs.append([float(x) for x in v])

        coords: Dict[str, List[float]] = {}
        fitted = False
        # §R.2 — the ontology shell sits INSIDE the chunk sphere (chunks at
        # target_radius are the outer comparison surface; the ontology is
        # the workspace's inner structure).
        onto_radius = self.target_radius * 0.6
        if vecs and _HAVE_SKLEARN:
            X = _np.asarray(vecs, dtype=_np.float32)
            norms = _np.linalg.norm(X, axis=1, keepdims=True).clip(min=1e-9)
            X = X / norms
            Y = self._embed_6d(X, X.shape[0])
            if Y is not None:
                fitted = True
                if Y.shape[1] < self._UMAP_DIM_TOTAL:
                    pad = _np.zeros(
                        (Y.shape[0], self._UMAP_DIM_TOTAL - Y.shape[1]),
                        dtype=Y.dtype)
                    Y = _np.hstack([Y, pad])
                pos = Y[:, :self._UMAP_DIM_POSITION].copy()
                pos = pos - pos.mean(axis=0, keepdims=True)
                span = float(_np.max(_np.abs(pos))) or 1.0
                pos = pos * (onto_radius / span)
                hsv = Y[:, self._UMAP_DIM_POSITION:self._UMAP_DIM_TOTAL].copy()
                for j in range(hsv.shape[1]):
                    col = hsv[:, j]
                    lo, hi = float(col.min()), float(col.max())
                    rng = hi - lo
                    hsv[:, j] = 0.5 if rng < 1e-9 else (col - lo) / rng
                for i, cid in enumerate(vec_ids):
                    coords[cid] = [
                        float(pos[i, 0]), float(pos[i, 1]), float(pos[i, 2]),
                        float(hsv[i, 0]), float(hsv[i, 1]), float(hsv[i, 2]),
                    ]
        # Vectorless concepts (and the no-sklearn path): deterministic
        # hash-direction placeholder on the ontology shell (§6.1 transient).
        for cid in names:
            if cid not in coords:
                coords[cid] = self._hash_unit(cid, onto_radius)

        # One-edge-table adjacency, coordinate-free (§18.34).
        edges: List[Dict[str, str]] = []
        try:
            if graph_editor is not None:
                for e in (graph_editor.list_concept_edges(
                        workspace_id=workspace_id, limit=5000) or []):
                    src = getattr(e, "source_id", "")
                    dst = getattr(e, "target_id", "")
                    if src in coords and dst in coords:
                        edges.append({
                            "src_id": src, "dst_id": dst,
                            "kind": getattr(e, "edge_type", "") or "RELATES_TO",
                        })
        except Exception:
            pass

        # Persist (memory + side file; the db_janitor sweeps test-workspace
        # orphans of this file, §R.9).
        with self._lock:
            if not hasattr(self, "_ontology_frames"):
                self._ontology_frames = {}
            self._ontology_frames[workspace_id] = coords
        try:
            with open(self._ontology_path(workspace_id), "w", encoding="utf-8") as f:
                json.dump({"workspace_id": workspace_id, "coords": coords,
                           "updated_at": time.time()}, f)
        except Exception:
            pass

        out = {
            "coords": coords, "names": names, "type_hints": type_hints,
            "edges": edges, "fitted": fitted, "count": len(coords),
        }
        if broadcast_frame and self._broadcast is not None:
            try:
                from backend.api.ws_frames import build_ontology_layout
                frame = build_ontology_layout(
                    workspace_id=workspace_id, coords=coords, names=names,
                    type_hints=type_hints, edges=edges, fitted=fitted,
                )
                self._broadcast(0, frame)
                out["frame"] = frame
            except Exception as e:
                logger.warning("ontology_layout broadcast failed: %s", e)
        return out

    # -------------------------------------------------------------------
    # 6D projection — real UMAP (neighbour-preserving) via ``_embed_6d``,
    # degrading loudly to TruncatedSVD (§6.1 / §B.2 / §13.4).
    #
    # §6.1 + §1.8 — n_components is 6: the first 3 components fill the
    # position channels (x, y, z); the next 3 fill the HSV channels. If
    # the embedding cannot support 6 components, the HSV channels are
    # zero-padded (the projector still renders; phantom HSV falls back to
    # the parent-chunk's stored colour state).
    # -------------------------------------------------------------------

    # 6D contract: 3 position + 3 HSV per §6.1 + §1.8.
    _UMAP_DIM_POSITION = 3
    _UMAP_DIM_HSV = 3
    _UMAP_DIM_TOTAL = _UMAP_DIM_POSITION + _UMAP_DIM_HSV  # 6
    # Below this sample count UMAP cannot form a meaningful neighbourhood
    # graph; the transient hash-radial placeholder (frontend §6.1) is the
    # right form there, so we use the structured SVD bridge for tiny sets
    # and reserve real UMAP for the full chunk space (§B.2 "the new, full
    # chunk space").
    _UMAP_MIN_SAMPLES = 8

    def _embed_6d(self, X, n_docs: int):
        """Neighbour-preserving 6D embedding of the (L2-normalised) TF-IDF
        matrix ``X`` per §6.1 / §B.2.

        Uses the standard robust TF-IDF→3D pipeline: a TruncatedSVD (LSA)
        densify/denoise step feeding real ``umap.UMAP`` (which preserves the
        cosine neighbourhood TruncatedSVD-alone would scramble). Degrades
        **loudly** (§13.4 — never silently) to TruncatedSVD when umap is
        unavailable, the sample set is too small for a neighbour graph, or
        UMAP raises at runtime. Returns the raw ``(n_docs, k)`` embedding
        (post-processing — sphere-fit + HSV normalise — happens in
        ``_project``), or ``None`` when even SVD cannot run.
        """
        target = self._UMAP_DIM_TOTAL  # 6
        if _HAVE_UMAP and n_docs >= self._UMAP_MIN_SAMPLES:
            try:
                # LSA bridge: dense, denoised input keeps UMAP off the
                # sparse-cosine slow path while preserving the structure.
                svd_dim = min(50, X.shape[0] - 1, X.shape[1] - 1)
                if svd_dim >= target:
                    Xd = TruncatedSVD(
                        n_components=svd_dim, random_state=42
                    ).fit_transform(X)
                else:
                    Xd = X.toarray() if sp.issparse(X) else np.asarray(X)
                n_neighbors = max(2, min(15, n_docs - 1))
                reducer = umap.UMAP(
                    n_components=target,
                    n_neighbors=n_neighbors,
                    min_dist=0.1,
                    metric="cosine",
                    random_state=42,
                    init="spectral",
                    verbose=False,
                )
                return reducer.fit_transform(Xd)
            except Exception as e:  # pragma: no cover - runtime degradation
                logger.warning(
                    "LayoutService: real UMAP failed (%s); DEGRADING to "
                    "TruncatedSVD (§13.4 loud, not silent).", e,
                )
        elif not _HAVE_UMAP:
            logger.warning(
                "LayoutService: umap-learn unavailable; DEGRADING to "
                "TruncatedSVD (§13.4 loud). Install umap-learn for the "
                "neighbour-preserving §6.1 layout authority.",
            )
        # Structured SVD bridge (tiny sets or umap failure/absence).
        n_comp = min(target, X.shape[0] - 1, X.shape[1] - 1)
        if n_comp < 1:
            return None
        return TruncatedSVD(n_components=n_comp, random_state=42).fit_transform(X)

    def _project(self, tf_matrix, chunk_ids: List[str]) -> Dict[str, List[float]]:
        """Run the canonical 6D projection.

        Returns ``{chunk_id: [x, y, z, h, s, v]}`` per §6.1 + §1.8 6D
        contract. The first three components are the spatial position
        (already fit-to-target-sphere) and the last three are the HSV
        channels normalised to [0, 1] for the projector to consume
        directly into ``THREE.Color.setHSL`` per §8.2.1.2.
        """
        if not _HAVE_SKLEARN:
            # Fallback: hash-based deterministic 6-vectors if sklearn missing.
            return {cid: self._hash_unit(cid, self.target_radius) for cid in chunk_ids}
        n_docs = tf_matrix.shape[0]
        if n_docs < 1 or tf_matrix.shape[1] == 0:
            return {}
        X = tf_matrix.astype(np.float32)
        if normalize is not None:
            X = normalize(X, norm="l2", axis=1, copy=False)
        else:
            sq = X.multiply(X).sum(axis=1)
            norms = np.sqrt(np.asarray(sq).ravel()).clip(min=1e-9)
            X = sp.diags(1.0 / norms) @ X
        Y = self._embed_6d(X, n_docs)
        if Y is None:
            return {}
        # Pad up to 6D if the TF-IDF matrix couldn't yield enough rank.
        if Y.shape[1] < self._UMAP_DIM_TOTAL:
            pad = np.zeros((Y.shape[0], self._UMAP_DIM_TOTAL - Y.shape[1]),
                           dtype=Y.dtype)
            Y = np.hstack([Y, pad])
        # Position channels: fit-to-target-sphere (§2.1 step 1).
        pos = Y[:, :self._UMAP_DIM_POSITION].copy()
        pos = pos - pos.mean(axis=0, keepdims=True)
        span = float(np.max(np.abs(pos)))
        if span < 1e-9:
            span = 1.0
        pos = pos * (self.target_radius / span)
        # HSV channels: normalise each independently to [0, 1] so the
        # frontend can pass straight into THREE.Color.setHSL(h, s, v).
        hsv = Y[:, self._UMAP_DIM_POSITION:self._UMAP_DIM_TOTAL].copy()
        if hsv.size > 0:
            for j in range(hsv.shape[1]):
                col = hsv[:, j]
                lo, hi = float(col.min()), float(col.max())
                rng = hi - lo
                if rng < 1e-9:
                    # Degenerate: fall back to mid-band so the frontend
                    # still has a valid HSL triple (mid hue, mid sat,
                    # mid value) rather than a NaN or all-zero column.
                    hsv[:, j] = 0.5
                else:
                    hsv[:, j] = (col - lo) / rng
        # Compose the 6-vector per chunk.
        out: Dict[str, List[float]] = {}
        for i, cid in enumerate(chunk_ids):
            out[cid] = [
                float(pos[i, 0]), float(pos[i, 1]), float(pos[i, 2]),
                float(hsv[i, 0]) if hsv.shape[1] > 0 else 0.5,
                float(hsv[i, 1]) if hsv.shape[1] > 1 else 0.5,
                float(hsv[i, 2]) if hsv.shape[1] > 2 else 0.5,
            ]
        return out

    @staticmethod
    def _hash_unit(key: str, radius: float) -> List[float]:
        """Deterministic 6-vector for hash-based fallback layout.

        Returns ``[x, y, z, h, s, v]`` per the 6D contract; the position
        is sphere-projected to ``radius`` and HSV is hash-derived
        deterministically so retries land on the same colour.
        """
        h = abs(hash(key))
        ax = ((h & 0xFF) / 255.0) * 2 - 1
        ay = (((h >> 8) & 0xFF) / 255.0) * 2 - 1
        az = (((h >> 16) & 0xFF) / 255.0) * 2 - 1
        # Normalise to unit then scale.
        n = max(1e-9, float(np.sqrt(ax * ax + ay * ay + az * az)))
        # HSV derived from later bits so position and colour are
        # independent variates of the same hash.
        hue = (((h >> 24) & 0xFF) / 255.0)
        sat = (((h >> 32) & 0xFF) / 255.0) * 0.6 + 0.2  # 0.2 .. 0.8
        val = (((h >> 40) & 0xFF) / 255.0) * 0.6 + 0.3  # 0.3 .. 0.9
        return [ax / n * radius, ay / n * radius, az / n * radius,
                float(hue), float(sat), float(val)]

    # -------------------------------------------------------------------
    # Post-processing (§9.5 per-URL placement, §9.7 collider repulsion)
    # -------------------------------------------------------------------

    def _collider_repulsion(
        self,
        coords: Dict[str, List[float]],
        iterations: Optional[int] = None,
    ) -> Dict[str, List[float]]:
        """Hard repulsion pass — push pairs apart to ≥ 2·R·safety (§9.7).

        Pairs at separation ≥ 2·R exert zero force; below, exact
        correction-to-target in one step (§2.1 step 2 / §9.7).

        Operates on the position channels (first 3 elements) only; HSV
        channels (elements 3..5) are preserved verbatim because colour
        state has no spatial collision semantics. The 6-vector contract
        (§1.8) is maintained on input and output.
        """
        if not coords:
            return coords
        iters = int(iterations if iterations is not None else self.collider_iterations)
        ids = list(coords.keys())
        n = len(ids)
        if n < 2:
            return coords
        # Position-only matrix for the physics; HSV preserved alongside.
        P = np.array([coords[i][:3] for i in ids], dtype=np.float32)
        hsv_tail = {i: list(coords[i][3:6]) if len(coords[i]) >= 6
                    else [0.5, 0.5, 0.5] for i in ids}
        threshold = 2.0 * self.collider_radius * self.collider_safety
        thr2 = threshold * threshold
        for _ in range(iters):
            moved_any = False
            for i in range(n):
                for j in range(i + 1, n):
                    d = P[i] - P[j]
                    d2 = float(d.dot(d))
                    if d2 >= thr2 or d2 < 1e-12:
                        continue
                    dist = float(np.sqrt(d2))
                    overlap = threshold - dist
                    if overlap <= 0:
                        continue
                    unit = d / max(dist, 1e-9)
                    push = unit * (overlap * 0.5)
                    P[i] = P[i] + push
                    P[j] = P[j] - push
                    moved_any = True
            if not moved_any:
                break
        return {ids[i]: [float(P[i, 0]), float(P[i, 1]), float(P[i, 2]),
                          float(hsv_tail[ids[i]][0]),
                          float(hsv_tail[ids[i]][1]),
                          float(hsv_tail[ids[i]][2])]
                for i in range(n)}

    def _per_url_postprocess(
        self,
        coords: Dict[str, List[float]],
        chunk_url_map: Dict[str, str],
    ) -> Tuple[Dict[str, List[float]], Dict[str, Dict[str, Any]]]:
        """Per-URL centroid translation + bounding-radius placement (§9.5).

        For each URL, compute the centroid of its chunks in the
        projected position space (first 3 channels) and translate them
        so the centroid sits at the URL's ``root_position``. HSV
        channels (elements 3..5 of the 6-vector) are preserved. New
        URLs are placed outside every existing workspace's bounding
        sphere with ``safety_gap``. Existing URLs keep their previous
        ``root_position``.

        Returns ``(translated_coords, url_roots)`` where ``url_roots``
        is ``{url: {"root_position": [x,y,z], "bounding_radius": r}}``.
        """
        if not coords or not chunk_url_map:
            return coords, {}

        # Group chunk ids by URL.
        by_url: Dict[str, List[str]] = {}
        for cid, url in chunk_url_map.items():
            if cid in coords:
                by_url.setdefault(url or "", []).append(cid)

        new_url_roots: Dict[str, Dict[str, Any]] = dict(self._url_roots)

        # Compute centroid + bounding radius for each URL in projected
        # position space (first 3 channels of the 6-vector).
        for url, cids in by_url.items():
            if not cids:
                continue
            arr = np.array([coords[cid][:3] for cid in cids], dtype=np.float32)
            centroid = arr.mean(axis=0)
            # bounding radius = max distance from centroid (position only)
            d = np.linalg.norm(arr - centroid, axis=1)
            bounding = float(np.max(d)) if d.size else 0.0

            # Decide root_position. Existing URL: reuse. New URL: place
            # outside every other existing bounding sphere with safety gap.
            if url in new_url_roots:
                root = np.array(new_url_roots[url]["root_position"], dtype=np.float32)
            else:
                root = self._allocate_new_root(new_url_roots, bounding)

            # Translate this URL's chunks so centroid lands at root,
            # preserving the HSV channels verbatim.
            shift = root - centroid
            for cid in cids:
                c = coords[cid]
                hsv_tail = list(c[3:6]) if len(c) >= 6 else [0.5, 0.5, 0.5]
                coords[cid] = [
                    float(c[0] + shift[0]),
                    float(c[1] + shift[1]),
                    float(c[2] + shift[2]),
                    float(hsv_tail[0]),
                    float(hsv_tail[1]),
                    float(hsv_tail[2]),
                ]

            new_url_roots[url] = {
                "root_position": [float(root[0]), float(root[1]), float(root[2])],
                "bounding_radius": bounding,
            }

        self._url_roots = new_url_roots
        return coords, new_url_roots

    def _allocate_new_root(
        self,
        existing_roots: Dict[str, Dict[str, Any]],
        new_bounding: float,
    ) -> np.ndarray:
        """Greedy non-overlap placement for a new URL's root (§9.5)."""
        if not existing_roots:
            return np.zeros(3, dtype=np.float32)
        # Try a small set of candidate unit directions; pick the one
        # maximising minimum-distance to existing root spheres.
        candidates = [
            np.array([1, 0, 0], dtype=np.float32),
            np.array([-1, 0, 0], dtype=np.float32),
            np.array([0, 1, 0], dtype=np.float32),
            np.array([0, -1, 0], dtype=np.float32),
            np.array([0, 0, 1], dtype=np.float32),
            np.array([0, 0, -1], dtype=np.float32),
            np.array([0.707, 0.707, 0], dtype=np.float32),
            np.array([-0.707, 0.707, 0], dtype=np.float32),
            np.array([0.707, 0, 0.707], dtype=np.float32),
        ]
        # Distance from origin = max(existing bounding) + new_bounding + gap.
        max_existing_b = max(
            float(rec.get("bounding_radius", 0.0)) for rec in existing_roots.values()
        )
        radial = max_existing_b + new_bounding + DEFAULT_SAFETY_GAP
        best_pos = candidates[0] * radial
        best_score = -1.0
        for unit in candidates:
            pos = unit * radial
            # Score = minimum distance from pos to any existing root.
            mind = float("inf")
            for rec in existing_roots.values():
                r = np.array(rec["root_position"], dtype=np.float32)
                d = float(np.linalg.norm(pos - r))
                if d < mind:
                    mind = d
            if mind > best_score:
                best_score = mind
                best_pos = pos
        return best_pos

    # -------------------------------------------------------------------
    # Perimeter rescale (§6.6.1 — agent outputs to the outer envelope).
    # -------------------------------------------------------------------

    def _perimeter_rescale(
        self,
        coords: Dict[str, List[float]],
        chunk_meta: Dict[str, Dict[str, Any]],
        provenance: Dict[str, str],
    ) -> Dict[str, List[float]]:
        """Push ``agent-output``-provenance chunks to the workspace's
        outer perimeter (§6.6.1 perimeter-encompassing rescale).

        The Imaginary → Real return path is *geometric*: every emission
        from a self-conscious chamber lands on the outer envelope of
        the workspace's bounding region, never lost in its interior.
        The position vector is rescaled to live on the perimeter sphere
        at radius ``target_radius``; HSV channels stay untouched.

        Anti-goal §18.23: "Agent outputs lost to manifold interior".
        Verified by env-scenario ``perimeter-rescale`` (planned).
        """
        if not coords:
            return coords
        from backend.api.ws_frames import Provenance
        for cid, vec in list(coords.items()):
            # Re-read provenance from per-chunk metadata if present;
            # the projection-time provenance fallback is SCANNER_EMITTED.
            md = chunk_meta.get(cid) or {}
            prov = (md.get("provenance") or provenance.get(cid)
                    or Provenance.SCANNER_EMITTED)
            if prov != Provenance.AGENT_OUTPUT:
                continue
            # Position-only rescale to perimeter.
            pos = np.array(vec[:3], dtype=np.float32)
            n = float(np.linalg.norm(pos))
            if n < 1e-9:
                # Degenerate centre — drop to a hash-derived direction
                # on the perimeter sphere so two agent-output chunks
                # don't both end up at origin.
                fallback = self._hash_unit(cid, self.target_radius)
                pos = np.array(fallback[:3], dtype=np.float32)
            else:
                pos = pos * (self.target_radius / n)
            hsv_tail = list(vec[3:6]) if len(vec) >= 6 else [0.5, 0.5, 0.5]
            coords[cid] = [
                float(pos[0]), float(pos[1]), float(pos[2]),
                float(hsv_tail[0]), float(hsv_tail[1]), float(hsv_tail[2]),
            ]
            # Bump the provenance map so downstream consumers see the tag.
            provenance[cid] = Provenance.AGENT_OUTPUT
        return coords

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def recompute(
        self,
        *,
        min_docs: int = 8,
        workspace_id: str = "",
    ) -> Optional[LayoutFrame]:
        """Recompute canonical coords for the workspace's TF-IDF store.

        Returns the resulting :class:`LayoutFrame`, or ``None`` if the
        store doesn't have enough chunks yet.

        Fix: the global TF-IDF store is not yet workspace-scoped,
        so calling ``recompute(workspace_id=X)`` actually fits UMAP
        over EVERY chunk in the store regardless of which workspace
        owns it. For a single-workspace user this is fine; for
        multi-workspace setups it cross-contaminates the layout.
        We filter the chunk-id set by the store's per-chunk
        workspace_id metadata when present. Chunks missing the
        metadata fall through (treated as the default workspace).
        """
        # Lazy import to avoid module-load-time costs.
        from backend.services.global_tfidf_store import get_default_store
        store = get_default_store()
        n_docs = store.doc_count
        if n_docs < int(min_docs) or n_docs == 0:
            return None
        all_chunk_ids = list(store._chunk_ids)
        # The store's ``_chunk_meta`` is a LIST of ChunkMeta dataclasses
        # row-aligned with ``_chunk_ids`` (NOT a dict keyed by chunk_id —
        # treating it as one crashed every real scan-end broadcast with
        # `'list' object has no attribute 'get'`, found by the §16.5
        # probe). Build the cid→meta map once.
        meta_list = getattr(store, "_chunk_meta", None) or []
        meta_by_id: Dict[str, Any] = {}
        for i, cid in enumerate(all_chunk_ids):
            if i < len(meta_list) and meta_list[i] is not None:
                meta_by_id[str(cid)] = meta_list[i]

        def _ws_of(cid: str) -> str:
            """Workspace ownership of a stored row. ChunkMeta carries no
            workspace field — scanner-emitted rows are implicitly the
            default workspace (fall through, per the docstring above);
            ``graph__<ws>__…`` compute outputs encode theirs in the id."""
            m = meta_by_id.get(str(cid))
            w = (getattr(m, "workspace_id", "") or "") if m is not None else ""
            if w:
                return w
            s = str(cid)
            if s.startswith("graph__"):
                return s[len("graph__"):].split("__", 1)[0]
            return ""

        scope = workspace_id or ""
        if scope:
            chunk_ids = [
                cid for cid in all_chunk_ids
                if _ws_of(cid) in ("", scope)
            ]
        else:
            chunk_ids = all_chunk_ids
        # Re-check the min_docs threshold against the FILTERED set.
        if len(chunk_ids) < int(min_docs):
            return None
        # If we filtered, build a subset TF matrix via row-indexing.
        tf = store._tf
        if tf is None or tf.shape[0] != n_docs or tf.shape[1] == 0:
            return None
        if len(chunk_ids) != n_docs:
            # Subset the TF matrix to filtered chunks. Map chunk_id
            # to its row index in the store's matrix.
            id_to_row = {cid: i for i, cid in enumerate(all_chunk_ids)}
            row_indices = [id_to_row[cid] for cid in chunk_ids if cid in id_to_row]
            tf = tf[row_indices, :]
            n_docs = len(row_indices)
        # Build chunk_id -> url mapping from the row-aligned ChunkMeta.
        chunk_url_map: Dict[str, str] = {}
        for cid in chunk_ids:
            md = meta_by_id.get(str(cid))
            url = ""
            if md is not None:
                url = getattr(md, "url", "") or ""
                if not url:
                    urls = getattr(md, "urls", None) or []
                    url = urls[0] if urls else ""
            chunk_url_map[str(cid)] = url

        # Stage A: 6D projection (3 position + 3 HSV per §6.1, §1.8).
        coords = self._project(tf, [str(cid) for cid in chunk_ids])
        if not coords:
            return None
        # Stage B: per-URL post-processing.
        coords, url_roots = self._per_url_postprocess(coords, chunk_url_map)
        # Stage C: hard collider repulsion.
        coords = self._collider_repulsion(coords)

        # Provenance flag — scanner-emitted for all of these.
        from backend.api.ws_frames import Provenance
        provenance = {cid: Provenance.SCANNER_EMITTED for cid in coords.keys()}

        # Stage D: perimeter-encompassing rescale for agent-output chunks
        # (§6.6.1, §1.8). `_perimeter_rescale` reads a dict-shaped meta view
        # ({cid: {provenance}}); ChunkMeta rows carry no provenance field,
        # so the view falls through to the provenance map (agent-output
        # flags arrive via output_projection's own broadcasts).
        meta_view = {
            cid: {"provenance": getattr(meta_by_id.get(str(cid)), "provenance", "") or ""}
            for cid in coords.keys()
        }
        coords = self._perimeter_rescale(coords, meta_view, provenance)

        frame = LayoutFrame(
            workspace_id=workspace_id,
            coords=coords,
            url_roots=url_roots,
            provenance=provenance,
            updated_at=time.time(),
        )
        with self._lock:
            self._frames[workspace_id] = frame
        self.save_frame(workspace_id)
        return frame

    def recompute_and_broadcast(
        self,
        *,
        snapshot_id: int,
        workspace_id: str = "",
        min_docs: int = 8,
    ) -> Optional[LayoutFrame]:
        """Recompute and emit a ``umap_canonical`` frame (§11.5)."""
        frame = self.recompute(min_docs=min_docs, workspace_id=workspace_id)
        if frame is None:
            return None
        if self._broadcast is not None:
            from backend.api.ws_frames import build_umap_canonical
            payload = build_umap_canonical(
                workspace_id=workspace_id or "_default",
                coords=frame.coords,
                url_roots=frame.url_roots,
                provenance=frame.provenance,
            )
            try:
                self._broadcast(snapshot_id, payload)
            except Exception:
                # Broadcast failure should not crash the service; the
                # frontend can fetch via GET on reconnect.
                pass
        return frame


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_LAYOUT_SERVICE: Optional[LayoutService] = None
_LAYOUT_SERVICE_LOCK = threading.Lock()


def get_layout_service(
    broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> LayoutService:
    """Return the process-wide LayoutService singleton.

    The first caller may provide the broadcast hook; subsequent callers
    that omit it keep the existing hook. This lets ``routes.py`` (which
    owns ``_ws_push``) wire the broadcast on its first use while other
    services (mapper, scanner) can fetch the same instance without
    needing to know about the hook.
    """
    global _LAYOUT_SERVICE
    with _LAYOUT_SERVICE_LOCK:
        if _LAYOUT_SERVICE is None:
            _LAYOUT_SERVICE = LayoutService(broadcast=broadcast)
        elif broadcast is not None and _LAYOUT_SERVICE._broadcast is None:
            _LAYOUT_SERVICE._broadcast = broadcast
    return _LAYOUT_SERVICE
