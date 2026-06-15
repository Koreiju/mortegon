# Test Generation Task: foodnetwork_comrecipes.html

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

- **Total chunks:** 55
- **Structural chunks:** 15
- **Text/Nav chunks:** 38
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.block.capsule` (freq=23, pq_sig=`div(div(a(img)),div(h3(a(span,span(span))),div(spa`)
  - Chunk 1: `div.block.capsule` (freq=13, pq_sig=`div(div(a(img)),div(h3(a(span)),div(a(span(div,div`)
  - Chunk 2: `div.block.capsule` (freq=2, pq_sig=`div(div(a(img)),div(h3(a(span)),div(a(span(div,div`)
  - Chunk 3: `div.block.editorial` (freq=23, pq_sig=`div(div(a(div(img),noscript)),div(h3(a(span))))`)
  - Chunk 4: `div.capsule.editorial` (freq=5, pq_sig=`div(span,section(header(div(h2(span))),div(div(div`)
  - Chunk 5: `div.capsule.editorial` (freq=2, pq_sig=`div(span,section(header(div),div(div(div(div(a),di`)
  - Chunk 6: `div.block.capsule` (freq=5, pq_sig=`div(div(a(img)),div(h3(a(span,span(span))),div(spa`)
  - Chunk 7: `div.block.capsule` (freq=2, pq_sig=`div(div(a(img)),div(h3(a(span)),div(a(span(div,div`)
  - Chunk 8: `div.block.capsule` (freq=2, pq_sig=`div(div(a(img)),div(h3(a(span)),div(a(span(div,div`)
  - Chunk 9: `a.com.foodnetwork` (freq=4, pq_sig=`a(span(div,div,div,div,div),span(div,span))`)
  - Chunk 10: `button.active.chicken` (freq=6, pq_sig=`button(div(img,span,span),p)`)
  - Chunk 11: `div.block.media` (freq=60, pq_sig=`div(a(img))`)
  - Chunk 12: `div.block.media` (freq=39, pq_sig=`div(h3(a(span)))`)
  - Chunk 13: `div.dropdown.item` (freq=28, pq_sig=`div(a(div,div(img,noscript)))`)
  - Chunk 14: `span.headline.promo` (freq=23, pq_sig=`span(a(span))`)

**Text/Nav chunks:**
  - Chunk 17: `[text_content:li×2]` (freq=2)
  - Chunk 18: `[nav_content:li×25]` (freq=25)
  - Chunk 19: `[nav_content:li×7]` (freq=7)
  - Chunk 20: `[nav_content:li×6]` (freq=6)
  - Chunk 21: `[nav_content:a×19]` (freq=19)
  - Chunk 23: `[nav_content:a×25]` (freq=25)
  - Chunk 23: `[nav_content:a×25]` (freq=25)
  - Chunk 24: `[nav_content:li×5]` (freq=5)
  - Chunk 25: `[nav_content:li×5]` (freq=5)
  - Chunk 26: `[nav_content:li×8]` (freq=8)
  - Chunk 27: `[nav_content:li×10]` (freq=10)
  - Chunk 28: `[nav_content:li×8]` (freq=8)
  - Chunk 29: `[nav_content:li×6]` (freq=6)
  - Chunk 30: `[nav_content:a×37]` (freq=37)
  - Chunk 31: `[nav_content:li×7]` (freq=7)
  - Chunk 32: `[nav_content:li×7]` (freq=7)
  - Chunk 33: `[nav_content:a×19]` (freq=19)
  - Chunk 34: `[nav_content:a×4]` (freq=4)
  - Chunk 35: `[nav_content:a×6]` (freq=6)
  - Chunk 36: `[text_content:h4×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h1×1]` (freq=1)
  - Chunk 39: `[text_content:h6×1]` (freq=1)
  - Chunk 40: `[text_content:h6×1]` (freq=1)
  - Chunk 41: `[text_content:h6×1]` (freq=1)
  - Chunk 42: `[text_content:h6×1]` (freq=1)
  - Chunk 43: `[text_content:h6×1]` (freq=1)
  - Chunk 44: `[text_content:h2×1]` (freq=1)
  - Chunk 45: `[text_content:h2×1]` (freq=1)
  - Chunk 46: `[text_content:h3×1]` (freq=1)
  - Chunk 47: `[text_content:h2×1]` (freq=1)
  - Chunk 48: `[text_content:h2×1]` (freq=1)
  - Chunk 49: `[text_content:h3×1]` (freq=1)
  - Chunk 50: `[text_content:h3×1]` (freq=1)
  - Chunk 51: `[text_content:h3×1]` (freq=1)
  - Chunk 52: `[text_content:h2×1]` (freq=1)
  - Chunk 53: `[text_content:h3×1]` (freq=1)
  - Chunk 54: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: foodnetwork_comrecipes.html ===
Chunks: 55 (structural=15, functional=20, text=20)
Categories: {'card': 14, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 20, 'menu_item': 18}
Content: 218 tagged, 202 preserved (93%)
Leaks: 16 total, 9 high-importance

--- Chunk 0: div.block.capsule ---
  type=card freq=23 excl=0.07
  pattern_xpath: ///div[contains(@class,'capsule')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(div(a(img)),div(h3(a(span,span(span))),div(span,span(a)),div(p)))
  content: [HREF=3 IMG=1 TEXT=5]

--- Chunk 1: div.block.capsule ---
  type=card freq=13 excl=0.07 LEAKS=1
  pattern_xpath: ///div[contains(@class,'capsule')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(div(a(img)),div(h3(a(span)),div(a(span(div,div,div,div,div),span(span))),div
  content: [ATTR=1 HREF=4 IMG=2 TEXT=2]
  LEAKS (high):
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/editorial/talent/geoffrey-zakarian/FN-Talent (img URL not in rendered)

--- Chunk 2: div.block.capsule ---
  type=card freq=2 excl=0.07
  pattern_xpath: ///div[contains(@class,'capsule')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(div(a(img)),div(h3(a(span)),div(a(span(div,div,div,div,div),span(span)))))
  content: [ATTR=1 HREF=3 IMG=1 TEXT=2]

--- Chunk 3: div.block.editorial ---
  type=card freq=23 excl=0.32
  pattern_xpath: ///div[contains(@class,'gallery')][contains(@class,'editorial')][contains(@class,'promo')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(div(a(div(img),noscript)),div(h3(a(span))))
  content: [ATTR=3 HREF=2 IMG=1 TEXT=2]
  LEAKS (medium):
    [TEXT] <div class="m-MediaBlock__m-ResponsiveImage m-MediaBlock__m-Responsive

--- Chunk 4: div.capsule.editorial ---
  type=card freq=5 excl=0.25 LEAKS=2
  pattern_xpath: ///div[contains(@class,'section')][contains(@class,'editorial')][contains(@class,'promo')][contains(@class,'capsule')]
  tree_sig: div(span,section(header(div(h2(span))),div(div(div(div(a),div(h3)),div(div(a),di
  content: [ATTR=7 HREF=6 IMG=3 TEXT=7]
  LEAKS (high):
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/fullset/2021/02/05/Baked-Feta-Pasta-4_s4x3.j (img URL not in rendered)
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/fullset/2017/2/28/0/FNK_Instapot-Opener-H-01 (img URL not in rendered)
  LEAKS (medium):
    [TEXT] <div class="m-MediaBlock__m-ResponsiveImage m-MediaBlock__m-Responsive
    [TEXT] <div class="m-MediaBlock__m-ResponsiveImage m-MediaBlock__m-Responsive
    [TEXT] <div class="m-MediaBlock__m-ResponsiveImage m-MediaBlock__m-Responsive

--- Chunk 5: div.capsule.editorial ---
  type=card freq=2 excl=0.25 LEAKS=5
  pattern_xpath: ///div[contains(@class,'section')][contains(@class,'editorial')][contains(@class,'promo')][contains(@class,'capsule')]
  tree_sig: div(span,section(header(div),div(div(div(div(a),div(h3,section,div)),div(div(a),
  content: [ATTR=9 HREF=9 IMG=6 TEXT=9]
  LEAKS (high):
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/fullset/2012/3/20/0/0182148_corn-and-cheese- (img URL not in rendered)
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/fullset/2011/4/7/1/CL9455_no-bake-cookies_s4 (img URL not in rendered)
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/editorial/talent/ina-garten/FN-TalentAvatar- (img URL not in rendered)
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/editorial/talent/ree-drummond/FN-TalentAvata (img URL not in rendered)
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/editorial/talent/food-network-kitchen/FN-Ava (img URL not in rendered)
  LEAKS (medium):
    [TEXT] <div class="m-MediaBlock__m-ResponsiveImage m-MediaBlock__m-Responsive
    [TEXT] <div class="m-MediaBlock__m-ResponsiveImage m-MediaBlock__m-Responsive
    [TEXT] <div class="m-MediaBlock__m-ResponsiveImage m-MediaBlock__m-Responsive

--- Chunk 6: div.block.capsule ---
  type=card freq=5 excl=0.07
  pattern_xpath: ///div[contains(@class,'capsule')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(div(a(img)),div(h3(a(span,span(span))),div(span,span(a)),div(p)))
  content: [HREF=3 IMG=1 TEXT=5]

--- Chunk 7: div.block.capsule ---
  type=card freq=2 excl=0.07
  pattern_xpath: ///div[contains(@class,'capsule')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(div(a(img)),div(h3(a(span)),div(a(span(div,div,div,div,div),span(span)))))
  content: [ATTR=1 HREF=3 IMG=2 TEXT=2]

--- Chunk 8: div.block.capsule ---
  type=card freq=2 excl=0.07 LEAKS=1
  pattern_xpath: ///div[contains(@class,'capsule')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(div(a(img)),div(h3(a(span)),div(a(span(div,div,div,div,div),span(span))),div
  content: [ATTR=1 HREF=4 IMG=2 TEXT=2]
  LEAKS (high):
    [IMG] //food.fnr.sndimg.com/content/dam/images/food/editorial/talent/jeff-mauro/FN-TalentAvatar- (img URL not in rendered)

--- Chunk 9: a.com.foodnetwork ---
  type=card freq=4 excl=0.69
  pattern_xpath: ///a[contains(@class,'rating')][contains(@class,'stars')][contains(@class,'link')]
  tree_sig: a(span(div,div,div,div,div),span(div,span))
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 10: button.active.chicken ---
  type=button freq=6 excl=0.67
  pattern_xpath: ///button[contains(@class,'tile')][contains(@class,'kdp')]
  tree_sig: button(div(img,span,span),p)
  content: [ATTR=2 IMG=1 TEXT=3]

--- Chunk 11: div.block.media ---
  type=card freq=60 excl=0.41
  pattern_xpath: ///div[contains(@aria-hidden,'true')][contains(@class,'wrap')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(a(img))
  content: [HREF=1 IMG=1]

--- Chunk 12: div.block.media ---
  type=card freq=39 excl=0.18
  pattern_xpath: ///div[contains(@class,'wrap')][contains(@class,'text')][contains(@class,'block')][contains(@class,'media')]
  tree_sig: div(h3(a(span)))
  content: [HREF=1 TEXT=1]

--- Chunk 13: div.dropdown.item ---
  type=card freq=28 excl=0.28
  pattern_xpath: ///div[contains(@class,'menu')][contains(@class,'dropdown')][contains(@class,'item')][contains(@class,'promo')]
  tree_sig: div(a(div,div(img,noscript)))
  content: [ATTR=2 HREF=1 IMG=1 TEXT=2]

--- Chunk 14: span.headline.promo ---
  type=card freq=23 excl=0.40
  pattern_xpath: ///span[contains(@class,'schedule')][contains(@class,'promo')][contains(@class,'headline')]
  tree_sig: span(a(span))
  content: [HREF=1 TEXT=1]

--- Chunk 15: [search_inputs] ---
  type=search_input freq=5 excl=1.00
  pattern_xpath: ///input[contains(@autocomplete,'off')][contains(@class,'form')][contains(@class,'input')][contains(@class,'search')][contains(@data-type,'input')]
  content: [ATTR=2]

--- Chunk 16: [pagination_buttons] ---
  type=pagination freq=28 excl=0.00
  pattern_xpath: ///a
  content: [TEXT=1]

--- Chunk 17: [text_content:li×2] ---
  type=text_singleton freq=2 excl=1.00
  pattern_xpath: ///li[contains(@class,'footer')][contains(@class,'fresh')][contains(@class,'brands')][contains(@class,'copyright')][contains(@class,'has')]
  content: [HREF=6 TEXT=7]

--- Chunk 18: [nav_content:li×25] ---
  type=menu_item freq=25 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 19: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 20: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 21: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:a×25] ---
  type=menu_item freq=25 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:a×25] ---
  type=menu_item freq=25 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 25: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 26: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.08
  pattern_xpath: ///li[contains(@class,'text')][contains(@class,'link')]
  content: [HREF=1 TEXT=1]

--- Chunk 27: [nav_content:li×10] ---
  type=menu_item freq=10 excl=0.08
  pattern_xpath: ///li[contains(@class,'text')][contains(@class,'link')]
  content: [HREF=1 TEXT=1]

--- Chunk 28: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.08
  pattern_xpath: ///li[contains(@class,'text')][contains(@class,'link')]
  content: [HREF=1 TEXT=1]

--- Chunk 29: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.08
  pattern_xpath: ///li[contains(@class,'text')][contains(@class,'link')]
  content: [HREF=1 TEXT=1]

--- Chunk 30: [nav_content:a×37] ---
  type=menu_item freq=37 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 31: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.18
  pattern_xpath: ///li[contains(@class,'list')][contains(@class,'item')][contains(@class,'promo')]
  content: [HREF=1 TEXT=1]

--- Chunk 32: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.18
  pattern_xpath: ///li[contains(@class,'list')][contains(@class,'item')][contains(@class,'promo')]
  content: [HREF=1 TEXT=1]

--- Chunk 33: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 34: [nav_content:a×4] ---
  type=menu_item freq=4 excl=0.34
  pattern_xpath: ///a[contains(@class,'responsive')][contains(@class,'image')][contains(@class,'link')][contains(@class,'block')][contains(@class,'media')]
  content: [HREF=3 TEXT=3]

--- Chunk 35: [nav_content:a×6] ---
  type=menu_item freq=6 excl=0.46
  pattern_xpath: ///li[contains(@class,'header')]/a[contains(@class,'icon')][contains(@class,'links')][contains(@class,'social')][contains(@target,'blank')]
  content: [ATTR=1 HREF=1]

--- Chunk 36: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///h4[contains(@class,'cat')][contains(@id,'bg')][contains(@id,'header')][contains(@id,'id')][contains(@class,'header')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 38: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.53
  pattern_xpath: ///h1[contains(@class,'asset')][contains(@class,'title')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h6[contains(@class,'group')][contains(@class,'heading')][contains(@class,'text')][contains(@class,'link')]
  content: [TEXT=1]

--- Chunk 40: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h6[contains(@class,'group')][contains(@class,'heading')][contains(@class,'text')][contains(@class,'link')]
  content: [TEXT=1]

--- Chunk 41: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h6[contains(@class,'group')][contains(@class,'heading')][contains(@class,'text')][contains(@class,'link')]
  content: [TEXT=1]

--- Chunk 42: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h6[contains(@class,'group')][contains(@class,'heading')][contains(@class,'text')][contains(@class,'link')]
  content: [TEXT=1]

--- Chunk 43: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///div[contains(@class,'wrapper')]//h6[contains(@class,'group')][contains(@class,'heading')][contains(@class,'text')][contains(@class,'link')]
  content: [TEXT=1]

--- Chunk 44: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.22
  pattern_xpath: ///h2[contains(@class,'atoms')][contains(@class,'headline')][contains(@class,'capsule')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h2[contains(@class,'headline')][contains(@class,'capsule')]
  content: [TEXT=1]

--- Chunk 46: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///section[contains(@class,'bulleted')]//h3[contains(@class,'headline')][contains(@class,'capsule')]
  content: [TEXT=1]

--- Chunk 47: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h2[contains(@class,'headline')][contains(@class,'capsule')]
  content: [TEXT=1]

--- Chunk 48: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.22
  pattern_xpath: ///h2[contains(@class,'atoms')][contains(@class,'headline')][contains(@class,'capsule')]
  content: [TEXT=1]

--- Chunk 49: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'headline')][contains(@class,'block')][contains(@class,'media')]
  content: [HREF=1 TEXT=1]

--- Chunk 50: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'headline')][contains(@class,'block')][contains(@class,'media')]
  content: [HREF=1 TEXT=1]

--- Chunk 51: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'headline')][contains(@class,'block')][contains(@class,'media')]
  content: [HREF=1 TEXT=1]

--- Chunk 52: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h2[contains(@class,'headline')][contains(@class,'block')][contains(@class,'media')]
  content: [HREF=1 TEXT=1]

--- Chunk 53: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'headline')][contains(@class,'block')][contains(@class,'media')]
  content: [HREF=2 TEXT=2]

--- Chunk 54: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.71
  pattern_xpath: ///h4[contains(@class,'metadata')][contains(@class,'video')][contains(@class,'title')][contains(@class,'kdp')]
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
4. Use filename `foodnetwork_comrecipes.html` in all `_distill()` calls
5. Name the module `test_foodnetwork_comrecipes_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
