# Spec — Backend / Scanner (Selenium · Chunk Build · pattern_map · Web Ontology)

> Deepens [`code_architecture/backend/scanner.md`](../../code_architecture/backend/scanner.md). Files: `selenium_client.py`, `chunk_builder.py`, `compiled_from_scans.py`, `backend/dom/`. Types: [`../types.md`](../types.md) §4. Constants: [`../constants.md`](../constants.md) §6. Selenium = no-mocks boundary.

> **All-real (DOMAIN §0 / §13, Q.1).** The scanner is one of the four real subsystems. Every scan-bearing test runs against **live Selenium** (`NO_WEBDRIVER` unset; `/api/subsystem_status.selenium.loaded:true`); the `NO_WEBDRIVER` gate is harness-only. The timed-scan verification (`timed-scan-duration-port`) and `scripts/probe_live_archive_scan.py` run all-real against `archive.org`.

> **§15.8 realised (backend core).** `extract_golden_trio` (§2, joint-presence gate) + `ChunkPatternSchema` + `build_pattern_schemas` are in `chunk_builder.py`; `CompiledFromScansMaterialiser.update_pattern_map` (§3) upserts the live `pattern_map` ConceptNode via an accretive merge, wired into `backend/dom/pipeline.py`'s persist branch (shared by `run_pipeline_live`). Guarded by `scripts/probe_pattern_map.py`. Open refinements: per-pattern-detection (vs. per-snapshot) granularity, chunk-pattern-graph PageRank, the persistent-accessor-table short-circuit, and the frontend signal-stream panel — see [`../../object_model/ChunkPatternSchema.md`](../../object_model/ChunkPatternSchema.md) Status.

---

## §1 — `WebBrowserManager` (driver) + the scan orchestration

```python
# Realized: WebBrowserManager (selenium_client.py) is a thin DRIVER wrapper —
# the scan/web_query ORCHESTRATION (navigate → discover input → walk → emit
# chunks → paginate) lives in backend/dom/pipeline.py::run_pipeline_live, driven
# by the scan routes (POST /api/web_browser/scan, GET /api/snapshot).
class WebBrowserManager:
    def get_driver(self): ...          # headful Firefox via GECKODRIVER_PATH; eager on lifespan
    def get_page_source(self) -> str: ...
    def close(self): ...
# orchestration (backend/dom/pipeline.py):
def run_pipeline_live(url, query=None, samples=..., max_duration: int = 0, ...) -> ...   # streams chunks + persists + emits frames
```
- **Driver init** — headful Firefox via `GECKODRIVER_PATH`; eager on lifespan. Fake gate `NO_WEBDRIVER` → driver init skipped, `loaded:false` on `/api/subsystem_status`. A failed load surfaces as 503 on scan routes.
- **scan / web_query (orchestration)** — `run_pipeline_live` streams `Chunk`s **as they materialise** (not batch). Each chunk is persisted (lifecycle.md), added to `GlobalTfidfStore` (retrieval.md) + scheduled into the layout refit (layout.md), and broadcast as `chunk_added` to the **workspace** WS (dual-route, §18.1). `web_query` stops after `samples`; `scan` runs to DOM exhaustion + implicit pagination.
- **`max_duration` time-box (§15.10 / §9.8 `duration_s` port, Q.2).** `max_duration > 0` bounds the scan by **wall-clock seconds**: the pagination/emit loop checks elapsed time each iteration and finalises (final UMAP fit + `done`) when `max_duration` is hit. `max_duration = 0` ⇒ sample-bounded (legacy). The two bounds are independent — **whichever fires first stops the scan**. This is the value the `duration_s` input port carries down from the graph editor (api.md `WebBrowserScanRequest.duration_s` / `SnapshotRequest.max_duration` → `trigger_snapshot(max_duration=…)` → `mapper.snapshot(max_duration=…)`); the previously hard-coded `max_duration=180` becomes the **default-when-unset**, not a fixed ceiling. A "full scan of archive.org for N seconds" sets a generous/unbounded `samples` + finite `max_duration`.
- **Algorithm:** navigate(url) → discover search input (heuristics) → if query: type+submit → recursive **shadow-DOM-aware** walk → `chunk_builder.build_chunks(dom)` → yield each → follow implicit pagination (next-link / infinite-scroll) until exhausted, `samples` reached, **or `max_duration` elapsed**.
- **Raises** — `ScanError` on driver/navigation failure; already-yielded chunks persist; a partial `done` frame is emitted (errors.md §1).

---

## §2 — `chunk_builder`

```python
# Realized (chunk_builder.py): the chunk-emit is the `_recurse_absolute_trie`
# method; the recursive ChunkPatternSchema tree is `build_pattern_schemas`; the
# personalized pattern PageRank is `_compute_pattern_pagerank`.
def _recurse_absolute_trie(self, ...) -> ...                    # emit one Chunk per homogeneous sibling
def extract_golden_trio(pattern_or_accessors) -> tuple[str, str, str] | None   # module fn (chunk_builder:229)
def build_pattern_schemas(...) -> list[ChunkPatternSchema]      # the recursive pattern tree
def _compute_pattern_pagerank(schemas, damping=0.85, iters=20) # personalized PageRank, prior ∝ sampled-chunk count
```
- **`_recurse_absolute_trie`** — find repeating **homogeneous** sibling patterns (≥ `PATTERN_MIN_MEMBERS`) → emit one `Chunk` per member; each chunk gets a stable integer `chunk_id`.
- **`extract_golden_trio`** — resolve (title, link, content) accessors under the **joint-presence gate**: a pattern qualifies only if **all three** resolve together (§15.8.1); else returns `None` (the pattern still yields chunks but without a golden trio). Uses `backend/dom/` distillation (WL hashing / Zhang-Shasha / PQ-trees) — **scanner-internal only**, never surfaced in the editor (migration.md).

---

## §3 — `pattern_map` + compiled-from-scans

```python
# Realized (compiled_from_scans.py::CompiledFromScansMaterialiser): one
# materialise_* method per web-ontology peer; `compile_accessors` is the spec's
# umbrella label for them.
def update_pattern_map(self, pattern_schemas, ...) -> None                 # LIVE during scan
def materialise_searchable_url(self, ...) -> dict                          # SearchableURL peer
def materialise_detected_accessor(self, ...) -> dict                       # DetectedAccessor peer
def materialise_xpath_pattern(self, ...) -> dict                           # XPathPattern peer
```
- **`update_pattern_map`** — upsert the `pattern_map` ConceptNode whose `data` is the recursive `ChunkPatternSchema` tree; **incremental during the scan** — `backend/dom/pipeline.py` emits per-pattern `update_pattern_map` frames (§3.1 / §18.29), so the user watches patterns accrete. Under the signal-stream constraint the panel shows **one `pattern_hash` at a time** (§4.6.1; cell.md).
- **`materialise_searchable_url` / `materialise_detected_accessor` / `materialise_xpath_pattern`** — materialise `SearchableURL`, `DetectedAccessor`, `XPathPattern` (+ `PinnedComponent`, `ChunkInstance`) as ConceptNode **peers of the fixtures** (not children of Database); backings `searchable_url::<h>` etc.; web-ontology edges (§8D.39). Idempotent on hash (re-scan upserts → the persistent accessor table is reused, probe_pattern_map §2.2); backing-version bump invalidates dependents (persistence.md).

---

## §4 — Dependencies / Excluded
**Calls:** Selenium WebDriver, `backend/dom/`, lifecycle.md (emit chunks/peers), layout.md (`index_chunk_incremental`), GlobalTfidfStore (retrieval.md). **Called by:** api.md scan routes, the `WebBrowser` fixture, the §8D.49 iterated-compile flow. **Excluded:** the `dom/` algorithm derivations (scanner-internal impl); the Real-register meaning of "chunk."
