# pattern_map & url_set — Scanner Output & Multi-URL Input Panels

> **Status: realised (frontend core) — both pattern_map and url_set.** The two specialised concept panels of the scan workflow: the `pattern_map` output (§15.8.2) and the `{urls_panel}` URL-set aggregator (§15.7), both ordinary `ConceptView` + `FieldTree` panels under the signal-stream constraint. **`pattern_map` rendering is realised**: `concept_graph.js::_patternMapSignalPrint` renders a `type_hint="pattern_map"` node **one `pattern_hash` at a time** (§3.1.2 / §18.24 — never the flat all-patterns list), with golden-trio rows + sampled-chunk/sub-pattern counts, and `_attachPatternMapStepper` gives the ‹ i/N › stepper that swaps the visible pattern in place. Both fire the signal-stream mirror with **`field_path="pattern_hash"`** (now a first-class field on `/api/ui/signal_{stream,advance}` + `UIStateService`, REPL-verified) so peers + the §11.8 viewer track the position. The backend node it renders is built by the §15.8 pipeline (see [`../object_model/ChunkPatternSchema.md`](../object_model/ChunkPatternSchema.md)). **`url_set` rendering is also realised (frontend core)**: `concept_graph.js::_urlSetSignalPrint` renders a `type_hint="url_set"` node as the multi-line URL list (§2, editable at rest §3.2.1) with a ▸ cursor on the currently-iterated URL, and `_attachUrlSetStepper` gives the ‹ url i/N › + ▶/⏸ stepper that advances **one URL at a time** (§3.2.2 / §18.30 — never a bulk concatenated scan), driving the backend `RolloutCoordinator` with **`field_path="url"`** (REPL-verified: play→`paused=False`, step→`idx` advances, the signal entry carries `field_path="url"`). Both panels' play/pause runs through the §7.5 RolloutCoordinator (see [`../object_model/RolloutCoordinator.md`](../object_model/RolloutCoordinator.md)). **Open:** the sampled-chunk→fly+halo click (§3.1.4), the downstream single-cycling-readout under iteration (§3.1.5 / §O.11), `url_set` progressive materialisation of a clicked URL into a `{var}` compute node (§3.2.1), and wiring `{urls_panel}` into a scan `url` port for actual per-URL scan iteration (§3.2.2 backend).

---

## §1 — Identity

These are not special widgets — they are ConceptNodes (§3.1) rendered by the same `ConceptView` (`concept_view.md`) + `FieldTree` (`field_tree.md`) as everything else, specialised only by their data shape and type tag. **`pattern_map`** is `WebBrowser.scan`'s primary output: a live-updating recursive tree of chunk-pattern schemas (golden trio, sampled chunks, sub-patterns) under the signal-stream constraint over `pattern_hash` keys. **`url_set`** (`{urls_panel}`) is a user-created panel holding an evolving multi-URL list, referenced into a scan's `url` input port and iterated once per URL.

---

## §2 — Structure

Both are `panel`-mode `ConceptView`s whose `data` field-tree carries the specialised structure:

- **`pattern_map`** (`type_hint`-tagged): `data` = `{ <pattern_hash> → { url_root, generalized_xpath, golden_trio:{title,link,content}, sampled_chunks:[…], pagerank, sub_patterns:{…} } }`. The top-level `pattern_hash` map is `meta.iterable` (signal-stream over patterns).
- **`url_set`** (tag `url_set`): `data` = a multi-line pure-print list of URLs (tabs group sub-lists); referenced as `{urls_panel}`. The URL list is `meta.iterable` (signal-stream over URLs) when wired into a scan input.

**Owns:** nothing beyond a normal panel; structure is the `FieldTree`'s. **Reads:** `concepts[id].data`, `ui.signal_stream["id::pattern_hash"]` / `["scan_id::url"]`.

---

## §3 — Behaviours

### §3.1 pattern_map (§15.8.2, §18.29)
1. **Live during scan.** Each newly-detected pattern adds a top-level entry; each newly-sampled chunk appends to that pattern's `sampled_chunks`; PageRank refits incrementally; TF-IDF/nomic index so retrieval is usable the moment a chunk lands. Materialisation that waits for scan-end is the §18.29 violation; at least one `pattern_map` mutation is visible before `done`.
2. **Signal-stream over patterns (§4.6.1).** The `FieldTree` shows **one `pattern_hash` at a time**; advancing (`ui-signal-advance`) swaps the visible pattern's golden trio / sampled-chunks / sub-patterns in place. The full pattern set stays in the store; never a flat all-patterns list (§18.24).
3. **Golden trio (§15.8.1).** Each pattern's `(title, link, content)` are named field-tree rows; they gate content-precise extraction (joint-presence) on the backend; the frontend simply renders them as labelled rows.
4. **Click a sampled chunk → fly + halo (§8.5, §17.1.3).** Clicking a sampled chunk in the visible pattern flies the camera to that chunk and opens a halo around the focal (`halo.md`, `retrieval_and_sidebar.md`).
5. **One cycling readout under iteration (§O.11/§O.7).** When a downstream function iterates over `pattern_map.<hash>.sampled_chunks`, it shows the current sample's output in a *single* readout node (not one per sample); the sampled chunks themselves live in 3D and are referenced (§O.7), the panel rendering only the current signal's data.

### §3.2 url_set (§15.7, §17.1.4, §18.30)
1. **Progressive materialisation (§4.6).** The URL list sits as plain pure-print until the user clicks a URL; that URL becomes a single-key:value compute node with its own `{var}` slug (`field_tree.md` §6.2), growable into a fuller panel.
2. **Iterate once per URL, signal-stream (§17.1.4, §18.30).** When `{urls_panel}` is wired into a `WebBrowser.scan` `url` port, the scan fires **once per URL under the signal-stream constraint** — not in parallel, not as one bulk scan. The panel shows the currently-iterated URL's scan as the visible signal; the rollout stepper (`agent_and_rollout.md`) advances.
3. **URL-specific TF-IDF only (§15.7).** URLs vectorise through the TF-IDF axis with a url-specific tokenisation (split on `/ ? & = .`); they do **not** go to the nomic axis. (Backend concern; noted so the frontend never implies otherwise.)

---

## §4 — Composition

| Peer | Through |
|---|---|
| `ConceptView` / `FieldTree` | renders both panels; signal-stream gating |
| `scan_streaming.md` | `pattern_map` materialises live in parallel with the 3D stream |
| `agent_and_rollout.md` | the play/pause stepper advances the signal (pattern or URL) |
| `Halo` / `Projector` | sampled-chunk click → fly + halo |
| `GestureGateway` | `ui-signal-advance`, `web-scan` (wired via `{urls_panel}`), edit gestures |

---

## §5 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Advance pattern | `ui-signal-advance {card_id, field_path:"pattern_hash"}` | next pattern visible |
| Advance URL | `ui-signal-advance {scan_id, field_path:"url"}` | next URL's scan visible |
| Click sampled chunk | `ui-row-click` | fly + halo |
| Edit URL list | `field-tree-*` | grow the url_set |
| Wire `{urls_panel}` | `editor-overwrite {scan_node, data:"url:{urls_panel}"}` | per-URL iteration |

---

## §6 — Sequences

### §6.1 pattern_map iteration (§17.1.3)
```
scan completes → pattern_map ConceptNode materialised (live during scan)
ui-signal-advance {pattern_map_id, "pattern_hash"} → next pattern visible
   → FieldTree re-renders golden_trio + sampled_chunks + sub_patterns for the new pattern
   → click a sampled chunk → fly camera + open halo
   → downstream {pattern_map} consumer fires per visible pattern (recursion-over-iteration §12.2.1)
   → REPL viewer pattern-map row: "pattern <hash> @ <url_root> | trio=(title,link,content) | samples=N"
```
### §6.2 {urls_panel} expansion (§17.1.4)
```
scan node url port wired to {urls_panel}
compile → resolve {urls_panel} (type url_set, §15.9) → signal-stream takes over
   for each url: signal_index advances → scan sequence (scan_streaming.md) runs for that url
      → pattern_map accumulates schemas across URLs; chunks land at 6D positions
   on complete: signal_index=0 + final aggregate pattern_map
   → REPL viewer urls-panel row: "urls_panel=<slug> | url=i+1/N visible | chunks_cumulative=N"
```

---

## §7 — Data

**pattern_map reads:** `concepts[pattern_map_id].data` (schema tree), `ui.signal_stream`. **url_set reads:** `concepts[urls_panel_id].data` (URL list), `ui.signal_stream`. **Sends:** `ui-signal-advance`, edit gestures, the wired `web-scan`. **Receives:** `concept_changed` (live pattern_map updates), `ui_state_changed (signal_advance)`.

---

## §8 — Results

A live-updating pattern_map panel showing one pattern at a time with its golden trio and samples, and a url_set panel that drives per-URL iterated scans. Telemetry: `signal_stream["id::field"]` (index + total) drives the `pattern-map` and `urls-panel` viewer rows (§11.8).

---

## §9 — REPL Mirroring

`signal_stream` is a §10.5 mirror field; the full iteration position (which pattern / which URL, i of N) is legible **only** in the REPL viewer's `pattern-map` and `urls-panel` rows (§11.8) — never as an in-panel overlay (§18.24). REPL `ui-signal-advance` drives the same in-place signal swap a user's stepper would; the `live-scan-real-with-cleanup` probe (§16.5) asserts incremental pattern_map updates with a non-empty golden trio before `done`.

---

## §10 — Theme

Both are standard steel-on-black `ConceptView` panels (`concept_view.md` §10) with monospace pure-print field-trees (`field_tree.md` §10). Golden-trio row labels (`title`/`link`/`content`) render in `--text-dim`; their values in `--text-primary`. The signal-stream shows exactly one pattern/URL — the minimalist single-signal print, no list chrome. Sampled-chunk references are `{var}`-style `--text-primary` with a `--steel-700` underline; clicking flies to the 3D chunk (the exception-zone HSV node). No colour here except the inherited HSV when a sampled chunk's halo phantom is ray-projected (`halo.md`).

---

## §11 — References

- `DOMAIN_MODEL.md`: §15.7 (url-set panel), §15.8 (chunk-pattern schema), §15.8.1 (golden trio), §15.8.2 (pattern_map), §15.9 (type inheritance), §4.6.1 (signal-stream), §17.1.3/§17.1.4 (sequences); anti-goals §18.24/§18.29/§18.30.
- Object docs: [`../object_model/ChunkPatternSchema.md`](../object_model/ChunkPatternSchema.md), [`../object_model/PatternMap.md`](../object_model/PatternMap.md), [`../object_model/URLSetPanel.md`](../object_model/URLSetPanel.md).
- Peers: `concept_view.md`, `field_tree.md`, `scan_streaming.md`, `agent_and_rollout.md`.
