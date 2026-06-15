"""Rank-dominance over the ConceptEdge graph (DOMAIN §8.1.2; Q.3-Q.6).

This module computes the *dominated set* of a node — the structural
containment/reachability set that the generalized rank-dominance collapse
gesture (§6.6.5 in 3D / §7.3.5 in 2D) folds and (in the 3D projector)
isolates.

Q.6 finding (checked, recorded in USER_REQUIREMENTS_VERBATIM §Q.6):
rank-dominance and PageRank are computed over the **same** ConceptEdge
graph (the one-edge-table invariant, §3.2) but are **distinct** measures.
PageRank is the stationary-distribution **centrality** weight used
multiplicatively in the retrieval triple product (§8.1). Rank-dominance is
the **containment/reachability ordering** (a dominator relation) that
defines *which* descendants a collapse hides. They are aligned but not
identical: a dominator (a root-URL hub, a bisector compute node) tends to
be a high-PageRank hub *because* it dominates many nodes, so PageRank is
the **collapse-onto heuristic** (which node to fold onto) while the
dominated-set reachability is the collapse **membership** (what folds and
hides). This module computes membership; PageRank lives in
``concept_index_service`` and reuses the same Kuzu edge traversal — no
second graph, no second edge table.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple


def build_chunk_url_map(store: Any) -> Dict[str, str]:
    """Build ``{chunk_id: url}`` from a TF-IDF store's per-chunk metadata.

    Defensive against the two shapes ``_chunk_meta`` takes across the
    codebase: a ``list[ChunkMeta]`` (global_tfidf_store) or a
    ``dict[chunk_id, dict]`` (the layout refit's view). Returns ``{}`` if
    no metadata is available rather than raising — a fresh workspace with
    no scans simply has an empty map.
    """
    out: Dict[str, str] = {}
    meta = getattr(store, "_chunk_meta", None)
    if isinstance(meta, dict):
        for cid, md in meta.items():
            if isinstance(md, dict):
                url = md.get("url") or md.get("page_url") or ""
            else:
                url = getattr(md, "url", "") or ""
            out[str(cid)] = url or ""
    elif isinstance(meta, (list, tuple)):
        for m in meta:
            if isinstance(m, dict):
                cid = m.get("chunk_id")
                url = m.get("url") or m.get("page_url") or ""
            else:
                cid = getattr(m, "chunk_id", None)
                url = getattr(m, "url", "") or ""
            if cid is not None:
                out[str(cid)] = url or ""
    return out


def build_adjacency(edges: Iterable[Any]) -> Dict[str, List[str]]:
    """Build a forward-adjacency ``{source_id: [target_id, ...]}`` from an
    edge iterable. Accepts ConceptEdge objects (``.source_id`` /
    ``.target_id``) or dicts (``source_id`` / ``target_id``) — the shapes
    ``graph_editor.list_concept_edges`` and the REST ``edges`` payload
    return. This is the SAME edge set PageRank traverses (§8.1.2), so
    rank-dominance and PageRank share one graph (the one-edge-table
    invariant, §3.2)."""
    adj: Dict[str, List[str]] = {}
    for e in edges or []:
        if isinstance(e, dict):
            s = e.get("source_id")
            t = e.get("target_id")
        else:
            s = getattr(e, "source_id", None)
            t = getattr(e, "target_id", None)
        if s and t:
            adj.setdefault(str(s), []).append(str(t))
    return adj


def forward_reachable(
    start: str,
    adj: Dict[str, List[str]],
    *,
    max_nodes: int = 100_000,
) -> Set[str]:
    """Forward-reachable descendants of ``start`` over the ConceptEdge graph.

    ``adj`` is the forward adjacency from :func:`build_adjacency` over the
    SAME edge set PageRank runs on (§8.1.2). This is the rank-dominance
    reachability set used when ``start`` is a compute/bisector node whose
    dominated members (its input + output/readout distributions) are wired
    as ConceptEdges. Cycle-safe (visited set); ``start`` excluded.
    """
    seen: Set[str] = set()
    stack: List[str] = [start]
    while stack and len(seen) < max_nodes:
        n = stack.pop()
        for t in adj.get(n, ()):
            if t and t != start and t not in seen:
                seen.add(t)
                stack.append(t)
    return seen


def compute_dominance_sets(
    node_id: str,
    *,
    coords_keys: Iterable[str],
    url_root_keys: Iterable[str],
    chunk_url_map: Dict[str, str],
    edges: Optional[Iterable[Any]] = None,
) -> Tuple[List[str], List[str]]:
    """Return ``(folded_set, hidden_set)`` for collapsing ``node_id``.

    - **folded_set** — the dominator's *dominated/contained* set
      (rank-dominance, §8.1.2). For a **root-URL doc-hub** (a node keyed by
      its url string) this is every chunk whose url equals ``node_id``
      (Q.3: "collapse its chunk samples"). For a **compute/bisector node**
      (Q.4) this is the ConceptEdge forward-reachable descendants — its
      input + output/readout distribution members wired into it.
    - **hidden_set** — every *other* currently-visible node (the 3D
      isolate, Q.3: "all other nodes disappear except the url node").

    Both sets visually disappear on collapse (the dominator alone remains);
    the distinction is semantic: the folded set is *folded into* the
    dominator and restored around it on re-expand, the hidden set is the
    rest of the manifold isolated away. ``coords_keys`` are the projector's
    chunk ids; ``url_root_keys`` the doc-hub url strings.
    """
    coords_set: Set[str] = {str(k) for k in coords_keys}
    url_roots: Set[str] = {str(k) for k in url_root_keys}
    # The projector's visible set IS the chunk store: every scanned chunk
    # (chunk_url_map keys) and every distinct url-root (its values) is a
    # node in 3D, independent of whether a per-workspace LayoutFrame has
    # been persisted yet. Union all three so the isolate (Q.3) hides every
    # OTHER node, not just those in a particular workspace's frame.
    chunk_ids: Set[str] = {str(c) for c in chunk_url_map.keys()}
    chunk_urls: Set[str] = {str(u) for u in chunk_url_map.values() if u}
    all_visible: Set[str] = coords_set | url_roots | chunk_ids | chunk_urls

    is_url_root = node_id in url_roots or any(
        u == node_id for u in chunk_url_map.values()
    )

    folded: Set[str]
    if is_url_root:
        folded = {
            str(cid)
            for cid, url in chunk_url_map.items()
            if url == node_id
        }
    elif edges is not None:
        folded = forward_reachable(node_id, build_adjacency(edges))
    else:
        folded = set()

    hidden = all_visible - {node_id} - folded
    return sorted(folded), sorted(hidden)
