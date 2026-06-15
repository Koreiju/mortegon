# Object: Editor — DEPRECATED as a foundational fixture (§S.1, 2026-06-12)

> **§S DEPRECATION.** The `Editor` is **no longer a foundational fixture** (the set is now three:
> Agent, WebBrowser, Database — DOMAIN_MODEL §9.5). Per §S.1 it is an anti-pattern: in-node editing
> and markdown-gesture syntax parsing over recursive text structures **already perform graph mutation
> implicitly within the unified knowledge-panel ↔ compute-graph scheme** (§4/§7), so a separate
> Function-typed `Editor` object is redundant. The create/link/overwrite/delete **gestures survive** as
> the panel scheme's own mutation path, routed through the same lifecycle dispatcher (`/concepts` +
> `/concept_edges`, `actor="editor"`) the agent emitter uses — but there is no `fixture::editor::<wsid>`
> card and no `Editor` python_object tree. "AgentState authored via Editor calls" (§12.1) → authored
> through that shared mutation lifecycle (§12.6.1). The rest of this doc is **historical** — read it for
> how the four mutation gestures behave (still accurate), not as evidence of a live fixture.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §1.2 (verbatim — *"Editor: exposes all concept graph editor gestures like create, link, overwrite, and delete actions on input nodes, where nodes are represented as passing IDs of the nodes in the editor"*), §9.5 (four fixtures), §9.5.1 Editor, §12.6.1 (agent/editor entanglement), §17.1.1 (Editor mutation sequence).

**Status.** Realised — `fixture::editor::<wsid>` is a foundational fixture (four-fixtures-present); the four primitives are wired at `POST /api/editor/{create,link,overwrite,delete}` (+ the `editor-{create,link,overwrite,delete}` REPL actions) and **all route through the same lifecycle dispatcher** — `apply_update_lifecycle` for create/overwrite, `apply_edge_create_lifecycle` (via `create_concept_edge`) for link, `apply_delete_lifecycle` for delete — tagged `actor="editor"`, so WS broadcast + ConceptIndex + output-projection + EvolutionLog + cascade fire identically whether the caller is a panel gesture or an agent emit-action (§12.6.1 entanglement). Verified by `editor-primitives-roundtrip` + full-smoke. *(Before this pass, `link` used the legacy ontology-node `create_edge` and create/overwrite/delete called the raw `graph_editor` primitives, all skipping the dispatcher — now corrected.)*

---

## §1 — What it is

The Editor fixture is the workspace's graph-mutation surface, surfaced as a foundational fixture (§9.5) alongside Agent, WebBrowser, and Database. It exposes four primitive functions — `create`, `link`, `overwrite`, `delete` — that operate on ConceptNode and ConceptEdge records by id. Each primitive routes through the lifecycle dispatcher (§10.2) and therefore composes identically with cascade re-fires, evolution-log appends, WS broadcasts, and apparition surface refreshes regardless of whether the caller is the user (via GUI gesture), the REPL (via action), the agent (via emitter ActionResolver), or another concept node's compile (via InvokeAction).

The §12.6.1 framing makes Editor the structural counterpart of Agent in the workspace's reflexivity: the agent's reasoning produces imagery (concept nodes, edges, renderings) in the same surface its perception reads from. Editor *is* that surface as a functional object, so the agent's emit catalogue and the user's manual gestures touch the same lifecycle by the same path. The §1.5 framing places Editor in the **Imaginary register** — it is the editor's mutation surface, manipulating the imaginary's structures directly.

---

## §2 — Shape

The Editor fixture is a `python_object` ConceptNode (`backing_pointer = fixture::editor::<wsid>`) with four primitive `python_function` children.

### §2.1 `Editor.create`

```
Signature: (name: str, *, description: str = "", data: str = "") -> node_id
Ports:
  inputs:  [{name: "name",        type: "str", required: true},
            {name: "description", type: "str", required: false, default: ""},
            {name: "data",        type: "str", required: false, default: ""}]
  outputs: [{name: "node_id",     type: "str"}]
Backing: editor::create::<wsid>
```

Materialise a new ConceptNode through the lifecycle (§10.2). Returns the new id. Determines `provenance` from the calling actor:

| Actor | Provenance |
|---|---|
| User via GUI / REPL | `user-authored` |
| Agent emitter via ActionResolver | `agent-authored` |
| Compile pipeline via variable-auto-creation | `derived-from-chunk` if the parent's data references a chunk; `user-authored` otherwise |
| Scanner via WebBrowser.scan | `scanner-emitted` |
| Materialiser via PythonAPIMaterialiser | `committed-subgraph` |

The default `name` is the slug-derived form; `description` and `data` may carry `{var}` references that resolve at the first Compile press.

### §2.2 `Editor.link`

```
Signature: (source_id: str, target_id: str, edge_type: str = "RELATES_TO",
            *, source_port: str = "", target_port: str = "") -> edge_id
Ports:
  inputs:  [{name: "source_id",   type: "str", required: true},
            {name: "target_id",   type: "str", required: true},
            {name: "edge_type",   type: "str", required: false, default: "RELATES_TO"},
            {name: "source_port", type: "str", required: false, default: ""},
            {name: "target_port", type: "str", required: false, default: ""}]
  outputs: [{name: "edge_id",     type: "str"}]
Backing: editor::link::<wsid>
```

Commit a hard link (§3.2.1) between two existing ConceptNodes. The `edge_type` defaults to `RELATES_TO`; explicit types from the §3.2 union enum override. Port fields bind function-node I/O when source/target are function nodes (§8D.4.1). Idempotent on `(source_id, target_id, edge_type, source_port, target_port)` — duplicate calls return the existing edge id without inflating PageRank.

### §2.3 `Editor.overwrite`

```
Signature: (node_id: str, *, name: str | None = None,
            description: str | None = None, data: str | None = None) -> node_id
Ports:
  inputs:  [{name: "node_id",     type: "str",        required: true},
            {name: "name",        type: "str | None", required: false, default: null},
            {name: "description", type: "str | None", required: false, default: null},
            {name: "data",        type: "str | None", required: false, default: null}]
  outputs: [{name: "node_id",     type: "str"}]
Backing: editor::overwrite::<wsid>
```

Field-merge update — only the kwargs explicitly passed mutate; unset kwargs preserve the prior value. Fires cascade per §7.4. The rename cascade (described in [`ConceptNode.md`](ConceptNode.md) §3.2) propagates `{old} → {new}` across every other card's description and data when `name` mutates.

### §2.4 `Editor.delete`

```
Signature: (node_id: str) -> bool
Ports:
  inputs:  [{name: "node_id", type: "str", required: true}]
  outputs: [{name: "ok",      type: "bool"}]
Backing: editor::delete::<wsid>
```

Remove a non-fixture ConceptNode through `apply_delete_lifecycle` per [`ConceptLifecycle.md`](ConceptLifecycle.md). Rejected for foundation fixtures (§9.5) — the fixture-delete-guard returns `false` with no mutation. Connected edges are removed atomically with the node; dependents referencing the node via `{var}` slugs receive `reference_invalidated` events but are not auto-deleted.

### §2.5 Companion methods (planned)

| Method | Purpose |
|---|---|
| `Editor.unlink(edge_id)` | Remove a specific hard link without going through node delete |
| `Editor.move(node_id, layout_xy)` | Update a node's persisted 2D editor position |
| `Editor.bulk_create(spec_list)` | Atomic multi-node create (single transaction; single multi-target EditDiff) |
| `Editor.bulk_link(spec_list)` | Atomic multi-edge link |

---

## §3 — Lifecycle

### §3.1 Fixture materialisation

`foundation_fixtures.ensure_foundation_fixtures(workspace_id)` produces the Editor fixture and its four primitive children on first workspace boot per [`FoundationFixtures.md`](FoundationFixtures.md). Idempotent on `backing_pointer` match.

### §3.2 Primitive invocation paths

All four primitives converge on the same `apply_update_lifecycle` / `apply_delete_lifecycle` dispatcher. The invocation paths:

| Path | Caller | Routing |
|---|---|---|
| GUI gesture | User clicking a button (Compile, Apply, etc.) | Frontend POST to `/api/editor/<primitive>` → REST route → primitive call |
| REPL action | `editor-create` / `editor-link` / `editor-overwrite` / `editor-delete` | REPL → REST → primitive call |
| Agent emit | `MetaCognitionTick` emitter | `ActionResolver` parses action JSON → primitive call (in-process, no REST) |
| Compile pipeline | `ConceptComputeNode` resolving `{var}` references to missing slugs | `variable_auto_creation` → primitive call (in-process) |
| Materialiser | `PythonAPIMaterialiser` on workspace boot or library import | Direct primitive call (in-process) |

All paths trace through the same dispatcher fan-out — Kuzu write, WS broadcast, ConceptIndex upsert, evolution-log diff, cascade scheduler nudge — so the user, the agent, the compiler, and the materialiser are *behaviourally indistinguishable* in their effect on the workspace state. The `actor` field on the resulting EditDiff is what distinguishes them.

### §3.3 The entanglement contract (§12.6.1)

The agent's emitter card is wired to `ActionResolver`, which maps each action JSON shape to one of the four primitives:

| ActionResolver action | Editor primitive |
|---|---|
| `CreateCardAction { name, description?, data? }` | `Editor.create(...)` |
| `LinkAction { source_id, target_id, edge_type?, ... }` | `Editor.link(...)` |
| `WriteFieldAction { node_id, field, value }` | `Editor.overwrite(node_id, {field: value})` |
| `DeleteCardAction { node_id }` | `Editor.delete(node_id)` |
| `InvokeAction { card_id, method, inputs }` | Compile dispatch on the target ConceptNode (not Editor; routes via `ConceptComputeNode.compile`) |

When the agent reasons over the workspace, the imagery it produces (new concept nodes, edges, mutated fields) flows through these four functions exactly as if a user were typing in the GUI. This is the structural entanglement: the agent's emit catalogue *is* the editor's primitive set, surfaced as a Function-typed concept tree the agent itself can call into.

---

## §4 — Persistence

| Artefact | Storage |
|---|---|
| Fixture node + four primitive children | Kuzu `ConceptNode` table |
| Mutations produced by the primitives | Whatever the primitive mutates (ConceptNode / ConceptEdge / both) lands in Kuzu via the lifecycle |
| EditDiff records | Kuzu `EditDiff` table; one per primitive invocation; carries `actor`, `target`, `before`, `after` |

Editor itself stores no state beyond its fixture identity; all state lives in the records it mutates.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | All four primitives enter the dispatcher; the dispatcher's fan-out is what makes them composable |
| [`ConceptNode.md`](ConceptNode.md) | `create`, `overwrite`, `delete` operate on rows in the ConceptNode table |
| [`ConceptEdge.md`](ConceptEdge.md) | `link` (and `delete` cascading to edges) operates on rows in the ConceptEdge table |
| [`AgentRuntime.md`](AgentRuntime.md) | `ActionResolver` maps emitter actions to Editor primitives |
| [`Agent.md`](Agent.md) | The agent's emitter card's backing pointer is `agent::emitter::<pcid>`; the emitter routes through `ActionResolver` which calls Editor |
| [`EvolutionLog.md`](EvolutionLog.md) | Every primitive invocation appends an EditDiff with `actor=user|agent:<id>|editor|cascade|materialiser` |
| [`UIStateService.md`](UIStateService.md) | Editor mutations trigger `ui_state_changed` updates via the broadcast hooks (e.g., `concept_changed` followed by pinned-panel re-render) |
| [`ConceptualCompute.md`](ConceptualCompute.md) | Compile-pipeline-issued primitives (via variable auto-creation) route here |
| [`PythonAPIMaterialiser.md`](PythonAPIMaterialiser.md) | The materialiser uses `Editor.create` / `Editor.link` to lay out the python_object/property/function trees |

---

## §6 — Cross-references

- Feature touchpoints — [`features/four_fixture_api.md`](../features/four_fixture_api.md), [`features/agent_integration_scheme.md`](../features/agent_integration_scheme.md), [`features/compile_collapse_dialectic.md`](../features/compile_collapse_dialectic.md) (Editor primitives are the primary mutators during double-left-click compile expand, §7.3.4/§O.1).
- Code constraints — [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) (one dispatcher rule), [`api_routes.md`](../code_constraints/api_routes.md) (`/api/editor/*` endpoint shapes), [`concurrency.md`](../code_constraints/concurrency.md) (idempotency on link; actor-aware short-circuit).
- Sequence reference — DOMAIN_MODEL §17.1.1 (Editor mutation sequence).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Mutating Kuzu directly without routing through Editor's primitives | Breaks the dispatcher's fan-out — no WS broadcast, no EvolutionLog, no cascade re-fire | Direct Kuzu writes are confined to `graph_editor.py` internals; the four primitives are the only public surface |
| Allowing `Editor.delete` to succeed on a foundation fixture | §18.22 / §18.27 fixture-deletability regression | The dispatcher's `apply_delete_lifecycle` checks `backing_pointer.startswith("fixture::")` and returns `false`; the `fixture_delete_guard` env-scenario asserts this for all four fixtures |
| Letting two `Editor.link` calls with identical 5-tuple create duplicate edges | Inflates PageRank; breaks the cascade dependency model | `link` checks for existing edge on the 5-tuple and returns the existing id |
| Routing agent emit actions through a path other than `ActionResolver` → Editor | Breaks the §12.6.1 entanglement contract; emitter actions could bypass the lifecycle | All agent-emitted actions enter through `ActionResolver` which invokes the Editor primitives |
| Calling Editor primitives with mismatched workspace_id | Cross-workspace pollution | Editor primitives derive `workspace_id` from the calling context (the REST route's body, the agent body's parameter_card workspace, the materialiser's bootstrap workspace) |
| Skipping the cascade scheduler on `overwrite` | Downstream cards consuming the value via `{var}` won't re-compile; the cascade contract breaks | The dispatcher always nudges the cascade scheduler on every modify |
| Treating Editor as a second mutation path alongside `graph_editor.py` direct calls | Two paths is the §2.2 anti-pattern: one dispatcher only | Editor is a *surface* on top of the dispatcher, not a second dispatcher |
