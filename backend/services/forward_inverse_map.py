"""Forward-call inverse-lookup functional maps (§R.6 / §7.7).

Verbatim anchor (USER_REQUIREMENTS_VERBATIM.md §R.6):

    "The computation graph also has special features that integrate external
    memory creation through curly brace variable references and forward-call
    inverse-lookup functional maps that reflect their full state space of
    mappings in the database."

Before this module the inverse direction was similarity-only
(``ApparitionService.closest_inverse`` — the nomic triple-product
generalisation). Nothing recorded which inputs a forward call actually
consumed to produce which output, so the inverse map could not "reflect the
full state space of mappings in the database."

This module closes the loop:

* Every forward call (a ``ConceptComputeNode.compile`` dispatch) records its
  consumed ``{ref}`` inputs → output node as ``FORWARD_MAPPED_TO``
  **ConceptEdges** — a new member of the one-edge-table union enum (§3.2 —
  one edge table, never two), idempotent on the natural five-tuple, with the
  function identity carried in ``variable_name``.

* :func:`inverse_map` reads the full recorded state space for a node (the
  mappings INTO it as an output, and FROM it as an input).

* :func:`recorded_inverse_ids` feeds ``closest_inverse`` so EXACT recorded
  inverses rank ahead of the nomic-similarity generalisation (§7.7 — the
  recorded map is ground truth; similarity fills the unmapped remainder).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("uvicorn")

#: §3.2 — one-edge-table union member for recorded forward applications.
FORWARD_EDGE_TYPE = "FORWARD_MAPPED_TO"


def referenced_input_ids(node, graph_editor, workspace_id: str = "") -> List[str]:
    """The concept-ids ``node`` consumes via ``{slug}`` references in its
    data + description, resolved the way the cascade resolves (concept_id
    first, slugified name second; self-refs dropped). These are the forward
    call's *inputs*."""
    if node is None or graph_editor is None:
        return []
    try:
        from backend.services.compile_pipeline import _slugify, _CONCEPT_REF_RE
    except Exception:
        return []
    text = f"{getattr(node, 'data', '') or ''}\n{getattr(node, 'description', '') or ''}"
    if "{" not in text:
        return []
    try:
        nodes = graph_editor.list_concepts(workspace_id=workspace_id, limit=5000) or []
    except Exception:
        return []
    by_id = {getattr(n, "concept_id", "") or "": n for n in nodes}
    by_slug: Dict[str, str] = {}
    for n in nodes:
        by_slug.setdefault(
            _slugify(getattr(n, "name", "") or ""),
            getattr(n, "concept_id", "") or "",
        )
    own = getattr(node, "concept_id", "") or ""
    out: List[str] = []
    seen: Set[str] = set()
    for m in _CONCEPT_REF_RE.finditer(text):
        ref = m.group(1)
        tgt = ref if ref in by_id else by_slug.get(_slugify(ref), "")
        if tgt and tgt != own and tgt not in seen:
            seen.add(tgt)
            out.append(tgt)
    return out


def record_forward_call(
    graph_editor,
    *,
    output_id: str,
    input_ids: List[str],
    fn_signature: str = "",
    workspace_id: str = "",
) -> int:
    """Record one forward application: each consumed input maps to the
    output node via an idempotent ``FORWARD_MAPPED_TO`` ConceptEdge (the
    five-tuple natural key makes repeated cascade re-fires free — the
    state space holds *distinct* mappings, not call counts).

    ``fn_signature`` identifies the mapping's function (the dispatch kind +
    entry — e.g. ``python:backend.x:fn``, ``prompt``, ``structured:Schema``,
    ``template``); carried in ``variable_name``. Returns the number of edges
    ensured (created or already present)."""
    if graph_editor is None or not output_id:
        return 0
    n = 0
    for iid in input_ids or []:
        if not iid or iid == output_id:
            continue
        try:
            graph_editor.create_concept_edge(
                source_id=iid,
                target_id=output_id,
                edge_type=FORWARD_EDGE_TYPE,
                variable_name=fn_signature or "",
                workspace_id=workspace_id or "",
            )
            n += 1
        except Exception as exc:
            logger.warning(
                "forward_inverse_map: record %s -> %s failed: %s",
                iid, output_id, exc,
            )
    return n


def _edge_dict(e) -> Dict[str, Any]:
    return {
        "edge_id": getattr(e, "edge_id", ""),
        "source_id": getattr(e, "source_id", ""),
        "target_id": getattr(e, "target_id", ""),
        "fn_signature": getattr(e, "variable_name", "") or "",
        "workspace_id": getattr(e, "workspace_id", "") or "",
        "created_at": getattr(e, "created_at", "") or "",
    }


def inverse_map(
    graph_editor,
    node_id: str,
    *,
    workspace_id: str = "",
    limit: int = 2000,
) -> Dict[str, Any]:
    """§R.6 — the node's full recorded mapping state space:

    * ``as_output`` — every recorded mapping INTO ``node_id`` (the exact
      inverse lookup: which inputs forward-called into this output, under
      which function);
    * ``as_input`` — every recorded mapping FROM ``node_id`` (where this
      node's value has flowed forward).

    Pure read over the one edge table."""
    if graph_editor is None or not node_id:
        return {"node_id": node_id, "as_output": [], "as_input": []}
    try:
        into = graph_editor.list_concept_edges(
            workspace_id=workspace_id or None,
            target_id=node_id, edge_type=FORWARD_EDGE_TYPE, limit=limit,
        ) or []
    except Exception:
        into = []
    try:
        outof = graph_editor.list_concept_edges(
            workspace_id=workspace_id or None,
            source_id=node_id, edge_type=FORWARD_EDGE_TYPE, limit=limit,
        ) or []
    except Exception:
        outof = []
    return {
        "node_id": node_id,
        "as_output": [_edge_dict(e) for e in into],
        "as_input": [_edge_dict(e) for e in outof],
    }


def recorded_inverse_ids(
    graph_editor, output_id: str, *, workspace_id: str = "", limit: int = 200,
) -> List[str]:
    """The exact recorded inverse of ``output_id``: the input concept-ids
    with a ``FORWARD_MAPPED_TO`` edge into it, most-recent first. Feeds
    ``closest_inverse`` so ground-truth mappings rank ahead of nomic
    generalisation (§7.7)."""
    m = inverse_map(graph_editor, output_id, workspace_id=workspace_id, limit=limit)
    rows = sorted(
        m["as_output"], key=lambda d: d.get("created_at", ""), reverse=True,
    )
    out: List[str] = []
    seen: Set[str] = set()
    for r in rows:
        sid = r.get("source_id", "")
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out
