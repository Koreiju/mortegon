# Test Generation Task: rom_on_ca.html

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

- **Total chunks:** 61
- **Structural chunks:** 9
- **Text/Nav chunks:** 50
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `ul.cky.cookie` (freq=39, pq_sig=`ul(li(div,div),li(div,div),li(div,div))`)
  - Chunk 1: `ul.cky.cookie` (freq=15, pq_sig=`ul(li(div,div),li(div,div),li(div,div(p)))`)
  - Chunk 2: `a.all.anim` (freq=6, pq_sig=`div(a(div(picture(source,source,img)),div(div,div(`)
  - Chunk 3: `a.after.card` (freq=2, pq_sig=`div(a(div(picture(source,source,img),div,div(div(d`)
  - Chunk 4: `nav.block.centre` (freq=2, pq_sig=`nav(h2,ul(li(a),li(a),li(a),li(a),li(a),li(a,a,a,a`)
  - Chunk 5: `div.[&.absolute` (freq=35, pq_sig=`div(div,picture(img,source,source,source,source))`)
  - Chunk 6: `div.[&.duration` (freq=20, pq_sig=`div(picture(img,source,source))`)
  - Chunk 7: `a.anywhere.btn` (freq=7, pq_sig=`a(span(i))`)
  - Chunk 8: `li` (freq=10, pq_sig=`li(a(i,span))`)

**Text/Nav chunks:**
  - Chunk 11: `[text_content:li×2]` (freq=2)
  - Chunk 12: `[text_content:li×2]` (freq=2)
  - Chunk 13: `[text_content:li×2]` (freq=2)
  - Chunk 14: `[text_content:li×2]` (freq=2)
  - Chunk 15: `[text_content:li×2]` (freq=2)
  - Chunk 16: `[text_content:li×2]` (freq=2)
  - Chunk 17: `[text_content:li×2]` (freq=2)
  - Chunk 18: `[text_content:li×2]` (freq=2)
  - Chunk 19: `[text_content:li×2]` (freq=2)
  - Chunk 20: `[nav_content:li×4]` (freq=4)
  - Chunk 23: `[nav_content:a×9]` (freq=9)
  - Chunk 22: `[nav_content:li×4]` (freq=4)
  - Chunk 23: `[nav_content:a×9]` (freq=9)
  - Chunk 24: `[nav_content:a×32]` (freq=32)
  - Chunk 25: `[nav_content:li×7]` (freq=7)
  - Chunk 26: `[nav_content:li×6]` (freq=6)
  - Chunk 27: `[nav_content:li×6]` (freq=6)
  - Chunk 28: `[nav_content:li×5]` (freq=5)
  - Chunk 29: `[nav_content:li×7]` (freq=7)
  - Chunk 30: `[nav_content:a×40]` (freq=40)
  - Chunk 31: `[text_content:p×1]` (freq=1)
  - Chunk 32: `[text_content:h2×1]` (freq=1)
  - Chunk 33: `[text_content:h2×1]` (freq=1)
  - Chunk 34: `[text_content:h2×1]` (freq=1)
  - Chunk 35: `[text_content:h2×1]` (freq=1)
  - Chunk 36: `[text_content:h2×1]` (freq=1)
  - Chunk 37: `[text_content:h2×1]` (freq=1)
  - Chunk 38: `[text_content:h2×1]` (freq=1)
  - Chunk 39: `[text_content:h2×1]` (freq=1)
  - Chunk 40: `[text_content:h2×1]` (freq=1)
  - Chunk 41: `[text_content:h2×1]` (freq=1)
  - Chunk 42: `[text_content:h2×1]` (freq=1)
  - Chunk 43: `[text_content:h2×1]` (freq=1)
  - Chunk 44: `[text_content:h2×1]` (freq=1)
  - Chunk 45: `[text_content:h2×1]` (freq=1)
  - Chunk 46: `[text_content:h2×1]` (freq=1)
  - Chunk 47: `[text_content:h3×1]` (freq=1)
  - Chunk 48: `[text_content:h3×1]` (freq=1)
  - Chunk 49: `[text_content:h3×1]` (freq=1)
  - Chunk 50: `[text_content:h3×1]` (freq=1)
  - Chunk 51: `[text_content:h3×1]` (freq=1)
  - Chunk 52: `[text_content:h3×1]` (freq=1)
  - Chunk 53: `[text_content:h3×1]` (freq=1)
  - Chunk 54: `[text_content:h3×1]` (freq=1)
  - Chunk 55: `[text_content:h3×1]` (freq=1)
  - Chunk 56: `[text_content:li×1]` (freq=1)
  - Chunk 57: `[text_content:li×1]` (freq=1)
  - Chunk 58: `[text_content:li×1]` (freq=1)
  - Chunk 59: `[text_content:li×1]` (freq=1)
  - Chunk 60: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: rom_on_ca.html ===
Chunks: 61 (structural=9, functional=13, text=39)
Categories: {'card': 6, 'structural': 1, 'menu_item': 13, 'search_input': 1, 'pagination': 1, 'text_singleton': 39}
Content: 669 tagged, 343 preserved (51%)
Leaks: 326 total, 187 high-importance

--- Chunk 0: ul.cky.cookie ---
  type=card freq=39 excl=0.46
  pattern_xpath: ///ul[contains(@class,'cookie')][contains(@class,'des')][contains(@class,'table')][contains(@class,'cky')]
  tree_sig: ul(li(div,div),li(div,div),li(div,div))
  content: [TEXT=6]

--- Chunk 1: ul.cky.cookie ---
  type=card freq=15 excl=0.46
  pattern_xpath: ///ul[contains(@class,'cookie')][contains(@class,'des')][contains(@class,'table')][contains(@class,'cky')]
  tree_sig: ul(li(div,div),li(div,div),li(div,div(p)))
  content: [TEXT=6]

--- Chunk 2: a.all.anim ---
  type=card freq=6 excl=1.00
  pattern_xpath: ///a[contains(@class,'all')][contains(@class,'cursor')][contains(@class,'image')][contains(@class,'pointer')][contains(@data-component-id,'image')]
  tree_sig: div(a(div(picture(source,source,img)),div(div,div(span),div(div,div(i)))))
  content: [ATTR=1 HREF=1 IMG=5 TEXT=3]

--- Chunk 3: a.after.card ---
  type=card freq=2 excl=0.73
  pattern_xpath: ///a[contains(@class,'event')][contains(@class,'eventinstance')][contains(@data-component-id,'event')][contains(@class,'card')][contains(@class,'col')]
  tree_sig: div(a(div(picture(source,source,img),div,div(div(div),div(span,span)),div(i)),di
  content: [HREF=1 IMG=5 TEXT=7]

--- Chunk 4: nav.block.centre ---
  type=structural freq=2 excl=0.90
  pattern_xpath: ///nav[contains(@role,'navigation')][contains(@class,'about')][contains(@class,'centre')][contains(@class,'media')][contains(@class,'block')]
  tree_sig: nav(h2,ul(li(a),li(a),li(a),li(a),li(a),li(a,a,a,a,a,a)))
  content: [HREF=11 TEXT=12]

--- Chunk 5: div.[&.absolute ---
  type=card freq=35 excl=0.90
  pattern_xpath: ///div[contains(@class,'absolute')][contains(@class,'cover')][contains(@class,'object')][contains(@class,'resp')][contains(@class,'[&')]
  tree_sig: div(div,picture(img,source,source,source,source))
  content: [ATTR=1 IMG=9]

--- Chunk 6: div.[&.duration ---
  type=card freq=20 excl=0.60
  pattern_xpath: ///div[contains(@class,'transform')][contains(@class,'[&')][contains(@class,'img')][contains(@class,'overflow')][contains(@class,'scale')]
  tree_sig: div(picture(img,source,source))
  content: [ATTR=1 IMG=5]

--- Chunk 7: a.anywhere.btn ---
  type=menu_item freq=7 excl=1.00
  pattern_xpath: ///a[contains(@class,'anywhere')][contains(@class,'btn')][contains(@class,'icon')][contains(@class,'inline')][contains(@class,'link')]
  tree_sig: a(span(i))
  content: [HREF=1 TEXT=1]

--- Chunk 8: li ---
  type=menu_item freq=10 excl=0.00
  pattern_xpath: ///li
  tree_sig: li(a(i,span))
  content: [HREF=1 TEXT=1]

--- Chunk 9: [search_inputs] ---
  type=search_input freq=10 excl=0.50
  pattern_xpath: ///input[contains(@class,'form')][contains(@data-drupal-selector,'edit')][contains(@data-drupal-selector,'search')][contains(@id,'edit')][contains(@id,'search')]
  content: [ATTR=1]

--- Chunk 10: [pagination_buttons] ---
  type=pagination freq=50 excl=0.00 OUTLIER=3.7x
  pattern_xpath: ///a
  content: [ATTR=1]

--- Chunk 11: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.20 LEAKS=15
  pattern_xpath: ///li[contains(@class,'first')][contains(@class,'pl')][contains(@class,'pr')][contains(@data-once,'main')][contains(@data-once,'menu')]
  content: [ATTR=1 HREF=11 IMG=18 TEXT=28]
  LEAKS (high):
    [HREF] /visit/visitor-information (href not in rendered output)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_1x_384_x_478/public/20171018-bta (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_2x_768_x_957/public/20171018-bta (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_1x_288_x_358/public/20171018-bta (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_2x_576_x_717/public/20171018-bta (img URL not in rendered)

--- Chunk 12: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 13: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 14: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 15: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 16: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 17: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 18: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 19: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 20: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.19
  pattern_xpath: ///li[contains(@class,'menu')][contains(@class,'item')]
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:a×9] ---
  type=menu_item freq=9 excl=0.70
  pattern_xpath: ///a[contains(@class,'peer')][contains(@class,'uderline')][contains(@class,'leading')][contains(@class,'no')][contains(@class,'normal')]
  content: [HREF=1 TEXT=1]

--- Chunk 22: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.19 OUTLIER=2.8x
  pattern_xpath: ///li[contains(@class,'menu')][contains(@class,'item')]
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:a×9] ---
  type=menu_item freq=9 excl=0.70
  pattern_xpath: ///a[contains(@class,'peer')][contains(@class,'uderline')][contains(@class,'leading')][contains(@class,'no')][contains(@class,'normal')]
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:a×32] ---
  type=menu_item freq=32 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 25: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 26: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 27: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 28: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 29: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 30: [nav_content:a×40] ---
  type=menu_item freq=40 excl=0.80
  pattern_xpath: ///a[contains(@class,'snug')][contains(@class,'tight')][contains(@class,'underline')][contains(@class,'leading')][contains(@class,'no')]
  content: [HREF=1 TEXT=1]

--- Chunk 31: [text_content:p×1] ---
  type=text_singleton freq=1 excl=0.87
  pattern_xpath: ///p[contains(@class,'title')][contains(@data-cky-tag,'title')][contains(@role,'heading')][contains(@style,'color')][contains(@class,'cky')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///h2[contains(@id,'mainnavigation')][contains(@class,'visually')][contains(@id,'menu')][contains(@class,'hidden')][contains(@id,'block')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///h2[contains(@id,'social')][contains(@class,'visually')][contains(@id,'menu')][contains(@class,'hidden')][contains(@id,'block')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///h2[contains(@id,'connect')][contains(@class,'visually')][contains(@id,'menu')][contains(@class,'hidden')][contains(@id,'block')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.21
  pattern_xpath: ///h2[contains(@id,'aboutrom')][contains(@id,'menu')][contains(@id,'block')][contains(@id,'rom')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.34
  pattern_xpath: ///h2[contains(@id,'workwithus')][contains(@id,'menu')][contains(@id,'block')][contains(@id,'rom')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.34
  pattern_xpath: ///h2[contains(@id,'business')][contains(@id,'menu')][contains(@id,'block')][contains(@id,'rom')]
  content: [TEXT=1]

--- Chunk 38: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.21
  pattern_xpath: ///h2[contains(@id,'mediacentre')][contains(@id,'menu')][contains(@id,'block')][contains(@id,'rom')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///h2[contains(@id,'legal')][contains(@class,'visually')][contains(@id,'menu')][contains(@class,'hidden')][contains(@id,'block')]
  content: [TEXT=1]

--- Chunk 40: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h2[contains(@class,'has')][contains(@class,'only')][contains(@class,'sr')][contains(@class,'mb')][contains(@class,'visually')]
  content: [TEXT=1]

--- Chunk 41: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h2[contains(@class,'has')][contains(@class,'only')][contains(@class,'sr')][contains(@class,'mb')][contains(@class,'visually')]
  content: [TEXT=1]

--- Chunk 42: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h2[contains(@class,'has')][contains(@class,'only')][contains(@class,'sr')][contains(@class,'mb')][contains(@class,'visually')]
  content: [TEXT=1]

--- Chunk 43: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.18
  pattern_xpath: ///h2[contains(@class,'has')][contains(@class,'only')][contains(@class,'sr')][contains(@class,'mb')][contains(@class,'visually')]
  content: [TEXT=1]

--- Chunk 44: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.33
  pattern_xpath: ///h2[contains(@class,'coign')][contains(@class,'xl')][contains(@class,'uppercase')][contains(@class,'white')][contains(@class,'font')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h2[contains(@class,'only')][contains(@class,'sr')]
  content: [TEXT=1]

--- Chunk 46: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.33
  pattern_xpath: ///h2[contains(@class,'coign')][contains(@class,'xl')][contains(@class,'uppercase')][contains(@class,'white')][contains(@class,'font')]
  content: [TEXT=1]

--- Chunk 47: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'mt')][contains(@class,'lg')]
  content: [TEXT=1]

--- Chunk 48: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'mt')][contains(@class,'lg')]
  content: [TEXT=1]

--- Chunk 49: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h3[contains(@class,'mt')][contains(@class,'lg')]
  content: [TEXT=1]

--- Chunk 50: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.12
  pattern_xpath: ///h3[contains(@class,'mb')][contains(@class,'mt')]
  content: [TEXT=1]

--- Chunk 51: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.12
  pattern_xpath: ///h3[contains(@class,'mb')][contains(@class,'mt')]
  content: [TEXT=1]

--- Chunk 52: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.12
  pattern_xpath: ///h3[contains(@class,'mb')][contains(@class,'mt')]
  content: [TEXT=1]

--- Chunk 53: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.12
  pattern_xpath: ///h3[contains(@class,'mb')][contains(@class,'mt')]
  content: [TEXT=1]

--- Chunk 54: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.21
  pattern_xpath: ///h3[contains(@class,'max')][contains(@class,'lg')]
  content: [TEXT=1]

--- Chunk 55: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.21
  pattern_xpath: ///h3[contains(@class,'max')][contains(@class,'lg')]
  content: [TEXT=1]

--- Chunk 56: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.20 LEAKS=17
  pattern_xpath: ///li[contains(@class,'first')][contains(@class,'pl')][contains(@class,'pr')][contains(@data-once,'main')][contains(@data-once,'menu')]
  content: [ATTR=2 HREF=12 IMG=18 TEXT=29]
  LEAKS (high):
    [HREF] /citypass-promotions (href not in rendered output)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_md_1x_496_x_618/public/2026-01/2025 (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_md_2x_992_x_1235/public/2026-01/202 (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_1x_384_x_478/public/2026-01/2025 (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_2x_768_x_957/public/2026-01/2025 (img URL not in rendered)
  LEAKS (medium):
    [TEXT] CityPASS & Promotions
    [TEXT] CityPASS & Promotions

--- Chunk 57: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.20 LEAKS=16
  pattern_xpath: ///li[contains(@class,'first')][contains(@class,'pl')][contains(@class,'pr')][contains(@data-once,'main')][contains(@data-once,'menu')]
  content: [ATTR=1 HREF=11 IMG=18 TEXT=30]
  LEAKS (high):
    [HREF] /whats-on/exhibitions/sharks (href not in rendered output)
    [HREF] /visit/visitor-information (href not in rendered output)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_1x_384_x_478/public/2024-09/rom% (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_2x_768_x_957/public/2024-09/rom% (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_1x_288_x_358/public/2024-09/rom% (img URL not in rendered)

--- Chunk 58: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.20 LEAKS=14
  pattern_xpath: ///li[contains(@class,'first')][contains(@class,'pl')][contains(@class,'pr')][contains(@data-once,'main')][contains(@data-once,'menu')]
  content: [ATTR=3 HREF=10 IMG=18 TEXT=27]
  LEAKS (high):
    [HREF] /join-donate/donate-now (href not in rendered output)
    [HREF] /visit/visitor-information (href not in rendered output)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_1x_288_x_358/public/imce/romfree (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_2x_576_x_717/public/imce/romfree (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_2x_576_x_717/public/imce/romfree (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Did You Know That ROM Is a Charitable Organization?

--- Chunk 59: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.20 LEAKS=15
  pattern_xpath: ///li[contains(@class,'first')][contains(@class,'pl')][contains(@class,'pr')][contains(@data-once,'main')][contains(@data-once,'menu')]
  content: [ATTR=1 HREF=11 IMG=18 TEXT=28]
  LEAKS (high):
    [HREF] /visit/visitor-information (href not in rendered output)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_1x_384_x_478/public/20171018-bta (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_sm_2x_768_x_957/public/20171018-bta (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_1x_288_x_358/public/20171018-bta (img URL not in rendered)
    [IMG] /sites/default/files/styles/navigation_teaser_portrait_xs_2x_576_x_717/public/20171018-bta (img URL not in rendered)

--- Chunk 60: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.67 LEAKS=110
  pattern_xpath: ///li[contains(@class,'span')][contains(@class,'col')]
  content: [ATTR=9 HREF=55 IMG=81 TEXT=86]
  LEAKS (high):
    [HREF] /whats-on/special-programs/family-day-weekend (href not in rendered output)
    [HREF] /citypass-promotions (href not in rendered output)
    [HREF] /whats-on (href not in rendered output)
    [HREF] /whats-on/special-programs/rom-after-dark (href not in rendered output)
    [HREF] /whats-on/exhibitions/sharks (href not in rendered output)
  LEAKS (medium):
    [TEXT] Adults & Lifelong Learning
    [TEXT] Curatorial Initiatives
    [TEXT] CityPASS & Promotions

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
4. Use filename `rom_on_ca.html` in all `_distill()` calls
5. Name the module `test_rom_on_ca_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
