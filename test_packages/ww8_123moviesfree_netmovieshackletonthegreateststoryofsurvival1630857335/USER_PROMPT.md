# Test Generation Task: ww8_123moviesfree_netmovieshackletonthegreateststoryofsurvival1630857335.html

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
- **Structural chunks:** 2
- **Text/Nav chunks:** 19
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `a.https.lost` (freq=10, pq_sig=`div(div(a(picture(source,img),div(h2),span)))`)
  - Chunk 1: `div.col` (freq=2, pq_sig=`div(div,ul(li(a),li(a),li(a),li(a),li(a)))`)

**Text/Nav chunks:**
  - Chunk 4: `[text_content:p×2]` (freq=2)
  - Chunk 5: `[nav_content:li×104]` (freq=104)
  - Chunk 6: `[nav_content:li×4]` (freq=4)
  - Chunk 7: `[nav_content:a×18]` (freq=18)
  - Chunk 8: `[nav_content:li×41]` (freq=41)
  - Chunk 9: `[nav_content:li×15]` (freq=15)
  - Chunk 10: `[text_content:h1×1]` (freq=1)
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

## Quality Report Summary

```
=== QUALITY REPORT: ww8_123moviesfree_netmovieshackletonthegreateststoryofsurvival1630857335.html ===
Chunks: 23 (structural=2, functional=7, text=14)
Categories: {'card': 1, 'structural': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 14, 'menu_item': 5}
Content: 62 tagged, 62 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: a.https.lost ---
  type=card freq=10 excl=1.00
  pattern_xpath: ///a[contains(@class,'poster')][contains(@class,'rounded')]
  tree_sig: div(div(a(picture(source,img),div(h2),span)))
  content: [ATTR=1 HREF=1 IMG=8 TEXT=2]

--- Chunk 1: div.col ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@class,'col')]
  tree_sig: div(div,ul(li(a),li(a),li(a),li(a),li(a)))
  content: [ATTR=5 HREF=5 TEXT=6]

--- Chunk 2: [search_inputs] ---
  type=search_input freq=1 excl=1.00
  pattern_xpath: ///input[contains(@class,'border')][contains(@class,'control')][contains(@class,'form')][contains(@id,'search')][contains(@name,'search')]
  content: [ATTR=2]

--- Chunk 3: [pagination_buttons] ---
  type=pagination freq=2 excl=1.00
  pattern_xpath: ///img[contains(@class,'entered')][contains(@class,'img')][contains(@class,'lazy')][contains(@class,'loaded')][contains(@class,'top')]
  content: [ATTR=1 IMG=2]

--- Chunk 4: [text_content:p×2] ---
  type=text_singleton freq=2 excl=1.00
  pattern_xpath: ///p[contains(@class,'mb')]
  content: [TEXT=2]

--- Chunk 5: [nav_content:li×104] ---
  type=menu_item freq=104 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 6: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 7: [nav_content:a×18] ---
  type=menu_item freq=18 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 8: [nav_content:li×41] ---
  type=menu_item freq=41 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 9: [nav_content:li×15] ---
  type=menu_item freq=15 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 10: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///div[contains(@class,'col')][contains(@class,'lg')][contains(@class,'border')]/h1[contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 13: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 18: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@class,'light')][contains(@class,'text')][contains(@class,'fs')][contains(@class,'title')][contains(@class,'card')]
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
4. Use filename `ww8_123moviesfree_netmovieshackletonthegreateststoryofsurvival1630857335.html` in all `_distill()` calls
5. Name the module `test_ww8_123moviesfree_netmovieshackletonthegreateststoryofsurvival1630857335_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
