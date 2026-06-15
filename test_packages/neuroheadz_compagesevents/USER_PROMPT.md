# Test Generation Task: neuroheadz_compagesevents.html

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

- **Total chunks:** 15
- **Structural chunks:** 3
- **Text/Nav chunks:** 10
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `span.hidden.visibility` (freq=184, pq_sig=`span(svg(path))`)
  - Chunk 1: `li` (freq=6, pq_sig=`li(a(span))`)
  - Chunk 2: `li.item.list` (freq=3, pq_sig=`li(a(span,span(svg(path))))`)

**Text/Nav chunks:**
  - Chunk 5: `[nav_content:li×4]` (freq=4)
  - Chunk 6: `[nav_content:li×4]` (freq=4)
  - Chunk 7: `[text_content:h1×1]` (freq=1)
  - Chunk 8: `[text_content:h2×1]` (freq=1)
  - Chunk 9: `[text_content:h2×1]` (freq=1)
  - Chunk 10: `[text_content:h2×1]` (freq=1)
  - Chunk 11: `[text_content:h2×1]` (freq=1)
  - Chunk 12: `[text_content:h2×1]` (freq=1)
  - Chunk 13: `[text_content:h2×1]` (freq=1)
  - Chunk 14: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: neuroheadz_compagesevents.html ===
Chunks: 15 (structural=3, functional=4, text=8)
Categories: {'card': 2, 'menu_item': 3, 'search_input': 1, 'pagination': 1, 'text_singleton': 8}
Content: 17 tagged, 17 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: span.hidden.visibility ---
  type=card freq=184 excl=0.00
  pattern_xpath: ///span
  tree_sig: span(svg(path))

--- Chunk 1: li ---
  type=menu_item freq=6 excl=0.00
  pattern_xpath: ///li
  tree_sig: li(a(span))
  content: [HREF=1 TEXT=1]

--- Chunk 2: li.item.list ---
  type=card freq=3 excl=0.33
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'list')][contains(@class,'social')]
  tree_sig: li(a(span,span(svg(path))))
  content: [HREF=1 TEXT=1]

--- Chunk 3: [search_inputs] ---
  type=search_input freq=11 excl=1.00
  pattern_xpath: ///input[contains(@aria-autocomplete,'list')][contains(@aria-haspopup,'listbox')][contains(@aria-owns,'results')][contains(@autocapitalize,'none')][contains(@autocomplete,'off')]
  content: [ATTR=1]

--- Chunk 4: [pagination_buttons] ---
  type=pagination freq=8 excl=0.00
  pattern_xpath: ///button

--- Chunk 5: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.33
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'block')][contains(@class,'newsletter')]//li[contains(@class,'item')][contains(@class,'list')][contains(@class,'social')]
  content: [HREF=1 TEXT=1]

--- Chunk 6: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.33
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'content')][contains(@class,'bottom')]//li[contains(@class,'item')][contains(@class,'list')][contains(@class,'social')]
  content: [HREF=1 TEXT=1]

--- Chunk 7: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h1[contains(@class,'main')][contains(@class,'page')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 8: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.67
  pattern_xpath: ///div[contains(@class,'drawer')][contains(@class,'header')]/h2[contains(@class,'drawer')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 9: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.67
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'block')][contains(@class,'newsletter')]/h2[contains(@class,'block')][contains(@class,'footer')][contains(@class,'inline')][contains(@class,'richtext')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 10: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.42
  pattern_xpath: ///div[contains(@class,'cart')][contains(@class,'drawer')][contains(@class,'warnings')]//h2[contains(@class,'cart')][contains(@class,'empty')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'total')][contains(@class,'totals')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.42
  pattern_xpath: ///div[contains(@class,'cart')][contains(@class,'ctas')]//h2[contains(@class,'cart')][contains(@class,'empty')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 13: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.70
  pattern_xpath: ///localization-form[contains(@class,'small')][contains(@class,'hide')][contains(@class,'medium')]//h2[contains(@id,'header')][contains(@id,'label')][contains(@class,'hidden')][contains(@class,'visually')][contains(@id,'country')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.67
  pattern_xpath: ///h2[contains(@class,'image')][contains(@class,'with')][contains(@class,'inline')][contains(@class,'richtext')][contains(@class,'heading')]
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
4. Use filename `neuroheadz_compagesevents.html` in all `_distill()` calls
5. Name the module `test_neuroheadz_compagesevents_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
