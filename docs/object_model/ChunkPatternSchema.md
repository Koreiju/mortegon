# Object: ChunkPatternSchema (`pattern_map` Entry)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §15.8 (chunk-pattern schema), §15.8.1 (golden-trio rule), §15.8.2 (`pattern_map` output), §15.4 (chunk emission discipline), §15.7 (URL-set panel), §5.4 / §8.7 (persistent accessor table).

**Status.** Realised (backend core) — `extract_golden_trio` (the §15.8.1 joint-presence gate) + the `ChunkPatternSchema` dataclass + `build_pattern_schemas` (recursive tree, sub-pattern nesting) live in `backend/mapper/chunk_builder.py`; `CompiledFromScansMaterialiser.update_pattern_map` upserts the single live `pattern_map` ConceptNode via an accretive merge (extend-don't-respawn, first-discovery `url_root` anchored) and is wired into `backend/dom/pipeline.py`'s persist branch — shared by both `run_pipeline` and the live-scan `run_pipeline_live`. Verified by `scripts/probe_pattern_map.py`. **Per-pattern-detection granularity (§3.1) is now wired**: `pipeline.py` emits `update_pattern_map` **once per detected top-level pattern** (a loop over the schema tree), so the node accretes one pattern at a time and each detection is a separately-visible mutation (§18.29 — patterns appear during the scan), on top of the per-snapshot/cross-URL accretion. The frontend renders it under the signal-stream constraint (`concept_graph.js::_patternMapSignalPrint` + stepper — one `pattern_hash` at a time, §4.6.1). The **chunk-pattern-graph `pagerank` (§2/§4) is now real**: `_compute_pattern_pagerank` runs a personalised PageRank over the pattern-containment graph (parent → sub_pattern edges) with the personalisation prior ∝ sampled-chunk count (the pattern↔chunk bipartite degree centrality), cached on each schema's `pagerank` (verified: prominent patterns outrank sparse ones, distribution sums to 1; `probe_pattern_map` asserts `> 0`). The **persistent accessor table (§2.2)** is realised at the data layer: each schema's `accessor_dict` carries the `(domain, pattern_hash)` accessor entry, and the accretive merge **reuses it across repeat scans** (the table is consulted/extended, not rebuilt — verified by `probe_pattern_map`: the `title`/`link`/`content` accessor entries persist unchanged after a second scan). The **skip-re-mining short-circuit (§2.2 / §7) is wired**: `_GOLDEN_TRIO_CACHE` keyed `(domain, pattern_hash)` caches each pattern's extracted golden trio + accessor map on first detection; on a repeat scan of the same domain (or later members of the same pattern) the trio is **reused, not re-mined** (verified: a second build over the same `(domain, pattern_hash)` runs **0** `extract_golden_trio` calls), and members are **tested against the cached trio** rather than re-extracted per member (the §7 anti-pattern guard). The legacy compiled-from-scans surface (§15.5) remains the `XPathPattern` baseline.

---

## §1 — What it is

The typed tree the scanner produces for each homogeneous repeating pattern (§15.4) it discovers during a scan. One ChunkPatternSchema per detected pattern; together the schemas form the `pattern_map` output panel of `WebBrowser.scan` (§15.8.2). Each schema carries the pattern's identity (a hash of its generalised xpath), the URL where it was first discovered (the schema's root — subsequent URL visits that match the same pattern *extend* the schema rather than spawning a new one), the generalised xpath, the accessor map (§8.7), the golden trio (§15.8.1), the most-recently-computed sampled chunks, the PageRank within the chunk-pattern graph, and a `sub_patterns` field for nested patterns (a card-grid pattern might have a card sub-pattern).

The §1.5 framing places ChunkPatternSchema in the **Real register** — it is the structured measurement of the world's repeating-element patterns. The Imaginary register reads it as a panel under signal-stream constraint (§4.6.1) for iteration.

---

## §2 — Shape

```python
@dataclass
class ChunkPatternSchema:
    pattern_hash:      str                              # hash of the generalised xpath
    url_root:          str                              # the URL where this pattern was first discovered
    generalized_xpath: str                              # /html/body/main/section/article (e.g.)
    accessor_map:      dict[field_slug, relative_xpath] # {title: "h3/text()", link: "a/@href", ...}
    golden_trio:       tuple[str, str, str]             # (title_slug, link_slug, content_slug)
    sampled_chunks:    list[chunk_id]                   # most-recently-computed sample set
    pagerank:          float                            # within the chunk-pattern graph
    sub_patterns:      dict[pattern_hash, "ChunkPatternSchema"]  # nested patterns inside this one
    domain:            str                              # domain extracted from url_root
    accessor_dict:     dict                             # persistent accessor table entry (§5.4)
    created_at:        str
    updated_at:        str
```

### §2.1 Golden trio (§15.8.1)

The three structurally load-bearing fields whose joint presence makes the pattern content-precise:

- **Title field** — highest-IDF text-bearing field across pattern members; preferred to be inside an `h1`/`h2`/`h3` or other heading-tagged subtree when one is present.
- **Link field** — an `<a href>` whose href is intra-domain and points to a resource rather than navigation; preferred to be the link the title field anchors.
- **Content field** — longest free-text-bearing field per pattern member; preferred to be a paragraph-shaped subtree.

The trio is co-extracted under joint-presence: a pattern member is included in `sampled_chunks` if and only if all three trio fields resolve cleanly (non-empty after distillation). The joint-presence rule filters out nav blocks, footers, sidebar widgets, and other repeating-but-uninteresting matches.

### §2.2 Persistent accessor table linkage (§5.4)

The `accessor_dict` field carries the persistent accessor table entry for `(domain, pattern_hash)`. On first discovery, the scanner populates this from observation; on subsequent visits to the same domain that match the pattern, the scanner consults the table first and short-circuits pattern rediscovery. The table is editable in the editor as an `XPathPattern` card (§8D.15); edits write back.

---

## §3 — Build lifecycle

### §3.1 Live incremental build

During a scan, `ChunkBuilder` (see [`ChunkBuilder.md`](ChunkBuilder.md)) detects homogeneous repeating patterns per §15.4. For each detected pattern:

1. **First-detect** — if `pattern_hash` is not yet in the workspace's `pattern_map`:
   - Create a fresh ChunkPatternSchema.
   - Set `url_root` to the current scan URL.
   - Run golden-trio extraction over the pattern's first batch of members.
   - Populate `accessor_map` from observation.
   - Update the persistent accessor table for `(domain, pattern_hash)`.
   - Insert the schema as a top-level entry in `pattern_map`.
   - Emit `concept_changed` on the `pattern_map` ConceptNode.
2. **Re-detect** (subsequent batches of the same pattern, or pattern matching a previously-seen `pattern_hash`):
   - Append new chunk_ids to `sampled_chunks`.
   - Re-run PageRank incrementally over the chunk-pattern graph.
   - Re-emit `concept_changed`.
3. **Sub-pattern detection** — if a pattern's members contain nested repeating sub-structures, recursively build sub-pattern schemas and attach them under `sub_patterns`.

The live incremental build is what makes the `pattern_map` output panel update *during* the scan (§18.29 anti-goal guard).

### §3.2 Schema persistence

The schema lives inside the `pattern_map` ConceptNode's `data` field as a structured tree. On scan completion, the schema's `sampled_chunks` reflects the final set; the user can continue iterating over it via the signal-stream mechanism (§4.6.1).

### §3.3 Cross-URL pattern extension

When a subsequent scan of a different URL produces chunks matching an existing `pattern_hash` (i.e., the same structural family appears on a sibling page), the existing schema is extended — `url_root` stays the same (first-discovery anchor), but the `sampled_chunks` grow. The persistent accessor table avoids re-discovering the pattern; the workspace's accumulated structural-knowledge cache (§5.4) is what makes this efficient.

---

## §4 — Persistence

| Artefact | Storage |
|---|---|
| `pattern_map` ConceptNode (carries the schema tree in its `data` field) | Kuzu |
| `ChunkPatternSchema` instances | Inside the `pattern_map` ConceptNode's `data` JSON |
| `sampled_chunks` chunk_ids | References to ChunkInstance ConceptNodes in Kuzu |
| Persistent accessor table entries | Kuzu, keyed by `(domain, pattern_hash)` |
| PageRank scores | Re-derivable from the chunk-pattern graph; cached in the schema's `pagerank` field |

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ChunkBuilder.md`](ChunkBuilder.md) | Builds the schemas during scan; runs golden-trio extraction |
| [`WebBrowser.md`](WebBrowser.md) | `scan` returns the `pattern_map` ConceptNode containing the schemas |
| [`PatternMap.md`](PatternMap.md) | Frontend panel renderer displays the schemas under signal-stream constraint |
| [`Database.md`](Database.md) | Stores the schemas + the persistent accessor table |
| [`ConceptIndexService.md`](ConceptIndexService.md) | The pattern band of multi-frequency PageRank reads from the chunk-pattern graph |
| [`URLSetPanel.md`](URLSetPanel.md) | Multi-URL scans accumulate schemas across the URL set; `url_root` attribution flows through |
| [`UIStateService.md`](UIStateService.md) | `signal_stream` mirror tracks which `pattern_hash` is currently visible |

---

## §6 — Cross-references

- Feature touchpoints — [`features/pattern_map.md`](../features/pattern_map.md), [`features/golden_trio.md`](../features/golden_trio.md), [`features/url_set_panel.md`](../features/url_set_panel.md), [`features/type_inheritance.md`](../features/type_inheritance.md).
- Code constraints — [`persistence.md`](../code_constraints/persistence.md) (schema storage), [`backend_services.md`](../code_constraints/backend_services.md) (ChunkBuilder ownership).
- Sequence reference — DOMAIN_MODEL §17.1.3 (pattern_map iteration), §17.1.4 ({urls_panel} expansion accumulates across URLs).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Materialising `pattern_map` only at scan-end | §18.29 violates live-update contract | Per-pattern incremental schema build emits `concept_changed` per detection |
| Including a chunk in `sampled_chunks` that fails the golden-trio joint-presence | False-positive pattern members would pollute downstream consumers | ChunkBuilder gates on trio presence before appending to `sampled_chunks` |
| Spawning a new schema for an existing `pattern_hash` instead of extending | Breaks cross-URL attribution and the persistent accessor table's reuse | First-detect check on `pattern_hash`; subsequent matches extend |
| Rendering the full schema tree at once in the panel | §18.24 / §4.6.1 violates signal-stream | Frontend reads `signal_stream` and renders one `pattern_hash` at a time |
| Storing the schema in a separate table outside the `pattern_map` ConceptNode | Breaks the one-record-table rule | Schema lives inside the `pattern_map` ConceptNode's `data` field |
| Letting the persistent accessor table fall out of sync with the schema's `accessor_map` | Cross-domain pattern reuse breaks | Schema and table updates are atomic |
| Re-running golden-trio extraction on every member (rather than on the first batch) | Wasteful; the trio is structurally stable once extracted | Trio extraction runs on the first detected batch; later members are tested against the trio for inclusion |
