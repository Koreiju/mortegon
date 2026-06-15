# Feature: The Three-Fixture API (§S re-baselined; was four)

> **§S DEPRECATION (2026-06-12).** This feature is now the **three-fixture** API — Agent, WebBrowser,
> Database. The fourth fixture, **`Editor`, is removed** (§S.1): its create/link/overwrite/delete
> gestures are intrinsic to the unified knowledge-panel ↔ compute-graph scheme and route through the
> shared mutation lifecycle (`/concepts` + `/concept_edges`, `actor="editor"`), not a Function-typed
> fixture object. The `editor-*` REPL actions + `/api/editor/*` routes survive as the gesture-drivers
> (re-framed as concept-graph mutation gestures of the panel scheme), but no `fixture::editor::<wsid>`
> card materialises. The `four-fixtures-present` scenario is now `three-fixtures-present`. The text
> below is historical where it says "four / Editor fixture."

## (historical) The Four-Fixture API

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §1.2 (verbatim user spec), §9.5 (four foundational fixtures), §9.5.1 (the four API signatures), §9.6 (Python-native trees), §9.7 (library-imports middleware), §12.6.1 (agent/editor entanglement).

**Status.** Realised (§S re-baselined to THREE). The three fixtures (Agent, WebBrowser, Database) materialise on workspace open via `ensure_foundation_fixtures` with distinct `type_hint`s (`fixture_agent`/`fixture_web_browser`/`fixture_database`), all undeletable through every seam (the §1.6 dispatcher guard + route 409). The signatures are realised: Agent SLM primitives (`/api/agent/meta_prompt`/`prompt`/`output` + `tick`/`spawn`), `Database.concept`, `WebBrowser.scan` (`/api/web_browser/scan`) with live `pattern_map` output. The former Editor primitives survive as concept-graph **mutation gestures** of the unified panel↔compute-graph scheme (`/api/editor/{create,link,overwrite,delete}` → shared lifecycle, `actor="editor"`), **not** a `fixture::editor` card. Verified by `three-fixtures-present`, `fixture-delete-guard` (both seams, all 3), `agent-fixture-present`, `editor-primitives-roundtrip` (now the mutation-gesture test), `agent-three-primitives-chain`, `database-concept-signal-stream` in `full-smoke`.

---

## §1 — What the user sees

The workspace boots with four foundational fixtures present as concept nodes the user can right-click to expand into their member trees. **Agent** carries three primitive functions (`meta_prompt`, `prompt`, `output`) for SLM composition plus the spawn/tick lifecycle for autonomous agents. **WebBrowser** carries `scan(url, query?)` producing a live-streaming `pattern_map` output of chunk-pattern schemas. **Database** carries `search`, `cypher`, and `concept(node_id [or list])` for retrieval + rank-1 KG walks under the signal-stream constraint. **Editor** carries `create`, `link`, `overwrite`, `delete` for graph mutations that the user invokes from the GUI and the agent invokes through its emitter — both routes converge on the same lifecycle dispatcher.

The four fixtures are the workspace's primary functional objects; everything else composes through them. When the user types a description into an empty primitive, the apparition halo surfaces these fixtures' functions as the most-pageranked soft-link candidates. When the agent reasons over its body subgraph, it invokes Editor primitives identically to how the user types from the GUI.

The §1.5 framing makes the four fixtures the *common substrate* the Real and Imaginary registers compose through — Database persists, WebBrowser measures, Agent reasons, Editor mutates.

---

## §2 — Cross-objects

| Object | Role in this feature |
|---|---|
| [`Agent`](../object_model/Agent.md) | The SLM fixture; three primitives + spawn/tick lifecycle |
| [`WebBrowser`](../object_model/WebBrowser.md) | The Selenium fixture; `scan(url, query?)` with `pattern_map` output |
| [`Database`](../object_model/Database.md) | The unified storage fixture; search/cypher/concept primitives |
| [`Editor`](../object_model/Editor.md) | The graph-mutation fixture; create/link/overwrite/delete |
| [`FoundationFixtures`](../object_model/FoundationFixtures.md) | `ensure_foundation_fixtures(workspace_id)` produces all four trees |
| [`PythonAPIMaterialiser`](../object_model/PythonAPIMaterialiser.md) | The middleware that walks each fixture's Python class into the ConceptNode tree |
| [`BackingRegistry`](../object_model/BackingRegistry.md) | Resolves `fixture::<kind>::<wsid>` backing pointers to live Python handles |
| [`ConceptLifecycle`](../object_model/ConceptLifecycle.md) | Every fixture method call routes through here |
| [`AgentRuntime`](../object_model/AgentRuntime.md) | The agent's emitter calls Editor primitives via ActionResolver |

---

## §3 — Gestures

| Gesture | REPL action | GUI gesture | Agent emit |
|---|---|---|---|
| Materialise fixtures | (automatic on workspace open) | (automatic on workspace open) | n/a |
| `Agent.meta_prompt(text)` | `agent-meta-prompt { text }` | Click `Agent.meta_prompt`'s compile button | `InvokeAction { card_id: agent::meta_prompt, inputs: {text} }` |
| `Agent.prompt(text)` | `agent-prompt { text }` | Click `Agent.prompt`'s compile button | `InvokeAction { card_id: agent::prompt, inputs: {text} }` |
| `Agent.output(schema?)` | `agent-output { schema? }` | Click `Agent.output`'s compile button | `InvokeAction { card_id: agent::output, inputs: {schema} }` |
| `WebBrowser.scan(url, query?)` | `web-scan { url, query? }` | Click `WebBrowser.scan`'s compile button | `InvokeAction { card_id: web_browser::scan, inputs: {url, query} }` |
| `Database.search(query, cypher?)` | `database-search { query, cypher? }` | Click `Database.search`'s compile button | `InvokeAction { card_id: database::search, inputs: {query, cypher} }` |
| `Database.cypher(query)` | `database-cypher { query }` | Click `Database.cypher`'s compile button | `InvokeAction { card_id: database::cypher, inputs: {query} }` |
| `Database.concept(node_id [or list])` | `database-concept { node_id }` | Click `Database.concept`'s compile button | `InvokeAction { card_id: database::concept, inputs: {node_id} }` |
| `Editor.create / link / overwrite / delete` | `editor-create / link / overwrite / delete` | Authoring gestures + apparition click promotion | `CreateCardAction / LinkAction / WriteFieldAction / DeleteCardAction` |

---

## §4 — State machine — fixture invocation

```
gesture (REPL / GUI / agent emit)
   │
   ▼
REST POST /api/<fixture-primitive>  OR  in-process ActionResolver call
   │
   ▼
BackingRegistry.resolve("<kind>::<primitive>::<wsid>") → live Python callable
   │
   ▼
callable invocation
   │
   ▼  side effects on the fixture's backing implementation:
   │     • Agent: SLM call, agent_token frames stream
   │     • WebBrowser: Selenium navigation + chunk emission
   │     • Database: Kuzu query / index read
   │     • Editor: ConceptNode/Edge mutation
   │
   ▼  result returned via REST OR ActionResolver
   │
   ▼  any mutations produced enter apply_update_lifecycle (§10.2)
   │
   ▼  WS broadcasts: concept_changed × N for any mutations; evolution_diff for each
   │
   ▼  frontend renders; REPL viewer rows update
```

---

## §5 — WS frames + telemetry

Every fixture invocation that produces a mutation emits the standard `concept_changed` + `evolution_diff` + `ui_state_changed` (as applicable). Fixture-specific frames:

| Fixture | Fixture-specific frame |
|---|---|
| Agent | `agent_token` (streaming SLM tokens during `Agent.output`) |
| WebBrowser | `chunk_added` × N + `umap_canonical` (incremental + scan-end) + `pattern_map`-bearing `concept_changed` |
| Database | (none beyond standard) |
| Editor | (none beyond standard — all mutations are standard concept_changed) |

---

## §6 — Acceptance bar (§S re-baselined to three)

The three-fixture API is realised when:

- `foundation_fixtures.ensure_foundation_fixtures` produces exactly three root python_object ConceptNodes with the correct backing pointers (`fixture::agent::<wsid>`, `fixture::web_browser::<wsid>`, `fixture::database::<wsid>`). No `fixture::editor::<wsid>` card materialises (§S.1).
- Each fixture's primary functions are materialised as python_function children with port schemas matching §9.5.1.
- `Agent.meta_prompt`, `Agent.prompt`, `Agent.output` can be wired into a three-node chain; the chain compiles end-to-end with real GPT4All streaming.
- `WebBrowser.scan` produces a live-streaming `pattern_map` ConceptNode (verifiable via §16.5 probe — pattern_map updates land before the `done` frame).
- `Database.concept(node_id_list)` returns iterable results displayed under signal-stream constraint (§4.6.1 + §17.1.2).
- The concept-graph mutation gestures (`create / link / overwrite / delete`) are invokable from both the REPL and the agent emitter, producing identical lifecycle fan-out (verifiable by comparing EditDiff `actor` fields) — routed through the unified panel↔compute-graph scheme (`/concepts` + `/concept_edges`), not a fixture object.
- `fixture-delete-guard` env-scenario asserts all three fixtures reject delete.
- The three-fixture count is verified by `foundation-ensure` action and reported in the REPL viewer's subsystems row.

*(Historical four-fixture acceptance criteria — including a `fixture::editor::<wsid>` card and the `four-fixtures-present` scenario — are superseded per the §S deprecation banner at the top of this doc.)*

---

## §7 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| Foundation fixture count drift | §18.27 |
| Foundation fixtures deletable | §18.22 |
| Library middleware orphan trees | §18.28 |
| Falling back to a stub SLM in production | §13 / §13.4 |
| Llama as SLM target | forbidden-concepts §3 |

---

## §8 — Code constraints

- [`backend_services.md`](../code_constraints/backend_services.md) — fixture singleton + real-vs-fake rules.
- [`api_routes.md`](../code_constraints/api_routes.md) — `/api/<fixture-primitive>` endpoint shapes.
- [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) — all fixture mutations route through the dispatcher.
- [`repl_actions.md`](../code_constraints/repl_actions.md) — every fixture primitive has a REPL action.

---

## §9 — Cross-features

- [`library_imports_middleware.md`](library_imports_middleware.md) — the generalisation that lets arbitrary Python libraries become peer fixtures.
- [`agent_integration_scheme.md`](agent_integration_scheme.md) — the agent's reasoning composes via Editor + Database + WebBrowser invocations.
- [`pattern_map.md`](pattern_map.md) — `WebBrowser.scan`'s primary output.
- [`signal_stream.md`](signal_stream.md) — `Database.concept(list)` iterates under this constraint.
- [`three_register_model.md`](three_register_model.md) — the fixtures are the substrate the three registers compose through.
