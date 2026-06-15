# Claude Memory — web_fiber_haptics

This file is the persistent design guide Claude returns to across sessions. The source-of-truth order is now:

1. **`docs/USER_REQUIREMENTS_VERBATIM.md`** — every binding requirement in the user's own phrasing (now incl. the §M / §N / §O review clarifications). When two documents disagree, this file wins.
2. **`docs/DOMAIN_MODEL.md`** — full design elaboration. Must not contradict the verbatim file.
3. **`docs/FRONTEND_REDESIGN.md`** + the **`docs/frontend/`** suite — the canonical, from-scratch frontend object model + per-surface reference (themed dark-minimal stainless-steel-over-black). Canonical for all frontend specifics.
4. **`docs/DOC_MAP.md`** — structural map of the documentation chain (design ideation → object model → features → code constraints). Read this to navigate between layers.
5. **`docs/MORTEGON_INTEGRATION_SCHEME.md`** and **`docs/CODEBASE_GAP_ANALYSIS.md`** — **HISTORICAL analysis-plan, superseded (§O.17)**: the operational 3D↔2D scheme and the old-code gap audit. Their additive design detail is lifted into the design docs (DOMAIN_MODEL §6.1 / §7.3.2 / §4.6 + the `frontend/` suite); the audited code is being discarded. Consult for historical reasoning only — **not** implementation targets.


The layered companion documentation (per `DOC_MAP.md`):
- **`docs/object_model/`** — one doc per first-class object in the workspace (data records, the three foundational fixtures, backend services, frontend components). *(§S, 2026-06-12: the fourth `Editor` fixture is deprecated — its create/link/overwrite/delete gestures are intrinsic to the unified panel↔compute-graph scheme, not a fixture; `object_model/Editor.md` carries the deprecation banner.)*
- **`docs/features/`** — one doc per cross-cutting user-visible feature (organised by Mortegon register).
- **`docs/code_constraints/`** — one doc per programming surface with must-hold / must-not / anti-goal-anchor sections.
- **`docs/code_architecture/`** — the implementation blueprint *below* code_constraints (data schemas, REST + WS contracts, backend service decomposition + internal logic, the greenfield frontend module tree). Selectively distilled from design (its README §0 IN/OUT filter); backend **aligned** + frontend **greenfield** + a keep/remove ledger for the forbidden (graph-analytics, hyperbolic layout, Llama) / legacy (`cp/*.js`) code.
- **`docs/code_specs/`** — the line-level implementation specs *below* code_architecture, immediately above CODE: every function fully typed with pre/post-conditions, raised errors, step-precise algorithms + complexity + examples. A `types`/`constants`/`errors` foundation, per-area backend (api · lifecycle · layout · retrieval · compute · agent · materialiser · scanner · persistence) + frontend (spine · cell · real · imaginary · membranes · pulse) specs, and `repl.md` (sim_frontend actions · watch-activity 7-row dashboard · env-scenario contract · live probes). The implementable contract a developer/reviewer checks code against line-for-line.

This file is the *lodestar summary* of the design's load-bearing commitments and the worked use case that anchors them.

## Process Discipline (Doc First)

> "I suggest you clear up discrepancies in our documentation along the lines that I'm specifying, then making sure that are also reflected in code. I need you to pay much closer attention to the solutions you provide to ensure that they are correct rather than comprehensive."

The order of operations on every iteration is: (1) capture the requirement in `USER_REQUIREMENTS_VERBATIM.md` verbatim, (2) audit the codebase against the doc, (3) record the gap analysis (`CODEBASE_GAP_ANALYSIS.md` is now historical, §O.17 — supersede it with a fresh audit), (4) only then change code. **A screenshot is not feature proof.** Verification runs in the REPL against the live full stack.

## The Lodestar Use Cases — Three Facets + One Synthesis

The workspace has three lodestar use cases (facets) that compose into one synthesis. **All four must hold against the real subsystems on every commit.**

- **§8D.45 — Archive.org University Library (outside-in)**: real Selenium scan → real TF-IDF retrieval → spine extrusion → click-and-stick → right-click compile. Evidence probe: `scripts/probe_live_archive_scan.py`.
- **§8D.47 — Concept Graph Editor Authoring (inside-out)**: empty primitive → typed description → real nomic apparition radiation → resolve via wiring → `{var}` auto-creation → real LangGraph+GPT4All compile chain → multi-step compute graph with real SLM dispatch in the middle node → closest-inverse lookup → inline cypher detection + real Kuzu execution → evolution log audit → rollback restores prior state. Evidence probe: `scripts/probe_live_concept_graph.py`.
- **§8D.48 — Live Agent Tick (autonomous)**: spawn agent body subgraph (parameter + perception + transformer + emitter trio) → verify backing pointers `agent::{kind}::<pcid>` → tick fires real GPT4All against real apparition perception → token buffer holds real streamed tokens → pause/resume via parameter-card edit → evolution log captures actor=`agent:spawn` diffs → termination via parameter-card delete. Evidence probe: `scripts/probe_live_agent.py`.
- **§8D.49 — Unified Iterated-Compile (the synthesis)**: scan archive.org → build a three-node langgraph+pydantic templated compute graph (`chunk_sample` + `structured_prompt` + `formatted_output`) → iterate over N sampled chunks → play/pause editing at each iteration → real halo + right-click compile/collapse round-trip on the compiled-graph nodes. Evidence probe: `scripts/probe_live_iterated_compile.py`.

The three trajectories interlock; §8D.49 is the synthesis: the workspace as actually used. The play loop (§8D.25) is the cycle these strokes spin around.

## Compact Representation Standard (§8D.1.3)

Across every surface, concept nodes appear in three forms:

- **Unfolded panel** — the four canonical editable rows (`name`, `description`, `value` as the field-tree, `compiled`) plus user-added key:value rows at any depth via horizontal `+→` (parent→child) and vertical `+↓` (sibling) plus-signs.
- **Apparition halo phantom** — shows **only the candidate's name**. No score chips, no description preview, no rendering snippet. Scores live in slow-hover tooltips.
- **Compiled-graph child node** — shows **only the value**. Name is implicit from structural position in the parent's field-tree. Multi-line values expand the box to fit.

The data block as a separate JSON-shaped blob dissolves; the field-tree is the data, syntax-agnostically rendered. Auto-complete in the name field of a new row binds to existing concept-node names by inserting `{<linked_name>}` into the value (the on-ramp to typed linking).

## §8D.45 In Detail — The Outside-In Lodestar

The **archive.org university library** walkthrough is the design's acceptance bar:

1. **Empty workspace** — three foundational fixtures only (Database, WebBrowser, Agent) per §8D.35.1 flat ontology of fixtures.
2. **Scan archive.org** with query `"university library"` via `WebBrowser.web_query(url, query, samples)`.
3. **Streaming chunks** materialise into the workspace; scan-end UMAP joint fit emits `umap_canonical` per §11.5.
4. **Retrieval result rows** render in the side panel; **ALL retrieval chunks are collapsed-hidden by default** per §8D.18.1 strict rule. No third path for 3D visibility.
5. **Scroll the result list** → IntersectionObserver flips `chunkCollapseTarget` per row → ONLY visible-viewport rows extrude their chunks radially from the doc-hub. Scrolling past re-hides. Scroll-driven and ONLY scroll-driven.
6. **Hover a row** (e.g., a Canadian university library result) → unified knowledge panel previews at hover billboard rect.
7. **Click the row** → panel **pins at the same screen rect** (freeze-at-hover-position contract per MORTEGON §1.2).
8. **Right-click panel body** → expands to simplified compute graph (§8D.2.2): single `name:value` children, stringless edges, form-fit boxes, multiline support, `{var}` propagation to literal-data leaves.
9. **Right-click central node** → collapses back to the original panel. The toggle is symmetric.

## Six Commitments The Use Case Enforces

1. **Strict spine rule (§8D.18.1)** — retrieval chunks collapsed-hidden by default; ONLY scroll-viewport-visible OR pinned-panel-referenced chunks visible. No global "show all", no debug bulk-expand, no third path.
2. **Latch + form-fit + slide-out data panel (§8D.1.2)** — knowledge panels open latched (name + description + rendering only); latch button slides data block out as a side panel at equal height; cards form-fit to actual string content; empty rows hide entirely.
3. **Right-click compile/collapse toggle (§8D.2.2)** — symmetric gesture on central panel-or-node. Expansion = simplified subgraph (one level deep). Collapse = restore original panel. Children dissolve on collapse; underlying ConceptNode record untouched on either flip.
4. **Python-native Object/Property/Function ConceptNode trees (§8D.4.2)** — `WebBrowserManager`, `Database` handle, `agent_runtime` project into `type_hint=python_object/python_property/python_function` trees. All carry `read_only: true` (🔒 indicator, latch hidden, no edits). Function nodes carry `no_datablock: true` — the data field holds signature metadata only, NEVER projects the function body / source code into the editor. Docstring → description. Edges `OBJECT_HAS_PROPERTY`, `OBJECT_HAS_FUNCTION`, `FUNCTION_INPUT_TYPE`, `FUNCTION_OUTPUT_TYPE` compose the downstream type ontology §8D.42.1.
5. **Cascade is the default (§8D.38.4)** — compilation is continuous downstream of user edits, meta-cognition re-firings, scanner emissions. The Compile button is an affordance for forced synchronisation, not the primary trigger.
6. **REPL in-place activity viewer (§11.8)** — `watch-activity` REPL command renders a fixed six-row dashboard (scan / retrieval / visible 3D / hidden 3D / pinned / compile) that updates **in place** via ANSI cursor codes. No append-spam. The operator's terminal is a faithful mirror of GUI state.

## Foundational Fixtures (§8D.35.1)

Three peer ConceptNodes, all undeletable, all flat (no hub):

- `Database` (`fixture::database::<workspace_id>`) — unified workspace storage handle (persistence + TF-IDF + concept graph + web ontology + meta-cognition substrate).
- `WebBrowser` (`fixture::web_browser::<workspace_id>`) — live Selenium runtime; emits chunks into Database on scan.
- `Agent` (`fixture::agent::<workspace_id>`) — meta-cognition tick + emitter catalogue. Lightweight; actual agent body lives in user-designated parameter cards per §8D.37.

**No centrality hub.** Database is not the root; it's the concept node whose backing pointer happens to resolve to persistence. SearchableURL / DetectedAccessor / XPathPattern (compiled-from-scans per §8D.39) are peers of the fixtures, not children of Database.

## ConceptNode Schema (§8D.44) — The One Record

```python
@dataclass
class ConceptNode:
    concept_id: str
    name: str
    description: str           # nomic-indexed (functional declaration §8D.40)
    data: str                  # constructor template §8D.30
    rendering: str             # tf-idf-indexed; compile output §8D.20
    linked_nodes_json: str
    backing_pointer: str       # opaque handle; runtime registry resolves
    pagerank: float
    provenance: str            # user-authored | agent-authored | derived-from-chunk | committed-subgraph
    workspace_id: str
    layout_xy: str
    ui_state: str
    type_hint: str             # naming convention, NOT type discriminator
    created_at: str
    updated_at: str
```

Edge: one `ConceptEdge` dataclass; `edge_type` is the union enum of §8A.2 typed labels + §8D port-binding labels + web-ontology edges + Python-native edges. **One edge table; never two.**

## Verification Surface (§11.7 / §11.8)

- `scripts/sim_frontend.py` is the REPL harness. ~160+ actions across 19 categories.
- `env-scenario --name full-smoke` runs the 92-scenario contract (96 registered). All scenarios must stay green on every commit (in both stub and real-stack modes). Includes the §1.2-update roundtrips: `signal-stream`, `rollout`, `node-fold`, `compile-expand-collapse`, `watch-activity-mirror`, `pattern-map-live-update`, `urls-panel-iteration`, `library-middleware`, `perimeter-rescale`, `apparition-mode`, `database-concept-signal-stream`, `6d-umap-format`, `editor-primitives`, `agent-three-primitives-chain`; the `complex-interaction-walkthrough` composite (rollout + halo + compile + signal coexist in one UIState envelope without interference); the `cascade-reflow-roundtrip` (§8D.38.4 — a data edit auto-recompiles downstream `{ref}`-consumers); plus `live-scan-real-with-cleanup` (all_real-gated, skips in stub).
- **§E.1 scenario (2026-06-12)**: `syntax-agnostic-compile` — the ONE recursive descent over all five authored syntaxes (JSON · HTML element trees · non-JSON bracketed lists · §R.5 markdown outlines · indent `key: value` trees · plain-text passthrough), asserted through `/api/compile_pipeline` entries + §8D.20 clean renderings against the live stack. Backend `_try_parse_structured` is the single detector; frontend `_decomposeValue` mirrors the strategy order; decompose splits out the ROOT's children (§4.5), so panel→graph→panel commutes minus exactly one root level (§R.1).
- **§R scenarios (2026-06-11, all green in stub AND real modes)**: `markdown-restructure-roundtrip` (§R.5 — dash/tab/number/newline-with-trailing-text gestures restructure the computation-graph side; one canonical `decompose_top_level` shared by backend + frontend + mirror), `inverse-map-state-space` (§R.6 — every forward call persists a `FORWARD_MAPPED_TO` ConceptEdge; `GET /api/inverse_map/{id}` reflects the full state space; `closest_inverse` ranks recorded mappings above nomic generalisation), `ontology-projection-roundtrip` (§R.2 — `POST /api/ontology/layout` projects EVERY ConceptNode — fixtures, python-native trees, user concepts, compiled-from-scans — into the 6D nomic-UMAP space alongside chunks; `ontology_layout` WS frame + projector overlay), `readout-panel-projection` (§R.4 — peripheral-only output: ONLY terminal readouts (no succeeding links) ship as rendered panels with name + §8D.20 clean-text tree), `iterated-signal-rerender` (§R.7/§4.6.1 — "the cascade re-fires per visible signal": `/api/ui/signal_advance` routes through RolloutCoordinator and recompiles the `{ref}`-consumers per sample), `db-janitor-hygiene` (§R.9 — `backend/services/db_janitor.py` + `POST /api/maintenance/cleanup_test_artifacts`: one canonical `wfh_test_` temp-DB prefix, ctx-managed lifetimes, atexit net, retention sweeps over legacy-prefix strays + ws_-convention side files; `_default` untouchable).
- **§S re-baseline (2026-06-12, green stub + real)**: `three-fixtures-present` (§S.1 — Agent/WebBrowser/Database only; asserts NO `fixture_editor`; `four-fixtures-present` kept as an alias) replaces the old four-fixture scenario; `fixture-delete-guard` / `fixtures-undeletable` / `agent-fixture-present` re-baselined to three; `editor-primitives-roundtrip` is now the concept-graph **mutation-gesture** test (the Editor *fixture* is removed — its create/link/overwrite/delete gestures are intrinsic to the unified panel↔compute-graph scheme, routed via `/concepts` + `/concept_edges`; `/editor/*` survive only as gesture-drivers). The retrieval **sidebar** is removed (in-editor halos subsume it, §8.2). The **black-slate** panel/node design (DOMAIN_MODEL §4.1.2) is live: thin silver border, black infill, serif white text, NO chrome (no header/×/minimiser/topbar) — browser-verified.
- `env-scenario --name <specific>` runs one scenario.
- `watch-activity` — in-place seven-row dashboard (scan / retrieval / visible 3D / hidden 3D / pinned / compile / subsystems) updating via ANSI cursor codes.

### Probes

- `scripts/probe_shims.py` — `to_concept_node()` migration shims (§8D.44.2).
- `scripts/probe_backing_version.py` — `backing_pointer_version_seq` mechanics (§8D.39.6).
- `scripts/probe_python_api.py` — Python-native Object/Property/Function tree materialisation (§8D.4.2); asserts `OBJECT_HAS_*` + `FUNCTION_*_TYPE` edges persist + transitive type closure.
- `scripts/probe_pattern_map.py` — §15.8 golden-trio joint-presence gate (§15.8.1) + live `pattern_map` ConceptNode (§15.8.2). Drives the real DOM pipeline against a fixture card-grid+nav page: card resolves a golden trio + enters `sampled_chunks`, nav is gated out, a second scan accretes into the same peer node (browserless via temp Kuzu + fake gates).
- `scripts/probe_use_case.py` — 11-step synthetic walkthrough of §8D.45.
- `scripts/probe_no_mocks.py` — §8D.46 contract verification (real GPT4All + real nomic + real Selenium + real LangGraph).
- `scripts/probe_live_archive_scan.py` — **§8D.45 LIVE end-to-end evidence (outside-in)**. Triggers a real Selenium scan of `https://archive.org/search?query=university+library`, watches the per-snapshot WebSocket through `done`, runs real `/api/chunk_search` retrieval (real hits like "Princeton University Library Chronicle 1940-11"), pins via `/api/ui/pin`, fires `/api/ui/compile_expand` mirror, runs a real LangGraph+GPT4All compile (e.g. "Library is a treasure trove of knowledge.").
- `scripts/probe_live_concept_graph.py` — **§8D.47 LIVE end-to-end evidence (inside-out)**. Authors a fresh concept-graph subgraph from the empty primitive: real nomic radiation against typed description, real wiring through `/api/concept_edges`, `{var}` reference in data block, real LangGraph compile_chain, real focal-centric apparitions, real evolution-log audit, real rollback that itself records as a new diff. **Extended**: multi-step compute graph with real GPT4All dispatch in the middle, closest-inverse lookup at the output port, inline cypher detection + real Kuzu rewrite.
- `scripts/probe_live_agent.py` — **§8D.48 LIVE end-to-end evidence (autonomous)**. Spawns agent body (parameter + perception + transformer + emitter), verifies backing-pointer trio, fires `/api/agent/tick` which calls real GPT4All against real nomic apparitions; token buffer + rationale prove the SLM streamed real tokens reasoning over the workspace's auto-materialised Python-API concepts.
- `scripts/probe_live_iterated_compile.py` — **§8D.49 LIVE end-to-end evidence (synthesis)**. Re-uses chunks from a recent archive.org scan; authors the three-node templated compute graph; iterates real GPT4All compile over N sampled chunks; verifies halo + right-click round-trip on the compiled-graph nodes.
- `scripts/probe_live_scan_with_cleanup.py` — **§16.5 LIVE acceptance artifact (mandated)**. all_real → purge-to-clean-baseline (chunk pool 0 + zero ghost TF-IDF rows) → real archive.org scan → TF-IDF+nomic indices alive → real-UMAP 6D fit over the scanned space → purge cleanup contract (`layout_dropped` + `tfidf_rows_dropped`) → re-scan rebuilds to a comparable pool. First passed 2026-06-12 after it exposed two purge gaps (scan-substrate tables + scanner-emitted TF-IDF rows surviving purges) and the scan-end layout-broadcast crash.
- `scripts/probe_live_dominance_and_timed_scan.py` — **§Q LIVE end-to-end evidence (timed scan + rank-dominance collapse)**. Fresh workspace → timed archive.org scan via the exposed `duration_s` port (§15.10; honors the wall-clock time-box) → right-click root-URL node collapses its chunk samples AND isolates every other node (§6.6.5, Q.3) → re-expand restores → compute/bisector-node collapse folds BOTH input + output distributions (Q.4) over the **same** Kuzu ConceptEdge graph PageRank traverses (§8.1.2, Q.6). All-real (`all_real:true`).

## Environment Knobs

- `WFH_FAKE_SLM=1` — short-circuit SLM to deterministic stub. **Harness only**; production never sets this.
- `WFH_FAKE_EMBEDDER=1` — short-circuit nomic to hash-deterministic 768-dim fake. **Harness only**.
- `NO_WEBDRIVER=1` — skip Selenium init at backend boot. **Harness only**.
- `WFH_SLM_MODEL=...` — production GGUF; **defaults to Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf**. **Llama is not a fallback**; do not set this to any Llama variant.
- `WFH_SLM_DEVICE=cuda` (default) — CUDA in all LLM runs.
- `WFH_EMBEDDER_DEVICE=cuda` (default) — CUDA in all embedding runs.
- `WFH_DB_PATH=...` — override Kuzu DB path. **kuzu ≥ 0.11 is file-based**: when the path is an existing non-empty directory (the legacy `<repo>/kuzu_db/` artifact layout holding the per-workspace side files), the store nests as `<path>/data.kuzu` (`backend/database.py::_effective_db_path`); a fresh/file path is used directly.
- Backend default port is 8080 (`backend/main.py`); REPL default backend is `http://localhost:8000` — pass `--backend http://127.0.0.1:8080` (global flag, BEFORE the subcommand) or set `WFH_BACKEND_URL` to align.
- **Test-DB hygiene (§R.9)**: never `tempfile.mkdtemp` a throwaway DB directly — use `backend/services/db_janitor.py` (`temp_db_dir(label)` ctx-manager, or `register_for_cleanup(new_temp_db_path(label))` for import-time `WFH_DB_PATH` pins). One canonical `wfh_test_` prefix; `sweep_all()` / `POST /api/maintenance/cleanup_test_artifacts` collects legacy-prefix strays and `ws_`-convention side-file orphans (`concept_index_*` / `evolution_log_*` / `layout_frame_*` / `ontology_frame_*`); `_default` and human-named workspaces are never swept.

## The No-Mocks Contract (§8D.46)

**Production paths run real subsystems. Always.** The four loud ones:

| Subsystem | Real | Fake gate (harness-only) |
|---|---|---|
| SLM | GPT4All `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA. **No Llama allowed.** | `WFH_FAKE_SLM=1` |
| Embedder | GPT4All `Embed4All` `nomic-embed-text-v1.5.f16.gguf` on CUDA. | `WFH_FAKE_EMBEDDER=1` |
| Selenium | Headful Firefox via `backend/drivers/geckodriver.exe` | `NO_WEBDRIVER=1` |
| LangGraph | `langgraph.graph.StateGraph` (no fake gate — missing = hard error) | none |

**`GET /api/subsystem_status`** reports `{slm, embedder, selenium, langgraph, all_real}`. The contract: `all_real: true` in production. CI asserts this before any contract-bearing scenario runs. `WFH_EMBEDDER_DEVICE=cpu` is a real-to-real device override; it stays in the no-mocks lane.

Real-backend → stub fallback is **forbidden in production**. A failed load returns 503 + cascade halts; quiet degradation is the anti-pattern.

## Architectural Non-Negotiables

- **Backend computes; frontend renders.** Layout, embeddings, PageRank are all backend services. Frontend has no UMAP runtime, no embedding fitter.
- **One lifecycle dispatcher** (`backend/services/concept_lifecycle.py::apply_update_lifecycle` + `apply_delete_lifecycle`). Every mutation goes through it: WS broadcast → ConceptIndex upsert → output projection schedule → evolution log → cascade nudge.
- **Two progressive vectorization pipelines** (chunk side: TF-IDF incremental + UMAP joint; concept side: nomic incremental + PageRank joint). Layout Service + Concept Index Service are sibling services, never nested.
- **WebSocket frame seq is monotone per workspace.** `?resume=<seq>` replays last 5 minutes. Lossy backpressure drops oldest progress frames, keeps `done` / `error` / latest `generation`.
- **Idempotency keys on every mutation route.** Retry-safe by construction.
- **Append-only evolution log.** Three rollback scopes: single edit, edit range, actor scope. Rollback is itself recorded as an edit.
- **Optimistic concurrency, not pessimistic locking.** Last-write-wins; conflict resolution is the user's tool (rollback), not the runtime's policy. Cascade scheduler's actor-aware short-circuit prevents agent self-loops but does NOT serialise across actors.

## What Always Holds Across Iterations

1. The §8D.45 use case runs end-to-end **against real subsystems** (`all_real: true` on `/api/subsystem_status`).
2. `env-scenario --name full-smoke` is green in both modes: real (no env gates) AND stub (`WFH_FAKE_*=1`).
3. The doc and the code agree on the six commitments + the schema invariants above + the §8D.46 no-mocks contract.
4. New observable state extends an existing seven-row row in the watch viewer; it does NOT spawn a parallel log stream.
5. New capability is one more peer fixture / one more compiled-from-scans / one more Python-API materialised tree — never a special-cased card type with its own table.
6. **Subsystem failures are loud.** A failed nomic load, a dead Selenium driver, a missing GGUF — these surface as 503s and halted cascades, never silent stub substitutions.

## Forbidden Concepts (Hard Deletions)

The following ideas are **removed** from the design and must not be re-introduced in doc or code:

- **Concentric Fibonacci spheres** as the 3D layout. The 3D layout is the **UMAP-linear-radial force-directed hybrid**: UMAP places chunks, force-directed converges along root-URL rays, hard collider repulsion. The 2D editor uses the 2D analogue (ray-constrained placement around the focal card). The hash-direction + radial-distance placeholder is permitted only as the transient between chunk arrival and the next UMAP refit.
- **Graph analytics** retrieval framework (depth, subtree_size, branching_factor, cluster_id, pattern_frequency, content_density, wl_hash). Retrieval ranks by the triple product `pagerank · tfidf_cos · nomic_cos`. The two embedding axes (nomic over description, TF-IDF over rendering) never mix.
- **Llama** as an SLM target. Production and harness both run Nous Hermes 2 DPO on CUDA.
- **Two-panel hover/click split**. There is one knowledge-panel anatomy, one code path. The pinned panel materialises at the exact screen rect the hover billboard occupied at click time.
- **Stray dotted UI lines.** Dotted 2D↔3D arrows and dotted debug overlays are removed. The 2D↔3D link arrow is solid.
- **Concentric concept-graph rings.** The 2D editor's `_fibonacciPosition` is replaced by ray-constrained placement around the focal card.
- **(§S.1) The `Editor` fourth foundational fixture.** There are **three** fixtures (Database, WebBrowser, Agent). The concept-graph mutation gestures (create/link/overwrite/delete) are intrinsic to the unified panel↔compute-graph scheme (in-node editing + markdown-gesture syntax parsing perform graph mutation implicitly), routed through the same lifecycle (`/concepts` + `/concept_edges`) the agent emitter uses — never a Function-typed `Editor` object. "AgentState authored via Editor calls" → authored through that same mutation lifecycle.
- **(§S.3) The retrieval sidebar.** The standalone NL-search side panel (`#sidebar` / `#rs-latch`) is removed; in-editor halo queries with ray projections (§8.2) are the retrieval surface. The retrieval backend (`/chunk_search`, `/apparitions`, triple-product index) stays.
- **(§S.4) Panel/node chrome.** No coloured header, hash hue, `×`, minimiser, or top bar — anywhere. Every knowledge panel AND computation node is the **black slate**: thin silver border, completely black infill, serif white text (DOMAIN_MODEL §4.1.2). Fixture undeletability is enforced at the lifecycle layer, not by an absent button. A gesture collapses panels into their parent field computation node; clicking a collapsed node fires the §8.2 halo, which stays **proximal to the central node** while abstracting over the folded semantic-space complexity (§S.5).

Return to this file at the start of each session to re-anchor before touching code. Consult `docs/USER_REQUIREMENTS_VERBATIM.md` for the source-of-truth requirements, `docs/CODEBASE_GAP_ANALYSIS.md` for the next-step implementation order, `docs/DOMAIN_MODEL.md` for the full design statement, and `docs/DOC_MAP.md` to navigate into the object-model / features / code-constraints layered docs.
