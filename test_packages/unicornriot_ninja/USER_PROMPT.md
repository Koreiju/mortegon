# Test Generation Task: unicornriot_ninja.html

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

- **Total chunks:** 12
- **Structural chunks:** 6
- **Text/Nav chunks:** 4
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.block.centered` (freq=2, pq_sig=`div(div(a(img)),div(a(img)),div(a(img)),div(a(img)`)
  - Chunk 1: `header.content.meta` (freq=40, pq_sig=`header(div(span(i,time,time)),h3(a))`)
  - Chunk 2: `div.archive.divider` (freq=15, pq_sig=`div(span(a,a,i,img))`)
  - Chunk 3: `div.archive.divider` (freq=5, pq_sig=`div(span(a,i,img))`)
  - Chunk 4: `div.centered.column` (freq=12, pq_sig=`div(a(img))`)
  - Chunk 5: `li` (freq=7, pq_sig=`li(a(i))`)

**Text/Nav chunks:**
  - Chunk 8: `[nav_content:li×6]` (freq=6)
  - Chunk 9: `[nav_content:a×6]` (freq=6)
  - Chunk 10: `[text_content:h2×1]` (freq=1)
  - Chunk 11: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: unicornriot_ninja.html ===
Chunks: 12 (structural=6, functional=4, text=2)
Categories: {'card': 5, 'menu_item': 3, 'search_input': 1, 'pagination': 1, 'text_singleton': 2}
Content: 90 tagged, 90 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.block.centered ---
  type=card freq=2 excl=1.00
  pattern_xpath: ///div[contains(@class,'block')][contains(@class,'columns')][contains(@class,'general')][contains(@class,'inner')][contains(@class,'markup')]
  tree_sig: div(div(a(img)),div(a(img)),div(a(img)),div(a(img)),div(a(img)),div(a(img)))
  content: [ATTR=12 HREF=6 IMG=12]

--- Chunk 1: header.content.meta ---
  type=card freq=40 excl=1.00
  pattern_xpath: ///header[contains(@class,'content')][contains(@class,'meta')]
  tree_sig: header(div(span(i,time,time)),h3(a))
  content: [HREF=1 TEXT=3]

--- Chunk 2: div.archive.divider ---
  type=card freq=15 excl=0.46
  pattern_xpath: ///div[contains(@class,'archive')][contains(@class,'divider')][contains(@class,'story')][contains(@class,'home')]
  tree_sig: div(span(a,a,i,img))
  content: [ATTR=2 HREF=2 IMG=1 TEXT=2]

--- Chunk 3: div.archive.divider ---
  type=card freq=5 excl=0.46
  pattern_xpath: ///div[contains(@class,'archive')][contains(@class,'divider')][contains(@class,'story')][contains(@class,'home')]
  tree_sig: div(span(a,i,img))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=1]

--- Chunk 4: div.centered.column ---
  type=card freq=12 excl=0.88
  pattern_xpath: ///div[contains(@class,'column')][contains(@class,'has')][contains(@class,'text')][contains(@class,'centered')]
  tree_sig: div(a(img))
  content: [ATTR=2 HREF=1 IMG=2]

--- Chunk 5: li ---
  type=menu_item freq=7 excl=0.00
  pattern_xpath: ///li
  tree_sig: li(a(i))
  content: [HREF=1 TEXT=1]

--- Chunk 6: [search_inputs] ---
  type=search_input freq=4 excl=1.00
  pattern_xpath: ///input[contains(@name,'cf')][contains(@name,'eb')][contains(@name,'ec')][contains(@name,'ef')][contains(@name,'efbfb')]

--- Chunk 7: [pagination_buttons] ---
  type=pagination freq=118 excl=1.00 OUTLIER=2.8x
  pattern_xpath: ///a[contains(@rel,'category')][contains(@rel,'tag')]
  content: [ATTR=11 HREF=12 TEXT=9]

--- Chunk 8: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.70
  pattern_xpath: ///li[contains(@class,'page')][contains(@class,'post')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')]
  content: [HREF=1 TEXT=1]

--- Chunk 9: [nav_content:a×6] ---
  type=menu_item freq=6 excl=1.00
  pattern_xpath: ///a[contains(@rel,'me')]
  content: [ATTR=1 HREF=1]

--- Chunk 10: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.67
  pattern_xpath: ///div[contains(@class,'columns')][contains(@class,'footer')][contains(@class,'title')]//h2[contains(@class,'title')][contains(@class,'is')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h2
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
4. Use filename `unicornriot_ninja.html` in all `_distill()` calls
5. Name the module `test_unicornriot_ninja_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
