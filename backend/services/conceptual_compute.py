"""Conceptual Compute Node (Workstream W31; anchors §8C.7, §8D.5,
§8D.27, §8D.29, §8D.30).

The fundamental primitive that turns any **concept node** (a record
with name / description / data / rendering — see §8D.1) into a
**callable LangGraph node**. Compilation walks the four card fields:

  1. **Resolve** ``{slug}`` placeholders in description+data against
     upstream concept nodes (§8D.3 / §8D.21.1) — the existing
     ``resolve_concept_refs`` does this.
  2. **Classify** the card into one of these kinds, based on a
     ``compute_kind`` hint in the data block (or auto-detected):
       * ``"plain"``        — render the data tree → write to ``rendering``.
       * ``"prompt"``       — substitute refs in description as the
                              prompt; call the SLM streaming; write the
                              response to ``rendering``.
       * ``"structured"``   — same as prompt, but the data block carries
                              a JSON-schema'd Pydantic model. The SLM's
                              output is parsed + validated against it.
       * ``"python"``       — the data block declares an entry-point
                              string ``"module:callable"``; the callable
                              receives the resolved inputs dict and its
                              return value becomes ``rendering``.
  3. **Validate** with Pydantic (kinds 3+4) and persist the result back
     into the node's ``rendering`` field via the lifecycle so peer tabs
     observe the update.
  4. **Expose** the same call as a ``langgraph.graph.StateGraph`` node
     so subgraphs can be compiled into a chained executable plan
     (§8C.7's "LangGraph operations as functional-object cards").

The compiled LangGraph state is a flat dict keyed by ``concept_id``
whose values are the rendered outputs; downstream nodes read upstream
values via the resolved ``{slug}`` refs at execution time. The state
graph is built by walking edges backward from the focal node
(``compile_subgraph_to_langgraph``).

This module deliberately keeps the SLM call optional — if no SLM
client is wired or the on-device model isn't loadable, "prompt" /
"structured" kinds short-circuit to a deterministic stub response so
the harness can still exercise the wiring without spinning the GPU.
"""

from __future__ import annotations

import importlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data-block schema (read from the concept node's ``data`` field)
# ---------------------------------------------------------------------------

# These keys, when present in the JSON-parsed data block, drive the
# compute kind selection. Other keys are passed through as inputs.

_KIND_KEY        = "compute_kind"   # explicit kind override
_PROMPT_KEY      = "prompt"         # prompt template (uses {slug} refs)
_SYSTEM_KEY      = "system_prompt"  # optional SLM system instruction
_OUTPUT_KEY      = "output_schema"  # Pydantic schema (JSON-schema dict)
_PY_ENTRY_KEY    = "python_entry"   # "module.path:callable_name"
_INPUTS_KEY      = "inputs"         # dict passed as kwargs to python_entry


# ---------------------------------------------------------------------------
# Spec — what the data block declared (parsed once per compile)
# ---------------------------------------------------------------------------

@dataclass
class ComputeNodeSpec:
    """Parsed declaration extracted from a concept node's data block."""

    kind: str = "plain"              # one of the kinds above
    prompt: str = ""
    system_prompt: str = ""
    output_schema: Optional[Dict[str, Any]] = None    # raw JSON-schema
    python_entry: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    raw_data: str = ""               # the unparsed original data field

    @classmethod
    def from_concept(cls, node) -> "ComputeNodeSpec":
        """Parse ``node.data`` into a spec. Auto-classifies when no
        ``compute_kind`` is present."""
        spec = cls()
        spec.raw_data = node.data or ""
        if not spec.raw_data:
            return spec
        # Try JSON; non-JSON data falls through as "plain".
        try:
            parsed = json.loads(spec.raw_data)
        except Exception:
            return spec
        if not isinstance(parsed, dict):
            return spec
        spec.kind          = str(parsed.get(_KIND_KEY, "")).strip().lower()
        spec.prompt        = str(parsed.get(_PROMPT_KEY, "") or "")
        spec.system_prompt = str(parsed.get(_SYSTEM_KEY, "") or "")
        schema = parsed.get(_OUTPUT_KEY)
        if isinstance(schema, dict):
            spec.output_schema = schema
        spec.python_entry  = str(parsed.get(_PY_ENTRY_KEY, "") or "")
        inputs = parsed.get(_INPUTS_KEY)
        if isinstance(inputs, dict):
            spec.inputs = inputs
        # Auto-classify if no explicit kind was provided.
        if not spec.kind:
            if spec.python_entry:
                spec.kind = "python"
            elif spec.output_schema and spec.prompt:
                spec.kind = "structured"
            elif spec.prompt:
                spec.kind = "prompt"
            else:
                spec.kind = "plain"
        return spec


# ---------------------------------------------------------------------------
# Pydantic factory — build a runtime model class from a JSON-schema fragment
# ---------------------------------------------------------------------------

def build_pydantic_model_from_schema(
    schema: Dict[str, Any],
    *,
    model_name: str = "ComputeOutput",
) -> Optional[Type[Any]]:
    """Build a Pydantic v1/v2-compatible BaseModel subclass from a
    flat JSON-schema-shaped dict.

    Supports the common shape used in the data block:

        {"type": "object", "properties": {
            "title":  {"type": "string"},
            "price":  {"type": "number"},
            "tags":   {"type": "array", "items": {"type": "string"}}}}

    Returns ``None`` if Pydantic isn't importable or the schema is
    unparseable; the caller falls back to permissive dict validation.
    """
    try:
        from pydantic import BaseModel, create_model
    except Exception:
        return None
    if not isinstance(schema, dict):
        return None
    props = schema.get("properties") or {}
    if not isinstance(props, dict):
        return None
    type_map: Dict[str, Type[Any]] = {
        "string":  str,
        "integer": int,
        "number":  float,
        "boolean": bool,
        "array":   list,
        "object":  dict,
    }
    fields: Dict[str, Any] = {}
    required = set(schema.get("required") or [])
    for fname, fspec in props.items():
        if not isinstance(fspec, dict):
            continue
        py_type = type_map.get(str(fspec.get("type", "string")).lower(), Any)
        default = ... if fname in required else None
        fields[str(fname)] = (py_type, default)
    if not fields:
        return None
    try:
        return create_model(model_name, **fields, __base__=BaseModel)
    except Exception as exc:
        logger.warning("build_pydantic_model_from_schema failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# The core primitive — one concept node, compiled
# ---------------------------------------------------------------------------

class ConceptComputeNode:
    """Wrap one concept node as a callable LangGraph-compatible node.

    Constructor binds the concept_id + a graph_editor + optional
    SLM client. ``__call__(state)`` is the LangGraph node signature
    (state dict in, state dict out). ``compile()`` is the synchronous
    one-shot entry the REPL + scenarios use.

    The returned dict from both entry points has the shape:

        { concept_id: { "rendering": str, "raw_output": Any, "kind": str } }

    so downstream LangGraph nodes can read the upstream rendering via
    ``state[upstream_id]["rendering"]``. The same dict is also useful
    in tests — a single compile() call gives you the full diagnostic.
    """

    def __init__(
        self,
        concept_id: str,
        *,
        graph_editor,
        slm_client=None,
        broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
        persist_rendering: bool = True,
    ):
        self.concept_id = concept_id
        self._ge = graph_editor
        self._slm = slm_client
        self._broadcast = broadcast
        self._persist = persist_rendering

    # -----------------------------------------------------------------
    # LangGraph node signature
    # -----------------------------------------------------------------

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        out = self.compile(extra_state=state or {})
        merged: Dict[str, Any] = dict(state or {})
        merged[self.concept_id] = out
        return merged

    # -----------------------------------------------------------------
    # Synchronous compile entry
    # -----------------------------------------------------------------

    def compile(self, *, extra_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compile this concept node once. Returns a diagnostic dict
        with at least ``rendering``, ``raw_output``, and ``kind``.

        The compile pipeline is:
            1. Fetch the concept node.
            2. Parse its data block into a ComputeNodeSpec.
            3. Resolve {slug} refs in the resolved prompt + description.
            4. Dispatch by kind.
            5. Optionally persist the new rendering via the lifecycle.
        """
        node = self._ge.get_concept(self.concept_id) if self._ge else None
        if node is None:
            return {
                "rendering": "",
                "raw_output": None,
                "kind": "missing",
                "error": f"concept {self.concept_id!r} not found",
            }
        spec = ComputeNodeSpec.from_concept(node)
        # Always resolve refs in description + prompt first.
        from backend.services.compile_pipeline import (
            resolve_concept_refs, compute_rendering_tree,
        )
        resolved_description = resolve_concept_refs(
            node.description or "", ge=self._ge,
        )
        resolved_prompt = resolve_concept_refs(
            spec.prompt or "", ge=self._ge,
        )

        # Dispatch by kind.
        if spec.kind == "python":
            raw_out, rendering = self._dispatch_python(spec, resolved_prompt)
        elif spec.kind == "structured":
            raw_out, rendering = self._dispatch_structured(spec, resolved_prompt, resolved_description)
        elif spec.kind == "prompt":
            raw_out, rendering = self._dispatch_prompt(spec, resolved_prompt, resolved_description)
        else:
            # "plain" — use the existing tree-print pipeline.
            rendering = compute_rendering_tree(spec.raw_data, ge=self._ge)
            raw_out = rendering

        # §R.6 — record the forward application in the inverse-lookup map:
        # the {ref} inputs this dispatch consumed map FORWARD_MAPPED_TO this
        # node, under the dispatch's function identity. Idempotent on the
        # edge natural key, so cascade re-fires don't grow the state space;
        # best-effort — a mapping-log hiccup never blocks the compile.
        try:
            from backend.services.forward_inverse_map import (
                record_forward_call, referenced_input_ids,
            )
            consumed = referenced_input_ids(
                node, self._ge, workspace_id=getattr(node, "workspace_id", "") or "",
            )
            if consumed:
                if spec.kind == "python":
                    fn_sig = f"python:{spec.python_entry or ''}"
                elif spec.kind == "structured":
                    _title = (spec.output_schema or {}).get("title", "") if isinstance(spec.output_schema, dict) else ""
                    fn_sig = f"structured:{_title}"
                elif spec.kind == "prompt":
                    fn_sig = "prompt"
                else:
                    fn_sig = "template"
                record_forward_call(
                    self._ge,
                    output_id=self.concept_id,
                    input_ids=consumed,
                    fn_signature=fn_sig,
                    workspace_id=getattr(node, "workspace_id", "") or "",
                )
        except Exception as exc:
            logger.warning(
                "ConceptComputeNode forward-map record failed for %s: %s",
                self.concept_id, exc,
            )

        # Persist back into the node's rendering field via the lifecycle
        # so peer tabs see the new rendering and the evolution log records.
        if self._persist and rendering != (node.rendering or ""):
            try:
                from backend.services.concept_lifecycle import (
                    apply_update_lifecycle, _node_to_dict,
                )
                pre_dict = _node_to_dict(node)
                updated = self._ge.update_concept(
                    self.concept_id, rendering=rendering,
                )
                if updated is not None:
                    apply_update_lifecycle(
                        updated, self._ge,
                        pre_dict=pre_dict,
                        embed_fields_changed=False,  # rendering doesn't reembed
                        actor="conceptual_compute",
                        push_fn=self._broadcast,
                    )
            except Exception as exc:
                logger.warning(
                    "ConceptComputeNode persist failed for %s: %s",
                    self.concept_id, exc,
                )

        return {
            "rendering": rendering,
            "raw_output": raw_out,
            "kind": spec.kind,
            "concept_id": self.concept_id,
            "description_resolved": resolved_description,
            "prompt_resolved": resolved_prompt,
        }

    # -----------------------------------------------------------------
    # Dispatch helpers
    # -----------------------------------------------------------------

    def _dispatch_python(
        self, spec: ComputeNodeSpec, resolved_prompt: str,
    ) -> tuple:
        """Resolve module:callable, invoke with resolved inputs."""
        if not spec.python_entry or ":" not in spec.python_entry:
            return None, f"[python] invalid entry: {spec.python_entry!r}"
        modpath, _, callable_name = spec.python_entry.partition(":")
        try:
            mod = importlib.import_module(modpath)
            fn = getattr(mod, callable_name, None)
            if fn is None:
                return None, f"[python] missing callable: {spec.python_entry}"
            result = fn(**(spec.inputs or {}))
            # Stringify the result for the rendering field.
            if isinstance(result, (str, int, float, bool)):
                rendering = str(result)
            else:
                try:
                    rendering = json.dumps(result, indent=2, default=str)
                except Exception:
                    rendering = str(result)
            return result, rendering
        except Exception as exc:
            logger.warning("ConceptComputeNode python dispatch failed: %s", exc)
            return None, f"[python error] {exc}"

    def _dispatch_prompt(
        self, spec: ComputeNodeSpec,
        resolved_prompt: str, resolved_description: str,
    ) -> tuple:
        """Call SLM with the resolved prompt. Returns raw text + rendering
        (same string for an unstructured prompt)."""
        # Prefer the prompt key; fall back to the description so users
        # can build a card that just has a single text field.
        prompt_text = resolved_prompt or resolved_description
        if not prompt_text.strip():
            return "", "[prompt] empty"
        text = self._invoke_slm(prompt_text, spec.system_prompt)
        return text, text

    def _dispatch_structured(
        self, spec: ComputeNodeSpec,
        resolved_prompt: str, resolved_description: str,
    ) -> tuple:
        """Call SLM, parse output against the declared Pydantic schema.

        Returns (validated_instance_or_dict, rendering_string). The
        rendering is the JSON-dumped validated payload so downstream
        text-substitution sees the structured fields.
        """
        prompt_text = resolved_prompt or resolved_description
        if not prompt_text.strip():
            return None, "[structured] empty prompt"

        # Build a Pydantic model from the schema (if Pydantic available).
        model_cls = build_pydantic_model_from_schema(
            spec.output_schema or {}, model_name=f"Output_{self.concept_id[:8]}",
        )
        # Augment the prompt with the JSON-schema so the SLM emits the
        # required shape — this is the §8D.5 contract surfaced.
        schema_hint = json.dumps(spec.output_schema or {}, indent=2)
        instruction = (
            f"{prompt_text}\n\n"
            "Reply with ONLY a single JSON object matching this schema:\n"
            f"{schema_hint}\n"
        )
        # Try structured SLM path first; fall back to streaming + parse.
        raw = self._invoke_slm_json(instruction, spec.system_prompt)
        # Validate against the Pydantic model if available.
        if model_cls is not None and isinstance(raw, dict):
            try:
                inst = model_cls(**raw)
                payload = inst.model_dump() if hasattr(inst, "model_dump") else inst.dict()
                return payload, json.dumps(payload, indent=2)
            except Exception as exc:
                logger.warning(
                    "ConceptComputeNode pydantic validation failed for %s: %s",
                    self.concept_id, exc,
                )
                return {
                    "_validation_error": str(exc),
                    "_raw": raw,
                }, json.dumps({"_validation_error": str(exc), "_raw": raw}, indent=2)
        # No model class or non-dict raw — pass through.
        if isinstance(raw, dict):
            return raw, json.dumps(raw, indent=2)
        return raw, str(raw)

    # -----------------------------------------------------------------
    # SLM access — best-effort, falls back to deterministic stub
    # -----------------------------------------------------------------

    def _invoke_slm(self, prompt: str, system_prompt: str = "") -> str:
        """Call the SLM (sync). If unavailable, return a stub."""
        if self._slm is None:
            return self._stub_response(prompt, system_prompt)
        try:
            # Prefer a sync structured-text method if present.
            fn = getattr(self._slm, "generate_text", None)
            if fn is not None:
                return str(fn(prompt, system_prompt=system_prompt) or "")
            # Otherwise call generate_json and stringify.
            data = self._slm.generate_json(prompt, system_prompt=system_prompt)
            return json.dumps(data) if data else ""
        except Exception:
            # A real SLM call failed — propagate loudly (§8D.46), do NOT
            # swallow to a stub. The harness stub path is the WFH_FAKE_SLM
            # gate inside SLMClient (returns stub text WITHOUT raising) and
            # the use_slm=False `self._slm is None` branch above; only a
            # genuine backend failure reaches here.
            raise

    def _invoke_slm_json(self, prompt: str, system_prompt: str = "") -> Any:
        """Call the SLM expecting JSON. Returns dict | list | None."""
        if self._slm is None:
            return self._stub_json(prompt, system_prompt)
        try:
            fn = getattr(self._slm, "generate_structured", None)
            if fn is not None:
                return fn(prompt, system_prompt=system_prompt)
            return self._slm.generate_json(prompt, system_prompt=system_prompt)
        except Exception:
            # Real SLM failure — propagate loudly (§8D.46), never swallow
            # to a stub. Harness stub is the WFH_FAKE_SLM gate (no raise)
            # or the use_slm=False None branch above.
            raise

    def _stub_response(self, prompt: str, system_prompt: str = "") -> str:
        """Deterministic offline stub so scenarios can verify wiring
        without a model loaded. Returns an echo with provenance tag."""
        head = prompt.strip().splitlines()[0] if prompt.strip() else ""
        return f"[stub-slm] echoes: {head[:160]}"

    def _stub_json(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """Deterministic JSON stub for structured scenarios."""
        return {
            "_stub":  True,
            "prompt_head": prompt.strip().splitlines()[0][:120] if prompt.strip() else "",
        }


# ---------------------------------------------------------------------------
# Subgraph compilation — wrap a wired neighbourhood as a LangGraph plan
# ---------------------------------------------------------------------------

def _collect_back_references(
    graph_editor, focal_id: str, *, max_depth: int = 4,
    workspace_id: str = "",
) -> List[str]:
    """Return concept ids reachable by walking edges INTO ``focal_id``
    (i.e., upstream dependencies). Breadth-first, depth-bounded so a
    densely-wired graph doesn't blow up.
    """
    if not focal_id or graph_editor is None:
        return []
    seen: List[str] = [focal_id]
    seen_set = {focal_id}
    frontier = [focal_id]
    depth = 0
    while frontier and depth < max_depth:
        next_frontier: List[str] = []
        for cid in frontier:
            try:
                # Edges where THIS node is the TARGET → its sources are upstream.
                upstream_edges = graph_editor.list_concept_edges(
                    workspace_id=workspace_id, target_id=cid, limit=200,
                )
            except Exception:
                upstream_edges = []
            for e in upstream_edges:
                src = getattr(e, "source_id", "") or ""
                if not src or src in seen_set:
                    continue
                seen_set.add(src)
                seen.append(src)
                next_frontier.append(src)
        frontier = next_frontier
        depth += 1
    # Return in dependency order: deepest upstream first, focal last.
    return list(reversed(seen))


def _component_index(
    focal_id: str, *, graph_editor, workspace_id: str = "",
) -> tuple:
    """Shared core for :func:`readout_nodes` / :func:`input_nodes` /
    :func:`graph_component`: build the focal node's ``{ref}``-connected
    component and each component node's **in-component** forward refs.

    Returns ``(component:set, refs_by_id:dict, by_id:dict)`` where
    ``refs_by_id[cid]`` is the set of in-component concept-ids ``cid``
    references via ``{slug}`` (data+description), resolved exactly the
    way the cascade resolves (by concept_id or slugified name; self-refs
    dropped). An **empty component** means ``focal_id`` is not a known
    node. Pure read; cycle-safe (component BFS over a visited set);
    query-invariant — any node of the graph yields the same component.
    """
    if not focal_id or graph_editor is None:
        return set(), {}, {}
    try:
        from backend.services.compile_pipeline import _slugify, _CONCEPT_REF_RE
    except Exception:
        return set(), {}, {}
    try:
        nodes = graph_editor.list_concepts(workspace_id=workspace_id, limit=5000) or []
    except Exception:
        return set(), {}, {}
    by_id = {getattr(n, "concept_id", "") or "": n for n in nodes}
    by_slug: Dict[str, str] = {}
    for n in nodes:
        by_slug.setdefault(
            _slugify(getattr(n, "name", "") or ""), getattr(n, "concept_id", "") or "",
        )

    def _refs_of(n) -> set:
        """Resolved concept-ids this node references via ``{slug}`` in
        data+description (matched exactly the way the cascade resolves —
        by concept_id or slugified name; self-refs dropped)."""
        text = f"{getattr(n, 'data', '') or ''}\n{getattr(n, 'description', '') or ''}"
        out: set = set()
        if "{" not in text:
            return out
        own = getattr(n, "concept_id", "") or ""
        for m in _CONCEPT_REF_RE.finditer(text):
            ref = m.group(1)
            tgt = ref if ref in by_id else by_slug.get(_slugify(ref), "")
            if tgt and tgt != own:
                out.add(tgt)
        return out

    # Build the {ref}-adjacency (undirected) over all nodes + cache refs.
    adj: Dict[str, set] = {}
    all_refs: Dict[str, set] = {}
    for n in nodes:
        cid = getattr(n, "concept_id", "") or ""
        refs = _refs_of(n)
        all_refs[cid] = refs
        adj.setdefault(cid, set()).update(refs)
        for r in refs:
            adj.setdefault(r, set()).add(cid)

    if focal_id not in adj:
        # focal isolated (no refs in or out) — it is its own component
        # iff it is a known node; otherwise the component is empty.
        if focal_id in by_id:
            return {focal_id}, {focal_id: set()}, by_id
        return set(), {}, by_id

    # BFS the focal's connected component.
    component: set = set()
    frontier = [focal_id]
    while frontier:
        cur = frontier.pop()
        if cur in component:
            continue
        component.add(cur)
        frontier.extend(adj.get(cur, ()))

    refs_by_id = {cid: (all_refs.get(cid, set()) & component) for cid in component}
    return component, refs_by_id, by_id


def readout_nodes(
    focal_id: str, *, graph_editor, workspace_id: str = "",
) -> List[str]:
    """§7.8.2 — the rollout's READOUT perimeter for ``focal_id``'s
    ``{ref}``-connected graph.

    A node is a **readout** (a final-most node / the spherical
    hypersurface, §6.6.1) iff:

      * it is in the focal node's ``{ref}``-connected component, AND
      * **no other in-component node references it** via a ``{slug}``
        (the §6.6.1 terminal criterion — nobody downstream consumes it),
        AND
      * its ``rendering`` has **settled** (non-empty).

    The complement is the **hidden state** (intermediate mappings). The
    set is recomputed every rollout, so a node that gains a downstream
    ``{ref}`` silently demotes readout→hidden — the advancing
    abstraction front (§7.8.5). Pure read; cycle-safe (component BFS
    over a visited set). Query-invariant: any node of the graph yields
    the same perimeter.
    """
    component, refs_by_id, by_id = _component_index(
        focal_id, graph_editor=graph_editor, workspace_id=workspace_id,
    )
    if not component:
        return []
    # referenced-within-component = anything pointed at by a component node.
    referenced: set = set()
    for r in refs_by_id.values():
        referenced |= r
    # readout = component node referenced by nobody in-component + settled.
    out: List[str] = []
    for cid in component:
        if cid in referenced:
            continue
        n = by_id.get(cid)
        if n is None:
            continue
        if (getattr(n, "rendering", "") or "").strip():
            out.append(cid)
    return out


def input_nodes(
    focal_id: str, *, graph_editor, workspace_id: str = "",
) -> List[str]:
    """§7.8.1 — the rollout's INPUT sources for ``focal_id``'s
    ``{ref}``-connected graph: the **source leaves** where the
    reservoir's driving signal enters — component nodes that hold **no
    forward ``{ref}``** to any other in-component node.

    Symmetric to :func:`readout_nodes` (the sinks). These are the nodes
    whose 6D-UMAP coordinates form the *input centroid* of the §6.6.4
    bisector. Inputs are **not** settle-gated (a source provides data
    regardless of whether it has been compiled; the bisector centroid
    skips any input that lacks a coordinate). Pure read; query-invariant.
    """
    component, refs_by_id, _by_id = _component_index(
        focal_id, graph_editor=graph_editor, workspace_id=workspace_id,
    )
    if not component:
        return []
    return [cid for cid in component if not refs_by_id.get(cid)]


def graph_component(
    focal_id: str, *, graph_editor, workspace_id: str = "",
) -> List[str]:
    """The focal's full ``{ref}``-connected component as a **sorted**
    list — every node the compute graph spans (hidden state + readout
    perimeter, §7.8.2). The stable, **component-invariant** ``graph_id``
    is ``graph_component(...)[0]`` (the lexicographically-smallest
    concept-id), so any focal node of the same graph yields the same id —
    keeping the §6.6.4 overlay's ``settle_seq`` keyed to one logical
    graph regardless of which node the user clicked. Pure read.
    """
    component, _refs, _by_id = _component_index(
        focal_id, graph_editor=graph_editor, workspace_id=workspace_id,
    )
    return sorted(component)


#: §R.4 — wire cap for the readout panel's clean-text tree (panels form-fit
#: to content; the projector never needs more than this to render the
#: peripheral panel — full text remains one concept-fetch away).
READOUT_RENDERING_MAX_CHARS = 1200


def readout_panel_payload(
    rid: str, coord, *, graph_editor,
) -> Dict[str, Any]:
    """§R.4 — one readout's projector payload as a RENDERED PANEL:

      "project only the outermost computation nodes in the form of their
       rendered panel versions with clean-text tree structures that don't
       have any succeeding links in the computation graph representation."
       (USER_REQUIREMENTS_VERBATIM.md §R.4, verbatim)

    Carries the node's ``name`` + settled ``rendering`` (the §8D.20
    clean-text tree the compile produced) alongside the perimeter
    coordinate, so the 3D mirror renders the readout as a panel — never a
    bare dot, and never for hidden-state nodes (the readout set already
    excludes anything with succeeding links, ``readout_nodes``)."""
    out: Dict[str, Any] = {
        "chunk_id": rid,
        "pos": [float(x) for x in coord[:3]] if (coord is not None and len(coord) >= 3) else None,
        "hsv": [float(x) for x in coord[3:6]] if (coord is not None and len(coord) >= 6) else None,
        "name": "",
        "rendering": "",
    }
    try:
        n = graph_editor.get_concept(rid) if graph_editor is not None else None
    except Exception:
        n = None
    if n is not None:
        out["name"] = getattr(n, "name", "") or ""
        rendering = (getattr(n, "rendering", "") or "").strip()
        if len(rendering) > READOUT_RENDERING_MAX_CHARS:
            rendering = rendering[:READOUT_RENDERING_MAX_CHARS] + "\n…"
        out["rendering"] = rendering
    return out


def stream_readout_deltas(
    focal_id: str, *, graph_editor, layout_service, workspace_id: str = "",
    broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    max_inflight: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """§7.8.3 — stream the readout perimeter to the projector as **per-node
    deltas**: one ``compute_graph_layout`` frame per readout, in settle
    order, each carrying **that single readout's** perimeter coordinate +
    the re-placed bisector node (``settle_seq`` increments per emit) + the
    coordinate-free links.

    This is the async-output contract realised the simple, correct way (the
    handoff's key insight): a single-threaded **per-readout sequential
    emit** already satisfies "asynchronous = not barrier-synchronised" —
    each readout emits its own frame with its own monotone ``settle_seq``,
    so the client re-sequences out-of-order arrivals and a fast subgraph
    never waits for a slow one. Full cross-thread concurrency is a later
    refinement; the **forbidden** shape (§18.34) is a global barrier that
    waits for all readouts then emits one batch.

    Backpressure (§4 / ``READOUT_DELTA_MAX_INFLIGHT``): at most
    ``max_inflight`` distinct per-node deltas are kept in flight, coalesced
    **per node, keep-latest** (a node that settles twice before its delta
    is consumed emits once, with its latest value).

    Pure-emission helper — takes ``layout_service`` as a parameter (no
    import) so it never couples the compute layer to layout internals.
    Returns the list of emitted frames (also pushed via ``broadcast``).
    """
    from backend.api.ws_frames import build_compute_graph_layout
    if max_inflight is None:
        try:
            from backend.services.settings import get_settings
            max_inflight = int(get_settings().readout_delta_max_inflight)
        except Exception:
            max_inflight = 64

    component = graph_component(
        focal_id, graph_editor=graph_editor, workspace_id=workspace_id)
    graph_id = component[0] if component else focal_id
    readouts = readout_nodes(
        focal_id, graph_editor=graph_editor, workspace_id=workspace_id)
    inputs = input_nodes(
        focal_id, graph_editor=graph_editor, workspace_id=workspace_id)

    frame_obj = layout_service.get_frame(workspace_id)
    coords = frame_obj.coords if frame_obj is not None else {}

    # Per-node keep-latest coalescing (a dict naturally collapses repeated
    # settles of the same node to its latest payload), then bound the
    # in-flight set to max_inflight (settle order preserved). Each payload
    # carries the §R.4 rendered-panel fields (name + clean-text tree).
    pending: Dict[str, Dict[str, Any]] = {}
    for rid in readouts:
        pending[rid] = readout_panel_payload(
            rid, coords.get(rid), graph_editor=graph_editor,
        )
    ordered_ids = readouts[:max_inflight] if (max_inflight and max_inflight > 0) else readouts

    # The links are identical for every per-node delta (the perimeter set is
    # fixed within one stream) — compute once; re-place per emit so each
    # delta carries a fresh monotone settle_seq.
    links = layout_service.compute_projector_links(
        workspace_id, graph_id,
        input_ids=inputs, readout_ids=readouts, url_sample_map={})

    emitted: List[Dict[str, Any]] = []
    for rid in ordered_ids:
        placement = layout_service.place_compute_graph_node(
            workspace_id, graph_id, inputs, readouts)
        frame = build_compute_graph_layout(
            workspace_id=workspace_id, placement=placement,
            readouts=[pending[rid]], links=links)
        if broadcast is not None:
            broadcast(0, frame)
        emitted.append(frame)
    return emitted


# ---------------------------------------------------------------------------
# §7.8.1 — inverse-lookup inputs over generalized chunk-pattern samples
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChunkSampleRef:
    """§7.8.1 — a resolved **generalized chunk-pattern sample**: the nearest
    inverse-lookup input for a consuming node's port.

    ``chunk_id``  — the sample concept-id (a ``pattern_map.sampled_chunks``
                    member, §15.8.2);
    ``pattern_id``— the xpath pattern hash that produced it (the family the
                    sample generalizes);
    ``score``     — the inverse triple-product rank from ``closest_inverse``.
    """
    chunk_id: str
    pattern_id: str
    score: float


def _pattern_sample_index(graph_editor, workspace_id: str = "") -> Dict[str, str]:
    """Map ``chunk_id -> pattern_id`` over the workspace ``pattern_map``'s
    ``sampled_chunks`` (§15.8.2), recursing ``sub_patterns``. These are the
    *generalized chunk-pattern samples* the §7.8.1 inverse lookup ranges over.
    Empty when no ``pattern_map`` exists (no scan yet). Pure read."""
    if graph_editor is None:
        return {}
    node = None
    for cid in (f"pattern_map::{workspace_id or '_default'}",
                f"pattern_map::{workspace_id}"):
        try:
            node = graph_editor.get_concept(cid)
        except Exception:
            node = None
        if node is not None:
            break
    if node is None:
        return {}
    try:
        parsed = json.loads(getattr(node, "data", "") or "{}")
    except Exception:
        return {}
    patterns = parsed.get("patterns", parsed) if isinstance(parsed, dict) else {}

    out: Dict[str, str] = {}

    def _walk(tree) -> None:
        if not isinstance(tree, dict):
            return
        for phash, spec in tree.items():
            if not isinstance(spec, dict):
                continue
            for cid in (spec.get("sampled_chunks") or []):
                if cid and cid not in out:
                    out[cid] = phash
            _walk(spec.get("sub_patterns") or {})

    _walk(patterns)
    return out


def _port_declared_type(graph_editor, node_id: str, port: str) -> str:
    """Best-effort declared type of input ``port`` on the consuming node —
    read from an authored ``inputs``/``ports`` map in the node's data block
    (the structured kind, §O.20). Returns ``""`` when no structured port
    schema is authored (the §9.8 ``port_schema`` ontology is not yet a
    first-class record, so the §7.8.1 secondary type filter stays lenient)."""
    if not port or graph_editor is None:
        return ""
    try:
        node = graph_editor.get_concept(node_id)
        parsed = json.loads(getattr(node, "data", "") or "{}")
    except Exception:
        return ""
    if not isinstance(parsed, dict):
        return ""
    for key in ("inputs", "ports", "input_schema"):
        sub = parsed.get(key)
        if isinstance(sub, dict) and port in sub:
            decl = sub[port]
            if isinstance(decl, str):
                return decl.strip()
            if isinstance(decl, dict):
                return str(decl.get("type", "") or "").strip()
    return ""


def resolve_input_by_inverse_lookup(
    node_id: str, port: str, *, graph_editor, workspace_id: str = "",
    apparition_service=None, k: int = 10,
) -> Optional[ChunkSampleRef]:
    """§7.8.1 — resolve a consuming node's input ``port`` to the nearest
    **generalized chunk-pattern sample** by inverse lookup.

    Ranks candidate inputs via ``ApparitionService.closest_inverse(node_id)``
    — the inverse triple-product against the *consuming node's*
    description+rendering signature (NOT a free type string; ``exclude_self``
    is on inside ``closest_inverse``) — then keeps only candidates that are
    **xpath chunk-pattern samples** (``pattern_map.sampled_chunks`` §15.8.2).
    The input port's declared type is a **best-effort secondary** filter
    (lenient until the §9.8 ``port_schema`` ontology lands — see
    ``_port_declared_type``). Returns the highest-inverse-score
    ``ChunkSampleRef(chunk_id, pattern_id, score)``, or ``None`` when no
    pattern-sample candidate survives — an unresolvable port stays a braced
    marker (the cascade leaves it, mirroring ``resolve_concept_refs``).

    Pure read; ``O(k)`` over the ranked candidates. The cascade then drives
    the resolved sample as a render-compile chain (§7.4) over real
    functional-object links (§9.6.1), not a string match. Idempotent given an
    unchanged sample family (a §8D.39.6 backing-version bump re-fires).
    """
    if not node_id or graph_editor is None:
        return None
    sample_index = _pattern_sample_index(graph_editor, workspace_id)
    if not sample_index:
        return None
    if apparition_service is None:
        try:
            from backend.services.apparition_service import get_apparition_service
            apparition_service = get_apparition_service(graph_editor=graph_editor)
        except Exception:
            return None
    try:
        candidates = apparition_service.closest_inverse(
            node_id, workspace_id=workspace_id, k=k) or []
    except Exception:
        return None

    # Secondary type filter (best-effort): if the port declares a type AND a
    # candidate sample declares a conflicting output type, skip it. Both are
    # absent today (no §9.8 port_schema), so the filter is currently lenient —
    # the pattern-sample membership above is the authoritative filter.
    port_type = _port_declared_type(graph_editor, node_id, port)

    for cand in candidates:
        cid = getattr(cand, "card_id", "") or ""
        if cid not in sample_index:
            continue
        if port_type:
            try:
                sample = graph_editor.get_concept(cid)
                sdata = json.loads(getattr(sample, "data", "") or "{}")
                sample_type = str(sdata.get("output_type", "") or "").strip() \
                    if isinstance(sdata, dict) else ""
            except Exception:
                sample_type = ""
            if sample_type and sample_type != port_type:
                continue
        return ChunkSampleRef(
            chunk_id=cid,
            pattern_id=sample_index[cid],
            score=float(getattr(cand, "score", 0.0) or 0.0),
        )
    return None


def compile_subgraph_to_langgraph(
    focal_id: str,
    *,
    graph_editor,
    slm_client=None,
    broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    workspace_id: str = "",
    max_depth: int = 4,
):
    """Build a LangGraph StateGraph rooted at ``focal_id``.

    The graph is a *linear chain* in dependency order — deepest
    upstream node fires first, the focal node last. For most concept-
    card subgraphs this captures the expected compile order without
    needing per-edge typing. The state is a single dict keyed by
    concept_id (the ConceptComputeNode contract above).

    Returns ``(compiled_app, ordered_ids)``.

    Falls back to a Python-callable chain if ``langgraph`` isn't
    importable, so the harness can still drive an end-to-end compile
    on machines without the package. The signature is unchanged.
    """
    ordered = _collect_back_references(
        graph_editor, focal_id,
        max_depth=max_depth, workspace_id=workspace_id,
    )
    if not ordered:
        ordered = [focal_id]

    nodes = [
        ConceptComputeNode(
            cid, graph_editor=graph_editor,
            slm_client=slm_client, broadcast=broadcast,
        )
        for cid in ordered
    ]

    try:
        from langgraph.graph import StateGraph, END
    except Exception:
        # No LangGraph available — provide a plain Python compiled-app
        # surrogate with the same ``invoke`` signature.
        return _PlainChainApp(nodes), ordered

    # Use a flat dict state — LangGraph's typed-state requires either a
    # TypedDict or a Pydantic model; ``dict`` is accepted in recent
    # versions and is the easiest shape to keep generic here.
    g = StateGraph(dict)
    for i, n in enumerate(nodes):
        g.add_node(n.concept_id, n)
    for i in range(len(nodes) - 1):
        g.add_edge(nodes[i].concept_id, nodes[i + 1].concept_id)
    g.set_entry_point(nodes[0].concept_id)
    g.add_edge(nodes[-1].concept_id, END)
    app = g.compile()
    return app, ordered


class _PlainChainApp:
    """Surrogate for compiled langgraph apps on machines without the
    langgraph package. Same ``invoke(state) → state`` contract."""

    def __init__(self, nodes: List[ConceptComputeNode]):
        self._nodes = nodes

    def invoke(self, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        st: Dict[str, Any] = dict(state or {})
        for n in self._nodes:
            st = n(st)
        return st
