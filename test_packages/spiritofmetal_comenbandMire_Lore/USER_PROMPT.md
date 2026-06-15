# Test Generation Task: spiritofmetal_comenbandMire_Lore.html

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

- **Total chunks:** 18
- **Structural chunks:** 7
- **Text/Nav chunks:** 9
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div` (freq=3, pq_sig=`div(span,span(a))`)
  - Chunk 1: `div` (freq=3, pq_sig=`div(span,span)`)
  - Chunk 2: `a.band.center` (freq=5, pq_sig=`a(br,svg(path))`)
  - Chunk 3: `a.col.com` (freq=20, pq_sig=`a(div,svg(path))`)
  - Chunk 4: `div.be.cloned` (freq=12, pq_sig=`div(div(div(a,div,div)))`)
  - Chunk 5: `div.cloned.item` (freq=12, pq_sig=`div(a(img))`)
  - Chunk 6: `h1` (freq=2, pq_sig=`h1(a(span))`)

**Text/Nav chunks:**
  - Chunk 9: `[nav_content:li×7]` (freq=7)
  - Chunk 10: `[text_content:h2×1]` (freq=1)
  - Chunk 11: `[text_content:h3×1]` (freq=1)
  - Chunk 12: `[text_content:h3×1]` (freq=1)
  - Chunk 13: `[text_content:h3×1]` (freq=1)
  - Chunk 14: `[text_content:h3×1]` (freq=1)
  - Chunk 15: `[text_content:h3×1]` (freq=1)
  - Chunk 16: `[text_content:h3×1]` (freq=1)
  - Chunk 17: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: spiritofmetal_comenbandMire_Lore.html ===
Chunks: 18 (structural=7, functional=3, text=8)
Categories: {'card': 4, 'menu_item': 3, 'structural': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 8}
Content: 35 tagged, 35 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div ---
  type=card freq=3 excl=0.00
  pattern_xpath: ///div
  tree_sig: div(span,span(a))
  content: [HREF=1 TEXT=2]

--- Chunk 1: div ---
  type=card freq=3 excl=0.00
  pattern_xpath: ///div
  tree_sig: div(span,span)
  content: [TEXT=2]

--- Chunk 2: a.band.center ---
  type=menu_item freq=5 excl=0.67
  pattern_xpath: ///a[contains(@class,'text')][contains(@rel,'nofollow')][contains(@class,'col')][contains(@class,'xs')][contains(@class,'center')]
  tree_sig: a(br,svg(path))
  content: [HREF=1 TEXT=1]

--- Chunk 3: a.col.com ---
  type=menu_item freq=20 excl=0.50
  pattern_xpath: ///div[contains(@id,'search')][contains(@id,'box')]//a[contains(@class,'col')][contains(@class,'xs')]
  tree_sig: a(div,svg(path))
  content: [HREF=1 TEXT=1]

--- Chunk 4: div.be.cloned ---
  type=card freq=12 excl=0.50
  pattern_xpath: ///div[contains(@class,'item')][contains(@class,'owl')][contains(@style,'px')][contains(@style,'width')]
  tree_sig: div(div(div(a,div,div)))
  content: [HREF=1]

--- Chunk 5: div.cloned.item ---
  type=card freq=12 excl=0.50
  pattern_xpath: ///div[contains(@class,'item')][contains(@class,'owl')][contains(@style,'px')][contains(@style,'width')][contains(@class,'cloned')]
  tree_sig: div(a(img))
  content: [HREF=1 IMG=1]

--- Chunk 6: h1 ---
  type=structural freq=2 excl=0.00
  pattern_xpath: ///h1
  tree_sig: h1(a(span))
  content: [HREF=1 TEXT=2]

--- Chunk 7: [search_inputs] ---
  type=search_input freq=11 excl=0.00
  pattern_xpath: ///input
  content: [ATTR=1]

--- Chunk 8: [pagination_buttons] ---
  type=pagination freq=2 excl=1.00
  pattern_xpath: ///form[contains(@id,'for')][contains(@id,'mlogin')][contains(@method,'post')]
  content: [ATTR=4 HREF=2 TEXT=2]

--- Chunk 9: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 10: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'ribbon')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h3[contains(@class,'ribbon')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h3[contains(@class,'ribbon')]
  content: [TEXT=1]

--- Chunk 13: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///div[contains(@class,'hidden')][contains(@class,'xs')][contains(@class,'sm')]//h3[contains(@class,'ribbon')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 15: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h3[contains(@class,'ribbon')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///section[contains(@id,'videos')]/h3[contains(@class,'ribbon')]
  content: [TEXT=1]

--- Chunk 17: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h4[contains(@itemprop,'name')]
  content: [TEXT=2]

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
4. Use filename `spiritofmetal_comenbandMire_Lore.html` in all `_distill()` calls
5. Name the module `test_spiritofmetal_comenbandMire_Lore_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
