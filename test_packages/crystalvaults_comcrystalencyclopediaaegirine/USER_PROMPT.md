# Test Generation Task: crystalvaults_comcrystalencyclopediaaegirine.html

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

- **Total chunks:** 23
- **Structural chunks:** 4
- **Text/Nav chunks:** 17
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `p` (freq=12, pq_sig=`p(em(a),strong)`)
  - Chunk 1: `span.fl.icon` (freq=10, pq_sig=`span(a(i,span))`)
  - Chunk 2: `li.children.custom` (freq=2, pq_sig=`li(div(a,span),ul(li(a),li(a),li(a),li(a)))`)
  - Chunk 3: `p` (freq=3, pq_sig=`p(span(a))`)

**Text/Nav chunks:**
  - Chunk 6: `[text_content:p×57]` (freq=57)
  - Chunk 7: `[text_content:p×68]` (freq=68)
  - Chunk 8: `[text_content:li×2]` (freq=2)
  - Chunk 9: `[nav_content:h2×25]` (freq=25)
  - Chunk 10: `[nav_content:a×63]` (freq=63)
  - Chunk 11: `[nav_content:p×4]` (freq=4)
  - Chunk 12: `[nav_content:p×5]` (freq=5)
  - Chunk 13: `[nav_content:p×4]` (freq=4)
  - Chunk 14: `[nav_content:li×17]` (freq=17)
  - Chunk 15: `[nav_content:li×9]` (freq=9)
  - Chunk 16: `[nav_content:li×6]` (freq=6)
  - Chunk 17: `[nav_content:li×6]` (freq=6)
  - Chunk 18: `[text_content:h1×1]` (freq=1)
  - Chunk 19: `[text_content:h4×1]` (freq=1)
  - Chunk 20: `[text_content:h2×1]` (freq=1)
  - Chunk 21: `[text_content:h2×1]` (freq=1)
  - Chunk 22: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: crystalvaults_comcrystalencyclopediaaegirine.html ===
Chunks: 23 (structural=4, functional=11, text=8)
Categories: {'card': 3, 'structural': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 8, 'menu_item': 9}
Content: 71 tagged, 69 preserved (97%)
Leaks: 2 total, 2 high-importance

--- Chunk 0: p ---
  type=card freq=12 excl=0.00
  pattern_xpath: ///p
  tree_sig: p(em(a),strong)
  content: [HREF=1 TEXT=4]

--- Chunk 1: span.fl.icon ---
  type=card freq=10 excl=0.56
  pattern_xpath: ///div[contains(@class,'icon')][contains(@class,'group')]/span[contains(@class,'icon')][contains(@class,'fl')]
  tree_sig: span(a(i,span))
  content: [HREF=1 TEXT=1]

--- Chunk 2: li.children.custom ---
  type=structural freq=2 excl=0.27
  pattern_xpath: ///li[contains(@class,'children')][contains(@class,'has')][contains(@class,'submenu')][contains(@class,'custom')][contains(@class,'item')]
  tree_sig: li(div(a,span),ul(li(a),li(a),li(a),li(a)))
  content: [ATTR=1 HREF=5 TEXT=5]

--- Chunk 3: p ---
  type=card freq=3 excl=0.00
  pattern_xpath: ///p
  tree_sig: p(span(a))
  content: [HREF=1 TEXT=1]

--- Chunk 4: [search_inputs] ---
  type=search_input freq=11 excl=1.00
  pattern_xpath: ///input[contains(@autocomplete,'off')]
  content: [ATTR=1]

--- Chunk 5: [pagination_buttons] ---
  type=pagination freq=22 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1]

--- Chunk 6: [text_content:p×57] ---
  type=text_singleton freq=57 excl=0.00 LEAKS=1
  pattern_xpath: ///p
  LEAKS (high):
    [RENDER] empty (Instance rendered empty)

--- Chunk 7: [text_content:p×68] ---
  type=text_singleton freq=68 excl=0.00 LEAKS=1
  pattern_xpath: ///p
  LEAKS (high):
    [RENDER] empty (Instance rendered empty)

--- Chunk 8: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.27
  pattern_xpath: ///li[contains(@class,'children')][contains(@class,'has')][contains(@class,'submenu')][contains(@class,'custom')][contains(@class,'item')]
  content: [ATTR=2 HREF=12 TEXT=12]

--- Chunk 9: [nav_content:h2×25] ---
  type=menu_item freq=25 excl=0.00
  pattern_xpath: ///h2
  content: [HREF=1 TEXT=1]

--- Chunk 10: [nav_content:a×63] ---
  type=menu_item freq=63 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 11: [nav_content:p×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 12: [nav_content:p×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 13: [nav_content:p×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 14: [nav_content:li×17] ---
  type=menu_item freq=17 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 15: [nav_content:li×9] ---
  type=menu_item freq=9 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 16: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 17: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 18: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.78
  pattern_xpath: ///h1[contains(@class,'post')][contains(@class,'title')][contains(@itemprop,'headline')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h4[contains(@class,'heading')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'fl')]
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
4. Use filename `crystalvaults_comcrystalencyclopediaaegirine.html` in all `_distill()` calls
5. Name the module `test_crystalvaults_comcrystalencyclopediaaegirine_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
