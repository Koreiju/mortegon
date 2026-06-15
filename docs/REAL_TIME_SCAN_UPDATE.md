# Unified Real‑Time Chunk Scanning and Streaming Architecture

> **⚠ Status: HISTORICAL ANALYSIS-PLAN — SUPERSEDED (2026-05-30, see `USER_REQUIREMENTS_VERBATIM.md` §O.17).** This streaming-architecture plan describes the now-discarded codebase; the canonical design (live scan streaming, UMAP layout, the §18.1 severance fix) lives in [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) §10 / §6 / §18.1 + the [`frontend/`](frontend/) suite (`scan_streaming.md`, `frame_bus.md`). The `CODEBASE_GAP_ANALYSIS.md` it references is likewise historical. Consult for historical reasoning only.

> **Doc precedence (added 2026-05-27):** Source-of-truth requirements live in
> [`docs/USER_REQUIREMENTS_VERBATIM.md`](USER_REQUIREMENTS_VERBATIM.md). Any
> reference to a Fibonacci-style frontend layout below describes the legacy
> code path that the gap analysis in
> [`docs/CODEBASE_GAP_ANALYSIS.md`](CODEBASE_GAP_ANALYSIS.md) Part 1.4
> identifies as needing replacement by UMAP-as-primary + hash-direction
> placeholder transient. The current authoritative layout pipeline is the
> UMAP-linear-radial force-directed hybrid (§9 of the domain model).

## 1. Overview

This document describes the complete design for a **single‑pass, delta‑driven extraction and chunking pipeline** that scans a live web page and streams content‑complete chunks to a 3D GUI in real time. The architecture combines three traditionally separate stages—**content detection**, **chunk boundary determination**, and **instance grouping**—into **one recursive JavaScript extraction script** that runs inside the browser on each scroll iteration. Python receives the pre‑processed data, maintains lightweight incremental indexes, and performs **bottom‑up chunk assembly** only on the nodes that have actually changed. The resulting chunks are emitted as deltas (`added`, `replaced`, `removed`) over a WebSocket, allowing the frontend to update its 3D view with sub‑second latency.

The design explicitly addresses all requirements discussed:

- **Real‑time extraction** – millisecond‑scale per‑iteration processing by moving the majority of work onto the browser’s native C++ DOM engine.
- **Complete content coverage** – every detectable content type (text, URLs, media, interactive elements, embedded JSON) is catalogued, with a precise definition of what contributes to the chunk’s *character budget*.
- **Recursive chunking** – a bottom‑up walk from deepest content leaves, guided by a configurable context‑window budget and a commutation count that automatically groups repeated structural patterns (cards, list items, etc.).
- **Intelligent fingerprinting** – each DOM node carries a `content_hash` that encodes the *actual content structure* of its subtree, enabling the system to detect when two pattern instances are truly identical and when divergent sub‑structures require a split.
- **Delta streaming** – the frontend receives only the changes, never a full rebuild, and positions spheres using a deterministic Fibonacci‑hash from the instance identifier, eliminating server‑side layout computation entirely.

The document is written as a **self‑contained blueprint** for implementation, covering every detail from the in‑browser JavaScript traversal to the Python chunker and the WebSocket interface.

---

## 2. Domain Concepts and Terminology

| Term | Definition |
|------|------------|
| **Content‑distilled DOM** | The subset of the page DOM consisting only of nodes that carry human‑perceivable information (text, links, media, interactive widgets, metadata). Structural wrappers (`div`, `span` without content) are kept only as ancestry connectors. |
| **Generalized XPath** | An absolute XPath with index suffixes removed below `PATTERN_ANCHOR_DEPTH`. Segments above the anchor are kept verbatim to disambiguate page regions. `/html/body/main/div[2]/ul/li[3]/a` → `/html/body/main/div/ul/li/a` (anchor=3). |
| **Pattern** | Synonym for a region-anchored generalized XPath; the primary grouping key for structurally equivalent nodes within the same page region. |
| **Subtree Text Budget** | The total count of characters that are *prose‑relevant* within a subtree – visible text, accessible labels, interactive element descriptions, metadata, and embedded JSON. Explicitly excluded: raw URLs, media source strings, decorative whitespace. Computed from direct `Text` child nodes only, never `el.textContent`. |
| **Content Hash** | A 32‑bit rolling hash that fingerprints the *content signature* of a node and all its descendants. Used for delta detection and intra‑pattern homogeneity checks. |
| **Content Leaf** | The deepest node in the tree that has any detectable content (non‑empty `content_fields`) and whose children are all content‑less. Determined via the `hasContent` boolean propagated upward during the JS walk. |
| **Commutation Count** | The number of absolute XPaths that share the same generalized pattern. A count of 1 signals a unique structure; higher counts indicate repeated templates that can form a single chunk. |
| **HARD_CHAR_LIMIT** | The maximum character length of a chunk’s rendered content‑structure summary, acting as the budget for the recursive walk. Default 2048 (≈512 tokens). |
| **Fingerprint Consistency** | Equality of `content_hash` values across all instances of a pattern. Equal hashes → homogeneous. Unequal and `STRICT_HASH_MATCH=True` → split. Unequal and `STRICT_HASH_MATCH=False` → fall back to key-schema comparison. |
| **Landmark Anchor** | The nearest ancestor with a semantic landmark role (`<main>`, `<nav>`, `<header>`, `<footer>`, `<aside>`, `role="navigation"`, etc.) used to prefix the pattern key and prevent cross-region collisions. |
| **Verified Delta** | A batch of newly added/updated DOM nodes that the scanner has confirmed as stable (no further mutations at the same patterns in the subsequent scroll). Only verified deltas trigger chunk re‑evaluation. |
| **Chunk Ledger** | A per‑snapshot record of which absolute XPaths have already been consumed by a chunk, preventing double‑inclusion and enabling incremental updates. |
| **`_claimed`** | Reverse index of the chunk ledger: maps each consumed absolute XPath to its owning `chunk_id`. Enables O(1) leaf-claim checks without scanning all chunks. |
| **`instance_id`** | The `chunk_id` itself, used as the deterministic seed for Fibonacci sphere placement in the frontend. One sphere per chunk; its position is fully determined by `chunk_id` without any server-side coordinates. |
| **Chunk Ordinal** | A 0-based integer that distinguishes multiple chunks sharing the same pattern (produced by splits). Assigned by sorting split-cluster representative xpaths lexicographically and numbering them 0, 1, 2, … Stable as long as the split clustering is deterministic. |

---

## 3. System Architecture

The pipeline consists of **four layers**:

```
┌──────────────────────────────────────────────────────────────────┐
│                        Selenium / CDP                           │
│                                                                  │
│  1. Scroll + MutationObserver settle                            │
│  2. Execute EXTRACT_CHUNK_DATA_JS (pass prev_hashes map)        │
│     → walks full shadow DOM once                                 │
│     → returns {nodeMap (changed nodes only), leaves}             │
│  3. Python builds/updates master tree from nodeMap              │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Python Mapper (per snapshot)                 │
│                                                                  │
│  • _tag_cache (xpath → _meta dict)                               │
│  • _pattern_index (region-anchored gen_xpath → Set[abs_xpath])  │
│  • _chunk_ledger (chunk_id → Set[abs_xpath])                     │
│  • _claimed (abs_xpath → chunk_id)          ← reverse index     │
│  • _sorted_xpaths (SortedList[str])         ← bisect descent.   │
│  • _pattern_chunks (gen_xpath → List[Chunk])                    │
│  • _summary_cache (rep_xpath → content_fields dict)             │
│                                                                  │
│  On each verified delta:                                         │
│    a) Update caches (O(|delta|))                                 │
│    b) Evict removed xpaths from all indexes                      │
│    c) Execute BottomUpChunker on dirty patterns                  │
│    d) Emit chunk events (added / replaced / removed)             │
└─────────────┬────────────────────────────────────────────────────┘
              │ (chunk_added / chunk_replaced / chunk_removed)
              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    SnapshotPipeline (queue‑based)                │
│                                                                  │
│  Fast path → WebSocket (raw chunks, instance_id = chunk_id)     │
│  Background → TF‑IDF index, kuzu persist                         │
└─────────────┬────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  3D GUI (chunk_projector.js)                    │
│                                                                  │
│  • addNodesIncrementally (Fibonacci sphere, seed = chunk_id)    │
│  • chunk_replaced: update sphere in-place (same position)       │
│  • chunk_removed: remove sphere                                  │
│  • billboards lazy‑fetched on click via /api/chunk_details/{id} │
└──────────────────────────────────────────────────────────────────┘

```

**Key design decisions**:

- **No separate distill step** – content detection and chunk budgeting are fused into the JS extraction.
- **Hash-diff transport** – the JS script accepts the previous `content_hash` map from Python and returns only nodes whose hash changed, eliminating the JSON payload bottleneck on subsequent scrolls.
- **Layout is client‑side** – the frontend places spheres by Fibonacci hash seeded with `chunk_id`. No coordinates are sent from the backend. `instance_id = chunk_id`, which is stable across scroll iterations.
- **TF‑IDF and embedding** happen **asynchronously in the background**, never blocking the live stream.
- **`ChunkAbsorber` is superseded** – the existing `ChunkAbsorber` class and `_process_distill` flow are replaced by `_process_delta` + `BottomUpChunker`. `ChunkAbsorber` should be removed from `chunk_absorber.py` once the new pipeline is verified end-to-end.

---

## 4. Single‑Pass JS Extraction (`EXTRACT_CHUNK_DATA_JS`)

The script is injected via `driver.execute_script` and operates on the live page. It is the **single source of truth** for all per‑node content information.

### 4.1 Traversal and Shadow DOM

The function `extractChunkData(root)` recursively walks the DOM starting from `document.documentElement`. For each element:

1. If the element has a `shadowRoot`, it is traversed as well; shadow children are treated as a separate child list but their text and budgets are merged upward. Shadow children are assigned XPaths of the form `/host-xpath/#shadow-root/child-tag[N]`.
2. Elements inside `<head>`, `<style>`, or non‑JSON‑LD `<script>` are skipped entirely (they are not content‑bearing).
3. Visibility check is applied **only to known structural containers** (block-level elements: `div`, `section`, `article`, `nav`, `aside`, `header`, `footer`, `main`, `ul`, `ol`, `table`). `getComputedStyle` is skipped for inline elements, media elements, and interactive elements that are always content-bearing regardless of computed style, avoiding the per-node style recalculation cost on the majority of the DOM.
4. Void elements (`<img>`, `<br>`, `<input>`, etc.) have no children.
5. A maximum depth of 100 prevents infinite recursion.

**XPath construction**: Absolute XPaths require sibling indices. At each node, the script counts preceding siblings with the same `tagName` to compute the 1-based index, producing `/html/body/div[2]/ul/li[3]` rather than `/html/body/div/ul/li`. Shadow-root children use `#shadow-root` as a literal path segment. The generalized xpath (used as a pattern key) is derived by stripping all `[N]` indices from the absolute path.

**Text extraction**: Direct text content is read from `childNodes` filtered to `Node.TEXT_NODE`, *not* from `el.textContent`. Using `textContent` would capture all descendant text recursively, causing every character to be counted once per ancestor level and inflating the budget by up to the element’s depth. Only direct text nodes of the current element contribute to that node’s own budget; descendant text is already accounted for in the children’s `budget` values.

The recursion returns for each node:
- Its own direct properties (tag, absolute xpath, attributes, direct text).
- Aggregated values from children: `subtree_text_budget`, `hasImage`, `hasVideo`, `hasAudio`, `hasInteractive`, the child list’s content hashes.
- A `hasContent` boolean indicating whether this node or any child has non-empty `content_fields`, used for leaf detection.

### 4.2 Content Detection and Classification

At each node, the script determines the **content categories** present, following the same rules as the Python `ContentTagger` (see §5 Content Detection Reference). The categories are:

- **text.visible** – from direct text nodes (non‑whitespace).
- **text.accessible** – from `alt`, `title`, `aria-label`, `placeholder`, etc.
- **text.metadata** – from `<meta content>`, `datetime` attributes, `data-title`, etc.
- **urls.internal / external / resource** – from `href`, `src`, `srcset`, `action`, `poster`, `data‑*`, inline `style` backgrounds, and any attribute containing a URL‑like string.
- **media.images / video / audio / archives** – based on the element’s tag (`<img>`, `<video>`, `<audio>`, etc.) and the extension of URL attributes.
- **interactive** – `<a>`, `<button>`, `<input>`, `<select>`, `<textarea>`, `role="button"`, `onclick` attributes, etc.
- **json_data** – `<script type="application/ld+json">` or `data-*` attributes that parse as valid JSON.

The detection uses the same regex patterns and extension sets as the Python code, hard‑coded in the JS script for performance. When possible, it reuses the already‑walked DOM to avoid redundant `getAttribute` calls.

### 4.3 Budget Calculation (`subtree_text_budget`)

The budget is an integer counter that accumulates **only characters that contribute to the knowledge panel and SLM context**, i.e., the sum of the lengths of the rendered text for the categories that would appear in the content‑structure summary. The exact rule:

- **Include**: `text.visible`, `text.accessible`, `text.metadata`, `interactive` descriptions (but not empty tags), `json_data` contents (trimmed to fit).
- **Exclude**: `urls.*` (including `href` and `src` strings), `media.*` (the URL itself), completely empty interactive markers.

To compute the budget for a leaf element, we concatenate all qualifying text pieces (from direct `Text` child nodes and qualifying attributes) separated by a single space and sum the length. For an element with children, the budget is the sum of the budgets of its children plus its own **direct** text only — never `el.textContent`, which would double-count descendant contributions.

The budget is **not** the full HTML length; it is the compact rendered summary that the chunker’s `_format_summary` would produce. This ensures that the budget directly corresponds to the token count the SLM will later see.

### 4.4 Content Field Extraction

For each node, the script builds a dictionary of **relative addresses → values** that mirrors the `extraction_trie` leaf values:

```
{
  "text()":       "The Fool",
  "@href":        "/cards/the-fool",
  "@data-label":  "Breadcrumb:EXPLORE TAROT.COM",
  "img/@src":     "https://.../fool.jpg"
}
```

Only attributes with non‑empty strings are included; values longer than 80 characters are truncated (the full value is preserved in the DOM). Duplicate keys (e.g., multiple `@href` from different children) are not aggregated at this stage; the node only carries its own direct attributes. The bottom‑up chunker will later gather child addresses when building the summary.

For text nodes, the address is `text()`. For attributes, the address is `@attrname`. For shadow‑root children, the address is relative to the host.

This pre‑extraction provides everything needed for fingerprinting and chunk rendering without needing another DOM walk.

### 4.5 Content Fingerprint (`content_hash`)

To enable fast equivalence checks, each node receives a **32‑bit rolling hash** computed as:

```
content_hash = hash(sort_keys(content_fields), truncated_values)
for each child:
    content_hash ^= rotate_left(child.content_hash, 7)
```

The initial hash uses a simple FNV‑1a or DJB2 algorithm on the concatenation of sorted keys + first 20 chars of each value. The XOR‑rotate pattern with children ensures that any change in any descendant propagates up to the root.

This hash serves two purposes:
1. **Delta detection** – by comparing the hash of a node in the current capture with the stored hash from the previous iteration, the Python layer instantly knows whether the node’s content changed.
2. **Pattern homogeneity** – when forming a chunk, we compare the hashes (or a derived “fingerprint set”) of all instances of the pattern. If they differ beyond a threshold, the pattern is structurally heterogeneous and must be split.

### 4.6 Output Format

The script returns a **tree-structured** JSON object where every node carries a `_meta` property containing its content data. This unified format serves two purposes: the tree structure is used by the scanner's existing merge/dedup algorithm (requiring parent-child links and sibling order), while Python extracts the `_meta` fields to populate the flat `_tag_cache` and `_pattern_index` without a second DOM traversal.

```json
{
  "tagName": "li",
  "xpath": "/html/body/div[2]/ul/li[1]",
  "children": [...],
  "shadowRoot": null,
  "_meta": {
    "subtree_text_budget": 342,
    "has_image": true,
    "has_audio": false,
    "has_video": false,
    "has_interactive": true,
    "content_fields": {
      "text()": "The Fool",
      "a/@href": "/cards/the-fool",
      "img/@src": "https://.../fool.jpg"
    },
    "content_hash": "0xA3F2C1D4"
  }
}
```

At the top level, the script also returns a flat `leaves` array of absolute XPaths for all content leaves (deepest nodes with `content_fields` non-empty and no content-bearing children). Leaf detection uses the `hasContent` boolean returned up the recursion — not a check on `c.fields`, which would be undefined in the walk return value.

```json
{
  "tree": { ... },
  "leaves": [
    "/html/body/div[2]/ul/li[1]/a",
    "/html/body/div[2]/ul/li[2]/a",
    ...
  ]
}
```

**Hash-diff transport optimization**: The JS script accepts a `prevHashes` parameter — a plain JS object mapping `xpath → content_hash` from the previous iteration. When computing each node, if `hash === prevHashes[xpath]`, the node is not added to `nodeMap`. Python only receives nodes that actually changed, reducing subsequent-scroll payload from ~10MB to typically a few KB. On the first call, pass an empty object `{}`.

```javascript
// Invocation from Python:
// result = driver.execute_script(EXTRACT_CHUNK_DATA_JS, prev_hashes_dict)
// Arguments[0] = prevHashes
```

Python retains the `tree` object in memory as the **master tree** — used solely for lazy billboard serialization (`/api/chunk_details/{id}`) and never re-walked for scanning or chunking. The flat `_tag_cache` is populated by traversing `_meta` from changed nodes only. The master tree is updated by merging the new `nodeMap` into it using the existing scanner merge logic.

### 4.7 Shadow‑Root XPath Boundary Handling

When the bottom-up chunker ascends via `parent_xpath(current)` and the resulting ancestor segment is `#shadow-root`, that segment has no meaningful `subtree_text_budget` in `_tag_cache` and its generalized pattern would contain the literal `#shadow-root` string, making it appear unique (count=1) and forcing an early stop.

**Rule**: When `parent_xpath(current)` resolves to a `#shadow-root` node, skip it transparently and use `parent_xpath(parent_xpath(current))` — the shadow host element — as the effective ancestor. The host element's `subtree_text_budget` already aggregates the shadow subtree (merged upward during the JS walk), so the budget check remains correct. The chunk's `representative_xpath` may then point outside the shadow root, which is valid since the shadow subtree is already included in the chunk's member set.

---

## 5. Content Detection Reference

The following table enumerates every content category and subcategory, the detection method, and the attributes/elements scanned. This is the **canonical vocabulary** that both the JS extraction script and the Python chunker rely on.

| Category | Subcategory | Detection Method | Attributes / Context |
|----------|-------------|------------------|----------------------|
| **urls** | internal | URL regex on attribute values, plus explicit `href`, `src`, `action`, `poster`, `data-*`, `cite`, `longdesc` | All attributes except skip‑list |
|          | external | Same regex; explicit URL‑bearing attributes | |
|          | resource | `data:` / `blob:` URI prefix | |
| **media** | images | `<img>`, `<picture>`, `<svg>`, `<canvas>`, `<input type="image">`, CSS `background-image`; extension check (`.png`, `.jpg`, `.gif`, `.svg`, `.webp`, `.ico`, `.avif`, `.bmp`, `.tiff`, `.tif`, `.apng`, `.jfif`, `.pjpeg`, `.pjp`); `data:image/` prefix | `src`, `srcset`, `data-src`, `data-lazy-src`, `data-original`, `data-image`, `poster`, inline `style` |
|          | video | `<video>`, `<source>`, `<track>`; extension (`.mp4`, `.webm`, `.ogg`, `.ogv`, `.mov`, `.avi`, `.mkv`, `.flv`, `.wmv`, `.m4v`, `.3gp`, `.ts`, `.m3u8`); `data:video/` | same attributes as above |
|          | audio | `<audio>`; extension (`.mp3`, `.wav`, `.flac`, `.ogg`, `.oga`, `.aac`, `.wma`, `.opus`, `.m4a`, `.mid`, `.midi`); `data:audio/` | |
|          | archives | Extension (`.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, `.tgz`, `.cab`, `.iso`, `.dmg`) | |
| **text** | visible | Direct text nodes, element‑level text for inline containers | N/A |
|          | accessible | `alt`, `title`, `aria-label`, `aria-labelledby`, `aria-describedby`, `placeholder`, `aria-roledescription`, `aria-valuetext`, `label`, `summary`, `caption`, `abbr`, `acronym` | |
|          | metadata | `<meta content>`, `datetime` attribute, `data-title`, `data-description`, `data-tooltip`, `data-caption`, etc. (see `_META_TEXT_ATTRS` in content_tagger.py) | |
| **interactive** | inputs, buttons, links, forms, event handlers | Tag names `<input>`, `<textarea>`, `<select>`, `<button>`, `<a>`, `<form>`; `role` attribute in `_INTERACTIVE_ROLES` set; `contenteditable`; `onclick`, `onsubmit`, etc. | |
| **json_data** | ld_json | `<script type="application/ld+json">` | |
|              | data_attrs | Any `data-*` attribute that parses as valid JSON | |
|              | inline | (future: script blocks) | |

**Excluded attributes** (never scanned for URLs or text): `style`, `class`, `id`, `width`, `height`, `viewbox`, `d`, `fill`, `stroke`, etc. (see `_SKIP_ATTRS` and `_SKIP_ATTR_PREFIXES` in content_tagger.py).

---

## 6. Python‑Side Data Management

For each snapshot, the mapper holds four structures in memory. They are never written to disk during a scan; persistence happens only at the end.

### 6.1 Per‑Snapshot Indexes

| Index | Python Type | Key | Value | Lifecycle |
|-------|-------------|-----|-------|-----------|
| `_tag_cache` | `Dict[str, dict]` | absolute XPath | The `_meta` dict from JS extraction (budget, fields, hash, flags) | Updated on initial capture; patched on deltas by replacing entries whose `content_hash` changed |
| `_pattern_index` | `Dict[str, Set[str]]` | generalized XPath pattern | Set of absolute XPaths matching this pattern | Built once on first iteration; on subsequent deltas, new XPaths are added to the appropriate set |
| `_chunk_ledger` | `Dict[str, Set[str]]` | chunk_id | Set of absolute XPaths **consumed** by this chunk (the member xpaths + all their descendants) | Updated when a chunk is created, replaced, or removed |
| `_claimed` | `Dict[str, str]` | absolute XPath | The `chunk_id` that owns this xpath | **Reverse index of `_chunk_ledger`**. Enables O(1) leaf-claim checks; maintained in sync with `_chunk_ledger` |
| `_sorted_xpaths` | `List[str]` | — | Sorted list of all absolute XPaths in `_tag_cache` | Enables O(log N + descendants) prefix scan for descendant enumeration via `bisect` |
| `_pattern_chunks` | `Dict[str, List[Chunk]]` | generalized XPath pattern | List of `Chunk` objects currently covering this pattern. Normally 1 per pattern; multiple if a split occurred | Mutated by chunk events: added, replaced, or removed |

**Descendant enumeration**: When marking a chunk's descendants as consumed, use `bisect.bisect_left(_sorted_xpaths, mxp + '/')` to find the start of the descendant range, then scan forward while the prefix matches. This is O(log N + |descendants|) rather than a full-table scan.

### 6.2 Delta Integration and Cache Coherence

When a verified delta arrives, the `_process_delta` function in the mapper performs two phases:

**Phase 1 — Evict removed nodes** (xpaths present in `_tag_cache` but absent from the new full nodeMap):
1. Compute `removed_xpaths = set(_tag_cache.keys()) - set(new_nodeMap.keys())`.
2. For each `xp` in `removed_xpaths`: remove from `_tag_cache`, `_pattern_index[generalize(xp)]`, `_sorted_xpaths`, and `_claimed`.
3. Any chunk that contained a removed xpath in its `member_xpaths` is marked dirty (its pattern goes into `_dirty_patterns`).

**Phase 2 — Integrate new/changed nodes**:
1. Iterates over the new `nodeMap` (which contains only changed nodes due to hash-diff transport).
2. For each node, compares `content_hash` with the stored hash in `_tag_cache`. If equal, skip.
3. If different or new, updates `_tag_cache`, inserts into `_sorted_xpaths` via `SortedList.add()`, and adds the xpath to `_dirty_xpaths`.
4. Also updates `_pattern_index[generalize(xpath)]`.
5. After processing all new nodes, collects `_dirty_patterns` — all patterns that contain any dirty or removed xpath.
6. For each dirty pattern, invalidates existing chunks by removing them from `_pattern_chunks` and `_chunk_ledger`. Corresponding `_claimed` entries are cleared. Prior `chunk_removed` events are staged.
7. Runs `BottomUpChunker` on `_dirty_patterns`. New chunks produce `chunk_added` or `chunk_replaced` events.
8. Emits all staged events as an atomic batch to the WebSocket.

**Memory management**: At URL navigation or snapshot teardown, all indexes (`_tag_cache`, `_pattern_index`, `_chunk_ledger`, `_claimed`, `_sorted_xpaths`, `_pattern_chunks`, `_summary_cache`, master tree) are cleared and garbage-collected. Indexes are per-snapshot lifetime only.

This ensures that only patterns actually touched by the delta are re‑evaluated, and that DOM removals are handled without stale entries polluting subsequent chunk formations.

---

## 7. Bottom‑Up Recursive Chunking Algorithm

### 7.1 Algorithm Inputs

- `dirty_patterns` – set of generalized XPaths whose member set or content changed.
- `leaves` – global list of content leaves (updated when new nodes arrive).
- `_tag_cache`, `_pattern_index`, `_chunk_ledger`.

### 7.2 Main Loop (Leaf → Ancestor Walk)

For each dirty pattern, we collect all content leaves that belong to that pattern (i.e., leaves whose generalized XPath starts with the pattern). For each such leaf `L` that is **not** claimed in `_chunk_ledger`:

1. Let `current_xpath = L`.
2. While `depth(current_xpath) > 0`:
   - Let `ancestor = parent_xpath(current_xpath)` (derived by stripping the last path segment).
   - Look up `ancestor` in `_tag_cache` to retrieve its `subtree_text_budget`.
   - If `subtree_text_budget > HARD_CHAR_LIMIT` → **stop** (budget exceeded). The previous `current_xpath` is the chunk root.
   - Let `pattern = generalize(ancestor)` and `count = len(_pattern_index[pattern])`.
   - If `count == 1` → **stop** (unique structure). Use `current_xpath`.
   - **Fingerprint check**: compute the content fingerprint for ALL instances of `pattern` using `_tag_cache` (see §7.4). If fingerprints diverge, **stop** – the pattern is heterogeneous; use `current_xpath`.
   - Otherwise, set `current_xpath = ancestor` and continue upward.
3. When the loop stops, `current_xpath` is the **chunk representative xpath**. The chunk pattern is `generalize(current_xpath)`.

### 7.3 Budget and Commutation Checks

- **Budget check**: At each candidate ancestor, compare `_tag_cache[ancestor]['subtree_text_budget']` against `HARD_CHAR_LIMIT`. Note that this is the **aggregate** budget of the ancestor's entire subtree — all children combined. The check therefore asks "is this ancestor too large to serve as a chunk root?", not "is the representative instance too large?". For most pages this is the right conservative bound; a `<section>` containing 10 cards would have a 10× aggregate budget, correctly preventing the section from becoming a single chunk. If the ancestor's aggregate budget is still under the limit, the walk continues upward.
- **Commutation count** is read from `_pattern_index`. A count of 1 indicates the node is structurally unique; grouping it with nothing would create a 1‑member chunk, which is allowed but signals that we should not walk further (since the parent would also be unique).
- **Special case**: If the leaf itself has `subtree_text_budget > HARD_CHAR_LIMIT`, it becomes a single‑member chunk at that leaf (a large paragraph).

### 7.4 Structural Heterogeneity Detection (Fingerprint Consistency)

Pattern instances are considered structurally equivalent if and only if their `content_hash` values are **identical**.

```python
def pattern_is_consistent(pattern, pattern_index, tag_cache):
    hashes = {tag_cache[xp][‘content_hash’] for xp in pattern_index[pattern]}
    return len(hashes) == 1
```

The `content_hash` was designed specifically for this purpose (§4.5): it rolls up the entire subtree’s content signature, not just the node’s own `content_fields`. Using `content_fields` directly for this check would fail for ancestor nodes whose own fields are empty but whose children differ — the difference is only visible in the rolled-up hash.

**Why not Jaccard on `content_fields`?** An ancestor node’s `content_fields` only contains its own direct attributes and text, not its children’s. Two `<li>` elements would have empty `content_fields` at the `<li>` level even if one child is an `<img>` and the other is a `<video>`. The `content_hash` captures this difference; `content_fields` does not.

**Tolerant variant**: If minor text variations (different card titles that are otherwise structurally identical) should still commute, compare the **set of `content_fields` keys** (structural shape) as a secondary gate after hash inequality. Nodes with the same key schema but different values can be treated as homogeneous for chunking purposes. This is opt-in via `STRICT_HASH_MATCH` config flag (default: `True`).

**Per-pattern override**: `STRICT_HASH_MATCH` can be set at the pattern level, not just globally, to allow card lists to use tolerant mode while navigation menus use strict mode. The mapper stores a `Dict[pattern, bool]` that overrides the global default. Patterns are placed in tolerant mode automatically when the chunker observes that all instances share the same key schema but differ only in text values — i.e., when strict mode would have produced a split into N single-member chunks all with the same key set.

### 7.5 Chunk Formation and Ledger Updating

Once a consistent pattern is found, we create a `Chunk` object:

```
Chunk(
    chunk_id = sha1(url|pattern|ordinal)[:16],   # stable across scroll iterations
    pattern = pattern,
    representative_xpath = current_xpath,   # the leaf or the best ancestor
    member_xpaths = sorted(_pattern_index[pattern]),
    char_count = max(_tag_cache[xp]['subtree_text_budget'] for xp in member_xpaths),
    commutation_count = len(member_xpaths),
    content_fields = _build_summary(representative_xpath),
    text_preview = _text_only_from_summary(content_fields),
    image_urls = ...   # derived from content fields
)
```

**`chunk_id` stability**: The ID must not include `snapshot_id` (which changes each scroll iteration). Using `sha1(url|pattern|ordinal)[:16]` produces a stable ID for the same pattern on the same page across all scroll iterations, enabling `chunk_replaced` events to correctly update existing spheres rather than remove and re-add them.

**Ordinal assignment**: When a pattern yields only one chunk (the normal case), `ordinal = 0`. When a split produces multiple sub-chunks for the same pattern, assign ordinals by sorting the representative xpaths of each cluster lexicographically: the cluster whose representative xpath sorts first gets `ordinal=0`, next gets `ordinal=1`, etc. Lexicographic order of absolute xpaths equals document order for siblings, so ordinals are stable as long as the split clustering is deterministic (which it is, since it groups by `content_hash`).

**`chunk_replaced` vs `chunk_added` detection**: After re-running the chunker on a dirty pattern, compare the resulting chunk's `chunk_id` against `_pattern_chunks[pattern]`. If a chunk with the same `chunk_id` already exists, emit `chunk_replaced` with the updated member list. If no prior chunk had that `chunk_id` (new pattern or new split ordinal), emit `chunk_added`. Any prior chunks for this pattern that are no longer produced emit `chunk_removed`. This comparison happens at the end of the chunker run, after all events for a batch are collected, so the frontend receives a coherent atomic update.

**`_build_summary`**: Building the content-structure summary for the representative xpath requires traversing its subtree — not just reading `_tag_cache[representative_xpath]['content_fields']`, which only contains that node's own direct attributes. Use the **master tree** (retained in memory per §4.6) to walk the representative's subtree and aggregate all content fields with their relative addresses. This traversal is lazy (only triggered on chunk formation) and its result is cached on the Chunk object.

Then, for each `mxp` in `member_xpaths`:
- Mark `mxp` and all its descendants as consumed. Use `bisect` on `_sorted_xpaths` to enumerate descendants in O(log N + |descendants|).
- Update `_claimed[xpath] = chunk_id` for each consumed xpath (reverse index).
- Remove those xpaths from any other chunk that previously owned them (via `_claimed` lookups).

### 7.6 Splitting for Divergent Patterns

When the fingerprint check fails for a candidate pattern, we **split**:

1. Group the instances of the pattern into clusters with identical fingerprint sets.
2. For each cluster, recursively run the chunker **from the leaves that belong to that cluster**, but this time using a tighter budget (same `HARD_CHAR_LIMIT`) – effectively drilling down one level deeper.
3. The original coarse chunk is discarded (if it existed); new finer chunks are emitted.

This is the *recursive sampling* approach: we start optimistically with the widest pattern, and only refine when structural equivalence is violated.

### 7.7 Incremental Updates and Re‑chunking

When a delta marks any pattern as dirty, **always re-run the full bottom-up chunker on that pattern’s leaves** rather than trying to incrementally extend or patch an existing chunk. This is simpler, correct by construction, and fast because the chunker only touches dirty patterns.

The re-run will naturally produce:
- A `chunk_replaced` event if the new result has the same `chunk_id` (same `url|pattern|ordinal`) with an updated member list.
- A `chunk_removed` + one or more `chunk_added` events if the pattern split.

Do **not** attempt to extend `member_xpaths` in place and re-validate. The bottom-up walk may choose a different chunk root once new members arrive (e.g., if the aggregate budget now exceeds the limit), and a targeted patch would miss this.

### 7.8 Generalized XPath Collision Across Page Regions

Two structurally unrelated sections of a page (e.g., a navigation `<ul>` and a content results `<ul>`) can produce the same generalized XPath (e.g., `/html/body/div/ul/li`), landing in the same `_pattern_index` bucket. The fingerprint check will detect hash divergence and trigger a split — but the split clusters instances by `content_hash`, which may mix nav items with content items that happen to share a hash.

**Mitigation — Landmark Anchoring**: The pattern key is prefixed with the absolute XPath of the nearest ancestor that is a semantic landmark element. Landmark elements are: `<main>`, `<nav>`, `<header>`, `<footer>`, `<aside>`, `<article>`, `<section>` with an explicit `id` or `aria-label`, or any element with `role` in `{navigation, main, banner, contentinfo, complementary, region, search}`. The landmark’s own absolute XPath (including indices) serves as a stable discriminator.

This is robust on deep React trees where `PATTERN_ANCHOR_DEPTH=3` would hit generic wrapper `div`s, and correctly handles single-page-apps where the meaningful structure starts at arbitrary depth.

```python
LANDMARK_TAGS = {‘main’, ‘nav’, ‘header’, ‘footer’, ‘aside’, ‘article’}
LANDMARK_ROLES = {‘navigation’, ‘main’, ‘banner’, ‘contentinfo’, ‘complementary’, ‘region’, ‘search’}

def find_landmark_ancestor(xpath, tag_cache):
    """Walk up from xpath; return the absolute xpath of the nearest landmark ancestor."""
    current = xpath
    while True:
        parent = parent_xpath(current)
        if not parent or parent == ‘/html’:
            return ‘/html’  # fallback: root anchor
        node = tag_cache.get(parent, {})
        tag = node.get(‘tag’, ‘’)
        role = node.get(‘role’, ‘’)
        if tag in LANDMARK_TAGS or role in LANDMARK_ROLES:
            return parent
        # section is only a landmark if it has an accessible name
        if tag == ‘section’ and (node.get(‘aria_label’) or node.get(‘id’)):
            return parent
        current = parent

def generalize_xpath(xpath, tag_cache):
    """Region-anchored generalized xpath: landmark_abs_xpath + generalized_subpath."""
    landmark = find_landmark_ancestor(xpath, tag_cache)
    # Strip landmark prefix, generalize the remainder
    remainder = xpath[len(landmark):]
    generalized = re.sub(r’\[\d+\]’, ‘’, remainder)
    return landmark + generalized
```

The `tag_cache` entries must include `tag` and `role` for this to work; the JS extraction already provides both via the node’s `tagName` and `getAttribute(‘role’)`.

---

## 8. Streaming and Frontend Integration

### 8.1 Chunk Event Types

Three event types flow from the mapper to the pipeline’s fast path:

| Event | Payload | Meaning |
|-------|---------|---------|
| `chunk_added` | `{snapshot_id, url, chunk}` | A new pattern was discovered (or a split produced a new sub‑chunk). Add spheres to scene. |
| `chunk_replaced` | `{snapshot_id, url, chunk, replaced_chunk_id}` | An existing chunk grew/shrunk. Update the existing spheres. |
| `chunk_removed` | `{snapshot_id, url, chunk_id}` | A chunk was split or its pattern disappeared. Remove spheres. |

### 8.2 Fast Path Stream (pipeline_runner)

The `SnapshotPipeline.submit_verified_delta` method already contains a fast path that sends chunks and instances directly to the WebSocket before queueing them for TF‑IDF. Chunk events use the same infrastructure but bypass the TF‑IDF queue entirely; they are emitted as soon as the chunker produces them.

### 8.3 Deterministic 3D Layout

The frontend `chunk_projector.js` places each sphere using a Fibonacci sphere layout seeded by `instance_id`. **`instance_id` is defined as `chunk_id`** — the `sha1(url|pattern|ordinal)[:16]` value. This guarantees:
- The same chunk always appears at the same position across scroll iterations.
- A `chunk_replaced` event for an existing `chunk_id` updates sphere metadata in-place without moving the sphere (position is re-derived from the same seed).
- A `chunk_removed` event removes the sphere; a subsequent `chunk_added` for a new `chunk_id` at the same pattern (after a split) places the new sphere at a new position derived from its new ID.

No coordinates are sent from the backend. When a `chunk_added` event arrives, the frontend calls `addNodesIncrementally` with the new chunk and places it instantly. Billboard content is fetched lazily on click via `/api/chunk_details/{id}`.

### 8.4 Billboard Serialization (`/api/chunk_details/{id}`)

On click, the frontend requests the full content for a chunk. The backend:
1. Looks up the chunk by `chunk_id` from `_pattern_chunks`.
2. Locates the representative xpath in the master tree.
3. Serializes the subtree to HTML: tag names, non-skip attributes (using the same skip list as the JS extraction), direct text nodes, and `_meta.content_fields`. Shadow DOM children are expanded inline. Long text values are included in full (not truncated). Media `src` attributes are included for rendering.
4. Returns `{ chunk_id, html_raw, rendered_text, image_urls, content_fields }`.

The `rendered_text` is the plain-text version of `html_raw` (tags stripped, whitespace normalized) — this is what the knowledge panel displays and what is sent to the SLM as context. The `html_raw` is used for rich billboard rendering in the 3D scene.

---

## 9. Performance and Scalability

### 9.1 Bottleneck Analysis

The dominant cost at each iteration is **JSON serialization and Selenium wire-protocol transport**, not the Python algorithm. For a 50K-node page:

| Operation | First scan | Subsequent scrolls |
|-----------|-----------|-------------------|
| JS DOM walk (C++ engine) | ~150 ms | ~150 ms |
| JSON serialize (all nodes, ~10MB) | ~100 ms | ~5 ms (hash-diff: ~0.1% of nodes) |
| Selenium transport + Python `json.loads` | ~100–200 ms | ~5–10 ms |
| Python index update (O(\|delta\|)) | ~50 ms | ~2–5 ms |
| Bottom-up chunker (O(\|dirty patterns\|)) | ~50 ms | ~2–5 ms |
| **Total first-sphere latency** | **~500–700 ms** | **~20–30 ms** |

The hash-diff optimization (passing `prevHashes` to JS) is the single largest performance lever: it cuts the JSON payload by ~99% on subsequent scrolls.

### 9.2 Scalability Constraints

- **`_sorted_xpaths`**: Uses `sortedcontainers.SortedList` for O(log N) insertions. A plain `list` + `bisect.insort` degrades to O(N) per insertion; over 60 scrolls × 2000 new nodes = 120K insertions, that’s the difference between 1ms and 100ms total insert cost.
- **`_build_summary` memoization**: Results are cached in `_summary_cache[representative_xpath]`. The cache is invalidated only when `content_hash` for that xpath changes. Prevents repeated tree traversals when the same chunk is confirmed across multiple scroll iterations.
- **`getComputedStyle` selective calling**: Only called on structural container tags. Eliminates layout recalculation on the majority of the DOM, saving ~100–300 ms on the JS walk for large pages.
- **`get_leaves_for_cluster`**: Uses the same `bisect` prefix scan as descendant enumeration rather than linear `startswith` scan. O(log N + |cluster_leaves|) instead of O(|all_leaves| × |cluster|).

### 9.3 Concurrency Model

The mapper runs single-threaded per snapshot. The three pipeline stages (scanning+chunking, vectorization, streaming) communicate via `asyncio.Queue`. The mapper writes to all indexes synchronously; there are no shared mutable structures between processes. The invariant is: **indexes are modified only inside `_process_delta`, which is called from a single async task per snapshot**.

The architecture scales to 100K+ node pages without regression since the Python hot path is strictly O(|delta| + |affected patterns|) after the first scan.

---

## 10. Implementation Roadmap and File Impact

| File | Change |
|------|--------|
| `scanner.py` | Add `EXTRACT_CHUNK_DATA_JS`. Script accepts `prevHashes` argument and returns only changed nodes. Make this the default extraction path for verified scans. Pass `prevHashes` dict from Python on each call. |
| `content_tagger.py` | Convert `ContentTagger` to a thin wrapper that reads JS output. Keep existing logic for offline/headless use only. |
| `xpath_tree_builder.py` | Retained for offline analytics only; not used in the live scan pipeline. |
| `chunk_absorber.py` | **Delete** `ChunkAbsorber` class once `BottomUpChunker` is verified end-to-end. The `_pattern_contributions` attribute and the `absorb()` method have no equivalent in the new pipeline. |
| `chunk_builder.py` | Add `BottomUpChunker` implementing §7. Keep old `ChunkBuilder` as `TopDownChunker` for offline/debug use only. |
| `mapper.py` | Replace `_process_distill` with `_process_delta` (§6.2). Add all six indexes. Add `_summary_cache`. Remove `ChunkAbsorber` usage. Emit batched chunk events at end of each delta. |
| `pipeline_runner.py` | Add handling for `chunk_added`, `chunk_replaced`, `chunk_removed` as primary event types alongside existing `chunks_partial`. Events use same WebSocket payload builder. |
| `pipeline_config.py` | Add: `HARD_CHAR_LIMIT=2048`, `STRICT_HASH_MATCH=True`. Remove: `JACCARD_THRESHOLD`. `PATTERN_ANCHOR_DEPTH` is superseded by landmark anchoring and removed. |
| `routes.py` | Add `/api/chunk_details/{id}` endpoint that reads from master tree and returns `{chunk_id, html_raw, rendered_text, image_urls, content_fields}` per §8.4. |

### 10.1 Index Invariants

The following invariants must hold at all times between `_process_delta` calls:

1. `_claimed[xp] == cid` ↔ `xp ∈ _chunk_ledger[cid]` (reverse index consistency)
2. `xp ∈ _tag_cache` ↔ `xp ∈ _sorted_xpaths` (sorted list mirrors cache keys)
3. `xp ∈ _pattern_index[p]` → `xp ∈ _tag_cache` (no orphan pattern entries)
4. `cid ∈ _pattern_chunks[p]` → `cid ∈ _chunk_ledger` (no orphan chunk objects)
5. `_summary_cache[xp]` is valid → `_tag_cache[xp]['content_hash']` matches the hash at time of cache write (invalidate on hash change)

Violation of any invariant indicates a bug in delta integration. Unit tests should assert these after every `_process_delta` call.

---

## 11. Code Sketches (Key Algorithms)

### 11.1 `EXTRACT_CHUNK_DATA_JS` (simplified)

```javascript
// Arguments[0] = prevHashes: { xpath: content_hash } from previous iteration, or {} on first call
(function(prevHashes) {
    var STRUCT_TAGS = new Set(['div','section','article','nav','aside','header','footer','main','ul','ol','table','tbody','tr']);
    var MEDIA_TAGS = new Set(['img','picture','svg','canvas','video','audio','source']);
    var INTERACTIVE_TAGS = new Set(['a','button','input','select','textarea','form']);
    var SKIP_ATTRS = new Set(['style','class','id','width','height','viewbox','d','points','fill','stroke']);
    var TEXT_ATTRS = new Set(['alt','title','aria-label','aria-describedby','placeholder','aria-roledescription','aria-valuetext','summary','caption']);
    var URL_ATTRS = new Set(['href','src','srcset','action','poster','data-src','data-original','data-image','cite']);

    var nodeMap = {};
    var leaves = [];

    function siblingIndex(el) {
        var tag = el.nodeName;
        var idx = 1, sib = el.previousElementSibling;
        while (sib) { if (sib.nodeName === tag) idx++; sib = sib.previousElementSibling; }
        return idx;
    }

    function djb2(str) {
        var h = 5381;
        for (var i = 0; i < str.length; i++) h = (((h << 5) + h) + str.charCodeAt(i)) >>> 0;
        return h;
    }

    function hashFields(fields) {
        var keys = Object.keys(fields).sort();
        var s = '';
        for (var i = 0; i < keys.length; i++) s += keys[i] + '=' + fields[keys[i]].slice(0, 20) + '|';
        return djb2(s);
    }

    function rotateLeft(n, k) { return ((n << k) | (n >>> (32 - k))) >>> 0; }

    function isVisible(el, tag) {
        if (!STRUCT_TAGS.has(tag)) return true;  // skip getComputedStyle for non-containers
        try {
            var cs = window.getComputedStyle(el);
            return cs.display !== 'none' && cs.visibility !== 'hidden' && cs.opacity !== '0';
        } catch(e) { return true; }
    }

    function walk(el, depth, parentXpath, isShadow) {
        if (!el || depth > 100) return null;
        var tag = el.nodeName.toLowerCase();
        if (tag === 'head' || tag === 'style' || tag === '#comment') return null;
        if (tag === 'script' && el.type !== 'application/ld+json') return null;
        if (!isVisible(el, tag)) return null;

        var seg = (isShadow ? '#shadow-root/' : '') + tag + '[' + siblingIndex(el) + ']';
        var xpath = parentXpath + '/' + seg;

        var childResults = [];
        var allChildren = Array.from(el.children);
        if (el.shadowRoot) {
            var shadowKids = Array.from(el.shadowRoot.children);
            for (var i = 0; i < shadowKids.length; i++) {
                var r = walk(shadowKids[i], depth + 1, xpath, true);
                if (r) childResults.push(r);
            }
        }
        for (var i = 0; i < allChildren.length; i++) {
            var r = walk(allChildren[i], depth + 1, xpath, false);
            if (r) childResults.push(r);
        }

        var budget = 0, hasImg = false, hasVid = false, hasAud = false, hasInt = false;
        var childHashes = [], anyChildContent = false;
        for (var i = 0; i < childResults.length; i++) {
            var c = childResults[i];
            budget += c.budget;
            hasImg = hasImg || c.hasImg; hasVid = hasVid || c.hasVid;
            hasAud = hasAud || c.hasAud; hasInt = hasInt || c.hasInt;
            childHashes.push(c.hash);
            if (c.hasContent) anyChildContent = true;
        }

        // Direct TEXT_NODE children only — never el.textContent
        var fields = {}, directText = '';
        for (var cn = el.firstChild; cn; cn = cn.nextSibling) {
            if (cn.nodeType === 3) {
                var t = cn.nodeValue.trim();
                if (t) directText += (directText ? ' ' : '') + t;
            }
        }
        if (directText) { fields['text()'] = directText.slice(0, 80); budget += directText.length; }

        if (el.attributes) {
            for (var ai = 0; ai < el.attributes.length; ai++) {
                var a = el.attributes[ai];
                if (SKIP_ATTRS.has(a.name) || a.name.startsWith('data-wfh')) continue;
                if (TEXT_ATTRS.has(a.name)) { fields['@' + a.name] = a.value.slice(0, 80); budget += a.value.length; }
                else if (URL_ATTRS.has(a.name) && a.value) { fields['@' + a.name] = a.value.slice(0, 80); }
                else if (a.name === 'role') { fields['@role'] = a.value; }
            }
        }

        if (MEDIA_TAGS.has(tag)) { hasImg = tag !== 'video' && tag !== 'audio'; hasVid = tag === 'video' || tag === 'source'; hasAud = tag === 'audio'; }
        if (INTERACTIVE_TAGS.has(tag) || el.hasAttribute('onclick') || el.hasAttribute('contenteditable')) hasInt = true;

        var hasOwnContent = Object.keys(fields).length > 0;
        var hasContent = hasOwnContent || anyChildContent;

        var hash = hashFields(fields);
        for (var i = 0; i < childHashes.length; i++) hash = (hash ^ rotateLeft(childHashes[i], 7)) >>> 0;

        // Hash-diff: only emit to nodeMap if hash changed vs previous iteration
        if (prevHashes[xpath] !== hash) {
            nodeMap[xpath] = {
                tag: tag,
                role: el.getAttribute ? (el.getAttribute('role') || '') : '',
                subtree_text_budget: budget,
                has_image: hasImg, has_video: hasVid, has_audio: hasAud, has_interactive: hasInt,
                content_fields: fields,
                content_hash: hash
            };
        }

        if (hasOwnContent && !anyChildContent) leaves.push(xpath);

        return { budget, hasImg, hasVid, hasAud, hasInt, hash, hasContent };
    }

    walk(document.documentElement, 0, '', false);
    return JSON.stringify({ nodeMap: nodeMap, leaves: leaves });
})(arguments[0] || {});
```

### 11.2 BottomUpChunker (Python)

```python
import re, hashlib, bisect
from sortedcontainers import SortedList
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional

LANDMARK_TAGS = {'main', 'nav', 'header', 'footer', 'aside', 'article'}
LANDMARK_ROLES = {'navigation', 'main', 'banner', 'contentinfo', 'complementary', 'region', 'search'}

def parent_xpath(xpath: str) -> Optional[str]:
    idx = xpath.rfind('/')
    return xpath[:idx] if idx > 0 else None

def find_landmark_ancestor(xpath: str, tag_cache: dict) -> str:
    current = xpath
    while True:
        parent = parent_xpath(current)
        if not parent or parent == '/html':
            return '/html'
        node = tag_cache.get(parent, {})
        tag = node.get('tag', '')
        role = node.get('role', '')
        if tag in LANDMARK_TAGS or role in LANDMARK_ROLES:
            return parent
        if tag == 'section' and (node.get('content_fields', {}).get('@aria-label') or node.get('content_fields', {}).get('@id')):
            return parent
        current = parent

def generalize_xpath(xpath: str, tag_cache: dict) -> str:
    landmark = find_landmark_ancestor(xpath, tag_cache)
    remainder = xpath[len(landmark):]
    return landmark + re.sub(r'\[\d+\]', '', remainder)

def get_descendants(xp: str, sorted_xpaths: SortedList) -> List[str]:
    prefix = xp + '/'
    start = sorted_xpaths.bisect_left(prefix)
    result = []
    for i in range(start, len(sorted_xpaths)):
        if not sorted_xpaths[i].startswith(prefix):
            break
        result.append(sorted_xpaths[i])
    return result

def get_leaves_for_members(member_xpaths: List[str], all_leaves: SortedList) -> List[str]:
    result = []
    for mxp in member_xpaths:
        prefix = mxp + '/'
        start = all_leaves.bisect_left(mxp)
        for i in range(start, len(all_leaves)):
            lf = all_leaves[i]
            if lf == mxp or lf.startswith(prefix):
                result.append(lf)
            elif lf > prefix and not lf.startswith(prefix):
                break
    return result

def pattern_is_consistent(pattern: str, pattern_index: dict, tag_cache: dict,
                           strict_map: dict) -> bool:
    members = list(pattern_index.get(pattern, []))
    if len(members) <= 1:
        return True
    hashes = {tag_cache[xp]['content_hash'] for xp in members if xp in tag_cache}
    if len(hashes) == 1:
        return True
    strict = strict_map.get(pattern, True)  # per-pattern override, default strict
    if strict:
        # Auto-downgrade to tolerant if all members share key schema (text-only variation)
        key_sets = [frozenset(tag_cache[xp].get('content_fields', {}).keys())
                    for xp in members if xp in tag_cache]
        if len(set(key_sets)) == 1:
            strict_map[pattern] = False  # remember for future iterations
            return True
        return False
    # Tolerant mode: same key schema = consistent
    key_sets = [frozenset(tag_cache[xp].get('content_fields', {}).keys())
                for xp in members if xp in tag_cache]
    return len(set(key_sets)) == 1

def chunk_id(url: str, pattern: str, ordinal: int) -> str:
    return hashlib.sha1(f'{url}|{pattern}|{ordinal}'.encode()).hexdigest()[:16]

def run_bottom_up_chunker(dirty_patterns, tag_cache, pattern_index, claimed,
                           sorted_xpaths, pattern_chunks, all_leaves, summary_cache,
                           strict_map, url, budget=2048):
    """
    Returns list of (event_type, chunk_or_id) tuples.
    event_type ∈ {'chunk_added', 'chunk_replaced', 'chunk_removed'}
    """
    events = []

    for pattern in dirty_patterns:
        # Collect leaves for this pattern
        members = sorted(pattern_index.get(pattern, []))
        pattern_leaves = get_leaves_for_members(members, all_leaves)

        new_chunks = []
        local_claimed = set()

        for leaf_xp in pattern_leaves:
            if leaf_xp in claimed or leaf_xp in local_claimed:
                continue
            current = leaf_xp

            while True:
                ancestor = parent_xpath(current)
                if not ancestor:
                    break
                # Skip #shadow-root transparently
                if '#shadow-root' in ancestor:
                    ancestor = parent_xpath(ancestor)
                    if not ancestor:
                        break
                anc_data = tag_cache.get(ancestor)
                if not anc_data:
                    break
                if anc_data['subtree_text_budget'] > budget:
                    break
                anc_pattern = generalize_xpath(ancestor, tag_cache)
                anc_count = len(pattern_index.get(anc_pattern, []))
                if anc_count == 1:
                    break
                if not pattern_is_consistent(anc_pattern, pattern_index, tag_cache, strict_map):
                    break
                current = ancestor

            chunk_pattern = generalize_xpath(current, tag_cache)
            chunk_members = sorted(pattern_index.get(chunk_pattern, [current]))

            # Assign ordinal: sort by representative xpaths of each hash-cluster
            # For single-chunk patterns, ordinal=0
            ordinal = 0
            cid = chunk_id(url, chunk_pattern, ordinal)

            # Build summary (lazy, memoized)
            if current not in summary_cache or \
               tag_cache.get(current, {}).get('content_hash') != summary_cache.get(current + '__hash'):
                summary_cache[current] = _build_summary_from_master_tree(current)
                summary_cache[current + '__hash'] = tag_cache.get(current, {}).get('content_hash')

            new_chunk = {
                'chunk_id': cid,
                'pattern': chunk_pattern,
                'representative_xpath': current,
                'member_xpaths': chunk_members,
                'char_count': max((tag_cache[xp]['subtree_text_budget']
                                   for xp in chunk_members if xp in tag_cache), default=0),
                'commutation_count': len(chunk_members),
                'content_fields': summary_cache.get(current, {}),
            }
            new_chunks.append(new_chunk)

            # Mark consumed in local set to avoid double-processing this batch
            for mxp in chunk_members:
                local_claimed.add(mxp)
                for desc in get_descendants(mxp, sorted_xpaths):
                    local_claimed.add(desc)

        # Diff against existing pattern_chunks to produce events
        existing = {c['chunk_id']: c for c in pattern_chunks.get(pattern, [])}
        produced = {c['chunk_id']: c for c in new_chunks}

        for cid, chunk in produced.items():
            if cid in existing:
                events.append(('chunk_replaced', chunk))
            else:
                events.append(('chunk_added', chunk))
        for cid in existing:
            if cid not in produced:
                events.append(('chunk_removed', cid))

        pattern_chunks[pattern] = new_chunks

    return events
```

---

## 12. Glossary of Terms

| Term | Definition |
|------|------------|
| **Content Leaf** | Deepest node with any detectable content (`hasOwnContent=true`, no content-bearing children). The `hasContent` boolean from the JS walk determines this; starting points for bottom‑up chunking. |
| **Subtree Text Budget** | Total character length of prose‑relevant text within a subtree, computed from direct `TEXT_NODE` children only. Excludes URLs and media source strings. |
| **Content Hash** | 32‑bit DJB2 fingerprint of a node’s own `content_fields`, XOR-rotated with child hashes. Serves dual purpose: delta detection and intra-pattern homogeneity. |
| **Pattern** | Region-anchored generalized XPath: nearest landmark ancestor’s absolute path + generalized subpath. Primary grouping key for structurally equivalent nodes within the same page region. |
| **Landmark Anchor** | Nearest semantic landmark ancestor (`<main>`, `<nav>`, `<header>`, etc.). Prefixes the pattern key to prevent cross-region XPath collision. |
| **Commutation Count** | Number of absolute XPaths in `_pattern_index[pattern]`. Count=1 means unique structure; stops the upward walk. |
| **Chunk** | A group of pattern instances with a common content structure, fit within `HARD_CHAR_LIMIT`. Identified by `chunk_id = sha1(url\|pattern\|ordinal)[:16]`. |
| **Chunk Ordinal** | 0-based integer distinguishing multiple chunks from the same split pattern. Assigned by lexicographic sort of representative xpaths. |
| **Chunk Ledger** | `Dict[chunk_id, Set[abs_xpath]]` — which xpaths are consumed by each chunk. |
| **`_claimed`** | Reverse index of chunk ledger: `Dict[abs_xpath, chunk_id]`. Enables O(1) leaf-claim checks. Must stay in sync with `_chunk_ledger`. |
| **`_sorted_xpaths`** | `SortedList[str]` of all xpaths in `_tag_cache`. Enables O(log N + descendants) prefix scan for descendant enumeration. |
| **`_summary_cache`** | `Dict[rep_xpath, content_fields]` memoizing `_build_summary` results. Invalidated when `content_hash` changes for that xpath. |
| **`instance_id`** | Equal to `chunk_id`. Used as the Fibonacci sphere placement seed in the frontend. Stable across scroll iterations. |
| **Hash-diff Transport** | The JS script accepts `prevHashes = {xpath: hash}` and only emits nodes to `nodeMap` if their hash changed. Reduces subsequent-scroll payload from ~10MB to ~KB. |
| **Delta** | Newly added/updated DOM nodes in a scroll iteration, confirmed stable by the scanner. |
| **Verified Delta** | A delta confirmed stable across consecutive scans. Only verified deltas trigger chunk re-evaluation. |
| **`STRICT_HASH_MATCH`** | Per-pattern flag (default: `True`). When `True`, hash equality is required for consistency. Auto-downgrades to `False` for a pattern when all instances share key schema but differ only in text values. |