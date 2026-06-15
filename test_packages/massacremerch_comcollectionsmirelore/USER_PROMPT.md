# Test Generation Task: massacremerch_comcollectionsmirelore.html

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

- **Total chunks:** 16
- **Structural chunks:** 7
- **Text/Nav chunks:** 7
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.card.col` (freq=9, pq_sig=`div(a(div(div),img),div(div,div(div(div(s,span),di`)
  - Chunk 1: `div.card.cd` (freq=3, pq_sig=`div(a(div(div(span)),img),div(div,div(div(div(s,sp`)
  - Chunk 2: `li.drawer.grandchild` (freq=593, pq_sig=`li(a(span))`)
  - Chunk 3: `summary.child.header` (freq=12, pq_sig=`summary(div(a,svg(path)))`)
  - Chunk 4: `a.aspect.card` (freq=9, pq_sig=`a(div(div),img)`)
  - Chunk 5: `a.accent.block` (freq=8, pq_sig=`a(svg(path))`)
  - Chunk 6: `a.aspect.card` (freq=3, pq_sig=`a(div(div(span)),img)`)

**Text/Nav chunks:**
  - Chunk 9: `[text_content:h2×2]` (freq=1)
  - Chunk 10: `[text_content:h2×2]` (freq=1)
  - Chunk 11: `[nav_content:a×14]` (freq=14)
  - Chunk 12: `[text_content:h4×1]` (freq=1)
  - Chunk 13: `[text_content:h4×1]` (freq=1)
  - Chunk 14: `[text_content:h4×1]` (freq=1)
  - Chunk 15: `[text_content:h1×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: massacremerch_comcollectionsmirelore.html ===
Chunks: 16 (structural=7, functional=3, text=6)
Categories: {'card': 5, 'menu_item': 3, 'search_input': 1, 'pagination': 1, 'text_singleton': 6}
Content: 82 tagged, 82 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.card.col ---
  type=card freq=9 excl=0.60
  pattern_xpath: ///div[contains(@data-product-available,'true')][contains(@class,'col')][contains(@class,'items')][contains(@class,'space')][contains(@class,'stretch')]
  tree_sig: div(a(div(div),img),div(div,div(div(div(s,span),div(s,span,span(span,span,span,s
  content: [ATTR=1 HREF=1 IMG=8 TEXT=8]

--- Chunk 1: div.card.cd ---
  type=card freq=3 excl=0.60
  pattern_xpath: ///div[contains(@data-product-available,'false')][contains(@class,'col')][contains(@class,'items')][contains(@class,'space')][contains(@class,'stretch')]
  tree_sig: div(a(div(div(span)),img),div(div,div(div(div(s,span),div(s,span,span(span,span,
  content: [ATTR=1 HREF=1 IMG=8 TEXT=9]

--- Chunk 2: li.drawer.grandchild ---
  type=menu_item freq=593 excl=0.52
  pattern_xpath: ///li[contains(@class,'list')][contains(@class,'grandchild')][contains(@class,'drawer')][contains(@class,'item')][contains(@class,'menu')]
  tree_sig: li(a(span))
  content: [HREF=1 TEXT=1]

--- Chunk 3: summary.child.header ---
  type=card freq=12 excl=0.35
  pattern_xpath: ///summary[contains(@class,'child')][contains(@class,'header')][contains(@class,'item')][contains(@class,'link')][contains(@class,'menu')]
  tree_sig: summary(div(a,svg(path)))
  content: [HREF=1 TEXT=1]

--- Chunk 4: a.aspect.card ---
  type=card freq=9 excl=0.45
  pattern_xpath: ///a[contains(@class,'aspect')][contains(@class,'center')][contains(@class,'justify')][contains(@class,'media')][contains(@class,'card')]
  tree_sig: a(div(div),img)
  content: [ATTR=1 HREF=1 IMG=8]

--- Chunk 5: a.accent.block ---
  type=menu_item freq=8 excl=1.00
  pattern_xpath: ///a[contains(@class,'accent')][contains(@class,'block')][contains(@class,'hover')][contains(@class,'icon')][contains(@class,'social')]
  tree_sig: a(svg(path))
  content: [ATTR=1 HREF=1]

--- Chunk 6: a.aspect.card ---
  type=card freq=3 excl=0.45
  pattern_xpath: ///a[contains(@class,'aspect')][contains(@class,'center')][contains(@class,'justify')][contains(@class,'media')][contains(@class,'card')]
  tree_sig: a(div(div(span)),img)
  content: [ATTR=1 HREF=1 IMG=8 TEXT=1]

--- Chunk 7: [search_inputs] ---
  type=search_input freq=3 excl=1.00 OUTLIER=11.0x
  pattern_xpath: ///input[contains(@class,'bg')][contains(@class,'border')][contains(@class,'focus')][contains(@class,'input')][contains(@class,'primary')]
  content: [ATTR=1]

--- Chunk 8: [pagination_buttons] ---
  type=pagination freq=13 excl=0.48
  pattern_xpath: ///a[contains(@aria-current,'page')][contains(@class,'grandchild')][contains(@class,'item')][contains(@class,'link')][contains(@class,'menu')]

--- Chunk 9: [text_content:h2×2] ---
  type=text_singleton freq=1 excl=0.62
  pattern_xpath: ///div[contains(@class,'body')][contains(@class,'banner')][contains(@class,'pc')][contains(@class,'shopify')]
  content: [HREF=1 TEXT=3]

--- Chunk 10: [text_content:h2×2] ---
  type=text_singleton freq=1 excl=0.70
  pattern_xpath: ///div[contains(@class,'btns')][contains(@class,'granular')][contains(@class,'banner')][contains(@class,'pc')][contains(@class,'shopify')]
  content: [HREF=1 TEXT=6]

--- Chunk 11: [nav_content:a×14] ---
  type=menu_item freq=14 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 12: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.57
  pattern_xpath: ///div[contains(@class,'newsletter')][contains(@class,'lg')]//h4[contains(@class,'newsletter')][contains(@id,'newsletter')][contains(@id,'nav')][contains(@class,'footer')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 13: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.42
  pattern_xpath: ///div[contains(@class,'md')][contains(@class,'lg')][contains(@role,'navigation')]//h4[contains(@id,'information')][contains(@id,'nav')][contains(@class,'footer')][contains(@class,'menu')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.87
  pattern_xpath: ///div[contains(@class,'contact')][contains(@class,'lg')]//h4[contains(@class,'contact')][contains(@id,'get')][contains(@id,'in')][contains(@id,'touch')][contains(@id,'nav')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///div[contains(@class,'space')][contains(@class,'pb')][contains(@class,'border')]/h1[contains(@class,'collection')][contains(@class,'title')][contains(@class,'xl')][contains(@class,'text')]
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
4. Use filename `massacremerch_comcollectionsmirelore.html` in all `_distill()` calls
5. Name the module `test_massacremerch_comcollectionsmirelore_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
