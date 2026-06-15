"""Concept-mutation lifecycle hooks (DRY/KISS — domain anchor §8D.44).

Every ConceptNode create / update / delete triggers the same downstream
chain:

  1. Multi-tab WebSocket broadcast (other tabs hydrate without polling).
  2. ConceptIndex slot upsert / remove (W5 / §11.6 — embedding +
     PageRank).
  3. Output-projection schedule (W7 / §8D.19 / §8D.41 — peripheral
     concept-output 3D projection debounce).
  4. Evolution-log entry (C5 / §8D.33 — diff-consistent rollback).

Centralising the chain in one module keeps both the REST handlers
(``routes.py``) and the agent's ``ActionResolver`` (``agent_runtime``)
on a single code path. Anything that mutates a concept calls these
helpers; nothing downstream is forgotten.

Each helper swallows internal errors and prints a tagged warning so a
secondary subsystem hiccup never blocks the primary mutation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from backend.services.ids import ConceptId, EdgeId, WorkspaceId

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Functional core — pure diff classification of a concept mutation.
#
# Side-effect helpers below (broadcast / index / projection / log / cascade)
# consume the diff; the diff is computed once and read many times. Pulling
# the decision logic out of the imperative chain lets us:
#   * Test each branch in isolation (no I/O stubs needed).
#   * Reason about "what changed" without scanning the chain.
#   * Avoid the three-different-heuristic problem the embed-detection
#     code had before (routes peeked at PATCH keys; agent peeked at
#     field name; spine_delta hard-coded False).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConceptDiff:
    """Pure classification of a concept update. Built once from
    pre/post; all downstream decisions read from this object instead
    of re-deriving heuristics inline.

    ``backing_version_bumped`` (§8D.39.6) is set when the node's
    backing-pointer version seq has been bumped by the scanner
    subsystem since the last record snapshot. The lifecycle treats
    a bump as an effective ``data_changed`` so dependent compiles
    re-fire against the new implementation even when the visible
    ``data`` text is byte-identical.
    """
    data_changed: bool
    description_changed: bool
    rendering_changed: bool
    workspace_id: str
    is_create: bool = False
    backing_version_bumped: bool = False

    @property
    def embed_fields_changed(self) -> bool:
        """True iff a field that feeds the ConceptIndex moved.
        Description drives nomic; rendering drives TF-IDF. A
        backing-version bump alone does NOT re-embed — it only
        invalidates downstream compiles."""
        return self.description_changed or self.rendering_changed

    @property
    def effective_data_changed(self) -> bool:
        """True iff downstream compiles should re-fire — either the
        ``data`` text changed OR the backing implementation was
        re-versioned (§8D.39.6)."""
        return self.data_changed or self.backing_version_bumped

    @classmethod
    def from_pre_post(
        cls,
        pre_dict: Optional[Dict[str, Any]],
        node,
        *,
        pre_backing_version: Optional[int] = None,
    ) -> "ConceptDiff":
        """Compute the diff. ``pre_dict`` ``None`` means create.

        ``pre_backing_version`` is the backing-version seq as captured
        at the pre snapshot; the diff compares against the current
        backing-version registry to decide whether to flip
        ``backing_version_bumped`` (§8D.39.6).
        """
        ws_id = getattr(node, "workspace_id", "") or ""
        backing_ptr = getattr(node, "backing_pointer", "") or ""

        if pre_dict is None:
            return cls(
                data_changed=True,
                description_changed=True,
                rendering_changed=True,
                workspace_id=ws_id,
                is_create=True,
                backing_version_bumped=False,
            )

        version_bumped = False
        if backing_ptr and pre_backing_version is not None:
            try:
                from backend.services.backing_version import current as _bv_current
                cur = _bv_current(ws_id, backing_ptr)
                version_bumped = cur > int(pre_backing_version)
            except Exception:
                version_bumped = False

        pre_data = pre_dict.get("data") or ""
        pre_desc = pre_dict.get("description") or ""
        pre_rend = pre_dict.get("rendering") or ""
        return cls(
            data_changed=(pre_data != (getattr(node, "data", "") or "")),
            description_changed=(pre_desc != (getattr(node, "description", "") or "")),
            rendering_changed=(pre_rend != (getattr(node, "rendering", "") or "")),
            workspace_id=ws_id,
            is_create=False,
            backing_version_bumped=version_bumped,
        )


# ---------------------------------------------------------------------------
# WebSocket broadcast
# ---------------------------------------------------------------------------

def broadcast_concept_changed(
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]],
    *,
    change: str,
    concept_id: ConceptId,
    workspace_id: WorkspaceId = WorkspaceId(""),
    concept: Optional[Dict[str, Any]] = None,
) -> None:
    """Push a ``concept_changed`` WS frame so other tabs / clients sync."""
    if push_fn is None:
        return
    try:
        from backend.api.ws_frames import build_concept_changed
        push_fn(0, build_concept_changed(
            workspace_id=workspace_id or "_default",
            concept_id=concept_id,
            change=change,
            concept=concept,
        ))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# ConceptIndex slot up/remove
# ---------------------------------------------------------------------------

def upsert_concept_index_for(
    node,
    ge,
    *,
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> None:
    """Upsert the ConceptIndex slot for ``node`` (W5 / §11.6)."""
    if node is None:
        return
    try:
        from backend.services.concept_index_service import (
            get_concept_index_service, pattern_hash_from_data,
        )
        svc = get_concept_index_service(broadcast=push_fn, graph_editor=ge)
        svc.upsert_slot(
            card_id=node.concept_id,
            description=node.description,
            rendering=node.rendering,
            provenance=node.provenance,
            workspace_id=node.workspace_id,
            # §8.1.1 pattern band — the structural bucket from the card's data
            # (generalised xpath, present on scanner-emitted chunk_instances).
            pattern_hash=pattern_hash_from_data(getattr(node, "data", "") or ""),
        )
    except Exception as e:
        logger.warning("ConceptIndex upsert failed for %s: %s",
                       getattr(node, "concept_id", "?"), e)


def remove_concept_index_for(
    concept_id: ConceptId,
    ge,
    *,
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> None:
    """Remove the ConceptIndex slot for ``concept_id`` (W5 / §11.6)."""
    try:
        from backend.services.concept_index_service import get_concept_index_service
        svc = get_concept_index_service(broadcast=push_fn, graph_editor=ge)
        svc.remove_slot(concept_id)
    except Exception as e:
        logger.warning("ConceptIndex remove failed for %s: %s", concept_id, e)


# ---------------------------------------------------------------------------
# Output-projection debounce
# ---------------------------------------------------------------------------

def schedule_output_projection(
    workspace_id: WorkspaceId,
    ge,
    *,
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> None:
    """Arm the debounced peripheral output projection (W7 / §8D.41)."""
    try:
        from backend.services.output_projection import get_output_projection_service
        from backend.services.layout_service import get_layout_service
        proj = get_output_projection_service(
            broadcast=push_fn, graph_editor=ge,
            layout_service=get_layout_service(broadcast=push_fn),
        )
        proj.schedule_recompute(workspace_id=workspace_id or "")
    except Exception as e:
        logger.warning("OutputProjection schedule failed for ws=%r: %s",
                       workspace_id, e)


# ---------------------------------------------------------------------------
# Evolution log
# ---------------------------------------------------------------------------

def log_evolution(
    *,
    target: str,
    kind: str,
    before: Optional[Dict[str, Any]],
    after: Optional[Dict[str, Any]],
    workspace_id: str = "",
    ge=None,
    actor: str = "user:_anon",
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> None:
    """Record an evolution-log diff entry (C5 / §8D.33).

    If ``push_fn`` is provided (or the singleton already has one wired),
    each append also emits an ``evolution_log_diff`` WS frame so any
    open log-viewer panel updates without polling.
    """
    try:
        from backend.services.evolution_log import get_evolution_log
        get_evolution_log(graph_editor=ge, broadcast=push_fn).log(
            workspace_id=workspace_id,
            actor=actor,
            target=target,
            kind=kind,
            before=before,
            after=after,
        )
    except Exception as e:
        logger.warning("EvolutionLog %s logging failed for %s: %s",
                       kind, target, e)


# ---------------------------------------------------------------------------
# §8D.20 — auto-derive the rendering field from data
# ---------------------------------------------------------------------------

def derive_rendering_for(node, ge) -> Optional[str]:
    """Compute the syntax-free ``rendering`` for ``node`` from its ``data``.

    Returns the new rendering string (may be the same as the current
    one — caller can decide whether to persist). Returns ``None`` if
    the pipeline raised. §8D.20 contract: no braces, brackets, colons,
    or quotes; indentation alone carries structure.
    """
    if node is None:
        return None
    try:
        from backend.services.compile_pipeline import compute_rendering_tree
        return compute_rendering_tree(node.data or "", ge=ge)
    except Exception as e:
        logger.warning("Lifecycle derive rendering failed for %s: %s",
                       getattr(node, "concept_id", "?"), e)
        return None


def maybe_persist_rendering(node, ge) -> bool:
    """If ``node.rendering`` is stale or empty, derive and persist."""
    if node is None or ge is None:
        return False
    new_rendering = derive_rendering_for(node, ge)
    if new_rendering is None:
        return False
    current = getattr(node, "rendering", "") or ""
    if new_rendering == current:
        return False
    try:
        updated = ge.update_concept(node.concept_id, rendering=new_rendering)
        if updated is not None:
            # Mutate the in-memory node so subsequent helpers in the
            # same chain see the fresh rendering without a re-fetch.
            node.rendering = new_rendering
            return True
    except Exception as e:
        logger.warning("Lifecycle persist rendering failed for %s: %s",
                       node.concept_id, e)
    return False


# ---------------------------------------------------------------------------
# Edge-mutation broadcast
# ---------------------------------------------------------------------------

def broadcast_edge_changed(
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]],
    *,
    change: str,
    edge_id: EdgeId,
    workspace_id: WorkspaceId = WorkspaceId(""),
    edge: Optional[Dict[str, Any]] = None,
) -> None:
    """Push an ``edge_changed`` WS frame for multi-tab edge-set sync."""
    if push_fn is None or not edge_id:
        return
    try:
        from backend.api.ws_frames import build_edge_changed
        push_fn(0, build_edge_changed(
            workspace_id=workspace_id or "_default",
            edge_id=edge_id,
            change=change,
            edge=edge,
        ))
    except Exception:
        pass


def _edge_to_dict(edge) -> Dict[str, Any]:
    """Wire-shaped concept-edge dict. Mirrors ``routes._edge_to_dict``
    so the lifecycle chain doesn't have to reach back into routes.py
    (would create a circular import). The two must stay in sync — if
    new edge fields land, update both."""
    if edge is None:
        return {}
    return {
        "edge_id": getattr(edge, "edge_id", ""),
        "source_id": getattr(edge, "source_id", ""),
        "target_id": getattr(edge, "target_id", ""),
        "edge_type": getattr(edge, "edge_type", "RELATES_TO"),
        "source_port": getattr(edge, "source_port", ""),
        "target_port": getattr(edge, "target_port", ""),
        "weight": getattr(edge, "weight", None),
        "variable_name": getattr(edge, "variable_name", ""),
        "workspace_id": getattr(edge, "workspace_id", ""),
        "created_at": getattr(edge, "created_at", ""),
    }


def apply_edge_create_lifecycle(
    edge,
    ge,
    *,
    workspace_id: str = "",
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> Optional[Dict[str, Any]]:
    """Run the full create chain for a new ``ConceptEdge`` — broadcast
    + output-projection schedule. Returns the wire-shaped edge dict.

    Centralised so REST handlers, the agent's link emitter, the spawn
    helper's wiring step, and the fork helper all use one code path.
    Each used to pack its own edge dict + call broadcast + schedule;
    the four were drifting apart (missing fields, inconsistent
    workspace_id resolution).
    """
    if edge is None:
        return None
    edge_dict = _edge_to_dict(edge)
    # Dict.get returns Any|str; the NewType-strict downstream
    # signatures want concrete EdgeId / WorkspaceId. The constructors
    # are zero-cost runtime str wrappers, so cast at the boundary
    # rather than weakening the broadcast/scheduler signatures.
    ws = WorkspaceId(str(workspace_id or edge_dict.get("workspace_id") or ""))
    edge_id = EdgeId(str(edge_dict.get("edge_id") or ""))
    broadcast_edge_changed(
        push_fn, change="created",
        edge_id=edge_id,
        workspace_id=ws,
        edge=edge_dict,
    )
    # An edge add can flip both endpoints from peripheral to
    # intermediate (or vice-versa on delete); §8D.41 says these
    # transitions retire / spawn 3D chunks. The Layout Service
    # picks up the change on the next debounce.
    schedule_output_projection(ws, ge, push_fn=push_fn)
    return edge_dict


def apply_edge_delete_lifecycle(
    edge_id: EdgeId,
    workspace_id: WorkspaceId,
    ge,
    *,
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> None:
    """Run the full delete chain for an existing ``ConceptEdge`` —
    broadcast + output-projection schedule. Counterpart to
    ``apply_edge_create_lifecycle``."""
    if not edge_id:
        return
    broadcast_edge_changed(
        push_fn, change="deleted",
        edge_id=edge_id, workspace_id=workspace_id, edge=None,
    )
    schedule_output_projection(workspace_id, ge, push_fn=push_fn)


# ---------------------------------------------------------------------------
# Full-chain convenience for actor-aware mutations
# ---------------------------------------------------------------------------

def apply_create_lifecycle(
    node,
    ge,
    *,
    actor: str = "user:_anon",
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    node_dict: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Run the full create-lifecycle chain for a freshly-created concept node.

    Returns the final wire-shaped concept dict (post-rendering-derivation)
    so the caller can return it from a REST handler without having to
    re-serialise.
    """
    if node is None:
        return None
    # §8D.20 — derive rendering BEFORE the broadcast / index / projection
    # so peer tabs, the embedding service, and the output projector all
    # see the same syntax-free tree on first emission. If rendering was
    # explicitly supplied (e.g., a foundation fixture), keep it.
    rendering_refreshed = False
    if not (getattr(node, "rendering", "") or "").strip():
        rendering_refreshed = maybe_persist_rendering(node, ge)
    # Re-serialise after the in-place rendering update so the broadcast
    # carries the fresh tree (the caller's pre-call dict captured the
    # empty rendering and would otherwise mislead peer tabs).
    if rendering_refreshed or node_dict is None:
        node_dict = _node_to_dict(node)
    log_evolution(
        target=f"card:{node.concept_id}", kind="create",
        before=None, after=node_dict,
        workspace_id=node.workspace_id, ge=ge, actor=actor,
        push_fn=push_fn,
    )
    broadcast_concept_changed(
        push_fn, change="created",
        concept_id=node.concept_id, workspace_id=node.workspace_id,
        concept=node_dict,
    )
    upsert_concept_index_for(node, ge, push_fn=push_fn)
    schedule_output_projection(node.workspace_id, ge, push_fn=push_fn)
    return node_dict


# ---------------------------------------------------------------------------
# §8D.38.4 — the general {ref}-consumer cascade ("Cascade is the default").
# A DATA edit recompiles the downstream cards that reference the edited card
# via a {slug} token (their resolved value changed). This is distinct from the
# agent-tick CascadeScheduler (agent_runtime) which schedules meta-cognition
# ticks for agent body cards. Cycle-safe (visited-set) + depth-capped; the
# nested compile-persists run as actor="conceptual_compute", which is excluded
# from re-triggering this cascade, so the BFS here is the SOLE authority for the
# transitive walk (no recompile storm). Cross-actor is last-write-wins (§2.7).
# ---------------------------------------------------------------------------
_CASCADE_MAX_DEPTH = 16   # constants.md §3 CASCADE_MAX_DEPTH — recursion guard


def _find_ref_consumers(target_node, ge):
    """Workspace cards whose ``data``/``description`` reference ``target_node``
    via a ``{slug}`` token that resolves to it — matched exactly the way
    ``compile_pipeline.resolve_concept_refs`` resolves (by ``concept_id`` or by
    slugified ``name``). Read-only walk."""
    try:
        from backend.services.compile_pipeline import _slugify, _CONCEPT_REF_RE
    except Exception:
        return []
    target_id = getattr(target_node, "concept_id", "") or ""
    target_slug = _slugify(getattr(target_node, "name", "") or "")
    target_ws = getattr(target_node, "workspace_id", "") or ""
    if not (target_id or target_slug):
        return []
    try:
        # §1.10 workspace isolation — scope the referrer walk to the edited
        # card's OWN workspace. A `{ref}` never resolves across workspaces, so
        # the cascade must NEVER recompile a consumer in a different workspace
        # (editing workspace A's card must not touch workspace B). The purge
        # path scopes list_concepts the same way.
        candidates = ge.list_concepts(workspace_id=target_ws, limit=5000) or []
    except Exception:
        return []
    out = []
    for c in candidates:
        if getattr(c, "concept_id", "") == target_id:
            continue
        text = f"{getattr(c, 'data', '') or ''}\n{getattr(c, 'description', '') or ''}"
        if "{" not in text:
            continue
        for m in _CONCEPT_REF_RE.finditer(text):
            ref = m.group(1)
            if ref == target_id or _slugify(ref) == target_slug:
                out.append(c)
                break
    return out


def _cascade_recompile_consumers(target_node, ge, *, push_fn=None):
    """§8D.38.4 — BFS-recompile the transitive ``{ref}``-consumers of an edited
    card. Each consumer recompiles via ``ConceptComputeNode(...).compile()``
    (which persists its new rendering through the lifecycle with
    actor="conceptual_compute" — excluded from re-entering this cascade). The
    visited-set + ``_CASCADE_MAX_DEPTH`` cap make it cycle-safe and bounded."""
    try:
        from backend.services.conceptual_compute import ConceptComputeNode
    except Exception:
        return
    visited: set = set()
    frontier = [(target_node, 0)]
    while frontier:
        cur, depth = frontier.pop(0)
        if depth >= _CASCADE_MAX_DEPTH:
            continue
        for consumer in _find_ref_consumers(cur, ge):
            cid = getattr(consumer, "concept_id", "") or ""
            if not cid or cid in visited:
                continue
            visited.add(cid)
            try:
                ConceptComputeNode(
                    cid, graph_editor=ge, broadcast=push_fn,
                    persist_rendering=True,
                ).compile()
            except Exception:
                pass
            try:
                refreshed = ge.get_concept(cid)
            except Exception:
                refreshed = None
            frontier.append((refreshed or consumer, depth + 1))


def apply_update_lifecycle(
    node,
    ge,
    *,
    pre_dict: Optional[Dict[str, Any]],
    embed_fields_changed: Optional[bool] = None,
    actor: str = "user:_anon",
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    node_dict: Optional[Dict[str, Any]] = None,
    data_changed: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Run the full update-lifecycle chain for a modified concept node.

    ``data_changed`` — if True (or None and we can detect it from the
    pre/post diff), re-derive the §8D.20 rendering before broadcasting.
    Pass ``False`` explicitly to skip (e.g. layout_xy-only updates).

    ``embed_fields_changed`` — controls whether the ConceptIndex slot is
    re-embedded. When ``None`` (the default) the helper diffs ``pre_dict``
    against the live node and re-embeds iff ``description`` or
    ``rendering`` actually moved. Pass an explicit ``False`` to skip
    even when the embedded fields shifted (e.g. agent self-mutation
    that only touched ``data``).

    Returns the wire-shaped concept dict after rendering derivation so
    the REST handler can return the freshest copy.
    """
    if node is None:
        return None
    # Functional-core diff: classify the update once; downstream
    # decisions consume the diff instead of re-deriving heuristics.
    diff = ConceptDiff.from_pre_post(pre_dict, node)
    # Caller overrides take precedence when explicit — useful for
    # spine_delta (data-only, no embed touch).
    effective_data_changed = (
        data_changed if data_changed is not None else diff.data_changed
    )
    effective_embed_changed = (
        embed_fields_changed if embed_fields_changed is not None
        else diff.embed_fields_changed
    )
    # §8D.20 — when ``data`` changed, refresh the rendering tree so
    # embeddings + output projection track the latest authored
    # content. A rendering refresh implies embed_fields_changed too.
    rendering_refreshed = False
    if effective_data_changed:
        rendering_refreshed = maybe_persist_rendering(node, ge)
        if rendering_refreshed:
            effective_embed_changed = True
    # Re-serialise so the broadcast + the REST response both carry the
    # fresh rendering. If the caller pre-built node_dict and rendering
    # changed, that dict is stale and must be rebuilt.
    if rendering_refreshed or node_dict is None:
        node_dict = _node_to_dict(node)
    log_evolution(
        target=f"card:{node.concept_id}", kind="modify",
        before=pre_dict, after=node_dict,
        workspace_id=node.workspace_id, ge=ge, actor=actor,
        push_fn=push_fn,
    )
    broadcast_concept_changed(
        push_fn, change="updated",
        concept_id=node.concept_id, workspace_id=node.workspace_id,
        concept=node_dict,
    )
    # Description drives nomic; rendering drives TF-IDF. Other field
    # edits (layout_xy, ui_state, etc.) don't touch the index.
    if effective_embed_changed:
        upsert_concept_index_for(node, ge, push_fn=push_fn)
    schedule_output_projection(node.workspace_id, ge, push_fn=push_fn)
    # §8D.38.1 — if this update touches an agent's body (parameter /
    # perception / transformer / emitter card), nudge the cascade
    # scheduler so the agent gets a debounced tick. The scheduler
    # filters by type_hint, honours the parameter card's paused +
    # cascade_enabled flags, and rate-limits per agent. ``actor`` is
    # threaded through so the scheduler can short-circuit the agent's
    # own writeback (no self-induced tick loops per §8D.27.1).
    try:
        from backend.services.agent_runtime import get_cascade_scheduler
        get_cascade_scheduler().schedule_for_card(
            node, ge, push_fn=push_fn, actor=actor,
        )
    except Exception:
        pass
    # §8D.38.4 — "Cascade is the default": recompile the downstream
    # {ref}-consumers of this card when its DATA changed (their resolved
    # value just shifted). Skipped when the edit itself came FROM a compile
    # or the cascade (actor conceptual_compute|cascade*) so the bounded BFS in
    # _cascade_recompile_consumers is the single authority and never re-enters
    # itself — no recompile storm. The Compile button is a forced-sync
    # affordance, NOT the primary trigger (§8D.38.4).
    if effective_data_changed and actor not in (
        "conceptual_compute", "cascade", "cascade:ref",
    ):
        try:
            _cascade_recompile_consumers(node, ge, push_fn=push_fn)
        except Exception:
            pass
    return node_dict


def apply_delete_lifecycle(
    concept_id: ConceptId,
    pre_dict: Optional[Dict[str, Any]],
    ge,
    *,
    actor: str = "user:_anon",
    push_fn: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> None:
    """Run the full delete-lifecycle chain for a removed concept node."""
    # §1.6 / §2.4 (lifecycle_invariants) — foundation fixtures are
    # UNDELETABLE, and the guard lives HERE in the dispatcher (not only at
    # the HTTP routes) so EVERY caller is covered by one check: the agent
    # emitter's DeleteAction, the editor delete primitive, the DELETE route,
    # a future materialiser GC. This is the KISS/DRY, defense-in-depth seam.
    # `graph_editor.delete_concept` already refuses to drop the Kuzu node for
    # a `fixture::` id, so WITHOUT this guard a non-route caller that ignores
    # that return (e.g. the agent emitter) would still run the full fan-out —
    # stripping the ConceptIndex slot, appending a spurious `delete` EditDiff,
    # and broadcasting `concept_changed change=deleted` — for a node that
    # still exists in persistence. That divergence between the DB and the
    # peer surfaces is exactly the §18.1 severance the invariant forbids.
    # Keyed on `backing_pointer` (the §2.7 stable identifier) with the
    # concept_id prefix as belt-and-braces (fixtures carry both).
    _bp = str((pre_dict or {}).get("backing_pointer") or "")
    if _bp.startswith("fixture::") or (
        isinstance(concept_id, str) and concept_id.startswith("fixture::")
    ):
        logger.warning(
            "[lifecycle] §1.6 reject: refusing delete fan-out for foundation "
            "fixture %s (backing_pointer=%r) — fixtures are undeletable; no "
            "index removal / evolution diff / broadcast performed.",
            concept_id, _bp,
        )
        return
    # Wrap at the dict-extraction boundary so the rest of the function
    # speaks in WorkspaceId, matching the broadcast/scheduler contracts.
    workspace_id = WorkspaceId(str((pre_dict or {}).get("workspace_id") or ""))
    # §8D.38.1 — if this delete is removing an agent parameter card,
    # tell the cascade scheduler to drop its bookkeeping. Without this,
    # an armed debounce timer would fire a tick against a non-existent
    # agent and the per-agent fire counters would leak entries forever.
    # We also clean up if the deleted node is a perception / transformer
    # / emitter card — the scheduler keys by parameter card id, so the
    # cleanup is only needed for the parameter card itself.
    pre_hint = ((pre_dict or {}).get("type_hint") or "").lower()
    if pre_hint in ("agent_parameter", "parameter_card", "agent_state"):
        try:
            from backend.services.agent_runtime import get_cascade_scheduler
            get_cascade_scheduler().cleanup_for_agent(concept_id)
        except Exception:
            pass
    remove_concept_index_for(concept_id, ge, push_fn=push_fn)
    if pre_dict is not None:
        log_evolution(
            target=f"card:{concept_id}", kind="delete",
            before=pre_dict, after=None,
            workspace_id=workspace_id, ge=ge, actor=actor,
            push_fn=push_fn,
        )
    broadcast_concept_changed(
        push_fn, change="deleted",
        concept_id=concept_id, workspace_id=workspace_id, concept=None,
    )
    schedule_output_projection(workspace_id, ge, push_fn=push_fn)


def _node_to_dict(node) -> Dict[str, Any]:
    """Wire-shaped concept dict. Kept here so both routes.py and the
    agent runtime serialise consistently."""
    if node is None:
        return {}
    return {
        "concept_id": node.concept_id,
        "name": node.name,
        "description": node.description,
        "data": node.data,
        "rendering": node.rendering,
        "linked_nodes_json": getattr(node, "linked_nodes_json", ""),
        "backing_pointer": getattr(node, "backing_pointer", ""),
        "pagerank": float(getattr(node, "pagerank", 0.0) or 0.0),
        "provenance": getattr(node, "provenance", "user-authored"),
        "workspace_id": getattr(node, "workspace_id", ""),
        "layout_xy": getattr(node, "layout_xy", ""),
        "ui_state": getattr(node, "ui_state", ""),
        "type_hint": getattr(node, "type_hint", ""),
        "created_at": getattr(node, "created_at", ""),
        "updated_at": getattr(node, "updated_at", ""),
    }
