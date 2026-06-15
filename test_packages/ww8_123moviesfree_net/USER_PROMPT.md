# Test Generation Task: ww8_123moviesfree_net.html

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

- **Total chunks:** 8
- **Structural chunks:** 1
- **Text/Nav chunks:** 6
- **Search input found:** True
- **Pagination found:** False

**Structural chunks:**
  - Chunk 0: `div.col` (freq=2, pq_sig=`div(div,ul(li(a),li(a),li(a),li(a),li(a)))`)

**Text/Nav chunks:**
  - Chunk 2: `[text_content:p×23]` (freq=23)
  - Chunk 3: `[nav_content:li×104]` (freq=104)
  - Chunk 4: `[nav_content:li×4]` (freq=4)
  - Chunk 5: `[nav_content:a×18]` (freq=18)
  - Chunk 6: `[nav_content:li×41]` (freq=41)
  - Chunk 7: `[nav_content:li×15]` (freq=15)

## Quality Report Summary

```
=== QUALITY REPORT: ww8_123moviesfree_net.html ===
Chunks: 8 (structural=1, functional=6, text=1)
Categories: {'structural': 1, 'search_input': 1, 'text_singleton': 1, 'menu_item': 5}
Content: 33 tagged, 33 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.col ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@class,'col')]
  tree_sig: div(div,ul(li(a),li(a),li(a),li(a),li(a)))
  content: [ATTR=5 HREF=5 TEXT=6]

--- Chunk 1: [search_inputs] ---
  type=search_input freq=3 excl=1.00
  pattern_xpath: ///input[contains(@class,'control')][contains(@class,'form')][contains(@id,'search')][contains(@name,'search')][contains(@type,'text')]
  content: [ATTR=2]

--- Chunk 2: [text_content:p×23] ---
  type=text_singleton freq=23 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 3: [nav_content:li×104] ---
  type=menu_item freq=104 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 4: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 5: [nav_content:a×18] ---
  type=menu_item freq=18 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 6: [nav_content:li×41] ---
  type=menu_item freq=41 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 7: [nav_content:li×15] ---
  type=menu_item freq=15 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=1 TEXT=1]

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
4. Use filename `ww8_123moviesfree_net.html` in all `_distill()` calls
5. Name the module `test_ww8_123moviesfree_net_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
