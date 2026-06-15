"""
chunk_projector_service.py -- UMAP 6D projection of every ``ChunkInstance``
into (XYZ spatial, RGB color) node records.

STATUS (2026-04-29): NOT wired into the live API. The frontend chunk
projector (``backend/static/js/chunk_projector.js``) computes coordinates
and colors deterministically from each id's hash on the *client* side
via ``ChunkProjector.layOutNode``. The live ``/api/chunk_nodes`` endpoint
in ``backend/api/routes.py`` ships only ``{id, url, is_document, doc_id}``
rows — no x/y/z, no r/g/b — and never calls into this module.

This file is kept for **offline analysis** only. Two consumers:

  * ``diag_chunk_projector.py`` — the user's CLI debug script that prints
    the UMAP-projected node set against the current Kuzu state.
  * Future "deep / semantic" projector views that opt in to dense
    embeddings (after #4 the dense GGUF embedder is lazy, so most
    ``ChunkInstance.embedding`` rows are empty until a deep-search
    user explicitly populates them).

Implementation details (unchanged):

This mirrors the strategy used by ``old_projector_user_interface/app.py`` for
companies: fit UMAP with ``n_components=6`` once over the corpus, take the
first three components as spatial coordinates and the last three as color.

Two differences from the reference app:

1. We operate on rows coming out of Kuzu (``load_all_instances``) instead of
   a one-shot CSV load, so the set of nodes changes as the user scans more
   URLs. We therefore recompute UMAP on demand and cache the result by a
   fingerprint of the input embeddings (``count + sha1 of instance_ids``).
2. We fall back to a 3D-only projection when there are too few samples for
   the spectral initializer to decompose a 6D basis -- same guard as in
   ``demo_scanner.umap_scatter_from_db``. In that case color falls back to
   a neutral gray.

The returned node record carries the raw content-distilled HTML
(``html_raw``) so the frontend can display it as read-only text in the
billboard without a second round trip.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.services.chunk_containment import filter_redundant_rollups
from backend.services.chunk_instance_persistence import (
    ChunkInstanceRow,
    load_all_instances,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass
class ChunkProjectorNode:
    """One 3D projector node, ready to render as a sphere + billboard."""

    id: str                    # ChunkInstance.instance_id
    chunk_id: str
    pattern_id: str
    url: str
    absolute_xpath: str
    html_raw: str
    rendered_text: str
    x: float
    y: float
    z: float
    r: float
    g: float
    b: float


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


_CACHE: Dict[str, List[ChunkProjectorNode]] = {}


def _fingerprint(rows: List[ChunkInstanceRow]) -> str:
    """Stable key for the cache -- changes whenever the set of rows changes."""
    if not rows:
        return "empty"
    h = hashlib.sha1()
    h.update(str(len(rows)).encode("utf-8"))
    # Sort for order-independence.
    for iid in sorted(r.instance_id for r in rows):
        h.update(iid.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()[:20]


# ---------------------------------------------------------------------------
# UMAP driver
# ---------------------------------------------------------------------------


def _fit_umap(X: np.ndarray) -> Tuple[np.ndarray, int]:
    """Fit a 6D (or 3D fallback) UMAP and return ``(Y, n_components)``.

    Follows the same "n_samples > n_components + 1 strictly" guard as the
    demo scanner: UMAP's spectral initializer requires at least
    ``n_components + 2`` samples to be stable. With fewer than 8 rows we
    drop to a 3D-only projection rather than erroring.
    """
    import umap  # local import -- expensive module

    n_rows = X.shape[0]
    n_components = 6 if n_rows >= 8 else 3
    n_neighbors = min(15, max(2, n_rows - 1))
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        metric="cosine",
        random_state=42,
    )
    Y = reducer.fit_transform(X)
    return Y, n_components


def _normalize_xyz(xyz: np.ndarray, *, radius: float = 8.0) -> np.ndarray:
    """Center on origin and scale so the farthest point sits at ``radius``."""
    if xyz.shape[0] == 0:
        return xyz
    centroid = xyz.mean(axis=0, keepdims=True)
    centered = xyz - centroid
    span = float(np.linalg.norm(centered, axis=1).max() or 1.0)
    return centered * (radius / span)


def _normalize_rgb(rgb: np.ndarray) -> np.ndarray:
    """Per-channel MinMax normalize into [0, 1]."""
    if rgb.shape[0] == 0:
        return rgb
    mn = rgb.min(axis=0, keepdims=True)
    mx = rgb.max(axis=0, keepdims=True)
    spread = np.maximum(mx - mn, 1e-6)
    return (rgb - mn) / spread


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_chunk_projector_nodes(
    conn,
    *,
    min_rows: int = 4,
    radius: float = 8.0,
    use_cache: bool = True,
) -> List[ChunkProjectorNode]:
    """Return one :class:`ChunkProjectorNode` per ChunkInstance in the DB.

    Empty list when there are fewer than ``min_rows`` instances available --
    UMAP's eigendecomp is ill-defined below that threshold and the frontend
    can render the "empty state" message instead.
    """
    rows = load_all_instances(conn)
    rows = [r for r in rows if r.embedding and len(r.embedding) == 768]

    # Drop strict-ancestor rollup chunks before UMAP so the projection
    # isn't warped by a handful of monster 50+ KB "swallow everything"
    # nodes whose fine-grained children are already represented. Keyed
    # on absolute xpath per URL so rollups on page A don't accidentally
    # nuke unrelated chunks on page B that happen to share a prefix.
    #
    # Size gate: only drop ancestors whose html_raw exceeds the chunker's
    # hard HTML-char budget. A legitimate card-sized chunk containing a
    # smaller title-sized chunk is both within budget and is never
    # pruned. Only pathological rollups produced by older chunker runs
    # (that persisted data pre-dating the parent-contribution heuristic)
    # still qualify. Threshold = 2× hard limit so we stay well away from
    # anything the new chunker can legitimately emit.
    from backend.mapper.chunk_builder import HARD_CHAR_LIMIT
    rollup_threshold = 2 * HARD_CHAR_LIMIT

    by_url: Dict[str, List[ChunkInstanceRow]] = {}
    for r in rows:
        by_url.setdefault(r.url, []).append(r)
    pruned: List[ChunkInstanceRow] = []
    for url_rows in by_url.values():
        pruned.extend(
            filter_redundant_rollups(
                url_rows,
                xpath_of=lambda x: x.absolute_xpath,
                size_of=lambda x: len(x.html_raw or ""),
                min_rollup_size=rollup_threshold,
            )
        )
    if len(pruned) != len(rows):
        logger.info(
            "chunk projector: containment-pruned %d → %d rows before UMAP "
            "(rollup_threshold=%d)",
            len(rows), len(pruned), rollup_threshold,
        )
    rows = pruned

    if len(rows) < min_rows:
        logger.info(
            "chunk projector: %d rows available -- need >= %d for UMAP",
            len(rows), min_rows,
        )
        return []

    fp = _fingerprint(rows)
    if use_cache and fp in _CACHE:
        logger.debug("chunk projector: cache hit for fingerprint %s", fp)
        return _CACHE[fp]

    X = np.asarray([r.embedding for r in rows], dtype=np.float32)
    logger.info(
        "chunk projector: fitting UMAP on %d x %d embeddings",
        X.shape[0], X.shape[1],
    )
    Y, n_components = _fit_umap(X)

    xyz = _normalize_xyz(Y[:, :3], radius=radius)
    if n_components == 6:
        rgb = _normalize_rgb(Y[:, 3:6])
    else:
        # Not enough samples for the color split -- use a middle-gray tone.
        rgb = np.full((X.shape[0], 3), 0.55, dtype=np.float32)

    nodes: List[ChunkProjectorNode] = []
    for row, (x, y, z), (r, g, b) in zip(rows, xyz, rgb):
        nodes.append(
            ChunkProjectorNode(
                id=row.instance_id,
                chunk_id=row.chunk_id,
                pattern_id=row.pattern_id,
                url=row.url,
                absolute_xpath=row.absolute_xpath,
                html_raw=row.html_raw,
                rendered_text=row.rendered_text,
                x=float(x), y=float(y), z=float(z),
                r=float(r), g=float(g), b=float(b),
            )
        )

    if use_cache:
        _CACHE.clear()
        _CACHE[fp] = nodes
    return nodes


def invalidate_cache() -> None:
    """Call this when a new scan lands to force a fresh UMAP fit."""
    _CACHE.clear()


def node_to_dict(n: ChunkProjectorNode) -> Dict[str, Any]:
    return asdict(n)
