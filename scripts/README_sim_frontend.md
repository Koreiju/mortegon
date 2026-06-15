# `sim_frontend.py` — terminal harness for the frontend webapp

A single CLI that simulates the actions a user takes in the 3D / 2D GUI
(creating concepts, linking them, opening billboards, deleting cards,
triggering scans, querying apparitions, purging workspaces) **and**
tails the WebSocket broadcast stream so the resulting server-side
events are mirrored to the terminal. Use it whenever you want to
verify a backend change end-to-end without spinning up the browser.

## Why it exists

The frontend is a thick JS client driven by REST + a workspace-scoped
WebSocket. Verifying end-to-end behaviour after a backend change
historically meant `python -m backend.main` → browser → click through
the UI → squint at DevTools. The harness collapses that into typed
commands and a streaming console tail.

It also runs **scripted scenarios** so a quick post-change smoke check
is a single invocation.

## Two execution paths

| Path | When to use | How |
|---|---|---|
| Live backend | Verifying a change against the real server | `python -m backend.main` in another terminal, then point the harness at `http://127.0.0.1:8080` |
| No backend | Quick pipeline regression after a chunker / scanner edit | `python scripts/sim_frontend.py pipeline-smoke` (uses the built-in tarot fixture; no Selenium, no DB, no HTTP) |

## Quickstart

```bash
# Terminal 1: backend (with Selenium disabled so init is fast)
NO_WEBDRIVER=1 python -m backend.main
# wait for "Application startup complete."

# Terminal 2: probe REST surface
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 health
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 list-concepts
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 create-concept --name "Foo"

# Terminal 3: tail the WS broadcast stream
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 watch --seconds 60
```

Run a scripted scenario in one command (covers
create → link → apparitions → delete, asserts each step):

```bash
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 scenario --name create-and-link
```

Smoke-test the chunker without any backend running:

```bash
python scripts/sim_frontend.py pipeline-smoke
```

## Sub-commands

| Command | What it hits |
|---|---|
| `health` | `GET /api/health` |
| `list-concepts` | `GET /api/concepts` |
| `create-concept --name N [--desc D] [--data D]` | `POST /api/concepts` |
| `get-concept ID` | `GET /api/concepts/{id}` |
| `delete-concept ID` | `DELETE /api/concepts/{id}` |
| `link --src ID --tgt ID [--type T]` | `POST /api/concept_edges` |
| `apparitions ID [--k N]` | `GET /api/apparitions/{id}` |
| `purge [--confirm erase]` | `POST /api/purge_workspace` |
| `scan URL` | `GET /api/snapshot` |
| `watch [--seconds N] [--filter T1,T2] [--raw]` | tails `ws://…/api/ws/workspace/{wsid}` |
| `scenario --name NAME` | runs a pre-baked multi-step flow |
| `pipeline-smoke` | no-backend `run_pipeline` regression check |

### Scenarios

- `create-and-link` — create A, create B, link A→B, query apparitions(A), delete B, verify B is gone.
- `fixture-delete-guard` — confirm §8D.12 foundation fixtures reject DELETE with HTTP 409.

Add new ones by registering in `_SCENARIOS` at the bottom of `sim_frontend.py`.

## Flags

| Flag | Default | Notes |
|---|---|---|
| `--backend URL` | `http://localhost:8000` | Backend base URL. Override via `WFH_BACKEND_URL` env var. |
| `--workspace WS` | `""` (= `_default`) | Workspace id. Override via `WFH_WORKSPACE` env var. |

## What you'll see

REST commands print a uniform `request → response` shape:

```
✓ create 'sim::concept-A' → HTTP 200
{
  "concept_id": "card_eed1...",
  "name": "sim::concept-A",
  ...
}
```

WS frames in `watch` mode render one line per frame, colour-coded by
type so the event stream is scannable:

```
✓ connected
concept_changed       id=card_eed1 ws=_default change=created
edge_changed          edge=edge_xy ws=_default change=created
umap_canonical        ws=_default
agent_token           sess=foo
```

`--raw` switches to one-line JSON per frame for grepping / piping.

## Two bugs found while building this

Building the harness end-to-end surfaced two real bugs that had been
silently degrading the live app:

1. **35 routes were double-prefixed**. `@router.X("/api/...")` + `app.include_router(router, prefix="/api")` mounted them at `/api/api/...`, while the frontend (and this harness) called them at `/api/...`. The frontend was silently 404-ing on every concepts CRUD, apparitions, evolution-log, edges, agent tick/fork/spawn call. Fixed by stripping the redundant `/api/` from the decorators.
2. **WS handshake was racing with synchronous bootstrap**. `websocket_workspace_stream` called `await websocket.accept()` then immediately ran heavy sync init (ConceptIndex, nomic embedder load, foundation fixtures, layout hydrate). The accept-response stayed buffered until the next `await`, so the client timed out waiting for the handshake — even though the upgrade was logically complete. Fixed with an `await asyncio.sleep(0)` right after accept to force a flush.

Both are real production fixes. The harness is the fixture that caught them, and the `scenario fixture-delete-guard` flow is a one-shot regression test for the route-mount path.

## Gym-style environment (`repl` / `step` / `replay`)

Above the per-command surface sits a `FrontendEnv` — an OpenAI-Gym-style
wrapper around the running backend. It opens a persistent WS connection
on a background thread, accumulates broadcast frames between commands,
and surfaces `reset()` / `step(action, **kwargs)` / `observe()` /
`render()` over the same action vocabulary.

### Why this layer

REST commands are great for one-off probes, but real frontend behaviour
is a **sequence** of user gestures whose WS frames and graph-state
changes interact. The env makes each step's full effect inspectable:

```python
out = env.step("concept-create", name="Foo")
# out == {
#   "action":      "concept-create",
#   "args":        {"name": "Foo"},
#   "response":    {"_status": 200, "concept_id": "card_…", ...},
#   "frames":      [ {type: "concept_changed", ...}, ... ],
#   "state_delta": {"created": ["card_…"], "removed": [], "edges_created": [...]},
#   "elapsed_ms":  214.7,
# }
```

That same shape is what the `step` / `replay` sub-commands print, and
what the `repl` exposes interactively.

### Interactive REPL

```bash
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 repl
```

```
── FrontendEnv REPL  →  http://127.0.0.1:8080  ws=_default ──
  ws status: connected=True

sim> help
sim> concept-create name=Alpha description="first probe"
sim> concept-create name=Beta description="second probe"
sim> edge-create src=<alpha-id> tgt=<beta-id>
sim> apparitions focal=<alpha-id> k=10
sim> obs               # pretty-print current state
sim> state             # JSON state dump
sim> drain             # flush pending WS frames
sim> history           # last 20 steps + status codes
sim> reset             # purge + re-sync
sim> reset --keep      # re-sync without purging
sim> quit
```

A bare action name (e.g. `concept-create name=Foo`) is treated as an
implicit `step` for ergonomic one-line use.

### One-shot `step`

For shell scripts / `&&` chains:

```bash
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 step concept-create name=Foo
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 step apparitions focal=<id> k=10
python scripts/sim_frontend.py step pipeline fixture=tarot --no-purge   # no backend needed
```

Exit code is non-zero on HTTP failure or action error, so it composes
cleanly with `&&` / CI gates.

### Scripted `replay`

Action sequences are JSON-Lines files (one action per line). Comments
start with `#`. Example: `scripts/samples/sim_smoke.jsonl`:

```jsonl
{"action": "health"}
{"action": "concept-list"}
{"action": "concept-delete", "id": "fixture::database::_default"}
{"action": "pipeline", "fixture": "tarot"}
{"action": "assert-frame", "type": "concept_index_update", "min_count": 0}
```

```bash
python scripts/sim_frontend.py --backend http://127.0.0.1:8080 \
       replay scripts/samples/sim_smoke.jsonl
```

The replay walks each action, prints the per-step observation, and
returns exit 0 only if every `assert-*` step returned `ok: true` and
no response carried an `_error`. Use this as a one-line regression
gate after a backend change.

### Action vocabulary

`python scripts/sim_frontend.py actions-help` prints the full list with
arg signatures (**107 actions across 89 backend routes**). For a
JSON-structured listing grouped by category run `python scripts/sim_frontend.py step actions-by-category`. To dump every backend route + its mounted methods, run `python scripts/sim_frontend.py step routes-list` (offline — no backend needed).

`route-coverage` scenario asserts every backend route has a CLI mirror
(currently **89/89** — comprehensive coverage of the full app
surface). Coverage by category:

- **Meta / introspection** (3): `routes-list [prefix=P]`, `actions-by-category`, `app-info`. All offline-readable.
- **Legacy DOM graph** (7) — *new*: `upload`, `label-node`, `update-node`, `graph-fetch`, `nodes-fetch`, `node-details`, `profile`. The pre-§8D raw-node ingest path; useful for synthetic graph tests.
- **Mapper / scanner snapshots** (17) — *new*: `map-snapshot`, `map-urls`, `map-snapshots url=URL`, `map-detail`, `map-label`, `map-label-batch`, `map-select-structural`, `map-labels url=URL`, `map-structure-tag`, `map-structure-tags`, `map-restore`, `map-chunks id=SNAP`, `map-content-distilled id=SNAP`, `map-chunks-label`, `map-lca-subtree`, `map-commutation`, `map-subgroup-commutation`. The full mapper REST surface for snapshot inspection + labelling.
- **Analytics** (5) — *new*: `analytics-runs`, `analytics-fitted run=ID`, `analytics-auto-fit`, `analytics-features`, `analytics-ontologize`. §12 graph-theoretic feature pipeline.
- **Agentic fluid (legacy)** (3) — *new*: `agentic-instantiate`, `agentic-propagate fluid=ID`, `agentic-auto-run fluid=ID`. JSON-payloaded ports for the old fluid-simulation surface.
- **Compiled-from-scans (§8D.39)** (3) — *new*: `compiled-searchable-url`, `compiled-detected-accessor`, `compiled-xpath-pattern`. Manual triggers for the auto-materialisation paths the scanner normally fires.
- **Chat / session** (2) — *new*: `chat-session`, `session-reconcile url=URL`.
- **Chunk batch fetch + image proxy** (2) — *new*: `chunk-details-batch ids=A,B,C`, `image-proxy url=URL`.
- **UI gestures** (6, frontend-mirror) — *new*: `ui-select`, `ui-hover`,
  `ui-pin`, `ui-unpin`, `ui-state`, `spine-delta`. These write to the
  backend's per-workspace UI-state mirror so peer tabs / agents / the
  CLI all see the same "user attention" signal. ``ui-pin chunk_X``
  from the CLI is indistinguishable from the user click-and-sticking
  a billboard in the browser.
- **Browser automation** (2, optional) — *new*: `browser-screenshot`,
  `browser-eval`. Launch Firefox via the existing scanner client,
  load the frontend, snap a PNG or execute JS. Use to verify the
  3D / 2D surfaces actually rendered after a sequence of CLI gestures.
- **Concept CRUD** (5): `concept-create`, `concept-update`, `concept-get`,
  `concept-delete`, `concept-list`
- **Edges** (2): `edge-create`, `edge-delete`
- **Retrieval** (5): `apparitions`, `ontology-walk`, `closest-inverse`,
  `radiation`, `pattern-instances`
- **Compute graph** (4): `compile`, `recompute-index`, `recompute-umap`,
  `backing-invoke`
- **Agents** (7): `agent-tick`, `agent-spawn`, `agent-fork`,
  `agent-reviews`, `agent-resolve-review`, `agent-tokens`, `cascade-status`
- **Evolution log / rollback** (4): `evolution-log`, `rollback-single`,
  `rollback-range`, `rollback-actor`
- **Scan + chunks** (6): `scan`, `scan-status`, `pipeline` (no-backend),
  `chunk-search`, `chunk-details`, `chunk-nodes`
- **Search** (2): `search-hybrid`, `search-dom-text`
- **Graph / schema** (2): `graph-schema`, `graph-halo`
- **Import / export / telemetry / foundation** (4): `concepts-export`,
  `concepts-import`, `telemetry`, `foundation-ensure`
- **Workspace lifecycle** (2): `purge`, `health`
- **Control / introspection / assertions** (6): `wait`, `env-info`,
  `describe-action`, `frames-clear`, `assert-concept`, `assert-frame`

### Cross-step references in replay scripts

Scripted JSONL replays can chain step results via `${step[N].field}`
substitution. ``N`` is 0-based over prior steps; negative indices
count from the end. Resolution happens before each step fires; an
unknown reference fails the step instead of silently sending `None`.

```jsonl
{"action": "concept-create", "name": "Alpha"}
{"action": "concept-create", "name": "Beta"}
{"action": "edge-create",   "src": "${step[0].concept_id}",
                            "tgt": "${step[1].concept_id}"}
{"action": "assert-concept", "id": "${step[0].concept_id}", "exists": true}
```

See `scripts/samples/sim_full_flow.jsonl` for a complete example.

### Assertion vocabulary

| Action | What it asserts |
|---|---|
| `assert-concept` | concept id present/absent in env's current state |
| `assert-frame` | at least N WS frames of a given type seen |
| `assert-frame-payload` | at least one frame of type T has key K (optionally K=V) |
| `assert-state-count` | workspace currently holds exactly N concepts / M edges |
| `assert-response-key` | last step's response has (or lacks) a given key |
| `assert-elapsed-under` | last step ran in <N ms (perf canary) |
| `step-ref` | look up a field from a prior step (REPL convenience) |

All `assert-*` actions return `ok: True/False` in their response and
contribute to the replay exit code (failure → non-zero exit).

### Scenarios (15)

Run any of these with `python scripts/sim_frontend.py env-scenario --name <NAME>`:

| Name | What it verifies | Needs embedder |
|---|---|---|
| `action-registry-coverage` | every action has a kwarg signature; every scenario is callable | no |
| `route-coverage` | every backend route has at least one CLI action calling it (89/89 today) | no |
| `chunker-regression` | `pipeline` action emits per-instance `/article` chunk with 3 members | no |
| `chunker-edge-cases` | empty body → 0 chunks; single-paragraph body → no crash; tarot → 3-member /article | no |
| `route-mount-smoke` | health, scan-status, concept-list, graph-schema, cascade-status, evolution-log all 2xx | no (live backend, no embedder) |
| `graph-schema-shape` | schema declares canonical node types + every entry has edge_type + target_types | no (live backend, no embedder) |
| `health-perf` | warm `/api/health` returns in <100ms (perf canary) | no (live backend, no embedder) |
| `fixture-delete-guard` | §8D.12 fixture DELETE returns 409 | no (live backend, no embedder) |
| `ui-roundtrip` | select / pin (×2) / hover / unpin / purge — UI state mirror behaves correctly | no (live backend, no embedder) |
| `spine-delta-emits` | `POST /api/spine_delta` accepted (no-op with zero agents) | no (live backend, no embedder) |
| `warmup` | Pre-loads nomic embedder so subsequent scenarios run fast | yes (slow first time) |
| `concept-lifecycle` | create → update → get → delete → assert-gone | yes |
| `edge-roundtrip` | create A + B → link → delete edge → cleanup | yes |
| `apparitions-discover-link` | triple-product retrieval surfaces a freshly-linked target | yes |
| `purge-and-rebuild` | purge wipes workspace, `foundation-ensure` restores fixtures | yes |
| `evolution-rollback` | §8D.33 rollback restores pre-delete state | yes |
| `idempotency-replay` | same idempotency_key returns same concept_id | yes |
| `full-smoke` | Composes everything above, collects all failures | yes |

### Pytest integration

The no-backend scenarios run as standard pytest tests:

```bash
python -m pytest backend/tests/test_sim_env_scenarios.py -v
```

Each `_NO_BACKEND_SCENARIOS` entry becomes a parametrised test case,
so a CI failure points directly at the offending scenario name.
Coverage today: `action-registry-coverage`, `chunker-regression`,
`chunker-edge-cases` (plus two smoke tests for the registry sizes).

### Fake-embedder mode

For environments without GPU + GGUF weights, set
``WFH_FAKE_EMBEDDER=1`` before starting the backend:

```bash
NO_WEBDRIVER=1 WFH_FAKE_EMBEDDER=1 python -m backend.main
```

The `EmbeddingService` then returns deterministic SHA256-derived
768-dim vectors instead of loading the ~200MB nomic GGUF. Same
``embed()`` surface; the cosine geometry between similar inputs is
nonsensical but stable, so tests that assert on "X is in the
candidate set" still work, tests that assert on "X ranks higher
than Y" don't.

**Caveat**: there are other backend cold-start costs (TF-IDF store
hydrate, layout service init, foundation fixture create cascade)
that the fake-embedder alone doesn't eliminate. The first concept-
create after a cold backend can still be slow; see the cold-start
note above.

### Cold-start performance note

The backend's `ConceptIndexService` lazily loads a ~200MB nomic GGUF
model on the **first** call to any concept-create / lifecycle path.
On a cold backend (just-started) the first such call can take **60–
300s** depending on whether the model has to download. After that,
subsequent calls run in 10-50ms. The `warmup` scenario exists to pay
this cost up front so the rest of the run is fast.

If you only want to verify the chunker / route mount / fixture guard
(the parts that don't touch the embedder), use `route-mount-smoke`
+ `chunker-regression` + `fixture-delete-guard` — these run in ~2s
total against a cold backend.

### Adding a new action

In `sim_frontend.py`:

```python
def _act_my_action(env, *, foo: str = "") -> Dict[str, Any]:
    if not foo:
        raise TypeError("my-action requires foo=...")
    return env.backend._request("POST", "/api/my_route", body={"foo": foo})

_ACTIONS["my-action"] = _act_my_action
# Optional: add to _MUTATING_ACTIONS if it changes concept/edge state
```

That's it — REPL, `step`, and `replay` all see the new action via the
registry.

### Sample scripts

Under `scripts/samples/`:

- `sim_smoke.jsonl` — quick 5-step health + chunker + fixture-guard check
- `sim_chunker_regression.jsonl` — post-chunker-change regression
- `sim_apparitions_walk.jsonl` — apparitions / ontology-walk template

## One-terminal mode: `python app.py --repl`

For a single-terminal workflow, `app.py --repl` starts the backend
in a background thread AND drops the same console into the
FrontendEnv REPL:

```bash
python app.py --repl
# [app] Backend starting on http://127.0.0.1:8080 ...
# [app] Backend ready. Frontend → http://127.0.0.1:8080/  ·  type 'help' for actions.
#
# ── FrontendEnv REPL  →  http://127.0.0.1:8080  ws=_default ──
#   backend:    http://127.0.0.1:8080
#   workspace:  _default
#   type 'help' for actions, 'obs' for state, 'quit' to exit
#
# sim>
```

Any browser tab loading `http://127.0.0.1:8080/` connects to the
same backend. The frontend's MutationObservers POST DOM-change
reports back; the CLI in this same terminal drains them via
`ui-telemetry`.

## Frontend → backend telemetry channel

The frontend's `cp/telemetry.js` mixin installs MutationObservers
on the rendered surfaces the CLI cares about:

  - `#concept-editor` → emits `concept-card-list` reports
  - `#projector-panel` → emits `pinned-billboards` reports
  - `.concept-apparition-halo-overlay` → emits `apparition-halo` reports
  - `#three-container` → emits `three-container-attr` reports (size/style)

Each observer is debounced 200 ms. Reports are POSTed to
`/api/ui/telemetry` as `{kind, target_id?, count?, extra?}` and
stored in a per-workspace bounded ring buffer with monotonic seqs.

### CLI consumption

```bash
# Drain the buffer (paginate via since_seq):
sim> ui-telemetry since_seq=0 limit=50

# Continuous tail — prints every new entry for 30s:
sim> ui-telemetry-stream seconds=30 poll_ms=500

# Push a synthetic entry (useful for round-trip tests, also
# replicates what a manual gesture would emit):
sim> ui-telemetry-push kind=card-added target_id=card_X count=1
```

When the browser is open at the frontend, every user click that
mutates the visible DOM appears in `ui-telemetry-stream` within
~250 ms.  The CLI sees what the user sees — without screen-scraping,
without browser automation.

## Frontend gestures from CLI

The harness mirrors every user gesture the frontend can fire:

| User gesture (browser) | CLI action | Backend mirror |
|---|---|---|
| Click 3D node to select | `ui-select id=X` | `POST /api/ui/select` writes UI mirror |
| Hover 3D node for halo | `ui-hover id=X` | `POST /api/ui/hover` writes UI mirror |
| Click-and-stick billboard | `ui-pin id=X` | `POST /api/ui/pin` adds to pinned list |
| Close pinned panel | `ui-unpin id=X` | `POST /api/ui/unpin` removes from list |
| Drag spine handle | `spine-delta popped=X,Y folded=Z` | `POST /api/spine_delta` → active agents' zone_of_influence |
| Create concept (2D editor) | `concept-create name=X` | `POST /api/concepts` |
| Update concept inline | `concept-update id=X name=Y` | `PATCH /api/concepts/{id}` |
| Link two cards | `edge-create src=X tgt=Y type=T` | `POST /api/concept_edges` |
| Hover focal → halo apparitions | `apparitions focal=X k=N` | `GET /api/apparitions/{id}` |
| Right-click → Open Link halo | `ontology-walk focal=X depth=2` | `GET /api/ontology_walk/{id}` |
| Trigger DOM scan | `scan url=URL` | `GET /api/snapshot?url=...` |
| Click "purge workspace" | `purge confirm=erase` | `POST /api/purge_workspace` |
| Read current UI state | `ui-state` | `GET /api/ui/state?workspace_id=X` |

The UI state mirror is the new piece: previously these gestures
lived only in the browser tab, so an agent or the CLI couldn't know
what the user was attending to. Now they're a server-side dict per
workspace, broadcast on change, REST-readable. The frontend doesn't
have to be open for the CLI to drive the same signal.

## Browser automation (optional)

Two actions wrap the existing `WebBrowserManager` (the scanner's
Firefox client) so a CLI sequence can launch the actual frontend
and verify it visually:

```bash
sim> health
sim> ui-pin id=card_xyz
sim> browser-screenshot out=after_pin.png wait_ms=2000
```

```bash
sim> browser-eval js="return document.querySelectorAll('.concept-card').length"
# → response: {"value": 3}
```

Both actions launch + tear down per call; for sustained sessions
batch the JS into one `browser-eval` call. Requires Firefox + the
local geckodriver under `backend/drivers/` (same as `scripts/scan.py`).
Skipped gracefully on machines without those installed (returns
`_error: selenium not available`).

## Known limitations

- First `create-concept` against a cold backend takes ~60s (nomic
  embedder + ConceptIndex first-load). Subsequent calls are fast.
- Concept CRUD broadcasts a `concept_changed` WS frame, but you need
  to start `watch` BEFORE the action so you see it on the tail. The
  WS bootstrap also re-sends accumulated state on connect.
- The harness is HTTP/WS only — it doesn't drive the 3D Three.js
  surface (that's a browser concern). Pair this with the browser if
  you need visual confirmation.
