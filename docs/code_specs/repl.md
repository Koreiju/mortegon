# Spec — REPL (sim_frontend · watch-activity · env-scenario · probes)

> The Symbolic register's implementation surface. Files: `scripts/sim_frontend.py`, `scripts/probe_*.py`, `scripts/probe_live_*.py`. Deepens `DOMAIN_MODEL.md` §11.7 / §11.8 and `CLAUDE.md` "Verification Surface". Constants: [`constants.md`](constants.md) §9. The REPL is a **faithful mirror** of GUI state — it drives the same routes the GUI's `GestureGateway` does, and renders the same `UIState` mirror the GUI renders (it is **not** a parallel code path).

> **All-Real Tests For Everything (DOMAIN §0, Q.1).** This is the verification surface the §0 mandate names. **Every feature has an all-real probe or env-scenario** that runs through real models + real WebBrowser + real LangGraph (`all_real:true` asserted first, §3 pre-gate), a `watch-activity` row that mirrors it (§2), and a stub-mode counterpart that stays green (§3). A capability without an all-real probe/scenario is **not integrated** (§14.4). The §4 live-probe table is the standing realisation; it must stay **exhaustive over the feature surface** — new capability ships with its all-real probe (`timed-scan-duration-port`, `dominance-collapse-roundtrip`, …) or it does not ship.

---

## §1 — The Harness (`sim_frontend.py`)

```python
class SimFrontend:
    def __init__(self, backend: str = REPL_BACKEND_DEFAULT): ...          # pass --backend http://127.0.0.1:8080 to align
    def do(self, action: str, **kwargs) -> dict                           # one action → one route call
    def ws_listen(self) -> Iterator[Frame]                                # mirrors FrameBus (spine.md)
```
- **Surface** — `SIM_ACTIONS` (157, asserted by `action-registry-coverage`) across `19` categories. Each action is the REPL analogue of a `GestureKind` (spine.md §3) — it hits the **same** REST route with an `idempotency_key` body field and awaits the same frames. **Completeness rule (§14.4):** every gateway kind has a `sim_frontend` action; CI asserts the two sets are equal.
- **Action signature pattern** — `do(action, **kwargs) -> {ok, frames:[...], result?}`; kwargs mirror the route body (types.md §7). Categories (representative): `scan`, `retrieval`, `pin`, `edit`, `fold`, `compile`, `wire`, `halo`, `viewport`, `url_vis`, `agent`, `rollout`, `signal`, `library`, `evolution`, `purge`, `ui`, `status`, `watch`.
- **Connection** — one WS per workspace via `ws_listen` (the harness's `FrameBus`); applies frames to a local `UIState` shadow for assertions. `do` is synchronous (await `done`/`error`).

**Example:**
```python
sim = SimFrontend(backend="http://127.0.0.1:8080")
sim.do("scan", url="https://archive.org/search?query=university+library", duration_s=60)  # TIMED full scan (§15.10, Q.2); chunk_added → umap_canonical → done
hits = sim.do("retrieval", query="university library")["result"]               # triple-product hits
sim.do("pin", chunk_id=hits[0]["chunk_id"], rect={"top":120,"left":300,"w":420,"h":260})
sim.do("compile_expand", card_id=hits[0]["chunk_id"])                          # double-left mirror
sim.do("dominance_collapse", node_id=hits[0]["url_root"], collapsed=True)      # right-click root-URL isolate (§6.6.5, Q.3): chunks fold, others hidden
sim.do("dominance_collapse", node_id=hits[0]["url_root"], collapsed=False)     # right-click again → re-expand
```

- **`scan` action** takes `duration_s` (§15.10 time-box, Q.2): `duration_s=0` ⇒ sample-bounded (default); `duration_s>0` ⇒ time-bounded full scan. Maps to `POST /api/web_browser/scan{duration_s}` (api.md §3).
- **`dominance_collapse` action** (category `url_vis`/`dominance`) drives the generalized rank-dominance collapse/expand (§6.6.5 / §7.3.5, Q.3–Q.5): `{node_id, collapsed}` → `POST /api/ui/dominance_collapse` → mirror `dominance_collapse[node_id]`; the `visible 3D` / `hidden 3D` watch rows reflect the isolate. Works on a root-URL hub **and** a bisector compute node (Q.4).

---

## §2 — `watch-activity` (the in-place dashboard, §11.8)

```python
def watch_activity(self) -> None        # renders WATCH_ROWS (=7) rows, updated in place via ANSI cursor codes
```
- **Renders a fixed 7-row dashboard** that updates **in place** (ANSI `\033[<n>A` cursor-up + clear-line) — **no append-spam**. Each frame from `ws_listen` updates the relevant row's counters from the `UIState` mirror (persistence.md §4).
- **The 7 rows (exact, §11.8):**
```
scan        | url=<current>          chunks=<n> page=<p>      <spinner|done>
retrieval   | q="<query>"            hits=<n> top=<name>:<score>
visible 3D  | <n> extruded           rows=[<chunk_id>…]                 # viewport_visible_rows
hidden 3D   | <n> collapsed-hidden   urls_hidden=<n>                    # strict spine rule (§8D.18.1)
pinned      | <n> panels             top=<name> rect=<top,left,w,h>     # last_stick_rect
compile     | <n> cascading actor=<actor>  last=<name>                 # cascade_status
subsystems  | slm=<✓/✗> embed=<✓/✗> selenium=<✓/✗> langgraph=<✓/✗>  all_real=<bool>
```
- **Invariant** — new observable state **extends an existing row**; it does **not** spawn a parallel log stream (§11.8). The dashboard is the operator's GUI-equivalent.

---

## §3 — `env-scenario` (the contract runner, §11.7)

```python
def run_scenario(name: str) -> ScenarioResult        # env-scenario --name <name>
# ScenarioResult = {name, steps:[{action,assert,ok}], passed: bool, mode: "real"|"stub"}
```
- **`--name full-smoke`** runs the `FULL_SMOKE_SCENARIOS` (=83; 86 registered) contract. **All scenarios must stay green on every commit in BOTH modes:** real (no env gates) AND stub (`WFH_FAKE_SLM=WFH_FAKE_EMBEDDER=NO_WEBDRIVER=1`). `--name <specific>` runs one.
- **Pre-gate** — before any contract-bearing scenario, assert `GET /api/subsystem_status` → `all_real:true` (real mode) (errors.md §3; the no-mocks CI gate). Stub mode asserts the fake gates are set + behaviour is deterministic.
- **A scenario** = an ordered list of `do(action, …)` steps each with an assertion over the resulting frames / `UIState` shadow. Adding a new gesture **requires** a scenario (the completeness rule) or it isn't integrated.
- **New scenarios (Q.2–Q.5):** `timed-scan-duration-port` (all-real-gated — live Selenium scan honours `duration_s` wall-clock bound, §15.10); `dominance-collapse-roundtrip` (right-click root-URL hub **and** bisector compute node → fold + isolate → re-expand restores, asserting `dominance_collapse` mirror + `hidden 3D` row, §6.6.5); `dominance-collapse-2d` (panel/graph-form parity per §7.3.5). All three run in both real and stub mode (the duration-port one only proves the *wall-clock bound* in real mode).

---

## §4 — Live Probes (end-to-end evidence, real subsystems)

Each probe is a standalone script asserting a lodestar flow against the **real** stack (no fake gates). They are the §8D.45–§8D.49 acceptance evidence.

| Probe | Asserts (the lodestar) |
|---|---|
| `probe_live_archive_scan.py` | **§8D.45 outside-in** — real Selenium scan of archive.org → real triple-product retrieval (real hits) → `ui/pin` → `compile_expand` mirror → real LangGraph+GPT4All compile |
| `probe_live_concept_graph.py` | **§8D.47 inside-out** — author subgraph from empty primitive → real nomic radiation → wire → `{var}` ref → real compile_chain → focal apparitions → evolution-log audit → rollback-records-as-diff; + multi-step compute graph w/ real GPT4All mid-node, closest-inverse, inline cypher + real Kuzu |
| `probe_live_agent.py` | **§8D.48 autonomous** — spawn agent body (4 cards) → verify backing trio → `agent/tick` fires real GPT4All over real nomic apparitions → token buffer + rationale prove real streamed tokens |
| `probe_live_iterated_compile.py` | **§8D.49 synthesis** — reuse recent scan chunks → 3-node templated compute graph → real GPT4All compile over N samples → halo + double-left round-trip on compiled-graph nodes |
| `probe_live_dominance_and_timed_scan.py` | **§Q (Q.2–Q.6)** — fresh workspace → timed archive.org scan via the `duration_s` port (honors the wall-clock bound) → right-click root-URL collapse (folds chunk samples + isolates all other nodes) → re-expand → compute-node collapse folds BOTH input+output distributions over the same Kuzu ConceptEdge graph PageRank uses. All-real. |
| `probe_no_mocks.py` | **§8D.46** — `all_real:true`; real GPT4All + nomic + Selenium + LangGraph |
| `probe_python_api.py` / `probe_shims.py` / `probe_backing_version.py` / `probe_use_case.py` | materialised python trees / migration shims / backing-version invalidation / 11-step synthetic §8D.45 |

- **Probe contract** — exit 0 on full pass; print the real artefacts (real retrieval hit titles, real compiled text, real token rationale) — **a screenshot is not proof; the REPL run against the live full stack is** (`CLAUDE.md` process discipline).

---

## §5 — Excluded
ANSI escape minutiae (impl-choice); the Symbolic-register / transparency philosophy. The harness is real-stack by default; the fake gates are harness-only and the GUI never sets them.
