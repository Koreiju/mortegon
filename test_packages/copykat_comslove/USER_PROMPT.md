# Test Generation Task: copykat_comslove.html

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

- **Total chunks:** 48
- **Structural chunks:** 4
- **Text/Nav chunks:** 42
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.text.widget` (freq=2, pq_sig=`section(div(h3,div(div(a,a,a,a,a,a,a,a,a,a,a,a,a))`)
  - Chunk 1: `header.entry.header` (freq=3, pq_sig=`header(h2(a))`)
  - Chunk 2: `a.blank.com` (freq=15, pq_sig=`a(svg(title,use))`)
  - Chunk 3: `li.category.item` (freq=34, pq_sig=`li(a(span))`)

**Text/Nav chunks:**
  - Chunk 6: `[text_content:p×3]` (freq=3)
  - Chunk 7: `[text_content:h2×1]` (freq=1)
  - Chunk 8: `[text_content:h2×1]` (freq=1)
  - Chunk 9: `[text_content:h1×1]` (freq=1)
  - Chunk 10: `[text_content:h2×1]` (freq=1)
  - Chunk 11: `[text_content:h2×1]` (freq=1)
  - Chunk 12: `[text_content:h2×1]` (freq=1)
  - Chunk 13: `[text_content:h2×1]` (freq=1)
  - Chunk 14: `[text_content:h2×1]` (freq=1)
  - Chunk 15: `[text_content:h2×1]` (freq=1)
  - Chunk 16: `[text_content:h2×1]` (freq=1)
  - Chunk 17: `[text_content:h2×1]` (freq=1)
  - Chunk 18: `[text_content:h2×1]` (freq=1)
  - Chunk 19: `[text_content:h2×1]` (freq=1)
  - Chunk 20: `[text_content:h2×1]` (freq=1)
  - Chunk 21: `[text_content:h2×1]` (freq=1)
  - Chunk 22: `[text_content:h2×1]` (freq=1)
  - Chunk 23: `[text_content:h2×1]` (freq=1)
  - Chunk 24: `[text_content:h2×1]` (freq=1)
  - Chunk 25: `[text_content:h2×1]` (freq=1)
  - Chunk 26: `[text_content:h2×1]` (freq=1)
  - Chunk 27: `[text_content:h2×1]` (freq=1)
  - Chunk 28: `[text_content:h2×1]` (freq=1)
  - Chunk 29: `[text_content:h2×1]` (freq=1)
  - Chunk 30: `[text_content:h2×1]` (freq=1)
  - Chunk 31: `[text_content:h2×1]` (freq=1)
  - Chunk 32: `[text_content:h2×1]` (freq=1)
  - Chunk 33: `[text_content:h2×1]` (freq=1)
  - Chunk 34: `[text_content:h2×1]` (freq=1)
  - Chunk 35: `[text_content:h2×1]` (freq=1)
  - Chunk 36: `[text_content:h2×1]` (freq=1)
  - Chunk 37: `[text_content:h2×1]` (freq=1)
  - Chunk 38: `[text_content:h2×1]` (freq=1)
  - Chunk 39: `[text_content:h2×1]` (freq=1)
  - Chunk 40: `[text_content:h2×1]` (freq=1)
  - Chunk 41: `[text_content:h2×1]` (freq=1)
  - Chunk 42: `[text_content:h2×1]` (freq=1)
  - Chunk 43: `[text_content:h3×1]` (freq=1)
  - Chunk 44: `[text_content:h3×1]` (freq=1)
  - Chunk 45: `[text_content:h3×1]` (freq=1)
  - Chunk 46: `[text_content:h3×1]` (freq=1)
  - Chunk 47: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: copykat_comslove.html ===
Chunks: 48 (structural=4, functional=2, text=42)
Categories: {'structural': 1, 'card': 1, 'menu_item': 2, 'search_input': 1, 'pagination': 1, 'text_singleton': 42}
Content: 126 tagged, 126 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.text.widget ---
  type=structural freq=2 excl=0.51
  pattern_xpath: ///div[contains(@class,'wrap')][contains(@class,'text')][contains(@class,'widget')]
  tree_sig: section(div(h3,div(div(a,a,a,a,a,a,a,a,a,a,a,a,a))))
  content: [HREF=13 TEXT=14]

--- Chunk 1: header.entry.header ---
  type=card freq=3 excl=0.52
  pattern_xpath: ///header[contains(@class,'header')][contains(@class,'entry')]
  tree_sig: header(h2(a))
  content: [HREF=1 TEXT=1]

--- Chunk 2: a.blank.com ---
  type=menu_item freq=15 excl=1.00
  pattern_xpath: ///a[contains(@rel,'noopener')][contains(@rel,'noreferrer')][contains(@target,'blank')]
  tree_sig: a(svg(title,use))
  content: [HREF=1 TEXT=1]

--- Chunk 3: li.category.item ---
  type=menu_item freq=34 excl=1.00
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')][contains(@id,'item')]
  tree_sig: li(a(span))
  content: [HREF=1 TEXT=1]

--- Chunk 4: [search_inputs] ---
  type=search_input freq=12 excl=1.00
  pattern_xpath: ///input[contains(@class,'form')][contains(@class,'search')]
  content: [ATTR=2]

--- Chunk 5: [pagination_buttons] ---
  type=pagination freq=23 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=5 TEXT=8]

--- Chunk 6: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=2]

--- Chunk 7: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.47
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'widgets')][contains(@id,'genesis')]/h2[contains(@class,'genesis')][contains(@class,'reader')][contains(@class,'screen')][contains(@class,'sidebar')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 8: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.47
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'sidebar')][contains(@class,'wrap')]//h2[contains(@class,'genesis')][contains(@class,'reader')][contains(@class,'screen')][contains(@class,'sidebar')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 9: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.26
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'sidebar')][contains(@class,'wrap')]//h1[contains(@class,'archive')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 10: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 11: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 12: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 13: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 15: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 16: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 18: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 19: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 21: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 22: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 23: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 24: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 25: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 26: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 27: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 28: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 29: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 30: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 31: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 32: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 33: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 34: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 35: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 36: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 37: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 38: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 39: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 40: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 41: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 42: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h2[contains(@class,'entry')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 43: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'widget')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 44: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'widget')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'widget')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 46: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'widget')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 47: [text_content:h2×1] ---
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
4. Use filename `copykat_comslove.html` in all `_distill()` calls
5. Name the module `test_copykat_comslove_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
