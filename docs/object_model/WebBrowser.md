# Object: WebBrowser (Foundational Fixture)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §1.2 (verbatim — *"WebBrowser: for scanning, where scanning takes url input and maybe a search query and outputs a live-updated scan to the 3D gui of the shadow DOM"*), §9.5, §9.5.1 WebBrowser, §15 (the scanner pipeline), §15.7 (URL-set panel), §15.8 (chunk-pattern schema + `pattern_map` output), §17.1 (scan sequence), §18.1 (workspace-WS dual-routing).

**Status.** Realised — `WebBrowser.scan(url, query?)` is the unbounded canonical form (live Selenium → streaming chunks, exercised by `scanner-compute-pipeline` / `scanner-to-concept-roundtrip` / `scan-streaming-routes-to-workspace-ws`); the legacy `WebBrowser.web_query(url, query?, samples)` survives as the sample-bounded variant. The `pattern_map` output materialisation (§1.2.1) is **realised (backend core)**: `backend/dom/pipeline.py`'s persist branch (shared by the live-scan `run_pipeline_live`) builds the golden-trio-gated `ChunkPatternSchema` tree and upserts the live `pattern_map` ConceptNode — see [`ChunkPatternSchema.md`](ChunkPatternSchema.md) Status (+ `scripts/probe_pattern_map.py`). Open refinements (per-pattern-detection granularity, the frontend signal-stream panel) tracked there.

---

## §1 — What it is

The WebBrowser fixture is the workspace's live Selenium runtime for shadow-DOM scanning, surfaced as a foundational fixture (§9.5) alongside Agent, Database, and Editor. Its primary function is `scan(url, query?)`, which navigates to a URL, optionally detects and queries a search input, recursively scans the shadow DOM with implicit pagination, and outputs a live-updated 3D scan into the projector (chunks stream in as they materialise; the `pattern_map` output panel updates with detected chunk-pattern schemas).

The §1.5 framing places WebBrowser in the **Real register** — it is the workspace's measurement endpoint over the world (the open web). Its outputs land in the projector as observations (interior placement, scanner-emitted provenance); the user reads the projector's interior as *what the world contains* and the perimeter as *what the agent has synthesised from it* (§6.6.1).

---

## §2 — Shape

The WebBrowser fixture is a `python_object` ConceptNode (`backing_pointer = fixture::web_browser::<wsid>`) with properties and functions as `python_property` / `python_function` children.

### §2.1 Properties (`python_property` children)

| Property | Type | Source |
|---|---|---|
| `current_url` | `str` | `WebBrowserManager.driver.current_url` |
| `current_title` | `str` | `WebBrowserManager.driver.title` |
| `driver_alive` | `bool` | `WebBrowserManager.driver is not None` |
| `profile_path` | `str` | Geckodriver profile directory |

### §2.2 Primary function — `WebBrowser.scan`

```
Signature: (url: str, query: str | None = None, duration_s: int = 0) -> ScanResult
Ports:
  inputs:  [{name: "url",        type: "str | url_set", required: true},      # accepts a single URL or a {urls_panel} ref
            {name: "query",      type: "str | None",    required: false, default: null},
            {name: "duration_s", type: "int",           required: false, default: 0}]   # §15.10 time-box (Q.2): 0 ⇒ sample-bounded; >0 ⇒ scan for that many wall-clock seconds then finalise
  outputs: [{name: "pattern_map", type: "ChunkPatternSchema[]"},          # §15.8.2 — the typed/named output panel
            {name: "chunks",      type: "list[ChunkInstance]"}]          # the flat list of sampled chunks (also reachable via pattern_map traversal)
Backing: web_browser::scan::<wsid>
```

The **`duration_s` time-box** (§15.10, Q.2) is the exposed functional-object property for "run a full scan of archive.org for a set amount of time": it surfaces in the graph editor exactly like `query`/`samples`, maps down to `mapper.snapshot(max_duration=duration_s)` (the previously hard-coded `max_duration=180` becomes the default-when-unset), and stops the scan when whichever of `samples` / `duration_s` fires first. A *full* timed scan sets a generous/unbounded `samples` + a finite `duration_s`.

**Behaviour:**

1. Navigate to `url` via Selenium.
2. If `query` is provided, detect a search input field on the page and submit the query.
3. Recursively scan the shadow DOM with implicit pagination — the next-page button is pressed iff more samples remain.
4. On stale pagination (no next-page button or no new content), transition back to a previous URL (the workspace's URL-set panel if the input was `{urls_panel}`; otherwise stop).
5. For each emitted chunk:
   - Assign a stable integer chunk_id.
   - Materialise the chunk as a ConceptNode via `apply_update_lifecycle` (provenance=`scanner-emitted`).
   - LayoutService seeds a preliminary radial position.
   - TF-IDF + nomic incremental indexing (across all five multi-frequency bands per §8.1.1).
   - ChunkBuilder builds / extends the ChunkPatternSchema in `pattern_map` (§15.8.2).
   - Golden-trio extraction (§15.8.1) over the pattern's accumulating members.
   - WS frame `chunk_added` dual-routes to workspace WS + snapshot WS (§18.1).
6. As the scan progresses, LayoutService incrementally refits the 6D UMAP — emitting multiple `umap_canonical` frames mid-scan as new chunks accumulate (not just at scan-end).
7. On scan completion: final 6D UMAP fit, per-URL post-processing (centroid translation, bounding-radius scale, hard collider repulsion, HSV phase calibration), `done` frame emitted.
8. The `pattern_map` ConceptNode is materialised as a Function-output panel (§15.8.2) whose `data` field is the recursive ChunkPatternSchema tree, signal-stream-displayed (§4.6.1) over pattern_hash keys.

### §2.3 `{urls_panel}` expansion (§15.7, §17.1.4)

When `scan`'s `url` input port is wired to a `{urls_panel}` reference (a user-created URL-set knowledge panel), the compile resolves the panel via the typed-link inheritance of §15.9 and recognises the `url_set` type. The signal-stream constraint (§4.6.1) takes over: the scan fires *once per URL* in iteration, the panel displays the currently-iterated URL's scan as the visible signal, the play/pause stepper (§7.5) advances. The `pattern_map` output accumulates schemas across all URLs; each schema's `url_root` field inherits one URL per pattern.

### §2.4 Companion methods (`python_function` children)

| Method | Purpose |
|---|---|
| `snapshot()` | Capture the current page's DOM without scanning the full pattern; for stepwise inspection |
| `navigate(url)` | Drive Selenium to `url` without scanning |
| `click(xpath)` | Click an element by xpath; for stateful workflows |
| `search(query)` | Submit `query` into the page's detected search input field (without navigating away first) |
| `more_results()` | Press the next-page button if present |
| `filter(facet, value)` | Apply a facet filter (when the page exposes one) |
| `web_query(url, query?, samples)` | **Legacy** sample-bounded variant of `scan` — retained for back-compat with §16.1 lodestar probe |

---

## §3 — Lifecycle

### §3.1 Fixture materialisation

`foundation_fixtures.ensure_foundation_fixtures(workspace_id)` produces the WebBrowser fixture on workspace boot per [`FoundationFixtures.md`](FoundationFixtures.md). Idempotent on `backing_pointer` match.

### §3.2 Scan invocation

A scan can be invoked through several paths, all converging on the same `WebBrowserManager.scan` call:

- **GUI gesture** — user clicks the WebBrowser.scan compiled-graph node's Compile button.
- **REPL action** — `web-scan { url, query? }`.
- **Agent emission** — `InvokeAction { card_id: <scan_node_id> }` from the emitter.
- **Direct REST** — `POST /api/snapshot?url=...&workspace_id=...` (legacy path, kept for §16.1 probe).

All paths route through `WebBrowserManager.scan(url, query)`. The selenium driver is shared across paths (singleton, eagerly initialised in the FastAPI lifespan handler).

### §3.3 Live update flow

See [`features/live_scan_streaming.md`](../features/live_scan_streaming.md) and §17.1 for the full streaming-to-WS sequence. Critical invariants:

- Every emitted payload carries `workspace_id` so the `_ws_push` dual-router fans to the workspace WS (§18.1 severance guard).
- The workspace WS is pre-created at scan start so frames emitted before the frontend subscribes are not dropped.
- The error path also emits a `done` frame with `workspace_id` and `error` set, so the frontend sees the failure on the workspace WS.

### §3.4 Database cleanup contract

On `purge_workspace`, every WebBrowser-emitted ConceptNode (chunks, `pattern_map`, intermediate `ChunkInstance` records) is removed through `apply_delete_lifecycle` per [`ConceptLifecycle.md`](ConceptLifecycle.md). The TF-IDF and nomic indices return to empty; the LayoutFrame is dropped. See [`features/live_scan_cleanup.md`](../features/live_scan_cleanup.md) for the §16.5 acceptance probe.

---

## §4 — Persistence

| Artefact | Storage |
|---|---|
| Fixture node + python_property/function children | Kuzu `ConceptNode` table |
| Per-chunk `ChunkInstance` ConceptNode | Kuzu `ConceptNode` (one per emitted chunk; provenance=`scanner-emitted`) |
| `pattern_map` output ConceptNode | Kuzu `ConceptNode` (per scan); data field carries the recursive ChunkPatternSchema tree |
| `ChunkPatternSchema` records | Stored in the `pattern_map` node's `data` field as a structured tree; see [`ChunkPatternSchema.md`](ChunkPatternSchema.md) |
| Per-domain accessor table (§5.4) | Kuzu, keyed by `(domain, pattern_hash)`; populated by ChunkBuilder per scan |
| Per-chunk TF-IDF vectors | [`GlobalTfidfStore.md`](GlobalTfidfStore.md), incremental per band |
| Per-chunk nomic vectors | [`EmbeddingService.md`](EmbeddingService.md) + [`ConceptIndexService.md`](ConceptIndexService.md) cache |
| Per-chunk 6D UMAP coords | [`LayoutFrame.md`](LayoutFrame.md), per workspace |
| Selenium browser profile | Geckodriver profile dir on disk (survives backend restarts) |

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`SeleniumClient.md`](SeleniumClient.md) | `WebBrowserManager` singleton holds the Selenium driver; `scan` invokes its methods |
| [`ChunkBuilder.md`](ChunkBuilder.md) | Per-chunk extraction, generalised xpath, golden-trio detection (§15.8.1) |
| [`ChunkPatternSchema.md`](ChunkPatternSchema.md) | Live-built schema per detected pattern; surfaces in `pattern_map` output |
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | Each chunk + pattern_map lands as a ConceptNode through the lifecycle |
| [`LayoutService.md`](LayoutService.md) | 6D UMAP refits per chunk burst; per-URL placement |
| [`GlobalTfidfStore.md`](GlobalTfidfStore.md) | Incremental TF-IDF across all five frequency bands |
| [`URLSetPanel.md`](URLSetPanel.md) | `{urls_panel}` reference into the `url` input port triggers per-URL signal-stream iteration |
| [`PatternMap.md`](PatternMap.md) | Frontend panel renderer reads the materialised output and displays under signal-stream constraint |
| [`UIStateService.md`](UIStateService.md) | Scan progress reflected in viewer's `scan` row; `pattern_map` signal in the dedicated row |

---

## §6 — Cross-references

- Feature touchpoints — [`features/four_fixture_api.md`](../features/four_fixture_api.md), [`features/pattern_map.md`](../features/pattern_map.md), [`features/url_set_panel.md`](../features/url_set_panel.md), [`features/golden_trio.md`](../features/golden_trio.md), [`features/live_scan_streaming.md`](../features/live_scan_streaming.md), [`features/live_scan_cleanup.md`](../features/live_scan_cleanup.md).
- Code constraints — [`streaming.md`](../code_constraints/streaming.md), [`backend_services.md`](../code_constraints/backend_services.md) (Selenium real-vs-NO_WEBDRIVER), [`ws_frames.md`](../code_constraints/ws_frames.md) (dual-routing).
- Sequence reference — DOMAIN_MODEL §17.1 (scan), §17.1.4 ({urls_panel} expansion), §17.1.3 (pattern_map iteration).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Emitting scan payloads without `workspace_id` | §18.1 severance regression; the workspace WS dual-routing depends on workspace_id presence | `on_stream` injects `workspace_id` on every payload; `_ws_push` routes accordingly |
| Materialising `pattern_map` only at scan-end | §18.29 violates the live-update contract; the user cannot iterate over partial state | Per-pattern incremental schema build emits `concept_changed` on every new pattern/sample |
| Firing `scan` in parallel over a URL-set instead of per-signal | §18.30 breaks URL attribution and the play/pause stepper | The `{urls_panel}` expansion runs serial per signal-stream constraint |
| Falling back to a fake Selenium in production paths | Real-backend → stub fallback forbidden (§13.4); only `NO_WEBDRIVER=1` harness flag may engage the no-driver path | `subsystem-status` reports the active backend; CI gates on real Selenium |
| Mutating chunks directly in Kuzu without going through the lifecycle | Breaks the cascade + EvolutionLog invariants | Scanner emits via `Editor.create` (or the equivalent `apply_update_lifecycle` call); no direct DB writes |
| Treating `web_query` as the canonical surface for new code | `web_query` is legacy; `scan(url, query?)` is canonical per §9.5.1 | New code wires `scan`; route-coverage scenario keeps `web_query` reachable for back-compat |
| Letting old chunks survive `purge_workspace` | §18.4 stale state across rounds | The §16.5 cleanup probe asserts Kuzu, TF-IDF, LayoutFrame, accessor table all return to baseline |
| Rendering pattern_map as a flat list (all patterns visible at once) | §18.24 violates signal-stream constraint | Frontend reads `signal_stream` mirror and renders only the current pattern_hash |
