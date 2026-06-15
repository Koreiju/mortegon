# Test Generation Task: cbc_canews.html

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

- **Total chunks:** 128
- **Structural chunks:** 20
- **Text/Nav chunks:** 106
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `a.card.cqw` (freq=10, pq_sig=`li(div(a(div(div(div(figure,div))),div(div(div(h3)`)
  - Chunk 1: `a.canada.card` (freq=3, pq_sig=`a(div(div(div(div(figure(div)),h3)),div(div(div(fi`)
  - Chunk 2: `a.alpine.card` (freq=2, pq_sig=`a(div(div(div(div(figure(div)),h3)),div(div(div(fi`)
  - Chunk 3: `a.canada.card` (freq=3, pq_sig=`a(div(div(h3),div(div(div(span,span,time)))))`)
  - Chunk 4: `a.alberta.canada` (freq=2, pq_sig=`a(div(div(h3),div(div(div(span(span),span,span,tim`)
  - Chunk 5: `a.ambassador.bridge` (freq=2, pq_sig=`a(div(div(h3),div(div(div(time)))))`)
  - Chunk 6: `a.canada.card` (freq=3, pq_sig=`a(div(figure(div(img))),div(div(div(div(span),h3,d`)
  - Chunk 7: `div.card.content` (freq=5, pq_sig=`div(div(div(div(time))),div(h3))`)
  - Chunk 8: `li.card.discovery` (freq=5, pq_sig=`li(a,div(div(a(h3),span)))`)
  - Chunk 9: `a.canada.card` (freq=2, pq_sig=`li(a(div(figure(div(img))),div(div(div(h3),div(div`)
  - Chunk 10: `a.card.climate` (freq=2, pq_sig=`a(div(div(div(span),h3),div(div(div(span,span,time`)
  - Chunk 11: `a.al.analysis` (freq=2, pq_sig=`a(div(div(div(span),h3),div(div(div(span(span),spa`)
  - Chunk 12: `a.bakx.calgary` (freq=3, pq_sig=`a(div(div(h3),div(div(div(span(span),span(span),sp`)
  - Chunk 13: `a.african.artifacts` (freq=3, pq_sig=`a(div(div(h3),div(div(div(span(span),span,span,tim`)
  - Chunk 14: `a.bc.card` (freq=3, pq_sig=`a(div(div(h3),div(div(div(span(span),span,span,tim`)
  - Chunk 15: `a.biobank.card` (freq=2, pq_sig=`a(div(div(h3),div(div(div(span(span),span,span,tim`)
  - Chunk 16: `a.anishinabek.card` (freq=2, pq_sig=`a(div(figure(div(img))),div(div(div(h3),div(div(di`)
  - Chunk 17: `figure.full.image` (freq=59, pq_sig=`figure(div(img))`)
  - Chunk 18: `div.card.image` (freq=40, pq_sig=`div(figure(div(img)))`)
  - Chunk 19: `div.dw.heading` (freq=8, pq_sig=`div(div(a(h2(span(svg(g))))))`)

**Text/Nav chunks:**
  - Chunk 22: `[text_content:h3×2]` (freq=1)
  - Chunk 23: `[text_content:p×2]` (freq=2)
  - Chunk 24: `[text_content:p×2]` (freq=2)
  - Chunk 31: `[nav_content:li×33]` (freq=33)
  - Chunk 26: `[nav_content:li×4]` (freq=4)
  - Chunk 27: `[nav_content:li×7]` (freq=7)
  - Chunk 28: `[nav_content:li×10]` (freq=10)
  - Chunk 29: `[nav_content:li×9]` (freq=9)
  - Chunk 30: `[nav_content:a×35]` (freq=35)
  - Chunk 31: `[nav_content:li×33]` (freq=33)
  - Chunk 32: `[nav_content:li×6]` (freq=6)
  - Chunk 34: `[nav_content:a×15]` (freq=15)
  - Chunk 34: `[nav_content:a×15]` (freq=15)
  - Chunk 35: `[text_content:h2×1]` (freq=1)
  - Chunk 36: `[text_content:h3×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h3×1]` (freq=1)
  - Chunk 39: `[text_content:h3×1]` (freq=1)
  - Chunk 40: `[text_content:h3×1]` (freq=1)
  - Chunk 41: `[text_content:h5×1]` (freq=1)
  - Chunk 42: `[text_content:h1×1]` (freq=1)
  - Chunk 43: `[text_content:h2×1]` (freq=1)
  - Chunk 44: `[text_content:h2×1]` (freq=1)
  - Chunk 45: `[text_content:h3×1]` (freq=1)
  - Chunk 46: `[text_content:h2×1]` (freq=1)
  - Chunk 47: `[text_content:h2×1]` (freq=1)
  - Chunk 48: `[text_content:h2×1]` (freq=1)
  - Chunk 49: `[text_content:h2×1]` (freq=1)
  - Chunk 50: `[text_content:h2×1]` (freq=1)
  - Chunk 51: `[text_content:h2×1]` (freq=1)
  - Chunk 52: `[text_content:h2×1]` (freq=1)
  - Chunk 53: `[text_content:h2×1]` (freq=1)
  - Chunk 54: `[text_content:h2×1]` (freq=1)
  - Chunk 55: `[text_content:h2×1]` (freq=1)
  - Chunk 56: `[text_content:h2×1]` (freq=1)
  - Chunk 57: `[text_content:h2×1]` (freq=1)
  - Chunk 58: `[text_content:h2×1]` (freq=1)
  - Chunk 59: `[text_content:h2×1]` (freq=1)
  - Chunk 60: `[text_content:h3×1]` (freq=1)
  - Chunk 61: `[text_content:h3×1]` (freq=1)
  - Chunk 62: `[text_content:h3×1]` (freq=1)
  - Chunk 63: `[text_content:h3×1]` (freq=1)
  - Chunk 64: `[text_content:h3×1]` (freq=1)
  - Chunk 65: `[text_content:h3×1]` (freq=1)
  - Chunk 66: `[text_content:h3×1]` (freq=1)
  - Chunk 67: `[text_content:h3×1]` (freq=1)
  - Chunk 68: `[text_content:h3×1]` (freq=1)
  - Chunk 69: `[text_content:h3×1]` (freq=1)
  - Chunk 70: `[text_content:h3×1]` (freq=1)
  - Chunk 71: `[text_content:h3×1]` (freq=1)
  - Chunk 72: `[text_content:h3×1]` (freq=1)
  - Chunk 73: `[text_content:h3×1]` (freq=1)
  - Chunk 74: `[text_content:h3×1]` (freq=1)
  - Chunk 75: `[text_content:h3×1]` (freq=1)
  - Chunk 76: `[text_content:h3×1]` (freq=1)
  - Chunk 77: `[text_content:h3×1]` (freq=1)
  - Chunk 78: `[text_content:h3×1]` (freq=1)
  - Chunk 79: `[text_content:h3×1]` (freq=1)
  - Chunk 80: `[text_content:h3×1]` (freq=1)
  - Chunk 81: `[text_content:h2×1]` (freq=1)
  - Chunk 82: `[text_content:h3×1]` (freq=1)
  - Chunk 83: `[text_content:h3×1]` (freq=1)
  - Chunk 84: `[text_content:h3×1]` (freq=1)
  - Chunk 85: `[text_content:h3×1]` (freq=1)
  - Chunk 86: `[text_content:h3×1]` (freq=1)
  - Chunk 87: `[text_content:h3×1]` (freq=1)
  - Chunk 88: `[text_content:h3×1]` (freq=1)
  - Chunk 89: `[text_content:h3×1]` (freq=1)
  - Chunk 90: `[text_content:h3×1]` (freq=1)
  - Chunk 91: `[text_content:h3×1]` (freq=1)
  - Chunk 92: `[text_content:h3×1]` (freq=1)
  - Chunk 93: `[text_content:h3×1]` (freq=1)
  - Chunk 94: `[text_content:h3×1]` (freq=1)
  - Chunk 95: `[text_content:h3×1]` (freq=1)
  - Chunk 96: `[text_content:h3×1]` (freq=1)
  - Chunk 97: `[text_content:h3×1]` (freq=1)
  - Chunk 98: `[text_content:h3×1]` (freq=1)
  - Chunk 99: `[text_content:h3×1]` (freq=1)
  - Chunk 100: `[text_content:h3×1]` (freq=1)
  - Chunk 101: `[text_content:h3×1]` (freq=1)
  - Chunk 102: `[text_content:h3×1]` (freq=1)
  - Chunk 103: `[text_content:h3×1]` (freq=1)
  - Chunk 104: `[text_content:h3×1]` (freq=1)
  - Chunk 105: `[text_content:h3×1]` (freq=1)
  - Chunk 106: `[text_content:h3×1]` (freq=1)
  - Chunk 107: `[text_content:h3×1]` (freq=1)
  - Chunk 108: `[text_content:h3×1]` (freq=1)
  - Chunk 109: `[text_content:h3×1]` (freq=1)
  - Chunk 110: `[text_content:h3×1]` (freq=1)
  - Chunk 111: `[text_content:h3×1]` (freq=1)
  - Chunk 112: `[text_content:h2×1]` (freq=1)
  - Chunk 113: `[text_content:h3×1]` (freq=1)
  - Chunk 114: `[text_content:h3×1]` (freq=1)
  - Chunk 115: `[text_content:h3×1]` (freq=1)
  - Chunk 116: `[text_content:h3×1]` (freq=1)
  - Chunk 117: `[text_content:h3×1]` (freq=1)
  - Chunk 118: `[text_content:h3×1]` (freq=1)
  - Chunk 119: `[text_content:h3×1]` (freq=1)
  - Chunk 120: `[text_content:h3×1]` (freq=1)
  - Chunk 121: `[text_content:h3×1]` (freq=1)
  - Chunk 122: `[text_content:h3×1]` (freq=1)
  - Chunk 123: `[text_content:h3×1]` (freq=1)
  - Chunk 124: `[text_content:h3×1]` (freq=1)
  - Chunk 125: `[text_content:h3×1]` (freq=1)
  - Chunk 126: `[text_content:h3×1]` (freq=1)
  - Chunk 127: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: cbc_canews.html ===
Chunks: 128 (structural=20, functional=12, text=96)
Categories: {'card': 15, 'structural': 5, 'search_input': 1, 'pagination': 1, 'text_singleton': 96, 'menu_item': 10}
Content: 411 tagged, 392 preserved (95%)
Leaks: 19 total, 6 high-importance

--- Chunk 0: a.card.cqw ---
  type=card freq=10 excl=0.76
  pattern_xpath: ///a[contains(@class,'cqw')][contains(@class,'horizontal')][contains(@data-cy,'card')][contains(@class,'card')]
  tree_sig: li(div(a(div(div(div(figure,div))),div(div(div(h3)),div(div(div))))))
  content: [ATTR=2 HREF=1 IMG=5 TEXT=5]

--- Chunk 1: a.canada.card ---
  type=card freq=3 excl=0.21
  pattern_xpath: ///a[contains(@class,'contentlistcard')][contains(@class,'default')][contains(@data-cy,'story')][contains(@data-cy,'type')][contains(@class,'sclt')]
  tree_sig: a(div(div(div(div(figure(div)),h3)),div(div(div(figure(div),div),div(span(span),
  content: [HREF=1 IMG=6 TEXT=5]

--- Chunk 2: a.alpine.card ---
  type=card freq=2 excl=0.21
  pattern_xpath: ///a[contains(@class,'contentlistcard')][contains(@class,'default')][contains(@data-cy,'story')][contains(@data-cy,'type')][contains(@class,'sclt')]
  tree_sig: a(div(div(div(div(figure(div)),h3)),div(div(div(figure(div),div),div(span(span),
  content: [HREF=1 IMG=6 TEXT=7]

--- Chunk 3: a.canada.card ---
  type=card freq=3 excl=0.10
  pattern_xpath: ///a[contains(@class,'featurednewssecondarytopstoriescontentlistcard')][contains(@class,'text')][contains(@class,'sclt')][contains(@class,'card')]
  tree_sig: a(div(div(h3),div(div(div(span,span,time)))))
  content: [HREF=1 TEXT=3]

--- Chunk 4: a.alberta.canada ---
  type=structural freq=2 excl=0.10
  pattern_xpath: ///a[contains(@class,'featurednewssecondarytopstoriescontentlistcard')][contains(@class,'text')][contains(@class,'sclt')][contains(@class,'card')]
  tree_sig: a(div(div(h3),div(div(div(span(span),span,span,time)))))
  content: [HREF=1 TEXT=4]

--- Chunk 5: a.ambassador.bridge ---
  type=structural freq=2 excl=0.10
  pattern_xpath: ///a[contains(@class,'featurednewssecondarytopstoriescontentlistcard')][contains(@class,'text')][contains(@class,'sclt')][contains(@class,'card')]
  tree_sig: a(div(div(h3),div(div(div(time)))))
  content: [HREF=1 TEXT=2]

--- Chunk 6: a.canada.card ---
  type=card freq=3 excl=0.73
  pattern_xpath: ///a[contains(@class,'featurednewsprimarytopstoriescontentlistcard')][contains(@class,'listing')][contains(@class,'right')][contains(@class,'image')][contains(@class,'new')]
  tree_sig: a(div(figure(div(img))),div(div(div(div(span),h3,div),div(div(div(span,span,time
  content: [HREF=1 IMG=7 TEXT=5]

--- Chunk 7: div.card.content ---
  type=card freq=5 excl=0.21
  pattern_xpath: ///a[contains(@class,'related')][contains(@class,'text')][contains(@class,'card')]
  tree_sig: div(div(div(div(time))),div(h3))
  content: [HREF=1 TEXT=2]

--- Chunk 8: li.card.discovery ---
  type=card freq=5 excl=1.00
  pattern_xpath: ///li[contains(@class,'discovery')][contains(@class,'is')][contains(@class,'trending')][contains(@class,'verticallistcard')][contains(@data-feature-instance,'trending')]
  tree_sig: li(a,div(div(a(h3),span)))
  content: [HREF=2 TEXT=1]

--- Chunk 9: a.canada.card ---
  type=card freq=2 excl=0.25
  pattern_xpath: ///a[contains(@class,'contentlistmorenewscanadaottawacard')][contains(@class,'regular')][contains(@data-cy,'story')][contains(@data-cy,'type')][contains(@class,'sclt')]
  tree_sig: li(a(div(figure(div(img))),div(div(div(h3),div(div(div))))))
  content: [HREF=1 IMG=7 TEXT=5]

--- Chunk 10: a.card.climate ---
  type=structural freq=2 excl=0.24
  pattern_xpath: ///a[contains(@class,'analysis')][contains(@class,'new')][contains(@class,'flag')][contains(@class,'featurednewssecondarytopstoriescontentlistcard')][contains(@class,'text')]
  tree_sig: a(div(div(div(span),h3),div(div(div(span,span,time)))))
  content: [HREF=1 TEXT=4]

--- Chunk 11: a.al.analysis ---
  type=structural freq=2 excl=0.25
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'contentlistmorenewscanada')]//a[contains(@class,'contentlistmorenewsworldcard')][contains(@class,'analysis')][contains(@class,'flag')][contains(@class,'text')][contains(@class,'sclt')]
  tree_sig: a(div(div(div(span),h3),div(div(div(span(span),span,span(span),time),span),h3)))
  content: [HREF=1 TEXT=9]

--- Chunk 12: a.bakx.calgary ---
  type=card freq=3 excl=0.30
  pattern_xpath: ///a[contains(@class,'contentlistmorenewsbusinesscard')][contains(@class,'text')][contains(@class,'sclt')][contains(@class,'card')]
  tree_sig: a(div(div(h3),div(div(div(span(span),span(span),span,span,time,span(span,span)))
  content: [ATTR=1 HREF=1 TEXT=5]

--- Chunk 13: a.african.artifacts ---
  type=card freq=3 excl=0.18
  pattern_xpath: ///a[contains(@class,'contentlistmorenewsentertainmentcard')][contains(@class,'text')][contains(@class,'sclt')][contains(@class,'card')]
  tree_sig: a(div(div(h3),div(div(div(span(span),span,span,time)))))
  content: [HREF=1 TEXT=4]

--- Chunk 14: a.bc.card ---
  type=card freq=3 excl=0.30
  pattern_xpath: ///a[contains(@class,'contentlistmorenewspoliticscard')][contains(@class,'text')][contains(@class,'sclt')][contains(@class,'card')]
  tree_sig: a(div(div(h3),div(div(div(span(span),span,span,time)))))
  content: [HREF=1 TEXT=4]

--- Chunk 15: a.biobank.card ---
  type=structural freq=2 excl=0.18
  pattern_xpath: ///a[contains(@class,'contentlistmorenewshealthcard')][contains(@class,'text')][contains(@class,'sclt')][contains(@class,'card')]
  tree_sig: a(div(div(h3),div(div(div(span(span),span,span,time)))))
  content: [HREF=1 TEXT=4]

--- Chunk 16: a.anishinabek.card ---
  type=card freq=2 excl=0.43
  pattern_xpath: ///a[contains(@class,'contentlistmorenewsindigenouscard')][contains(@class,'contentlistmorenewsentertainmentcard')][contains(@class,'regular')][contains(@data-cy,'story')][contains(@data-cy,'type')]
  tree_sig: a(div(figure(div(img))),div(div(div(h3),div(div(div(figure,div),div(span,span,sp
  content: [HREF=1 IMG=16 TEXT=9]

--- Chunk 17: figure.full.image ---
  type=card freq=59 excl=0.61
  pattern_xpath: ///figure[contains(@class,'full')][contains(@class,'media')][contains(@class,'image')]
  tree_sig: figure(div(img))
  content: [IMG=5]

--- Chunk 18: div.card.image ---
  type=card freq=40 excl=0.46
  pattern_xpath: ///div[contains(@class,'wrap')][contains(@class,'image')][contains(@class,'card')]
  tree_sig: div(figure(div(img)))
  content: [IMG=5]

--- Chunk 19: div.dw.heading ---
  type=card freq=8 excl=0.68
  pattern_xpath: ///div[contains(@class,'dw')][contains(@class,'ru')][contains(@class,'heading')]
  tree_sig: div(div(a(h2(span(svg(g))))))
  content: [HREF=1 TEXT=1]

--- Chunk 20: [search_inputs] ---
  type=search_input freq=3 excl=1.00
  pattern_xpath: ///input[contains(@aria-autocomplete,'both')][contains(@aria-controls,'autocomplete')][contains(@aria-controls,'compact')][contains(@aria-controls,'gn')][contains(@aria-controls,'search')]
  content: [ATTR=2]

--- Chunk 21: [pagination_buttons] ---
  type=pagination freq=57 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 TEXT=1]

--- Chunk 22: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.70 LEAKS=6
  pattern_xpath: ///div[contains(@class,'basic')]/div[contains(@class,'account')][contains(@class,'column')][contains(@class,'footer')]
  content: [HREF=39 TEXT=47]
  LEAKS (high):
    [HREF] https://cbc.ca/torontostudios (href not in rendered output)
    [HREF] https://ici.radio-canada.ca/rci/en (href not in rendered output)
    [HREF] https://www.cbc.ca/lite (href not in rendered output)
    [HREF] https://gem.cbc.ca/ (href not in rendered output)
    [HREF] /accessibility (href not in rendered output)
  LEAKS (medium):
    [TEXT] Audience Relations, CBC
    [TEXT] P.O. Box 500 Station A
    [TEXT] Canada, M5W 1E6 Toll-free (Canada only):  1-866-306-4636

--- Chunk 23: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 24: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 31: [nav_content:li×33] ---
  type=menu_item freq=33 excl=0.31
  pattern_xpath: ///li[contains(@class,'sub')][contains(@class,'nav')][contains(@data-cy,'item')][contains(@data-cy,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 26: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.10
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'footer')]
  content: [HREF=1 TEXT=1]

--- Chunk 27: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.10
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'footer')]
  content: [HREF=1 TEXT=1]

--- Chunk 28: [nav_content:li×10] ---
  type=menu_item freq=10 excl=0.10
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'footer')]
  content: [HREF=1 TEXT=1]

--- Chunk 29: [nav_content:li×9] ---
  type=menu_item freq=9 excl=0.10
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'footer')]
  content: [HREF=1 TEXT=1]

--- Chunk 30: [nav_content:a×35] ---
  type=menu_item freq=35 excl=0.45
  pattern_xpath: ///a[contains(@target,'blank')][contains(@class,'link')][contains(@class,'footer')]
  content: [HREF=1 TEXT=1]

--- Chunk 31: [nav_content:li×33] ---
  type=menu_item freq=33 excl=0.31
  pattern_xpath: ///li[contains(@class,'sub')][contains(@class,'nav')][contains(@data-cy,'item')][contains(@data-cy,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 32: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.30
  pattern_xpath: ///li[contains(@class,'sub')][contains(@class,'list')][contains(@class,'nav')][contains(@data-cy,'item')][contains(@data-cy,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 34: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.31
  pattern_xpath: ///a[contains(@class,'more')][contains(@class,'nav')][contains(@data-cy,'item')][contains(@data-cy,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 34: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.31
  pattern_xpath: ///a[contains(@class,'more')][contains(@class,'nav')][contains(@data-cy,'item')][contains(@data-cy,'nav')]
  content: [HREF=1 TEXT=1]

--- Chunk 35: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h2
  content: [TEXT=1]

--- Chunk 36: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'footer')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'footer')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 38: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'footer')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///h3[contains(@class,'footer')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 40: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///div[contains(@class,'column')][contains(@class,'accessibility')]/h3[contains(@class,'footer')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 41: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.68
  pattern_xpath: ///h5[contains(@class,'menu')][contains(@class,'sidebar')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 42: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h1[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 43: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 44: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=2]

--- Chunk 46: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 47: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'ok')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 48: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 49: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 50: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 51: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 52: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 53: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 54: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 55: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 56: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 57: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 58: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 59: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 60: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 61: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 62: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 63: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 64: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 65: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 66: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 67: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 68: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 69: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 70: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 71: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 72: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 73: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 74: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 75: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 76: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 77: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 78: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 79: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 80: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 81: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'verticallist')]/h2[contains(@data-cy,'element')][contains(@data-cy,'heading')][contains(@class,'element')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 82: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 83: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 84: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 85: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 86: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 87: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 88: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 89: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 90: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 91: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 92: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 93: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 94: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 95: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 96: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 97: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 98: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 99: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 100: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 101: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 102: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 103: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 104: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 105: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 106: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 107: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 108: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 109: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 110: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 111: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 112: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'deck')]
  content: [TEXT=1]

--- Chunk 113: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 114: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 115: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 116: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 117: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 118: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 119: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 120: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 121: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 122: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 123: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 124: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 125: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 126: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.02
  pattern_xpath: ///h3[contains(@data-cy,'headline')][contains(@class,'headline')]
  content: [TEXT=1]

--- Chunk 127: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.45
  pattern_xpath: ///div[contains(@class,'ru')][contains(@class,'dw')]//li[contains(@class,'content')][contains(@class,'list')][contains(@class,'item')]
  content: [HREF=3 IMG=33 TEXT=12]

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
4. Use filename `cbc_canews.html` in all `_distill()` calls
5. Name the module `test_cbc_canews_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
