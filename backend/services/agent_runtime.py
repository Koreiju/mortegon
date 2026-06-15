"""Agent runtime (Workstream W10; domain anchor §8C.8, §8D.27,
§8D.32, §8D.37, §8D.38).

The agent is **not** an external runtime — it is a subgraph of
concept nodes whose meta-cognition node fires per tick and emits
action cards (CreateCardAction, LinkAction, WriteFieldAction, etc.)
that the editor's runtime resolves into canvas mutations (§8D.27).

This module wires that loop:

  * Meta-cognition node: an SLM-invocation concept node whose
    compile step reads its neighbourhood via Apparition Service
    (§8D.36 / §8D.38), invokes the on-device GPT4All SLM with
    live token streaming, and emits a structured ``MetaCognitionAction``.
  * Action resolver: applies the emitted actions to the canvas
    via graph_editor / concept_index_service primitives.
  * Live token streaming: each token from the SLM is pushed onto
    the workspace WS as an ``agent_token`` frame so the frontend
    can render the SLM's response as it materialises.

The runtime is intentionally lightweight: it doesn't impose a fixed
LangGraph schema; each tick is one read-reason-act cycle and the
agent's body can be edited live by the user (§8D.32).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# W30 — Pydantic schema for MetaCognitionAction
# ---------------------------------------------------------------------------

def _validate_meta_cognition_payload(data: Dict[str, Any]) -> Optional["MetaCognitionAction"]:
    """Validate ``data`` against the Pydantic MetaCognitionAction schema.

    Returns a populated MetaCognitionAction on success, or None if
    Pydantic isn't importable. Raises ValidationError on shape errors
    that aren't recoverable by item-skipping; the caller catches and
    falls back to the legacy permissive parser.

    Invalid items inside otherwise-valid lists are dropped with a
    logged warning rather than raised — the SLM occasionally emits
    one bad action among many good ones, and partial-success is
    the right default.
    """
    try:
        from pydantic import BaseModel, Field, ValidationError
    except Exception:
        return None

    class _CreateModel(BaseModel):
        name: str = ""
        type_hint: str = ""
        description: str = ""
        data: str = ""
        workspace_id: str = ""

        class Config:
            extra = "ignore"

    class _LinkModel(BaseModel):
        source_id: str
        target_id: str
        edge_type: str = "RELATES_TO"
        source_port: str = ""
        target_port: str = ""
        variable_name: str = ""
        workspace_id: str = ""

        class Config:
            extra = "ignore"

    class _WriteModel(BaseModel):
        target_id: str
        field: str
        value: Any = None

        class Config:
            extra = "ignore"

    class _DeleteModel(BaseModel):
        target_id: str

        class Config:
            extra = "ignore"

    class _InvokeModel(BaseModel):
        card_id: str
        method_name: str = ""
        kwargs: Dict[str, Any] = Field(default_factory=dict)

        class Config:
            extra = "ignore"

    class _CommitModel(BaseModel):
        name: str = ""
        card_ids: List[str] = Field(default_factory=list)

        class Config:
            extra = "ignore"

    class _ReviewModel(BaseModel):
        card_ids: List[str] = Field(default_factory=list)
        prompt: str = ""

        class Config:
            extra = "ignore"

    class _SpawnModel(BaseModel):
        goal: str = ""
        name: str = ""
        fork_from: str = ""
        workspace_id: str = ""

        class Config:
            extra = "ignore"

    class _EnvelopeModel(BaseModel):
        creates: List[Dict[str, Any]] = Field(default_factory=list)
        links: List[Dict[str, Any]] = Field(default_factory=list)
        writes: List[Dict[str, Any]] = Field(default_factory=list)
        deletes: List[Dict[str, Any]] = Field(default_factory=list)
        invokes: List[Dict[str, Any]] = Field(default_factory=list)
        commits: List[Dict[str, Any]] = Field(default_factory=list)
        reviews: List[Dict[str, Any]] = Field(default_factory=list)
        spawns: List[Dict[str, Any]] = Field(default_factory=list)
        self_state_updates: Dict[str, Any] = Field(default_factory=dict)
        rationale: str = ""

        class Config:
            extra = "ignore"

    try:
        envelope = _EnvelopeModel(**(data or {}))
    except ValidationError as e:
        logger.warning("MetaCognitionAction envelope validation failed: %s", e)
        return None

    out = MetaCognitionAction(
        rationale=envelope.rationale,
        self_state_updates=envelope.self_state_updates or {},
    )

    def _validate_each(items, model_cls, kind):
        """Validate each list item; skip-with-warning on failure."""
        ok = []
        for idx, item in enumerate(items or []):
            try:
                ok.append(model_cls(**(item or {})))
            except ValidationError as e:
                logger.warning(
                    "Skipping invalid %s item #%d: %s",
                    kind, idx, e.errors()[:2],
                )
        return ok

    for c in _validate_each(envelope.creates, _CreateModel, "create"):
        out.creates.append(CreateCardAction(
            name=c.name, type_hint=c.type_hint,
            description=c.description, data=c.data,
            workspace_id=c.workspace_id,
        ))
    for l in _validate_each(envelope.links, _LinkModel, "link"):
        out.links.append(LinkAction(
            source_id=l.source_id, target_id=l.target_id,
            edge_type=l.edge_type, source_port=l.source_port,
            target_port=l.target_port, variable_name=l.variable_name,
            workspace_id=l.workspace_id,
        ))
    for w in _validate_each(envelope.writes, _WriteModel, "write"):
        out.writes.append(WriteFieldAction(
            target_id=w.target_id, field=w.field, value=w.value,
        ))
    for d in _validate_each(envelope.deletes, _DeleteModel, "delete"):
        out.deletes.append(DeleteAction(target_id=d.target_id))
    for i in _validate_each(envelope.invokes, _InvokeModel, "invoke"):
        out.invokes.append(InvokeAction(
            card_id=i.card_id, method_name=i.method_name, kwargs=i.kwargs,
        ))
    for c in _validate_each(envelope.commits, _CommitModel, "commit"):
        out.commits.append(CommitSubgraphAction(
            name=c.name, card_ids=c.card_ids,
        ))
    for r in _validate_each(envelope.reviews, _ReviewModel, "review"):
        out.reviews.append(RequestUserReviewAction(
            card_ids=r.card_ids, prompt=r.prompt,
        ))
    for s in _validate_each(envelope.spawns, _SpawnModel, "spawn"):
        out.spawns.append(SpawnAgentAction(
            goal=s.goal, name=s.name,
            fork_from=s.fork_from, workspace_id=s.workspace_id,
        ))
    return out


# ---------------------------------------------------------------------------
# Action card schemas (§8C.8)
# ---------------------------------------------------------------------------

@dataclass
class CreateCardAction:
    name: str = ""
    type_hint: str = ""
    description: str = ""
    data: str = ""
    workspace_id: str = ""


@dataclass
class LinkAction:
    source_id: str = ""
    target_id: str = ""
    edge_type: str = "RELATES_TO"
    source_port: str = ""
    target_port: str = ""
    weight: Optional[float] = None
    variable_name: str = ""
    workspace_id: str = ""


@dataclass
class WriteFieldAction:
    target_id: str = ""
    field: str = ""  # name | description | data | rendering | layout_xy | ...
    value: Any = None


@dataclass
class DeleteAction:
    target_id: str = ""


@dataclass
class InvokeAction:
    card_id: str = ""
    method_name: str = ""
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommitSubgraphAction:
    name: str = ""
    card_ids: List[str] = field(default_factory=list)


@dataclass
class RequestUserReviewAction:
    card_ids: List[str] = field(default_factory=list)
    prompt: str = ""


@dataclass
class SpawnAgentAction:
    """§8D.32.2 — agent emits a request to spawn or fork a sibling agent.

    Two modes, distinguished by ``fork_from``:

      * ``fork_from`` set      → clone an existing agent's body
        (parameter card + perception / transformer / emitter) so the
        new agent inherits the source's customisations. Equivalent
        to ``POST /api/agent/fork`` from the user's perspective.

      * ``fork_from`` empty    → fresh spawn with the supplied
        ``goal`` + ``name``. Equivalent to ``POST /api/agent/spawn``.

    The fork case carries the lineage forward (``forked_from`` field
    in the new parameter card's data), so the evolution log + audit
    trail can reconstruct chains of agent-authored agents.
    """
    goal: str = ""
    name: str = ""
    fork_from: str = ""        # source parameter_card_id when forking
    workspace_id: str = ""


@dataclass
class MetaCognitionAction:
    """Structured output of a meta-cognition node tick.

    The SLM produces a JSON payload conforming to this shape; the
    action resolver below applies the contents in order.
    """

    creates: List[CreateCardAction] = field(default_factory=list)
    links: List[LinkAction] = field(default_factory=list)
    writes: List[WriteFieldAction] = field(default_factory=list)
    deletes: List[DeleteAction] = field(default_factory=list)
    invokes: List[InvokeAction] = field(default_factory=list)
    commits: List[CommitSubgraphAction] = field(default_factory=list)
    reviews: List[RequestUserReviewAction] = field(default_factory=list)
    spawns: List[SpawnAgentAction] = field(default_factory=list)
    self_state_updates: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return {
            "creates": [asdict(c) for c in self.creates],
            "links": [asdict(l) for l in self.links],
            "writes": [asdict(w) for w in self.writes],
            "deletes": [asdict(d) for d in self.deletes],
            "invokes": [asdict(i) for i in self.invokes],
            "commits": [asdict(c) for c in self.commits],
            "reviews": [asdict(r) for r in self.reviews],
            "spawns": [asdict(s) for s in self.spawns],
            "self_state_updates": self.self_state_updates,
            "rationale": self.rationale,
        }

    @classmethod
    def from_json_text(cls, text: str) -> "MetaCognitionAction":
        """Parse a JSON-shaped SLM response into a MetaCognitionAction.

        W30 — Use Pydantic for structured validation so malformed
        SLM outputs surface as graceful parse errors rather than
        runtime crashes. The Pydantic model is permissive on extra
        fields (the SLM may emit additional rationale-like keys)
        but strict on the action-shape types. Invalid items inside
        an otherwise-valid envelope are skipped individually with
        a logged warning, not raised — partial-success is the
        right default for an SLM that occasionally hallucinates
        a single bad action among many good ones.

        Falls back to the legacy hand-rolled parser if pydantic
        isn't importable or the structured validation explodes.
        """
        if not text:
            return cls()
        try:
            data = json.loads(text)
        except Exception:
            return cls(rationale=str(text))
        # Try the Pydantic path first.
        try:
            validated = _validate_meta_cognition_payload(data)
            if validated is not None:
                return validated
        except Exception:
            pass
        # Fallback: legacy permissive parsing.
        return cls._from_dict_legacy(data)

    @classmethod
    def _from_dict_legacy(cls, data: Dict[str, Any]) -> "MetaCognitionAction":
        out = cls(rationale=str(data.get("rationale", "")))
        for c in data.get("creates", []) or []:
            out.creates.append(CreateCardAction(**{
                k: c.get(k, "") for k in
                ("name", "type_hint", "description", "data", "workspace_id")
            }))
        for l in data.get("links", []) or []:
            out.links.append(LinkAction(**{
                k: l.get(k, "") for k in
                ("source_id", "target_id", "edge_type", "source_port",
                 "target_port", "variable_name", "workspace_id")
            }))
        for w in data.get("writes", []) or []:
            out.writes.append(WriteFieldAction(
                target_id=str(w.get("target_id", "")),
                field=str(w.get("field", "")),
                value=w.get("value"),
            ))
        for d in data.get("deletes", []) or []:
            out.deletes.append(DeleteAction(target_id=str(d.get("target_id", ""))))
        for i in data.get("invokes", []) or []:
            out.invokes.append(InvokeAction(
                card_id=str(i.get("card_id", "")),
                method_name=str(i.get("method_name", "")),
                kwargs=i.get("kwargs", {}) or {},
            ))
        for c in data.get("commits", []) or []:
            out.commits.append(CommitSubgraphAction(
                name=str(c.get("name", "")),
                card_ids=list(c.get("card_ids", []) or []),
            ))
        for r in data.get("reviews", []) or []:
            out.reviews.append(RequestUserReviewAction(
                card_ids=list(r.get("card_ids", []) or []),
                prompt=str(r.get("prompt", "")),
            ))
        for s in data.get("spawns", []) or []:
            out.spawns.append(SpawnAgentAction(
                goal=str(s.get("goal", "")),
                name=str(s.get("name", "")),
                fork_from=str(s.get("fork_from", "")),
                workspace_id=str(s.get("workspace_id", "")),
            ))
        out.self_state_updates = data.get("self_state_updates", {}) or {}
        return out


# ---------------------------------------------------------------------------
# Action resolver
# ---------------------------------------------------------------------------

class ActionResolver:
    """Applies MetaCognitionAction outputs to the canvas via graph_editor.

    Each emitted action becomes a concrete canvas mutation. The
    resolver is idempotent on already-applied actions because the
    graph_editor's create is idempotent on concept_id.
    """

    def __init__(self, graph_editor, concept_index=None, broadcast=None):
        self._ge = graph_editor
        self._ci = concept_index
        # Fix: previously the agent_review broadcast path called
        # ``getattr(self, "_broadcast", None)`` which always
        # returned None (the attribute was never set), silently
        # dropping every agent_review frame. Wire the broadcast
        # hook through on construction so the resolver can emit
        # ``agent_review`` WS frames when RequestUserReviewAction
        # entries land.
        self._broadcast = broadcast

    def apply(
        self,
        action: MetaCognitionAction,
        *,
        workspace_id: str = "",
        actor_label: str = "agent",
        broadcast=None,
    ) -> Dict[str, Any]:
        """Apply all sub-actions; returns a summary of effects.

        ``broadcast`` overrides the instance-level hook for the
        scope of this call. Useful when the same resolver is shared
        across multiple meta-cognition nodes that broadcast to
        different workspaces.
        """
        if broadcast is not None:
            self._broadcast = broadcast
        applied: Dict[str, int] = {
            "creates": 0, "links": 0, "writes": 0, "deletes": 0,
            "spawns": 0, "spawns_rate_limited": 0,
            "invokes": 0, "commits": 0, "reviews": 0, "self_state": 0,
        }
        new_ids: List[str] = []

        # Lifecycle hooks (broadcast / index / projection / log) live
        # in concept_lifecycle so user-driven REST mutations and agent-
        # driven mutations share one code path. ``actor_label`` flows
        # into the evolution log so rollback can target agent edits.
        from backend.services.concept_lifecycle import (
            apply_create_lifecycle,
            apply_update_lifecycle,
            apply_delete_lifecycle,
            schedule_output_projection,
            _node_to_dict,
        )

        for c in action.creates:
            try:
                node = self._ge.create_concept(
                    name=c.name,
                    description=c.description,
                    data=c.data,
                    workspace_id=c.workspace_id or workspace_id,
                    type_hint=c.type_hint or "agent_authored",
                    provenance="agent-authored",
                )
                if node:
                    new_ids.append(node.concept_id)
                    apply_create_lifecycle(
                        node, self._ge,
                        actor=actor_label, push_fn=self._broadcast,
                    )
                    applied["creates"] += 1
            except Exception:
                pass

        from backend.services.concept_lifecycle import apply_edge_create_lifecycle
        for l in action.links:
            try:
                edge = self._ge.create_concept_edge(
                    source_id=l.source_id,
                    target_id=l.target_id,
                    edge_type=l.edge_type or "RELATES_TO",
                    source_port=l.source_port,
                    target_port=l.target_port,
                    weight=l.weight,
                    variable_name=l.variable_name,
                    workspace_id=l.workspace_id or workspace_id,
                )
                # Multi-tab sync + projection schedule via the shared
                # lifecycle (broadcast + schedule were duplicated four
                # times before this consolidation).
                apply_edge_create_lifecycle(
                    edge, self._ge,
                    workspace_id=l.workspace_id or workspace_id,
                    push_fn=self._broadcast,
                )
                applied["links"] += 1
            except Exception:
                pass

        for w in action.writes:
            try:
                if not w.target_id or not w.field:
                    continue
                pre = self._ge.get_concept(w.target_id)
                pre_dict = _node_to_dict(pre) if pre else None
                kwargs = {w.field: w.value}
                node = self._ge.update_concept(w.target_id, **kwargs)
                if node is not None:
                    apply_update_lifecycle(
                        node, self._ge,
                        pre_dict=pre_dict,
                        embed_fields_changed=(w.field in ("description", "rendering")),
                        actor=actor_label, push_fn=self._broadcast,
                    )
                applied["writes"] += 1
            except Exception:
                pass

        for d in action.deletes:
            try:
                if d.target_id:
                    pre = self._ge.get_concept(d.target_id)
                    pre_dict = _node_to_dict(pre) if pre else None
                    # §1.6 — fire the fan-out only when the delete actually
                    # happened. `delete_concept` returns False for a
                    # `fixture::` id (fixtures are undeletable), so an agent
                    # emitter that targets a fixture must NOT broadcast a
                    # `deleted` frame for a node that still exists. Mirrors the
                    # editor delete route; the dispatcher also guards (§2.4
                    # defense-in-depth), but checking `ok` here avoids the
                    # wasted fan-out attempt and keeps the count honest.
                    ok = self._ge.delete_concept(d.target_id)
                    if ok:
                        apply_delete_lifecycle(
                            d.target_id, pre_dict, self._ge,
                            actor=actor_label, push_fn=self._broadcast,
                        )
                        applied["deletes"] += 1
            except Exception:
                pass

        for i in action.invokes:
            # C4 / §8D.44 — resolve via the backing-pointer registry.
            # ``card_id`` is the concept node carrying the backing
            # pointer; ``method_name`` is optional context. The
            # registry maps the node's backing_pointer to a callable.
            try:
                from backend.services.backing_registry import get_backing_registry
                reg = get_backing_registry()
                node = self._ge.get_concept(i.card_id) if i.card_id else None
                handle = node.backing_pointer if node else None
                if handle:
                    reg.invoke(handle, **(i.kwargs or {}))
                applied["invokes"] += 1
            except Exception:
                applied["invokes"] += 1

        # §8D.23.3 — specialised assembly closes the capability loop.
        # Each commit materialises a ``committed_subgraph`` ConceptNode
        # whose data block records the member card ids. The new card
        # has its own backing pointer (``committed_subgraph::<id>``) so
        # it shows up in the BackingRegistry's resolver chain and can
        # be invoked to enumerate / expand its members on demand. The
        # commit itself goes through the lifecycle so peer tabs see
        # the new node + the evolution log records the commit + the
        # concept index re-embeds the new card by its description.
        for c in action.commits:
            try:
                if not c.card_ids:
                    continue  # no body → nothing to commit
                commit_data = json.dumps({
                    "name": c.name,
                    "card_ids": list(c.card_ids),
                    "committed_at": time.time(),
                    "committed_by": actor_label,
                }, indent=2)
                slug = c.name or f"subgraph_{int(time.time()*1000)}"
                committed = self._ge.create_concept(
                    name=slug,
                    description=(
                        f"Committed subgraph '{slug}' wrapping "
                        f"{len(c.card_ids)} card(s). Re-expandable via "
                        f"backing-pointer invoke; surfaces in apparition "
                        f"retrieval like any other concept node (§8D.23.3)."
                    ),
                    data=commit_data,
                    provenance="committed-subgraph",
                    workspace_id=workspace_id,
                    type_hint="committed_subgraph",
                )
                if committed is not None:
                    # Backing pointer wires the committed subgraph into
                    # the runtime registry. ``register`` is direct (no
                    # prefix resolver) since each commit gets a unique
                    # callable closure that enumerates ITS member set.
                    handle = f"committed_subgraph::{committed.concept_id}"
                    try:
                        from backend.services.backing_registry import (
                            get_backing_registry,
                        )
                        reg = get_backing_registry()
                        member_ids = list(c.card_ids)
                        commit_name = slug
                        def _expand(**_kw):
                            """Return the member roster — callers (the
                            agent, the user via /api/backing/invoke) can
                            expand the subgraph back into its members."""
                            return {
                                "ok": True, "name": commit_name,
                                "card_ids": member_ids,
                                "member_count": len(member_ids),
                            }
                        reg.register(handle, _expand)
                        # Persist the backing pointer on the record so
                        # rehydration on next workspace open finds it.
                        self._ge.update_concept(
                            committed.concept_id, backing_pointer=handle,
                        )
                        committed.backing_pointer = handle
                    except Exception:
                        pass
                    # Route through the shared lifecycle so peer tabs
                    # + evolution log + concept index all observe the
                    # new node, then count the success.
                    apply_create_lifecycle(
                        committed, self._ge,
                        push_fn=self._broadcast, actor=actor_label,
                    )
                    new_ids.append(committed.concept_id)
                    applied["commits"] += 1
            except Exception as e:
                logger.warning("CommitSubgraphAction apply failed for %s: %s",
                               c.name, e)

        # §8D.32.2 — agent self-extension. Each ``spawn`` either forks
        # an existing agent (when ``fork_from`` is set) or creates a
        # fresh sibling. The workspace-level rate limit protects
        # against runaway proliferation: a single agent can't spawn
        # more than ``_SPAWN_MAX_PER_WORKSPACE_PER_MIN`` agents in a
        # rolling 60-second window. Rejected spawns are counted in
        # ``applied["spawns_rate_limited"]`` so the rationale stays
        # honest about what didn't happen.
        for s in action.spawns:
            ws = s.workspace_id or workspace_id or ""
            if not _check_spawn_rate(ws):
                applied["spawns_rate_limited"] += 1
                continue
            try:
                if s.fork_from:
                    result = fork_agent_body_subgraph(
                        graph_editor=self._ge,
                        source_parameter_card_id=s.fork_from,
                        workspace_id=ws,
                        new_name=s.name,
                        push_fn=self._broadcast,
                    )
                else:
                    # Mint a parameter card with the agent-supplied
                    # goal, then attach the body subgraph.
                    params_data = json.dumps({
                        "goal": s.goal or "Inspect the graph and suggest one useful next concept.",
                        "step_index": 0,
                        "zone_of_influence": {},
                        "cascade_enabled": False,
                        "paused": False,
                        "spawned_by": actor_label,
                    }, indent=2)
                    new_param = self._ge.create_concept(
                        name=s.name or "agent_parameters",
                        description=(
                            "Agent parameter card (§8D.27) spawned by "
                            f"{actor_label}. Holds goal, step_index, "
                            "zone_of_influence."
                        ),
                        data=params_data,
                        provenance="agent-authored",
                        workspace_id=ws,
                        type_hint="agent_parameter",
                    )
                    if new_param is None:
                        continue
                    apply_create_lifecycle(
                        new_param, self._ge,
                        push_fn=self._broadcast, actor=actor_label,
                    )
                    result = spawn_agent_body_subgraph(
                        graph_editor=self._ge,
                        parameter_card_id=new_param.concept_id,
                        workspace_id=ws,
                        push_fn=self._broadcast,
                    )
                if result and result.get("ok"):
                    applied["spawns"] += 1
                    new_pcid = result.get("parameter_card_id")
                    if new_pcid:
                        new_ids.append(new_pcid)
            except Exception:
                pass

        for r in action.reviews:
            applied["reviews"] += 1
            # W24 — register the review in the workspace-scoped pending
            # queue and broadcast an ``agent_review`` WS frame so the
            # frontend can surface a yellow-bordered review card with
            # accept/dismiss buttons.
            try:
                from backend.services.review_queue import get_review_queue
                from backend.api.ws_frames import build_agent_review
                # Try to pull the broadcast hook off self if present.
                bc = getattr(self, "_broadcast", None)
                q = get_review_queue()
                entry = q.enqueue(
                    workspace_id=workspace_id,
                    actor=actor_label,
                    card_ids=list(r.card_ids or []),
                    prompt=str(r.prompt or ""),
                )
                if bc is not None:
                    bc(0, build_agent_review(
                        workspace_id=workspace_id or "_default",
                        entry=entry.to_dict(),
                    ))
            except Exception:
                pass

        if action.self_state_updates:
            applied["self_state"] += len(action.self_state_updates)

        return {
            "applied": applied,
            "new_concept_ids": new_ids,
            "actor": actor_label,
            "rationale": action.rationale,
        }


# ---------------------------------------------------------------------------
# Meta-cognition node tick
# ---------------------------------------------------------------------------

class MetaCognitionTick:
    """One agent tick: read graph region → SLM → action.

    The instance carries the bindings the tick needs: the workspace
    id, the parameter card's id (its data block holds goal,
    active_context_ids, zone_of_influence), and the action resolver.
    Each call to ``run_async`` performs one full read-reason-act
    cycle and returns the applied summary.
    """

    def __init__(
        self,
        *,
        graph_editor,
        concept_index,
        apparition_service,
        slm_client=None,
        broadcast=None,
        workspace_id: str = "",
        parameter_card_id: str = "",
    ):
        self._ge = graph_editor
        self._ci = concept_index
        self._app = apparition_service
        self._slm = slm_client
        self._broadcast = broadcast
        self.workspace_id = workspace_id
        self.parameter_card_id = parameter_card_id
        # Fix: thread the broadcast hook into the resolver so
        # agent_review WS frames emit on RequestUserReviewAction.
        # Previously the resolver had no _broadcast attribute and
        # the W24 broadcast path silently no-op'd.
        self._resolver = ActionResolver(graph_editor, concept_index, broadcast=broadcast)

    async def run_async(self) -> Dict[str, Any]:
        """Read → reason → emit. Returns a summary dict.

        §8D.27 — if the parameter card has a visible body subgraph
        wired downstream (perception / transformer / emitter concept
        nodes), route through it via each card's backing pointer so
        the user can edit any step on canvas and see the agent's
        behaviour shift. Otherwise fall back to the inline default.
        """
        # 1. Read agent parameters from the parameter card's data block.
        params: Dict[str, Any] = {}
        # Fix: if the parameter card was deleted between when this
        # tick was scheduled and when it runs (a frequent multi-tab /
        # rapid-edit pattern), abort the tick cleanly instead of
        # firing an expensive SLM call against an empty perception.
        if self.parameter_card_id:
            try:
                node = self._ge.get_concept(self.parameter_card_id)
            except Exception:
                node = None
            if node is None:
                return {
                    "status": "aborted",
                    "reason": "parameter_card_not_found",
                    "parameter_card_id": self.parameter_card_id,
                }
            try:
                if node.data:
                    try:
                        params = json.loads(node.data)
                    except Exception:
                        params = {"raw": node.data}
            except Exception:
                params = {}

        goal = str(params.get("goal", "")) or "Inspect the graph and suggest one useful next concept."

        # 2/3. Build perception + run transformer. The visible-subgraph
        # path invokes the user-editable concept cards; the inline path
        # is the bootstrap default when no body has been spawned yet.
        body = self._find_visible_body()
        if body is not None and body.get("perception") and body.get("transformer"):
            perception, response_text = await self._run_visible_body(
                body=body, goal=goal,
            )
        else:
            perception = self._build_perception(params)
            prompt = self._compose_prompt(goal=goal, perception=perception)
            response_text = await self._call_slm_streaming(prompt)

        # 4. Parse the response into a MetaCognitionAction.
        action = MetaCognitionAction.from_json_text(response_text)

        # 5. Apply the action. If a visible emitter card is wired in,
        # route through its backing pointer (so editor filters apply);
        # otherwise the inline resolver handles it.
        if body is not None and body.get("emitter"):
            result = self._apply_via_emitter_card(
                emitter_card_id=body["emitter"], action_json=response_text,
            ) or {}
        else:
            result = self._resolver.apply(
                action,
                workspace_id=self.workspace_id,
                actor_label=f"agent:{self.parameter_card_id or 'anon'}",
            )
        # Record per-agent spawn counts in the cascade scheduler so the
        # diagnostics panel shows proliferation activity alongside fires.
        try:
            applied_counts = result.get("applied", {}) if isinstance(result, dict) else {}
            spawns = int(applied_counts.get("spawns", 0))
            rate_lim = int(applied_counts.get("spawns_rate_limited", 0))
            if spawns or rate_lim:
                get_cascade_scheduler().record_spawns(
                    self.parameter_card_id or "", spawns, rate_lim,
                )
        except Exception:
            pass

        # 6. Optionally write self-state-updates back to the parameter card.
        # §8D.27.1 — parameter-card self-mutation. The write must go
        # through ``apply_update_lifecycle`` so peer tabs see the new
        # step_index, the evolution log records the self-edit (with
        # actor ``agent:<pcid>`` for filtering), and the cascade
        # scheduler is aware. The previous raw graph_editor call
        # bypassed all three subsystems and broke the closure.
        #
        # Fix: re-check the parameter card still exists before writing.
        # The card may have been deleted mid-tick (rare but possible
        # with multi-tab editing).
        if action.self_state_updates and self.parameter_card_id:
            try:
                node = self._ge.get_concept(self.parameter_card_id)
                if node is None:
                    # The agent's owner removed the parameter card
                    # while this tick was in flight — skip silently.
                    pass
                else:
                    from backend.services.concept_lifecycle import (
                        apply_update_lifecycle, _node_to_dict,
                    )
                    pre_dict = _node_to_dict(node)
                    try:
                        old_params = json.loads(node.data) if node.data else {}
                    except Exception:
                        old_params = {}
                    # Auto-increment step_index so the user can see the
                    # agent making progress without the SLM having to
                    # remember to do it itself.
                    old_params["step_index"] = int(old_params.get("step_index", 0)) + 1
                    old_params.update(action.self_state_updates)
                    updated = self._ge.update_concept(
                        self.parameter_card_id,
                        data=json.dumps(old_params, indent=2),
                    )
                    if updated is not None:
                        apply_update_lifecycle(
                            updated, self._ge,
                            pre_dict=pre_dict,
                            embed_fields_changed=False,  # data-only edit
                            actor=f"agent:{self.parameter_card_id}",
                            push_fn=self._broadcast,
                        )
            except Exception:
                pass

        return {
            "status": "ok",
            "rationale": action.rationale,
            "applied": result.get("applied"),
            "new_concept_ids": result.get("new_concept_ids", []),
        }

    # -----------------------------------------------------------------
    # §8D.27 — visible-body lookup + invocation
    # -----------------------------------------------------------------

    def _find_visible_body(self) -> Optional[Dict[str, str]]:
        """Walk linked_nodes from the parameter card. If we find a
        perception card (backing_pointer ``agent::perception::<pcid>``),
        follow its downstream chain to the transformer and emitter.

        Returns ``{ perception, transformer, emitter }`` of concept ids
        (any may be missing) or ``None`` if no perception card exists.
        """
        if not self.parameter_card_id or self._ge is None:
            return None
        body: Dict[str, str] = {}

        def _find_downstream(src_id: str, target_handle: str) -> str:
            try:
                for e in self._ge.list_concept_edges(
                    workspace_id=self.workspace_id, source_id=src_id, limit=50,
                ):
                    tgt = self._ge.get_concept(e.target_id)
                    if tgt is not None and (tgt.backing_pointer or "") == target_handle:
                        return tgt.concept_id
            except Exception:
                return ""
            return ""

        body["perception"] = _find_downstream(
            self.parameter_card_id,
            agent_handle(AGENT_ROLE_PERCEPTION, self.parameter_card_id),
        )
        if not body["perception"]:
            return None
        body["transformer"] = _find_downstream(
            body["perception"],
            agent_handle(AGENT_ROLE_TRANSFORMER, self.parameter_card_id),
        )
        if body["transformer"]:
            body["emitter"] = _find_downstream(
                body["transformer"],
                agent_handle(AGENT_ROLE_EMITTER, self.parameter_card_id),
            )
        return body

    async def _run_visible_body(self, *, body: Dict[str, str], goal: str) -> tuple:
        """Invoke perception via its backing pointer, then call the SLM
        with the transformer card's prompt template — streaming tokens
        through ``_call_slm_streaming`` so the cascade-fire path emits
        ``agent_token`` WS frames just like the manual Tick path.

        The transformer card's *data* block stays editable (user-pinable;
        forkable per §8D.27). The backing-pointer indirection is reserved
        for direct ``InvokeAction`` calls that don't need streaming.

        Returns ``(perception_text, transformer_response_text)``.
        """
        from backend.services.backing_registry import get_backing_registry
        reg = get_backing_registry()
        # Perception step — still goes through the backing pointer
        # because it's not latency-sensitive and lets the data-block
        # config drive what's included.
        perception_text = ""
        try:
            out = reg.invoke(agent_handle(AGENT_ROLE_PERCEPTION, self.parameter_card_id))
            if out.get("ok"):
                inner = out.get("result", {}) or {}
                perception_text = str(inner.get("perception", "")) or ""
        except Exception:
            perception_text = ""
        # Transformer step — read the prompt template from the
        # transformer card's data block, substitute placeholders, then
        # stream the SLM call so tokens flow as ``agent_token`` frames.
        prompt = self._build_transformer_prompt(
            transformer_card_id=body.get("transformer", ""),
            perception=perception_text, goal=goal,
        )
        response_text = await self._call_slm_streaming(prompt)
        return perception_text, response_text

    def _build_transformer_prompt(
        self, *, transformer_card_id: str, perception: str, goal: str,
    ) -> str:
        """Assemble the SLM prompt using the transformer card's
        editable template. Substitutes ``{perception}`` and ``{goal}``.
        Falls back to the default if the card or its data is missing.
        """
        template = ""
        if transformer_card_id and self._ge is not None:
            try:
                card = self._ge.get_concept(transformer_card_id)
                if card is not None and card.data:
                    template = card.data
            except Exception:
                template = ""
        if not template:
            template = _DEFAULT_TRANSFORMER_PROMPT
        return (
            template
            .replace("{perception}", perception or "")
            .replace("{goal}", goal or "")
        )

    def _apply_via_emitter_card(
        self, *, emitter_card_id: str, action_json: str,
    ) -> Optional[Dict[str, Any]]:
        """Route action application through the emitter card so its
        ``allow`` filter (data block) gates the action kinds."""
        from backend.services.backing_registry import get_backing_registry
        reg = get_backing_registry()
        try:
            out = reg.invoke(
                agent_handle(AGENT_ROLE_EMITTER, self.parameter_card_id),
                action_json=action_json,
                workspace_id=self.workspace_id or "",
                actor=f"agent:{self.parameter_card_id or 'anon'}",
            )
            if out.get("ok"):
                return (out.get("result") or {}).get("summary") or {}
        except Exception:
            return None
        return None

    # -----------------------------------------------------------------
    # Inline helpers (fallback path)
    # -----------------------------------------------------------------

    def _build_perception(self, params: Dict[str, Any]) -> str:
        """Compose a short text summary of the agent's perceived state."""
        lines: List[str] = []
        ws = self.workspace_id or "_default"
        lines.append(f"workspace_id: {ws}")
        lines.append(f"parameter_card: {self.parameter_card_id or '(none)'}")
        if params:
            lines.append(f"parameters: {json.dumps(params)[:500]}")
        # §8D.36 mode 4 — meta-cognition retrieval focal is the local
        # subgraph centroid (not the parameter card's own embedding).
        # The agent perceives the wired neighbourhood, so candidates
        # reflect graph context, not just one record. Falls back to the
        # focal-only path if subgraph-centroid isn't available.
        if self._app and self.parameter_card_id:
            try:
                getter = getattr(
                    self._app, "apparitions_for_subgraph_centroid", None,
                ) or self._app.apparitions_for_focal
                cands = getter(
                    self.parameter_card_id,
                    workspace_id=self.workspace_id, k=5,
                )
                if cands:
                    lines.append("relevant nearby concepts:")
                    for c in cands:
                        lines.append(
                            f"  - {c.card_id} (score {c.score:.3f})"
                        )
            except Exception:
                pass
        # Show count of concept nodes in workspace.
        try:
            slots = self._ci.list_slots(self.workspace_id) if self._ci else {}
            lines.append(f"total concept nodes: {len(slots)}")
        except Exception:
            pass
        return "\n".join(lines)

    def _compose_prompt(self, *, goal: str, perception: str) -> str:
        """The structured-output prompt the SLM responds to."""
        schema = (
            '{ "rationale": "<one-paragraph explanation>", '
            '"creates": [{"name": "...", "description": "...", "data": "...", '
            '"type_hint": "agent_authored", "workspace_id": ""}], '
            '"links": [{"source_id": "...", "target_id": "...", "edge_type": "RELATES_TO"}], '
            '"writes": [{"target_id": "...", "field": "description", "value": "..."}], '
            '"deletes": [{"target_id": "..."}], '
            '"self_state_updates": {"goal": "..."} }'
        )
        return (
            "You are a meta-cognition node in a visible concept-graph editor. "
            "Read the perception below, decide one or two useful next actions, "
            "and respond ONLY with a JSON object matching this schema:\n"
            f"{schema}\n\n"
            f"Goal: {goal}\n\n"
            f"Perception:\n{perception}\n\n"
            "Respond with JSON only. Keep `creates` to at most 2 cards per tick. "
            "Use descriptive `description` fields that declare what each new "
            "card does. Empty arrays are fine if you have nothing to do."
        )

    async def _call_slm_streaming(self, prompt: str) -> str:
        """Call the SLM with token streaming, push each token to WS, "
        return the joined string.

        If no slm_client is wired, returns a minimal valid stub
        response so the resolver still has shape to apply.
        """
        if self._slm is None:
            return json.dumps({
                "rationale": "no SLM client wired; emitting empty action",
                "creates": [], "links": [], "writes": [], "deletes": [],
                "self_state_updates": {},
            })
        chunks: List[str] = []
        try:
            stream = self._slm.async_stream_chat(prompt)
        except Exception:
            return ""
        try:
            async for tok in stream:
                chunks.append(tok)
                self._push_token(tok)
        except Exception:
            # Some SLM clients return a sync iterable.
            try:
                for tok in stream:  # type: ignore
                    chunks.append(tok)
                    self._push_token(tok)
            except Exception:
                pass
        return "".join(chunks)

    def _push_token(self, tok: str) -> None:
        """Emit an ``agent_token`` WS frame for live streaming.

        Also writes into a process-wide ring buffer keyed by parameter
        card id so a tab reconnecting mid-tick can retroactively
        fetch the in-flight token stream via
        ``GET /api/agent/tokens/{pcid}``.
        """
        if not tok:
            return
        # Always append to the ring buffer, even if no broadcast hook
        # is wired — the REST endpoint then serves as the fallback
        # delivery path.
        _record_agent_token(
            self.parameter_card_id or "_default",
            self.workspace_id or "_default",
            tok,
        )
        if not self._broadcast:
            return
        from backend.api.ws_frames import build_agent_token
        payload = build_agent_token(
            workspace_id=self.workspace_id or "_default",
            token=tok,
            parameter_card_id=self.parameter_card_id,
        )
        try:
            self._broadcast(0, payload)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# §8D.38.1 — Cascade auto-fire scheduler
#
# A meta-cognition node continually re-fires as its inputs change
# (parameter card edited, perception config tweaked, transformer prompt
# updated, env signal arriving via spine_delta). Without this loop the
# agent is inert — the only way to advance it is a manual Tick.
#
# The scheduler debounces (per agent) and rate-limits (per minute and
# per minute-window) so a flurry of edits coalesces into one tick and
# a runaway action loop can't spin forever. Each parameter card carries
# a ``cascade_enabled`` flag in its data block; if False the scheduler
# is a no-op for that agent.
# ---------------------------------------------------------------------------

# Cascade scheduler + spawn limiter + token buffer — knob values live in
# :class:`backend.services.settings.Settings` (env-overridable). The
# module-level names below are kept as backward-compatible re-exports
# so existing tests/callers that read them keep working; reading via
# ``get_settings()`` is the preferred path going forward.

def _cfg() -> "Any":
    from backend.services.settings import get_settings
    return get_settings()

# Backward-compat exports (computed lazily on first import).
_CASCADE_DEBOUNCE_SEC = _cfg().cascade_debounce_sec
_CASCADE_MAX_TICKS_PER_MIN = _cfg().cascade_max_ticks_per_min

# §8D.32.2 — runaway proliferation guard.
_SPAWN_MAX_PER_WORKSPACE_PER_MIN = _cfg().spawn_max_per_workspace_per_min
_SPAWN_WINDOW: Dict[str, List[float]] = {}
_SPAWN_LOCK = threading.Lock()


# §8D.8 — agent_token ring buffer for retroactive fetch.
_AGENT_TOKEN_BUFFER_SIZE = _cfg().agent_token_buffer_size
_AGENT_TOKEN_BUFFERS: Dict[str, List[Dict[str, Any]]] = {}
_AGENT_TOKEN_LOCK = threading.Lock()


def _record_agent_token(parameter_card_id: str, workspace_id: str, token: str) -> None:
    """Append a token to the parameter card's ring buffer. Capped at
    ``settings.agent_token_buffer_size`` entries — older tokens roll off.
    """
    if not parameter_card_id or not token:
        return
    cap = _cfg().agent_token_buffer_size
    entry = {"workspace_id": workspace_id, "token": token, "ts": time.time()}
    with _AGENT_TOKEN_LOCK:
        buf = _AGENT_TOKEN_BUFFERS.setdefault(parameter_card_id, [])
        buf.append(entry)
        if len(buf) > cap:
            # Drop the oldest 25% so we don't slice on every push.
            del buf[: len(buf) - cap]


def get_agent_token_buffer(
    parameter_card_id: str, *, limit: int = 4000,
) -> List[Dict[str, Any]]:
    """Read the ring buffer for ``parameter_card_id``. Returns up to
    ``limit`` newest entries in append order (oldest first).
    """
    if not parameter_card_id:
        return []
    with _AGENT_TOKEN_LOCK:
        buf = _AGENT_TOKEN_BUFFERS.get(parameter_card_id, [])
        if limit <= 0 or limit >= len(buf):
            return list(buf)
        return list(buf[-limit:])


def clear_agent_token_buffer(parameter_card_id: str) -> None:
    """Drop the ring buffer entirely — called by cascade cleanup
    when the parameter card is deleted."""
    if not parameter_card_id:
        return
    with _AGENT_TOKEN_LOCK:
        _AGENT_TOKEN_BUFFERS.pop(parameter_card_id, None)


def _check_spawn_rate(workspace_id: str) -> bool:
    """Return True if a new spawn is allowed under the workspace cap.

    Reads ``settings.spawn_max_per_workspace_per_min`` live so an
    operator can tune the cap at runtime by setting the env var +
    rebuilding the singleton (via ``settings.reset_to_env()``).

    Side-effect: on True, records the spawn timestamp in the rolling
    window. On False, leaves the window unchanged.
    """
    key = workspace_id or "_default"
    now = time.time()
    cap = _cfg().spawn_max_per_workspace_per_min
    with _SPAWN_LOCK:
        window = [t for t in _SPAWN_WINDOW.get(key, []) if (now - t) < 60.0]
        if len(window) >= cap:
            _SPAWN_WINDOW[key] = window
            return False
        window.append(now)
        _SPAWN_WINDOW[key] = window
        return True

_AGENT_TYPE_HINTS = frozenset((
    "agent_parameter", "parameter_card", "agent_state",
    "agent_perception", "agent_transformer", "agent_emitter",
))


class CascadeScheduler:
    """Per-process scheduler that debounces + rate-limits agent ticks.

    Lifecycle hooks call ``schedule_for_card(node, ge, push_fn)`` after
    any concept mutation. If the node belongs to an agent body, the
    scheduler resolves the parameter card and arms a debounced tick.
    """

    def __init__(self):
        self._timers: Dict[str, threading.Timer] = {}     # pcid → Timer
        self._last_fire: Dict[str, float] = {}            # pcid → epoch
        self._minute_window: Dict[str, List[float]] = {}  # pcid → recent fire times
        self._total_fires: Dict[str, int] = {}            # pcid → lifetime count
        self._last_skip: Dict[str, str] = {}              # pcid → reason of last skipped schedule
        self._total_spawns: Dict[str, int] = {}           # pcid → cumulative spawns this agent has emitted
        self._total_spawns_rate_limited: Dict[str, int] = {}  # pcid → cumulative spawns rejected by the workspace cap
        self._lock = threading.Lock()

    def record_spawns(self, pcid: str, applied: int, rate_limited: int) -> None:
        """Record per-agent spawn counts after a tick lands. Called
        from ``MetaCognitionTick.run_async`` so the diagnostics panel
        can show how often the agent has proliferated.
        """
        if not pcid:
            return
        with self._lock:
            if applied:
                self._total_spawns[pcid] = int(self._total_spawns.get(pcid, 0)) + int(applied)
            if rate_limited:
                self._total_spawns_rate_limited[pcid] = (
                    int(self._total_spawns_rate_limited.get(pcid, 0)) + int(rate_limited)
                )

    def status(self, pcid: str = "") -> Dict[str, Any]:
        """Diagnostic snapshot — fire count, last fire age, rate-limit
        window for ``pcid`` (or every known agent if empty).
        """
        now = time.time()
        with self._lock:
            keys = [pcid] if pcid else sorted(set(
                list(self._total_fires.keys())
                + list(self._last_fire.keys())
                + list(self._timers.keys())
                + list(self._last_skip.keys())
                + list(self._total_spawns.keys())
                + list(self._total_spawns_rate_limited.keys())
            ))
            out: Dict[str, Any] = {}
            for k in keys:
                last = self._last_fire.get(k)
                window = [t for t in self._minute_window.get(k, []) if (now - t) < 60.0]
                self._minute_window[k] = window
                out[k] = {
                    "total_fires": int(self._total_fires.get(k, 0)),
                    "last_fire_age_sec": (now - last) if last else None,
                    "fires_last_minute": len(window),
                    "armed": k in self._timers,
                    "last_skip_reason": self._last_skip.get(k, ""),
                    "total_spawns": int(self._total_spawns.get(k, 0)),
                    "total_spawns_rate_limited": int(self._total_spawns_rate_limited.get(k, 0)),
                }
        return out

    def schedule_for_card(self, node, ge, *, push_fn=None, actor: str = "") -> None:
        if node is None or ge is None:
            return
        hint = (getattr(node, "type_hint", "") or "").lower()
        if hint not in _AGENT_TYPE_HINTS:
            return
        pcid = self._resolve_parameter_card_id(node, ge)
        if not pcid:
            return
        # §8D.27.1 — the agent's own writeback to its parameter card
        # (actor ``agent:<pcid>``) does NOT schedule another tick.
        # Without this short-circuit, every tick's self_state_updates
        # would cascade into another tick, spinning at the rate-limit
        # ceiling. External edits (user, peer tab, scroll, scanner)
        # still drive the loop because their actors don't match.
        if actor and actor == f"agent:{pcid}":
            with self._lock:
                self._last_skip[pcid] = "self-mutation"
            return
        if not self._cascade_enabled_for(pcid, ge):
            with self._lock:
                self._last_skip[pcid] = "cascade_disabled_or_paused"
            return
        if not self._under_rate_limit(pcid):
            with self._lock:
                self._last_skip[pcid] = "rate_limited"
            return
        with self._lock:
            self._last_skip[pcid] = ""
        self._arm(pcid, node.workspace_id or "", ge, push_fn=push_fn)

    # -- internals -----------------------------------------------------

    @staticmethod
    def _resolve_parameter_card_id(node, ge) -> str:
        """If ``node`` is the parameter card, return its id; otherwise
        decode the backing-pointer suffix (``agent::*::<pcid>``)."""
        hint = (getattr(node, "type_hint", "") or "").lower()
        if hint in ("agent_parameter", "parameter_card", "agent_state"):
            return node.concept_id
        bp = getattr(node, "backing_pointer", "") or ""
        if bp.startswith("agent::") and bp.count("::") >= 2:
            return bp.split("::", 2)[2]
        return ""

    @staticmethod
    def _cascade_enabled_for(pcid: str, ge) -> bool:
        try:
            param = ge.get_concept(pcid)
        except Exception:
            return False
        if param is None:
            return False
        try:
            meta = json.loads(param.data) if param.data else {}
        except Exception:
            return False
        if meta.get("paused", False):
            return False
        return bool(meta.get("cascade_enabled", False))

    def _under_rate_limit(self, pcid: str) -> bool:
        """Reject the schedule attempt only when the rolling 60-second
        window has already accumulated ``cascade_max_ticks_per_min``
        fires for this agent. The per-fire gap is enforced organically
        by the debounce: every new schedule re-arms the timer, so
        successive fires are at least debounce-seconds apart in
        steady-edit cases and further apart when edits coalesce.
        """
        now = time.time()
        cap = _cfg().cascade_max_ticks_per_min
        with self._lock:
            recent = [t for t in self._minute_window.get(pcid, []) if (now - t) < 60.0]
            self._minute_window[pcid] = recent
            if len(recent) >= cap:
                return False
        return True

    def _arm(self, pcid: str, workspace_id: str, ge, *, push_fn=None) -> None:
        with self._lock:
            existing = self._timers.get(pcid)
            if existing is not None:
                try:
                    existing.cancel()
                except Exception:
                    pass
            t = threading.Timer(
                _cfg().cascade_debounce_sec,
                self._fire,
                args=(pcid, workspace_id),
                kwargs={"push_fn": push_fn},
            )
            t.daemon = True
            self._timers[pcid] = t
            t.start()

    def _fire(self, pcid: str, workspace_id: str, *, push_fn=None) -> None:
        # Re-check the parameter card's flags right before launch. The
        # user may have paused the agent during the 1-second debounce
        # window; without this check the queued tick would still run
        # and emit actions the user wanted suppressed.
        try:
            from backend.services.graph_editor import get_default_graph_editor
            ge = get_default_graph_editor()
            if not self._cascade_enabled_for(pcid, ge):
                with self._lock:
                    self._timers.pop(pcid, None)
                    self._last_skip[pcid] = "paused_during_debounce"
                return
        except Exception:
            # If we can't verify, fail open — the alternative is
            # silently dropping a legitimate tick.
            pass
        with self._lock:
            self._timers.pop(pcid, None)
            now = time.time()
            self._last_fire[pcid] = now
            self._minute_window.setdefault(pcid, []).append(now)
            self._total_fires[pcid] = int(self._total_fires.get(pcid, 0)) + 1
        # Drive the tick on a thread (it's async, but launching a fresh
        # event loop from here is the simplest path that doesn't touch
        # the FastAPI lifespan loop).
        threading.Thread(
            target=_run_cascade_tick,
            args=(pcid, workspace_id),
            kwargs={"push_fn": push_fn},
            daemon=True,
        ).start()

    def cleanup_for_agent(self, pcid: str) -> None:
        """Drop all bookkeeping for ``pcid`` — called from the delete
        lifecycle so removed parameter cards don't leak scheduler
        state and don't fire orphan ticks if a debounce timer was
        armed at the moment of deletion. Also clears the agent_token
        ring buffer so a reconnecting tab doesn't see stale tokens
        for an agent that no longer exists.
        """
        if not pcid:
            return
        with self._lock:
            existing = self._timers.pop(pcid, None)
            self._last_fire.pop(pcid, None)
            self._minute_window.pop(pcid, None)
            self._total_fires.pop(pcid, None)
            self._last_skip.pop(pcid, None)
            self._total_spawns.pop(pcid, None)
            self._total_spawns_rate_limited.pop(pcid, None)
        if existing is not None:
            try:
                existing.cancel()
            except Exception:
                pass
        clear_agent_token_buffer(pcid)


def _run_cascade_tick(pcid: str, workspace_id: str, *, push_fn=None) -> None:
    """Synchronously execute one cascade tick in a worker thread."""
    try:
        from backend.services.graph_editor import get_default_graph_editor
        from backend.services.concept_index_service import get_concept_index_service
        from backend.services.apparition_service import ApparitionService
        ge = get_default_graph_editor()
        ci = get_concept_index_service(broadcast=push_fn, graph_editor=ge)
        app = ApparitionService(concept_index=ci, graph_editor=ge)
        slm = None
        try:
            from backend.services.slm_client import SLMClient
            slm = SLMClient()
        except Exception:
            slm = None
        tick = MetaCognitionTick(
            graph_editor=ge, concept_index=ci, apparition_service=app,
            slm_client=slm, broadcast=push_fn,
            workspace_id=workspace_id, parameter_card_id=pcid,
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(tick.run_async())
        finally:
            try:
                loop.close()
            except Exception:
                pass
    except Exception as e:
        logger.warning("CascadeScheduler tick for %s failed: %s", pcid, e)


_CASCADE_SCHEDULER: Optional[CascadeScheduler] = None
_CASCADE_SCHEDULER_LOCK = threading.Lock()


def get_cascade_scheduler() -> CascadeScheduler:
    global _CASCADE_SCHEDULER
    with _CASCADE_SCHEDULER_LOCK:
        if _CASCADE_SCHEDULER is None:
            _CASCADE_SCHEDULER = CascadeScheduler()
    return _CASCADE_SCHEDULER


# ---------------------------------------------------------------------------
# §8D.27 — Visible agent body subgraph
#
# Materialise three concrete concept nodes downstream of the parameter
# card: perception, transformer, emitter. Each has an ``agent::*``
# backing pointer (see backing_registry.py); the user can pin, edit,
# fork any of them and the behaviour shifts accordingly.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# §8D.27 — Agent backing-pointer handle format
#
# The trio of body cards (perception / transformer / emitter) use a
# uniform handle shape ``agent::<role>::<parameter_card_id>``. Centralising
# the construction + parsing here means renaming the format only touches
# this module — earlier the literal string was duplicated across 17 call
# sites in spawn / fork / find / invoke / registry resolvers, which made
# any rename a multi-file dance with high drift risk.
# ---------------------------------------------------------------------------

AGENT_HANDLE_PREFIX = "agent::"
AGENT_ROLE_PERCEPTION = "perception"
AGENT_ROLE_TRANSFORMER = "transformer"
AGENT_ROLE_EMITTER = "emitter"
_AGENT_ROLES = frozenset((AGENT_ROLE_PERCEPTION, AGENT_ROLE_TRANSFORMER, AGENT_ROLE_EMITTER))


def agent_handle(role: str, parameter_card_id: str) -> str:
    """Canonical backing-pointer string for an agent body card."""
    return f"{AGENT_HANDLE_PREFIX}{role}::{parameter_card_id}"


def parse_agent_handle(handle: str) -> Optional[tuple]:
    """Inverse of :func:`agent_handle`. Returns ``(role, parameter_card_id)``
    or ``None`` if the handle isn't an agent-body handle."""
    if not handle or not handle.startswith(AGENT_HANDLE_PREFIX):
        return None
    parts = handle.split("::", 2)
    if len(parts) < 3:
        return None
    role = parts[1]
    if role not in _AGENT_ROLES:
        return None
    return role, parts[2]


def agent_role_prefix(role: str) -> str:
    """Prefix used by ``BackingRegistry._resolve_by_prefix`` to match
    every handle for ``role``. Equivalent to ``agent_handle(role, "")``
    without the trailing pcid."""
    return f"{AGENT_HANDLE_PREFIX}{role}::"


_DEFAULT_PERCEPTION_CONFIG = {
    "include_params": True,
    "include_apparitions": True,
    "apparition_k": 5,
    "include_zoi": True,
    "include_concept_count": True,
}

_DEFAULT_TRANSFORMER_PROMPT = (
    "You are a meta-cognition node in a visible concept-graph editor. "
    "Read the perception below, decide one or two useful next actions, "
    "and respond ONLY with a JSON object matching this schema:\n"
    '{ "rationale": "<one-paragraph explanation>", '
    '"creates": [{"name": "...", "description": "...", "data": "...", '
    '"type_hint": "agent_authored", "workspace_id": ""}], '
    '"links": [{"source_id": "...", "target_id": "...", "edge_type": "RELATES_TO"}], '
    '"writes": [{"target_id": "...", "field": "description", "value": "..."}], '
    '"deletes": [{"target_id": "..."}], '
    '"spawns": [{"goal": "...", "name": "...", "fork_from": ""}], '
    '"self_state_updates": {"goal": "..."} }\n\n'
    "Goal: {goal}\n\nPerception:\n{perception}\n\n"
    "Respond with JSON only. Keep `creates` to at most 2 cards per tick. "
    "Use descriptive `description` fields that declare what each new "
    "card does. Empty arrays are fine if you have nothing to do. "
    "Use `spawns` ONLY when delegating a clearly-separable sub-goal to "
    "a sibling agent; the workspace caps proliferation at 5/min, so "
    "spawning sparingly is required. Set `fork_from` to your own "
    "parameter card id to clone yourself with a refined goal."
)

_DEFAULT_EMITTER_FILTER = {"allow": [
    "creates", "links", "writes", "deletes", "invokes",
    "commits", "reviews", "spawns",
]}


def spawn_agent_body_subgraph(
    *,
    graph_editor,
    parameter_card_id: str,
    workspace_id: str = "",
    push_fn: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Create the perception / transformer / emitter trio wired to a
    parameter card, with backing pointers that make each step
    addressable + editable. Idempotent — re-running with the same
    parameter card returns the existing nodes if they're present.

    Returns ``{ perception, transformer, emitter }`` as dicts (each
    with ``concept_id`` set) plus the edge ids that wire them.
    """
    if graph_editor is None or not parameter_card_id:
        return {"ok": False, "error": "graph_editor and parameter_card_id required"}
    from backend.services.concept_lifecycle import apply_create_lifecycle

    short = parameter_card_id[:12]

    # Compute deterministic positions so the agent body lays out as a
    # visible left-to-right chain on canvas (param → perception →
    # transformer → emitter). Anchor near the parameter card if it
    # already has a layout_xy; otherwise fan out from a hash-derived
    # column so multiple agents in one workspace don't pile up. Cards
    # stay drag-movable — these are just first-paint defaults.
    _PARAM_X, _CHAIN_DX, _CHAIN_Y_BASE = 200.0, 340.0, 240.0
    _ROW_DY = 220.0  # vertical offset per additional agent in workspace

    anchor_x, anchor_y = _PARAM_X, _CHAIN_Y_BASE
    try:
        param_node = graph_editor.get_concept(parameter_card_id)
        if param_node is not None and param_node.layout_xy:
            try:
                parsed = json.loads(param_node.layout_xy)
                if isinstance(parsed.get("x"), (int, float)):
                    anchor_x = float(parsed["x"])
                if isinstance(parsed.get("y"), (int, float)):
                    anchor_y = float(parsed["y"])
            except Exception:
                pass
        else:
            # Stagger by the number of existing agents in the workspace
            # so a fresh spawn doesn't overlap prior agents' rows.
            try:
                existing_params = [
                    n for n in graph_editor.list_concepts(
                        workspace_id=workspace_id, type_hint="agent_parameter",
                        limit=200,
                    ) or []
                    if n.concept_id != parameter_card_id
                ]
                anchor_y = _CHAIN_Y_BASE + len(existing_params) * _ROW_DY
            except Exception:
                pass
            # Persist the anchor on the parameter card so future spawns
            # and the frontend's layout_xy reader agree on its position.
            if param_node is not None:
                try:
                    graph_editor.update_concept(
                        parameter_card_id,
                        layout_xy=json.dumps({"x": anchor_x, "y": anchor_y}),
                    )
                except Exception:
                    pass
    except Exception:
        pass

    def _layout_for(slot: str) -> Dict[str, float]:
        offsets = {"perception": 1, "transformer": 2, "emitter": 3}
        return {"x": anchor_x + _CHAIN_DX * offsets.get(slot, 1), "y": anchor_y}

    def _spawn(name: str, type_hint: str, description: str, data: str, backing: str, slot: str) -> Any:
        # Re-use existing card if one with the same backing pointer
        # already lives in the workspace (idempotent spawn).
        try:
            for n in graph_editor.list_concepts(workspace_id=workspace_id, limit=1000) or []:
                if (n.backing_pointer or "") == backing:
                    return n
        except Exception:
            pass
        node = graph_editor.create_concept(
            name=name,
            description=description,
            data=data,
            backing_pointer=backing,
            provenance="agent-authored",
            workspace_id=workspace_id,
            type_hint=type_hint,
            layout_xy=_layout_for(slot),
        )
        if node is not None:
            apply_create_lifecycle(node, graph_editor, push_fn=push_fn, actor="agent:spawn")
        return node

    perception = _spawn(
        name=f"perception_{short}",
        type_hint="agent_perception",
        description=(
            "Reads the local subgraph around the parameter card and emits a "
            "perception text block for the downstream transformer. The "
            "``data`` block configures inclusion: params, apparitions, "
            "zone_of_influence, concept count."
        ),
        data=json.dumps(_DEFAULT_PERCEPTION_CONFIG, indent=2),
        backing=agent_handle(AGENT_ROLE_PERCEPTION, parameter_card_id),
        slot="perception",
    )
    transformer = _spawn(
        name=f"transformer_{short}",
        type_hint="agent_transformer",
        description=(
            "Calls the on-device SLM with the perception + the goal. The "
            "``data`` block is the prompt template; ``{perception}`` and "
            "``{goal}`` are substituted before the call."
        ),
        data=_DEFAULT_TRANSFORMER_PROMPT,
        backing=agent_handle(AGENT_ROLE_TRANSFORMER, parameter_card_id),
        slot="transformer",
    )
    emitter = _spawn(
        name=f"emitter_{short}",
        type_hint="agent_emitter",
        description=(
            "Applies the SLM's structured-output action envelope to the "
            "canvas via the shared ActionResolver. The ``data`` block can "
            "carry an ``allow`` filter to disable action kinds — useful for "
            "user-supervised modes."
        ),
        data=json.dumps(_DEFAULT_EMITTER_FILTER, indent=2),
        backing=agent_handle(AGENT_ROLE_EMITTER, parameter_card_id),
        slot="emitter",
    )

    def _wire(src: str, tgt: str) -> Optional[str]:
        if not src or not tgt:
            return None
        try:
            from backend.services.concept_lifecycle import apply_edge_create_lifecycle
            edge = graph_editor.create_concept_edge(
                source_id=src, target_id=tgt,
                edge_type="WIRES_TO", workspace_id=workspace_id,
            )
            apply_edge_create_lifecycle(
                edge, graph_editor,
                workspace_id=workspace_id, push_fn=push_fn,
            )
            return getattr(edge, "edge_id", None) if edge is not None else None
        except Exception:
            return None

    edges = {
        "param_to_perception": _wire(parameter_card_id, getattr(perception, "concept_id", "")),
        "perception_to_transformer": _wire(
            getattr(perception, "concept_id", ""), getattr(transformer, "concept_id", ""),
        ),
        "transformer_to_emitter": _wire(
            getattr(transformer, "concept_id", ""), getattr(emitter, "concept_id", ""),
        ),
    }

    return {
        "ok": True,
        "parameter_card_id": parameter_card_id,
        "perception": getattr(perception, "concept_id", "") if perception else None,
        "transformer": getattr(transformer, "concept_id", "") if transformer else None,
        "emitter": getattr(emitter, "concept_id", "") if emitter else None,
        "edges": edges,
    }


def fork_agent_body_subgraph(
    *,
    graph_editor,
    source_parameter_card_id: str,
    workspace_id: str = "",
    new_name: str = "",
    push_fn: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """§8D.32.3 — drag-clone an agent's subgraph as a new sibling.

    Reads the source parameter card + its perception / transformer /
    emitter cards (where present), then spawns a fresh trio bound to
    a new parameter card. The new parameter card's data block carries
    the source's goal + zone_of_influence but resets ``step_index`` to
    0 and clears ``paused`` / ``cascade_enabled`` (the fork starts on
    manual mode regardless of the source's state). Customised body
    cards (edited prompt template, tightened emitter filter) are
    cloned verbatim into the new body so the fork inherits the
    source's specialised configuration.
    """
    if graph_editor is None or not source_parameter_card_id:
        return {"ok": False, "error": "graph_editor and source_parameter_card_id required"}
    from backend.services.concept_lifecycle import apply_create_lifecycle

    src_param = graph_editor.get_concept(source_parameter_card_id)
    if src_param is None:
        return {"ok": False, "error": f"source parameter card {source_parameter_card_id} not found"}
    try:
        src_meta = json.loads(src_param.data) if src_param.data else {}
    except Exception:
        src_meta = {}
    forked_meta = {
        "goal": src_meta.get("goal", "Inspect the graph and suggest one useful next concept."),
        "step_index": 0,
        "zone_of_influence": dict(src_meta.get("zone_of_influence") or {}),
        "cascade_enabled": False,
        "paused": False,
        "forked_from": source_parameter_card_id,
    }
    fork_param = graph_editor.create_concept(
        name=new_name or f"{src_param.name}_fork",
        description=src_param.description + " (forked)",
        data=json.dumps(forked_meta, indent=2),
        provenance="user-authored",
        workspace_id=workspace_id or src_param.workspace_id,
        type_hint="agent_parameter",
    )
    if fork_param is None:
        return {"ok": False, "error": "failed to create forked parameter card"}
    apply_create_lifecycle(fork_param, graph_editor, push_fn=push_fn, actor="user:_anon")

    # Spawn the body subgraph for the new parameter card.
    spawn = spawn_agent_body_subgraph(
        graph_editor=graph_editor,
        parameter_card_id=fork_param.concept_id,
        workspace_id=workspace_id or src_param.workspace_id,
        push_fn=push_fn,
    )
    if not spawn.get("ok"):
        return spawn

    # Carry over any customisations from the source body. Walk the
    # source's edges to find its perception/transformer/emitter cards,
    # then overwrite the freshly-spawned cards' data with the source's
    # data. The backing pointers themselves don't need updating (they
    # already encode the new parameter card id by construction).
    from backend.services.concept_lifecycle import (
        apply_update_lifecycle, _node_to_dict,
    )

    def _copy_card_data(src_handle_prefix: str, dst_card_id: Optional[str]):
        if not dst_card_id:
            return
        try:
            for e in graph_editor.list_concept_edges(
                workspace_id=src_param.workspace_id, limit=200,
            ):
                src_node = graph_editor.get_concept(e.target_id)
                if (
                    src_node is not None
                    and (src_node.backing_pointer or "").startswith(src_handle_prefix)
                ):
                    pre = graph_editor.get_concept(dst_card_id)
                    if pre is None:
                        return
                    pre_dict = _node_to_dict(pre)
                    updated = graph_editor.update_concept(
                        dst_card_id, data=src_node.data or "",
                    )
                    if updated is not None:
                        apply_update_lifecycle(
                            updated, graph_editor,
                            pre_dict=pre_dict,
                            embed_fields_changed=False,
                            actor="user:_anon",
                            push_fn=push_fn,
                        )
                    return
        except Exception:
            pass

    _copy_card_data(
        agent_handle(AGENT_ROLE_PERCEPTION, source_parameter_card_id),
        spawn.get("perception"),
    )
    _copy_card_data(
        agent_handle(AGENT_ROLE_TRANSFORMER, source_parameter_card_id),
        spawn.get("transformer"),
    )
    _copy_card_data(
        agent_handle(AGENT_ROLE_EMITTER, source_parameter_card_id),
        spawn.get("emitter"),
    )

    return {
        "ok": True,
        "source_parameter_card_id": source_parameter_card_id,
        "parameter_card_id": fork_param.concept_id,
        "perception": spawn.get("perception"),
        "transformer": spawn.get("transformer"),
        "emitter": spawn.get("emitter"),
        "edges": spawn.get("edges"),
    }


# ---------------------------------------------------------------------------
# W35 / §8D.27 — Spine delta consumer
# ---------------------------------------------------------------------------

# Module-level lock to serialise spine-delta writes so two
# near-simultaneous frames don't both read the same zoi snapshot
# and one's increments get clobbered by the other's. Coarse but
# the volume is low (one frame per ~150ms scroll batch).
_SPINE_WRITE_LOCK = threading.Lock()


def apply_spine_delta_to_active_agents(
    *,
    graph_editor,
    workspace_id: str = "",
    popped: Optional[List[str]] = None,
    folded: Optional[List[str]] = None,
    push_fn: Optional[Callable[..., Any]] = None,
) -> int:
    """Write a viewport delta to every active agent's parameter card.

    §8D.27 — meta-cognition nodes read their parameter card's
    `zone_of_influence` field to know what the user is currently
    attending to. This helper updates that field on every concept
    node whose `type_hint` includes "parameter" (or "agent_state"
    legacy), scoped to ``workspace_id`` if provided.

    Returns the number of parameter cards updated.

    Fix: spine_delta frames can arrive concurrently across tabs
    (or from a fast scroll). Without serialisation, two writers
    can each read the same pre-state and the second's write
    clobbers the first's increments. We acquire a module-level
    lock for the read-modify-write so each delta lands atomically.
    """
    if graph_editor is None:
        return 0
    popped = list(popped or [])
    folded = list(folded or [])
    if not popped and not folded:
        return 0
    with _SPINE_WRITE_LOCK:
        try:
            candidates = []
            # Look for type_hint matches first; fall back to scanning all
            # concepts whose data block contains a ``goal`` field (legacy
            # parameter-card convention).
            for hint in ("agent_parameter", "parameter_card", "agent_state"):
                try:
                    candidates.extend(graph_editor.list_concepts(
                        workspace_id=workspace_id, type_hint=hint, limit=50,
                    ))
                except Exception:
                    pass
            n = 0
            for node in candidates:
                # Always re-fetch the node inside the lock to read
                # the freshest data block, in case another writer
                # updated it between candidate-listing and here.
                try:
                    fresh = graph_editor.get_concept(node.concept_id)
                    if fresh is None:
                        continue
                except Exception:
                    continue
                try:
                    meta = json.loads(fresh.data) if fresh.data else {}
                except Exception:
                    meta = {}
                zoi = dict(meta.get("zone_of_influence") or {})
                for cid in popped:
                    zoi[cid] = float(zoi.get(cid, 0.0) + 0.2)
                    if zoi[cid] > 1.0: zoi[cid] = 1.0
                for cid in folded:
                    if cid in zoi:
                        zoi[cid] = float(zoi[cid] * 0.5)
                        if zoi[cid] < 0.05: del zoi[cid]
                meta["zone_of_influence"] = zoi
                try:
                    from backend.services.concept_lifecycle import (
                        apply_update_lifecycle, _node_to_dict,
                    )
                    pre_dict = _node_to_dict(fresh)
                    updated = graph_editor.update_concept(
                        fresh.concept_id, data=json.dumps(meta),
                    )
                    if updated is not None:
                        # Route through the shared lifecycle so other
                        # tabs see the zoi change via concept_changed
                        # and the evolution log records the scroll-
                        # driven mutation. Only ``data`` changed →
                        # nomic/tfidf re-embed is unnecessary.
                        apply_update_lifecycle(
                            updated, graph_editor,
                            pre_dict=pre_dict,
                            embed_fields_changed=False,
                            actor="spine_delta",
                            push_fn=push_fn,
                        )
                    n += 1
                except Exception:
                    continue
            return n
        except Exception:
            return 0
