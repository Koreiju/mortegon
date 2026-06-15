# Feature: `pattern_map` (Live-Streaming Output)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §15.8.2 (`pattern_map` output), §15.8 (chunk-pattern schema), §15.8.1 (golden trio), §15.7 (URL-set panel), §15.9 (type inheritance), §1.2.1 verbatim, §17.1 (scan sequence), §17.1.3 (`pattern_map` iteration sequence).

**Status.** Realised. The `pattern_map` ConceptNode is built live by the §15.8 DOM pipeline (`backend/mapper/chunk_builder.py`: `extract_golden_trio`, `build_pattern_schemas`, `_compute_pattern_pagerank`) and the scanner emits per-pattern `update_pattern_map` frames incrementally (`backend/dom/pipeline.py`, §3.1 — not deferred to scan-end). The frontend renders it one `pattern_hash` at a time via `concept_graph.js::_patternMapSignalPrint` + `_attachPatternMapStepper` (the signal-stream display, `field_path="pattern_hash"`). Verified by `pattern-map-live-update` (full-smoke) + `scripts/probe_pattern_map.py` (golden-trio joint-presence gate §15.8.1 + live `pattern_map` node §15.8.2 + accessor-table reuse + pagerank>0).

---

## §1 — What the user sees

When the user fires a `WebBrowser.scan(url, query?)`, the scan produces (alongside the streaming chunks in the projector) a named output panel called `pattern_map` — a typed concept node whose `data` field carries a recursive tree of chunk-pattern schemas, one entry per detected pattern. Each entry shows the pattern's URL root, generalised xpath, golden trio (title / link / content), sampled chunks, PageRank, and any sub-patterns nested inside.

The `pattern_map` panel updates *live* as the scan streams — each newly-detected pattern adds a new top-level entry; each newly-sampled chunk per existing pattern appends to that pattern's `sampled_chunks`; PageRank refits incrementally over the chunk-pattern graph as new patterns and samples land. The user sees the patterns *appearing* during the scan, not just after.

The panel displays one pattern at a time under the signal-stream constraint (§4.6.1) — when the user iterates over the `pattern_hash` keys via the play/pause stepper, the visible signal is one pattern; pausing on a pattern lets the user click into its sampled chunks (each chunk being a `ChunkInstance` ConceptNode reachable from the pattern entry). When a downstream function consumes the `pattern_map` (a `Database.concept` walk over the sampled chunks, or an `Agent.prompt` whose template references golden-trio fields), the function fires per visible pattern under the same constraint, and the cascade composes the recursion-over-iteration tree.

The §1.5 framing places `pattern_map` at the boundary between Real and Imaginary — the chunks are observations from the Real (the open web), but the pattern schema is the Imaginary's structured abstraction of those observations.

---

## §2 — Cross-objects

| Object | Role |
|---|---|
| [`WebBrowser`](../object_model/WebBrowser.md) | The fixture whose `scan` produces the `pattern_map` |
| [`ChunkBuilder`](../object_model/ChunkBuilder.md) | Detects patterns, builds schemas, runs golden-trio extraction |
| [`ChunkPatternSchema`](../object_model/ChunkPatternSchema.md) | The typed tree entry per detected pattern |
| [`PatternMap`](../object_model/PatternMap.md) | The frontend panel renderer (under signal-stream constraint) |
| [`ConceptNode`](../object_model/ConceptNode.md) | The `pattern_map` is itself a ConceptNode whose `data` carries the schema tree |
| [`ConceptLifecycle`](../object_model/ConceptLifecycle.md) | Each pattern detection + sample append emits `concept_changed` on the `pattern_map` node |
| [`UIStateService`](../object_model/UIStateService.md) | `signal_stream` mirror tracks the visible `pattern_hash` |
| [`Database`](../object_model/Database.md) | Stores the `pattern_map` ConceptNode; the persistent accessor table cross-references the schemas |
| [`GlobalTfidfStore`](../object_model/GlobalTfidfStore.md) | The pattern band of multi-frequency PageRank reads from the chunk-pattern graph |

---

## §3 — Gestures

| Gesture | REPL action | Effect |
|---|---|---|
| Trigger a scan | `web-scan { url, query? }` | `pattern_map` materialises; live updates during scan |
| Advance pattern signal | `ui-signal-advance { card_id: pattern_map_id, field_path: "pattern_hash" }` | Next pattern visible; cascade re-fires consumers |
| Inspect a pattern's chunks | (click on `sampled_chunks` row → fly camera to chunk) | Camera tweens to chunk in projector; chunk's panel pins |
| Reference `pattern_map` downstream | (`{pattern_map}` in another card's data) | Downstream consumer iterates per signal-stream |

---

## §4 — State machine — live build + iteration

```
WebBrowser.scan fires
   │
   ▼
per emitted chunk (in ChunkBuilder):
   ▼  detect pattern_hash from generalised xpath
   ▼  if first detect:
   │     ▼  build fresh ChunkPatternSchema with url_root, generalised xpath, accessor_map
   │     ▼  run golden-trio extraction over first batch of members
   │     ▼  populate persistent accessor table for (domain, pattern_hash)
   │     ▼  insert schema as top-level pattern_map entry
   │     ▼  apply_update_lifecycle on pattern_map ConceptNode (modified)
   │     ▼  WS concept_changed
   │  else (re-detect):
   │     ▼  append chunk_id to schema's sampled_chunks
   │     ▼  re-fit PageRank incrementally over chunk-pattern graph
   │     ▼  apply_update_lifecycle (modified)
   │     ▼  WS concept_changed
   │
   ▼  detect sub-patterns recursively if pattern's members nest
   │
   ▼  frontend's PatternMap panel receives concept_changed; re-renders the visible pattern_hash
   │
   ▼  REPL viewer pattern-map row: "pattern <hash> @ <url_root> | trio=(title, link, content) | samples=<N>"

scan completes (done frame)
   │
   ▼
pattern_map ConceptNode's data field carries the final ChunkPatternSchema tree
   │
   ▼
user iterates: ui-signal-advance { card_id: pattern_map, field_path: pattern_hash }
   ▼  next pattern visible; cascade re-fires downstream consumers
   ▼  golden_trio fields, sampled_chunks list, sub_patterns tree all reflect the new pattern
   │
   ▼
user clicks a sampled_chunk in the visible pattern
   ▼  fly camera to chunk's position in projector
   ▼  pin chunk's knowledge panel via click-and-stick
   ▼  halo opens around the chunk's focal
```

---

## §5 — WS frames + telemetry

| Frame | Carries |
|---|---|
| `concept_changed` on pattern_map ConceptNode | The latest schema state (modified on every new pattern detection or sample append) |
| `ui_state_changed` (kind=signal_advance, card_id=pattern_map_id) | Current visible `pattern_hash` |
| `concept_changed` on downstream consumers | Re-fired compile values when the visible pattern advances |

REPL viewer `pattern-map` row shows the visible pattern's identity + golden trio + sample count.

---

## §6 — Acceptance bar

The `pattern_map` feature is realised when:

- A live `web-scan` produces a `pattern_map` ConceptNode that mutates *during* the scan (multiple `concept_changed` on the node before the `done` frame).
- The `pattern_map` data field carries the full ChunkPatternSchema tree at scan-end.
- The frontend panel displays one `pattern_hash` at a time under signal-stream; advancing the signal re-renders.
- Each schema entry carries a non-empty golden trio (verifiable by inspecting the data field).
- Clicking a `sampled_chunks` entry flies the camera to the chunk in the projector and pins the chunk's panel.
- The §16.5 probe asserts incremental `pattern_map` updates with at least one update before `done`.

---

## §7 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| `pattern_map` not live-updating during scan | §18.29 |
| Full-iterable rendering (all patterns visible at once) | §18.24 |
| Schema not linking back to chunk-pattern skeleton in the recursive tree | §15.8.2 spec |

---

## §8 — Code constraints

- [`backend_services.md`](../code_constraints/backend_services.md) — ChunkBuilder pattern detection + schema build invariants.
- [`ws_frames.md`](../code_constraints/ws_frames.md) — per-pattern `concept_changed` emission during scan.
- [`frontend_rendering.md`](../code_constraints/frontend_rendering.md) — PatternMap panel under signal-stream constraint.
- [`persistence.md`](../code_constraints/persistence.md) — schema lives inside `pattern_map` data field; one record table.

---

## §9 — Cross-features

- [`golden_trio.md`](golden_trio.md) — the joint-presence rule populating each schema entry.
- [`url_set_panel.md`](url_set_panel.md) — multi-URL scans accumulate schemas across the URL set.
- [`signal_stream.md`](signal_stream.md) — the iteration display rule the panel honours.
- [`type_inheritance.md`](type_inheritance.md) — downstream consumers inherit the chunk-pattern-schema type through `{var}` references.
- [`live_scan_streaming.md`](live_scan_streaming.md) — the `concept_changed` stream that drives the live updates.
- [`four_fixture_api.md`](four_fixture_api.md) — `WebBrowser.scan` is the producer.
