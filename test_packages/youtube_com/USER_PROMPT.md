# Test Generation Task: youtube_com.html

Analyze the attached files and generate executable Python regression tests
following the patterns and rules from your system instructions.

## Attached Files

| File | Purpose | How to use |
|------|---------|------------|
| `source.html` | Original HTML page | Pass 1: Ground truth construction |
| `distilled.html` | Pipeline output | Pass 2: Gap analysis |
| `quality_report.txt` | Content tags, leaks, samples | Cross-reference with distilled |
| `selector_tree.json` | Universal xpath tree | Structural template reference |

## Chunk Inventory

- **Total chunks:** 7
- **Structural chunks:** 1
- **Text/Nav chunks:** 4
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `yt-icon.entry.guide` (freq=34, pq_sig=`yt-icon(span(div(svg(path))))`)

**Text/Nav chunks:**
  - Chunk 3: `[nav_content:a×12]` (freq=12)
  - Chunk 4: `[text_content:h3×1]` (freq=1)
  - Chunk 5: `[text_content:h3×1]` (freq=1)
  - Chunk 6: `[text_content:h3×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: youtube_com.html ===
Chunks: 7 (structural=1, functional=3, text=3)
Categories: {'card': 1, 'search_input': 1, 'pagination': 1, 'menu_item': 1, 'text_singleton': 3}
Content: 9 tagged, 9 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: yt-icon.entry.guide ---
  type=card freq=34 excl=0.20
  pattern_xpath: ///yt-icon[contains(@class,'entry')][contains(@class,'guide')][contains(@class,'renderer')][contains(@class,'scope')][contains(@class,'style')]
  tree_sig: yt-icon(span(div(svg(path))))

--- Chunk 1: [search_inputs] ---
  type=search_input freq=3 excl=0.44 OUTLIER=3.0x
  pattern_xpath: ///input[contains(@class,'searchbox')][contains(@class,'component')][contains(@class,'yt')]
  content: [ATTR=1]

--- Chunk 2: [pagination_buttons] ---
  type=pagination freq=17 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=2]

--- Chunk 3: [nav_content:a×12] ---
  type=menu_item freq=12 excl=0.87
  pattern_xpath: ///a[contains(@class,'endpoint')][contains(@class,'simple')][contains(@id,'endpoint')][contains(@role,'link')][contains(@class,'entry')]
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 4: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'section')][contains(@class,'guide')][contains(@class,'renderer')][contains(@class,'scope')][contains(@class,'style')]
  content: [TEXT=1]

--- Chunk 5: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'section')][contains(@class,'guide')][contains(@class,'renderer')][contains(@class,'scope')][contains(@class,'style')]
  content: [TEXT=1]

--- Chunk 6: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'section')][contains(@class,'guide')][contains(@class,'renderer')][contains(@class,'scope')][contains(@class,'style')]
  content: [TEXT=1]

```

## Your Task

1. Read `source.html` — identify all repeating patterns, count atoms,
   note which content signals (headline, link, image) each atom carries
2. Read `quality_report.txt` and `distilled.html` — find segmentation gaps
   using the taxonomy: NESTED_ATOM, OVER_SEGMENTATION, MISSING_IMAGE,
   MISSING_LINK, MISSING_CHUNK, CROSS_CHUNK_DUPE, SELF_DUPE_TEXT
3. Generate a Python test file covering ALL applicable categories from
   the system prompt (cards, menus, text, search, pagination, images,
   cross-chunk duplication, coverage)
4. Use filename `youtube_com.html` in all `_distill()` calls
5. Name the module `test_youtube_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
