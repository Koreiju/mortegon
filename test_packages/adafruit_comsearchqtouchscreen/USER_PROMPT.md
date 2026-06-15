# Test Generation Task: adafruit_comsearchqtouchscreen.html

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

- **Total chunks:** 31
- **Structural chunks:** 7
- **Text/Nav chunks:** 22
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.feat.product` (freq=8, pq_sig=`div(div(img),a(div(p,p,div)))`)
  - Chunk 1: `li.https.org` (freq=7, pq_sig=`li(div(a(div,img)),div(h2(a),div(span),div),div(di`)
  - Chunk 2: `a.adafruit.com` (freq=16, pq_sig=`a(div(div,p,p))`)
  - Chunk 3: `div.container.text` (freq=10, pq_sig=`div(div,div(span),h2(a))`)
  - Chunk 4: `div.container.https` (freq=10, pq_sig=`div(div(div(div(div(span(span))),meta,meta),div(me`)
  - Chunk 5: `a.adafruit.blank` (freq=4, pq_sig=`a(svg(path))`)
  - Chunk 6: `div.content.header` (freq=2, pq_sig=`div(a(span),h3)`)

**Text/Nav chunks:**
  - Chunk 11: `[nav_content:a×15]` (freq=15)
  - Chunk 12: `[nav_content:a×11]` (freq=11)
  - Chunk 11: `[nav_content:a×15]` (freq=15)
  - Chunk 12: `[nav_content:a×11]` (freq=11)
  - Chunk 13: `[nav_content:a×26]` (freq=26)
  - Chunk 14: `[nav_content:a×13]` (freq=13)
  - Chunk 15: `[nav_content:a×39]` (freq=39)
  - Chunk 17: `[nav_content:a×57]` (freq=57)
  - Chunk 17: `[nav_content:a×57]` (freq=57)
  - Chunk 18: `[nav_content:a×7]` (freq=7)
  - Chunk 19: `[text_content:h1×1]` (freq=1)
  - Chunk 20: `[text_content:h2×1]` (freq=1)
  - Chunk 21: `[text_content:h2×1]` (freq=1)
  - Chunk 22: `[text_content:h2×1]` (freq=1)
  - Chunk 23: `[text_content:h3×1]` (freq=1)
  - Chunk 24: `[text_content:h3×1]` (freq=1)
  - Chunk 25: `[text_content:h3×1]` (freq=1)
  - Chunk 26: `[text_content:h3×1]` (freq=1)
  - Chunk 27: `[text_content:li×1]` (freq=1)
  - Chunk 28: `[text_content:li×1]` (freq=1)
  - Chunk 29: `[text_content:li×1]` (freq=1)
  - Chunk 30: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: adafruit_comsearchqtouchscreen.html ===
Chunks: 31 (structural=7, functional=12, text=12)
Categories: {'card': 6, 'structural': 1, 'search_input': 1, 'pagination': 1, 'menu_item': 10, 'text_singleton': 12}
Content: 516 tagged, 431 preserved (84%)
Leaks: 85 total, 41 high-importance

--- Chunk 0: div.feat.product ---
  type=card freq=8 excl=0.83
  pattern_xpath: ///div[contains(@class,'feat')][contains(@class,'row')][contains(@class,'product')]
  tree_sig: div(div(img),a(div(p,p,div)))
  content: [ATTR=2 HREF=1 IMG=1 TEXT=2]

--- Chunk 1: li.https.org ---
  type=card freq=7 excl=0.00
  pattern_xpath: ///li
  tree_sig: li(div(a(div,img)),div(h2(a),div(span),div),div(div(div(meta,meta,div(div(span))
  content: [ATTR=1 HREF=2 IMG=1 TEXT=8]

--- Chunk 2: a.adafruit.com ---
  type=card freq=16 excl=0.00
  pattern_xpath: ///a
  tree_sig: a(div(div,p,p))
  content: [ATTR=1 HREF=1 TEXT=2]

--- Chunk 3: div.container.text ---
  type=card freq=10 excl=0.42
  pattern_xpath: ///div[contains(@class,'text')][contains(@class,'container')]
  tree_sig: div(div,div(span),h2(a))
  content: [HREF=1 TEXT=3]

--- Chunk 4: div.container.https ---
  type=card freq=10 excl=0.83
  pattern_xpath: ///div[contains(@class,'price')][contains(@class,'stock')][contains(@itemprop,'offers')][contains(@class,'container')]
  tree_sig: div(div(div(div(div(span(span))),meta,meta),div(meta,span)))
  content: [TEXT=2]

--- Chunk 5: a.adafruit.blank ---
  type=card freq=4 excl=0.50
  pattern_xpath: ///a[contains(@rel,'noopener')][contains(@target,'blank')]
  tree_sig: a(svg(path))
  content: [ATTR=1 HREF=1]

--- Chunk 6: div.content.header ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'header')]
  tree_sig: div(a(span),h3)
  content: [HREF=1 TEXT=3]

--- Chunk 7: [search_inputs] ---
  type=search_input freq=2 excl=1.00
  pattern_xpath: ///input[contains(@autocapitalize,'none')][contains(@autocomplete,'off')][contains(@autocorrect,'off')][contains(@spellcheck,'false')][contains(@type,'text')]

--- Chunk 8: [pagination_buttons] ---
  type=pagination freq=14 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=8 TEXT=12]

--- Chunk 11: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 12: [nav_content:a×11] ---
  type=menu_item freq=11 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 11: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 12: [nav_content:a×11] ---
  type=menu_item freq=11 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 13: [nav_content:a×26] ---
  type=menu_item freq=26 excl=0.00
  pattern_xpath: ///a
  content: [HREF=2 TEXT=2]

--- Chunk 14: [nav_content:a×13] ---
  type=menu_item freq=13 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 15: [nav_content:a×39] ---
  type=menu_item freq=39 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 17: [nav_content:a×57] ---
  type=menu_item freq=57 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 17: [nav_content:a×57] ---
  type=menu_item freq=57 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 18: [nav_content:a×7] ---
  type=menu_item freq=7 excl=0.50
  pattern_xpath: ///a[contains(@rel,'noopener')][contains(@target,'blank')]
  content: [ATTR=1 HREF=1]

--- Chunk 19: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.62
  pattern_xpath: ///h1[contains(@id,'header')][contains(@id,'search')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.55
  pattern_xpath: ///h2[contains(@id,'results')][contains(@class,'only')][contains(@class,'sr')][contains(@id,'label')][contains(@id,'search')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.75
  pattern_xpath: ///div[contains(@class,'hidden')][contains(@class,'xs')][contains(@class,'sm')]/h2[contains(@id,'filtersortlabel')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.70
  pattern_xpath: ///h2[contains(@id,'flyout')][contains(@id,'products')][contains(@class,'only')][contains(@class,'sr')][contains(@id,'label')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.25
  pattern_xpath: ///h3[contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 24: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.25
  pattern_xpath: ///h3[contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.25
  pattern_xpath: ///h3[contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.25
  pattern_xpath: ///div[contains(@class,'feat')][contains(@class,'product')][contains(@class,'row')]/h3[contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 27: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=3 IMG=1 TEXT=8]

--- Chunk 28: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=2 IMG=1 TEXT=8]

--- Chunk 29: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.39 LEAKS=17
  pattern_xpath: ///div[contains(@class,'left')][contains(@class,'content')]//li[contains(@id,'container')][contains(@id,'desktop')][contains(@id,'menu')]
  content: [ATTR=16 HREF=40 IMG=8 TEXT=56]
  LEAKS (high):
    [HREF] https://www.adafruit.com/product/6453 (href not in rendered output)
    [HREF] https://www.adafruit.com/product/6452 (href not in rendered output)
    [HREF] https://www.adafruit.com/product/6455 (href not in rendered output)
    [HREF] https://www.adafruit.com/product/6445 (href not in rendered output)
    [HREF] /featured (href not in rendered output)
  LEAKS (medium):
    [TEXT] Raspberry Pi Flash Drive 256GB USB 3.0
    [TEXT] Raspberry Pi Flash Drive 128GB USB 3.0
    [TEXT] Adafruit SGP41 Multi-Pixel Gas Sensor Breakout - VOC & NOx

--- Chunk 30: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.39 LEAKS=24
  pattern_xpath: ///div[contains(@class,'right')][contains(@class,'content')]//li[contains(@id,'container')][contains(@id,'desktop')][contains(@id,'menu')]
  content: [ATTR=30 HREF=107 IMG=15 TEXT=134]
  LEAKS (high):
    [HREF] https://www.adafruit.com/product/6453 (href not in rendered output)
    [HREF] https://www.adafruit.com/product/6452 (href not in rendered output)
    [HREF] https://www.adafruit.com/product/6455 (href not in rendered output)
    [HREF] https://www.adafruit.com/product/6445 (href not in rendered output)
    [HREF] /featured (href not in rendered output)
  LEAKS (medium):
    [TEXT] Shop CategoriesNew ProductsFeatured Products
    [TEXT] Raspberry Pi Flash Drive 256GB USB 3.0
    [TEXT] Raspberry Pi Flash Drive 128GB USB 3.0

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
4. Use filename `adafruit_comsearchqtouchscreen.html` in all `_distill()` calls
5. Name the module `test_adafruit_comsearchqtouchscreen_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
