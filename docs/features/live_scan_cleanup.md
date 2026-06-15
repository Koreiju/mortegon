# Feature: Live-Scan + DB-Cleanup REPL Probe (Mandatory)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §16.5 (the live-scan + DB-cleanup REPL probe), §1.2 verbatim (*"live-scanning updates must be rigorously tested with proper database cleanup on real sites in our full-stack REPL test in the console"*), §18.1 (scan ↔ streaming severance — the most important anti-goal this probe guards), §13 (no-mocks contract).

**Status.** Realised. The `live-scan-real-with-cleanup` env-scenario is registered in `sim_frontend.py` + the `full-smoke` chain (gated on `all_real`: it runs the real Selenium→retrieval→purge round-trip when `/api/subsystem_status` reports `all_real:true`, and skips gracefully in stub mode per env_scenarios §1.5). The real live-stack evidence path is `scripts/probe_live_archive_scan.py` (§8D.45 outside-in lodestar). The purge half is realised in `POST /api/purge_workspace` (bulk Kuzu delete + LayoutFrame drop + the §1.8 global TF-IDF `remove_workspace` cleanup + consolidated `purge_workspace` frame).

---

## §1 — What the operator sees

The operator runs `python scripts/probe_live_scan_with_cleanup.py --backend http://127.0.0.1:8080` against a fresh real-stack backend (`all_real: true`). The probe scans a real archive.org URL with a search query, asserts every link in the Real ↔ Imaginary ↔ Symbolic loop, then purges the workspace and asserts the cleanup contract holds — Kuzu shrinks back to baseline, the TF-IDF + nomic indices return to empty, the persistent accessor table for the domain clears, the on-disk Kuzu file shrinks back to within 10 % of its pre-scan size — and finally re-runs the scan to verify the chunk count rebuilds identically (a stale index would cause incremental-update mismatch).

The probe is mandatory because the §18.1 scan-streaming severance and the cleanup contract together govern the workspace's ability to exercise the Real-Imaginary loop *repeatedly* on real sites without progressive degradation. Any drift between scan rounds — orphan chunks, stale TF-IDF entries, dangling URL roots — shows up here first.

The §1.5 framing makes this probe the **Symbolic register's primary acceptance instrument** for the Real-Imaginary loop's repeatability. The REPL transcript IS the witness.

---

## §2 — Cross-objects

| Object | Role in this probe |
|---|---|
| [`WebBrowser`](../object_model/WebBrowser.md) | `scan(url, query?)` is the subject; live streaming is verified |
| [`LayoutService`](../object_model/LayoutService.md) | 6D UMAP fits during scan emit `umap_canonical` frames; perimeter rescale applies to any agent-emitted chunks |
| [`ConceptIndexService`](../object_model/ConceptIndexService.md) | Multi-frequency indices update incrementally during scan; clear on purge |
| [`GlobalTfidfStore`](../object_model/GlobalTfidfStore.md) | TF-IDF doc count returns to 0 on purge |
| [`ApparitionService`](../object_model/ApparitionService.md) | Multi-frequency aggregation produces non-trivial scores after scan settles |
| [`ConceptLifecycle`](../object_model/ConceptLifecycle.md) | Every chunk emission routes through the dispatcher; purge walks every concept |
| [`Database`](../object_model/Database.md) | Persistent accessor table clears on purge; Kuzu file shrinks |
| [`FoundationFixtures`](../object_model/FoundationFixtures.md) | Three fixtures (Agent/WebBrowser/Database) remain present + reachable after purge (§S) |
| [`UIStateService`](../object_model/UIStateService.md) | All mirror fields clear on purge |
| [`PatternMap`](../object_model/PatternMap.md) | `pattern_map` output materialises with non-empty schema during scan |

---

## §3 — Probe steps

```
1. Fresh backend boot
   ▼  GET /api/subsystem_status → assert all_real: true
   ▼  no fake gates (WFH_FAKE_SLM, WFH_FAKE_EMBEDDER, NO_WEBDRIVER all unset)

2. Workspace purge — clean baseline
   ▼  POST /api/purge_workspace { confirm: "erase" }
   ▼  GET /api/concepts → assert count == foundation-fixture-baseline (three fixtures + their materialised member trees, §S)

3. Subscribe to workspace WS
   ▼  WS /api/ws/workspace/_default
   ▼  await connection open

4. Trigger real scan
   ▼  POST /api/snapshot?url=https://archive.org/details/texts&query=university%20library
   ▼  await 202 Accepted

5. Watch the live stream — assertions
   ▼  chunk_added frames arrive on the workspace WS (NOT just snapshot WS) — §18.1 severance closed
   ▼  chunk count climbs monotonically
   ▼  multiple umap_canonical frames arrive incrementally (not just at scan-end)
   ▼  umap_canonical frame carries 6-vector per chunk (3 position + 3 HSV)
   ▼  pattern_map ConceptNode materialises with concept_changed BEFORE the done frame
   ▼  pattern_map's data field carries at least one ChunkPatternSchema with non-empty golden_trio

6. Retrieval verification after scan settles
   ▼  POST /api/search → "university library" returns at least one chunk
   ▼  GET /api/apparitions/<top-hit-chunk-id> → at least one candidate with score above min_score_threshold

7. Inspect projector geometry
   ▼  GET /api/layout_frame → assert 6-vector format
   ▼  if any agent-output chunks present, assert they sit on the perimeter band

8. Database cleanup — purge again
   ▼  POST /api/purge_workspace { confirm: "erase" }
   ▼  assert:
   │    • Kuzu ConceptNode count == three-fixture-baseline (§S)
   │    • LayoutFrame dropped (GET /api/layout_frame returns empty)
   │    • TF-IDF doc_count == 0 (GET /api/health reports)
   │    • Persistent accessor table for archive.org cleared
   │    • On-disk Kuzu file size within 10% of pre-scan baseline
   │    • No 503s, no stub fallbacks anywhere in the trace
   │    • UIState mirror fields all cleared

9. Re-scan verification
   ▼  POST /api/snapshot?url=...&query=...
   ▼  await done
   ▼  assert chunk count rebuilds identically to step 5
   ▼  assert pattern_map ChunkPatternSchemas regenerate identically (within stochastic UMAP wobble tolerance)
```

---

## §4 — WS frames + telemetry

| Frame | When | Assertion |
|---|---|---|
| `chunk_added` | During scan | Must arrive on workspace WS; count monotone |
| `umap_canonical` | Multiple during scan + at scan-end | 6-vector format; incremental cadence |
| `concept_changed` on `pattern_map` | Multiple during scan | Live schema build |
| `done` (success) | At scan-end | Confirms scan completed |
| `purge_workspace` | After purge | Workspace state cleared on frontend |
| (no `error` or 503 in the trace) | — | Real-stack contract holds |

---

## §5 — Acceptance bar

The probe passes when every assertion in §3 holds. The probe is a CI gate per [`ci_acceptance.md`](../code_constraints/ci_acceptance.md) — failed merge if the probe is red.

---

## §6 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| Scan ↔ streaming severance | §18.1 |
| `pattern_map` not live-updating | §18.29 |
| Old domains/URLs persist after purge | §18.4 |
| Agent outputs lost to manifold interior (if probe extended with agent emission) | §18.23 |
| Foundation fixture count drift on re-materialisation | §18.27 |
| Quiet fallback to stubs on subsystem failure | §13.4 |

---

## §7 — Code constraints

- [`streaming.md`](../code_constraints/streaming.md) — workspace-WS dual-routing on every payload.
- [`persistence.md`](../code_constraints/persistence.md) — cleanup contract (Kuzu shrink, TF-IDF zero, accessor clear).
- [`testing.md`](../code_constraints/testing.md) — probe runnable in real-stack mode; no fake-gate engagement.
- [`ci_acceptance.md`](../code_constraints/ci_acceptance.md) — probe gate per release.
- [`error_handling.md`](../code_constraints/error_handling.md) — no quiet degradation; subsystem failure surfaces as 503.

---

## §8 — Cross-features

- [`live_scan_streaming.md`](live_scan_streaming.md) — the streaming contract this probe asserts holds.
- [`pattern_map.md`](pattern_map.md) — the live-update target.
- [`6d_umap.md`](6d_umap.md) — the 6-vector format the `umap_canonical` frames carry.
- [`three_register_model.md`](three_register_model.md) — the loop the probe exercises end-to-end.
- [`four_fixture_api.md`](four_fixture_api.md) — `WebBrowser.scan` is the entry point.
