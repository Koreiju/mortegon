# Test Generation Task: plato_stanford_eduentriespeircesemiotics.html

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
- **Structural chunks:** 1
- **Text/Nav chunks:** 20
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `tr` (freq=2, pq_sig=`tr(td(img),td(a))`)

**Text/Nav chunks:**
  - Chunk 3: `[text_content:p×2]` (freq=2)
  - Chunk 4: `[text_content:p×2]` (freq=2)
  - Chunk 5: `[text_content:p×99]` (freq=99)
  - Chunk 6: `[text_content:h3×4]` (freq=1)
  - Chunk 7: `[text_content:li×6]` (freq=6)
  - Chunk 8: `[text_content:li×10]` (freq=10)
  - Chunk 9: `[text_content:li×6]` (freq=6)
  - Chunk 10: `[text_content:li×36]` (freq=36)
  - Chunk 11: `[text_content:li×2]` (freq=2)
  - Chunk 12: `[nav_content:li×5]` (freq=5)
  - Chunk 13: `[nav_content:li×8]` (freq=8)
  - Chunk 14: `[nav_content:a×20]` (freq=20)
  - Chunk 15: `[text_content:h4×1]` (freq=1)
  - Chunk 16: `[text_content:h4×1]` (freq=1)
  - Chunk 17: `[text_content:h4×1]` (freq=1)
  - Chunk 18: `[text_content:h1×1]` (freq=1)
  - Chunk 19: `[text_content:h2×1]` (freq=1)
  - Chunk 20: `[text_content:h2×1]` (freq=1)
  - Chunk 21: `[text_content:h2×1]` (freq=1)
  - Chunk 22: `[text_content:blockquote×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: plato_stanford_eduentriespeircesemiotics.html ===
Chunks: 23 (structural=1, functional=5, text=17)
Categories: {'card': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 17, 'menu_item': 3}
Content: 220 tagged, 156 preserved (71%)
Leaks: 64 total, 0 high-importance

--- Chunk 0: tr ---
  type=card freq=2 excl=0.00
  pattern_xpath: ///tr
  tree_sig: tr(td(img),td(a))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=1]

--- Chunk 1: [search_inputs] ---
  type=search_input freq=1 excl=1.00
  pattern_xpath: ///input[contains(@name,'query')][contains(@type,'search')]
  content: [ATTR=1]

--- Chunk 2: [pagination_buttons] ---
  type=pagination freq=3 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 IMG=1]

--- Chunk 3: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [HREF=2 TEXT=5]

--- Chunk 4: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 5: [text_content:p×99] ---
  type=text_singleton freq=99 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 6: [text_content:h3×4] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///div[contains(@id,'bibliography')]
  content: [TEXT=138]
  LEAKS (medium):
    [TEXT] Hardwick, C., 1977. “Peirce’s Influence on Some
British Philosophers: 
    [TEXT] Hilpinen, R., 2015. “Conception, sense, and reference in
Peircean semi
    [TEXT] ––– 2019. “On the immediate and
dynamical interpretants and objects of

--- Chunk 7: [text_content:li×6] ---
  type=text_singleton freq=6 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=4]

--- Chunk 8: [text_content:li×10] ---
  type=text_singleton freq=10 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 9: [text_content:li×6] ---
  type=text_singleton freq=6 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=3]

--- Chunk 10: [text_content:li×36] ---
  type=text_singleton freq=36 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=3]

--- Chunk 11: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=1]

--- Chunk 12: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.33
  pattern_xpath: ///li[contains(@role,'menuitem')]
  content: [HREF=1 TEXT=1]

--- Chunk 13: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.33
  pattern_xpath: ///li[contains(@role,'menuitem')]
  content: [HREF=1 TEXT=1]

--- Chunk 14: [nav_content:a×20] ---
  type=menu_item freq=20 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 15: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
  content: [TEXT=1]

--- Chunk 16: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
  content: [TEXT=1]

--- Chunk 17: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
  content: [TEXT=1]

--- Chunk 18: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h1
  content: [TEXT=1]

--- Chunk 19: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@id,'aca')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h2
  content: [TEXT=1]

--- Chunk 21: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h2
  content: [TEXT=1]

--- Chunk 22: [text_content:blockquote×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///blockquote
  content: [ATTR=7 HREF=10 IMG=7 TEXT=16]

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
4. Use filename `plato_stanford_eduentriespeircesemiotics.html` in all `_distill()` calls
5. Name the module `test_plato_stanford_eduentriespeircesemiotics_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
