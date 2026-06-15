# Test Generation Task: ww8_123moviesfree_netmoviethesettlers1630856832.html

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

- **Total chunks:** 21
- **Structural chunks:** 3
- **Text/Nav chunks:** 17
- **Search input found:** True
- **Pagination found:** False

**Structural chunks:**
  - Chunk 0: `a.https.moviesfree` (freq=6, pq_sig=`div(div(a(picture(source,img),div(h2),span(i))))`)
  - Chunk 1: `a.feathers.https` (freq=5, pq_sig=`div(div(a(picture(source,img),div(h2),span)))`)
  - Chunk 2: `div.col` (freq=2, pq_sig=`div(div,ul(li(a),li(a),li(a),li(a),li(a)))`)

**Text/Nav chunks:**
  - Chunk 4: `[nav_content:li×104]` (freq=104)
  - Chunk 5: `[nav_content:li×4]` (freq=4)
  - Chunk 6: `[nav_content:a×18]` (freq=18)
  - Chunk 7: `[nav_content:li×41]` (freq=41)
  - Chunk 8: `[nav_content:li×15]` (freq=15)
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

## Quality Report Summary

```
=== QUALITY REPORT: ww8_123moviesfree_netmoviethesettlers1630856832.html ===
Chunks: 21 (structural=3, functional=6, text=12)
Categories: {'card': 2, 'structural': 1, 'search_input': 1, 'menu_item': 5, 'text_singleton': 12}
Content: 68 tagged, 68 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: a.https.moviesfree ---
  type=card freq=6 excl=0.50
  pattern_xpath: ///a[contains(@class,'poster')][contains(@class,'rounded')]
  tree_sig: div(div(a(picture(source,img),div(h2),span(i))))
  content: [ATTR=1 HREF=1 IMG=8 TEXT=2]

--- Chunk 1: a.feathers.https ---
  type=card freq=5 excl=0.50
  pattern_xpath: ///a[contains(@class,'poster')][contains(@class,'rounded')]
  tree_sig: div(div(a(picture(source,img),div(h2),span)))
  content: [ATTR=1 HREF=1 IMG=8 TEXT=2]

--- Chunk 2: div.col ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@class,'col')]
  tree_sig: div(div,ul(li(a),li(a),li(a),li(a),li(a)))
  content: [ATTR=5 HREF=5 TEXT=6]

--- Chunk 3: [search_inputs] ---
  type=search_input freq=1 excl=1.00
  pattern_xpath: ///input[contains(@class,'border')][contains(@class,'control')][contains(@class,'form')][contains(@id,'search')][contains(@name,'search')]
  content: [ATTR=2]

--- Chunk 4: [nav_content:li×104] ---
  type=menu_item freq=104 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 5: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 6: [nav_content:a×18] ---
  type=menu_item freq=18 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 7: [nav_content:li×41] ---
  type=menu_item freq=41 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 8: [nav_content:li×15] ---
  type=menu_item freq=15 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 9: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///div[contains(@class,'col')][contains(@class,'lg')][contains(@class,'border')]/h1[contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 10: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 13: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 18: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'card')][contains(@class,'fs')][contains(@class,'title')]
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
4. Use filename `ww8_123moviesfree_netmoviethesettlers1630856832.html` in all `_distill()` calls
5. Name the module `test_ww8_123moviesfree_netmoviethesettlers1630856832_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
