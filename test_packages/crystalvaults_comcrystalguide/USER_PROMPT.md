# Test Generation Task: crystalvaults_comcrystalguide.html

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

- **Total chunks:** 166
- **Structural chunks:** 4
- **Text/Nav chunks:** 160
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.bg.col` (freq=136, pq_sig=`div(div(div(div(div(div(a))))))`)
  - Chunk 1: `span.fl.icon` (freq=10, pq_sig=`span(a(i,span))`)
  - Chunk 2: `li.children.custom` (freq=2, pq_sig=`li(div(a,span),ul(li(a),li(a),li(a),li(a)))`)
  - Chunk 3: `p` (freq=3, pq_sig=`p(span(a))`)

**Text/Nav chunks:**
  - Chunk 6: `[text_content:li×2]` (freq=2)
  - Chunk 7: `[text_content:h2×2]` (freq=1)
  - Chunk 8: `[nav_content:p×4]` (freq=4)
  - Chunk 9: `[nav_content:p×5]` (freq=5)
  - Chunk 10: `[nav_content:p×4]` (freq=4)
  - Chunk 11: `[nav_content:li×17]` (freq=17)
  - Chunk 12: `[nav_content:li×9]` (freq=9)
  - Chunk 13: `[nav_content:li×6]` (freq=6)
  - Chunk 14: `[nav_content:li×6]` (freq=6)
  - Chunk 15: `[text_content:h4×1]` (freq=1)
  - Chunk 16: `[text_content:h2×1]` (freq=1)
  - Chunk 17: `[text_content:h2×1]` (freq=1)
  - Chunk 18: `[text_content:h2×1]` (freq=1)
  - Chunk 19: `[text_content:h2×1]` (freq=1)
  - Chunk 20: `[text_content:h4×1]` (freq=1)
  - Chunk 21: `[text_content:h4×1]` (freq=1)
  - Chunk 22: `[text_content:h4×1]` (freq=1)
  - Chunk 23: `[text_content:h4×1]` (freq=1)
  - Chunk 24: `[text_content:h4×1]` (freq=1)
  - Chunk 25: `[text_content:h4×1]` (freq=1)
  - Chunk 26: `[text_content:h4×1]` (freq=1)
  - Chunk 27: `[text_content:h4×1]` (freq=1)
  - Chunk 28: `[text_content:h2×1]` (freq=1)
  - Chunk 29: `[text_content:h4×1]` (freq=1)
  - Chunk 30: `[text_content:h4×1]` (freq=1)
  - Chunk 31: `[text_content:h2×1]` (freq=1)
  - Chunk 32: `[text_content:h4×1]` (freq=1)
  - Chunk 33: `[text_content:h4×1]` (freq=1)
  - Chunk 34: `[text_content:h2×1]` (freq=1)
  - Chunk 35: `[text_content:h4×1]` (freq=1)
  - Chunk 36: `[text_content:h4×1]` (freq=1)
  - Chunk 37: `[text_content:h4×1]` (freq=1)
  - Chunk 38: `[text_content:h4×1]` (freq=1)
  - Chunk 39: `[text_content:h4×1]` (freq=1)
  - Chunk 40: `[text_content:h4×1]` (freq=1)
  - Chunk 41: `[text_content:h4×1]` (freq=1)
  - Chunk 42: `[text_content:h4×1]` (freq=1)
  - Chunk 43: `[text_content:h4×1]` (freq=1)
  - Chunk 44: `[text_content:h4×1]` (freq=1)
  - Chunk 45: `[text_content:h4×1]` (freq=1)
  - Chunk 46: `[text_content:h4×1]` (freq=1)
  - Chunk 47: `[text_content:h2×1]` (freq=1)
  - Chunk 48: `[text_content:h4×1]` (freq=1)
  - Chunk 49: `[text_content:h4×1]` (freq=1)
  - Chunk 50: `[text_content:h4×1]` (freq=1)
  - Chunk 51: `[text_content:h4×1]` (freq=1)
  - Chunk 52: `[text_content:h4×1]` (freq=1)
  - Chunk 53: `[text_content:h4×1]` (freq=1)
  - Chunk 54: `[text_content:h4×1]` (freq=1)
  - Chunk 55: `[text_content:h4×1]` (freq=1)
  - Chunk 56: `[text_content:h4×1]` (freq=1)
  - Chunk 57: `[text_content:h4×1]` (freq=1)
  - Chunk 58: `[text_content:h4×1]` (freq=1)
  - Chunk 59: `[text_content:h4×1]` (freq=1)
  - Chunk 60: `[text_content:h4×1]` (freq=1)
  - Chunk 61: `[text_content:h4×1]` (freq=1)
  - Chunk 62: `[text_content:h4×1]` (freq=1)
  - Chunk 63: `[text_content:h4×1]` (freq=1)
  - Chunk 64: `[text_content:h4×1]` (freq=1)
  - Chunk 65: `[text_content:h4×1]` (freq=1)
  - Chunk 66: `[text_content:h4×1]` (freq=1)
  - Chunk 67: `[text_content:h4×1]` (freq=1)
  - Chunk 68: `[text_content:h2×1]` (freq=1)
  - Chunk 69: `[text_content:h4×1]` (freq=1)
  - Chunk 70: `[text_content:h4×1]` (freq=1)
  - Chunk 71: `[text_content:h4×1]` (freq=1)
  - Chunk 72: `[text_content:h4×1]` (freq=1)
  - Chunk 73: `[text_content:h4×1]` (freq=1)
  - Chunk 74: `[text_content:h4×1]` (freq=1)
  - Chunk 75: `[text_content:h4×1]` (freq=1)
  - Chunk 76: `[text_content:h2×1]` (freq=1)
  - Chunk 77: `[text_content:h4×1]` (freq=1)
  - Chunk 78: `[text_content:h4×1]` (freq=1)
  - Chunk 79: `[text_content:h4×1]` (freq=1)
  - Chunk 80: `[text_content:h4×1]` (freq=1)
  - Chunk 81: `[text_content:h4×1]` (freq=1)
  - Chunk 82: `[text_content:h4×1]` (freq=1)
  - Chunk 83: `[text_content:h4×1]` (freq=1)
  - Chunk 84: `[text_content:h4×1]` (freq=1)
  - Chunk 85: `[text_content:h4×1]` (freq=1)
  - Chunk 86: `[text_content:h4×1]` (freq=1)
  - Chunk 87: `[text_content:h4×1]` (freq=1)
  - Chunk 88: `[text_content:h4×1]` (freq=1)
  - Chunk 89: `[text_content:h4×1]` (freq=1)
  - Chunk 90: `[text_content:h4×1]` (freq=1)
  - Chunk 91: `[text_content:h4×1]` (freq=1)
  - Chunk 92: `[text_content:h4×1]` (freq=1)
  - Chunk 93: `[text_content:h4×1]` (freq=1)
  - Chunk 94: `[text_content:h4×1]` (freq=1)
  - Chunk 95: `[text_content:h4×1]` (freq=1)
  - Chunk 96: `[text_content:h4×1]` (freq=1)
  - Chunk 97: `[text_content:h4×1]` (freq=1)
  - Chunk 98: `[text_content:h4×1]` (freq=1)
  - Chunk 99: `[text_content:h4×1]` (freq=1)
  - Chunk 100: `[text_content:h2×1]` (freq=1)
  - Chunk 101: `[text_content:h4×1]` (freq=1)
  - Chunk 102: `[text_content:h2×1]` (freq=1)
  - Chunk 103: `[text_content:h4×1]` (freq=1)
  - Chunk 104: `[text_content:h2×1]` (freq=1)
  - Chunk 105: `[text_content:h4×1]` (freq=1)
  - Chunk 106: `[text_content:h2×1]` (freq=1)
  - Chunk 107: `[text_content:h4×1]` (freq=1)
  - Chunk 108: `[text_content:h4×1]` (freq=1)
  - Chunk 109: `[text_content:h2×1]` (freq=1)
  - Chunk 110: `[text_content:h4×1]` (freq=1)
  - Chunk 111: `[text_content:h2×1]` (freq=1)
  - Chunk 112: `[text_content:h4×1]` (freq=1)
  - Chunk 113: `[text_content:h4×1]` (freq=1)
  - Chunk 114: `[text_content:h2×1]` (freq=1)
  - Chunk 115: `[text_content:h4×1]` (freq=1)
  - Chunk 116: `[text_content:h4×1]` (freq=1)
  - Chunk 117: `[text_content:h4×1]` (freq=1)
  - Chunk 118: `[text_content:h4×1]` (freq=1)
  - Chunk 119: `[text_content:h4×1]` (freq=1)
  - Chunk 120: `[text_content:h4×1]` (freq=1)
  - Chunk 121: `[text_content:h4×1]` (freq=1)
  - Chunk 122: `[text_content:h4×1]` (freq=1)
  - Chunk 123: `[text_content:h4×1]` (freq=1)
  - Chunk 124: `[text_content:h4×1]` (freq=1)
  - Chunk 125: `[text_content:h4×1]` (freq=1)
  - Chunk 126: `[text_content:h4×1]` (freq=1)
  - Chunk 127: `[text_content:h4×1]` (freq=1)
  - Chunk 128: `[text_content:h2×1]` (freq=1)
  - Chunk 129: `[text_content:h4×1]` (freq=1)
  - Chunk 130: `[text_content:h4×1]` (freq=1)
  - Chunk 131: `[text_content:h4×1]` (freq=1)
  - Chunk 132: `[text_content:h4×1]` (freq=1)
  - Chunk 133: `[text_content:h4×1]` (freq=1)
  - Chunk 134: `[text_content:h4×1]` (freq=1)
  - Chunk 135: `[text_content:h4×1]` (freq=1)
  - Chunk 136: `[text_content:h4×1]` (freq=1)
  - Chunk 137: `[text_content:h2×1]` (freq=1)
  - Chunk 138: `[text_content:h4×1]` (freq=1)
  - Chunk 139: `[text_content:h4×1]` (freq=1)
  - Chunk 140: `[text_content:h2×1]` (freq=1)
  - Chunk 141: `[text_content:h4×1]` (freq=1)
  - Chunk 142: `[text_content:h4×1]` (freq=1)
  - Chunk 143: `[text_content:h4×1]` (freq=1)
  - Chunk 144: `[text_content:h4×1]` (freq=1)
  - Chunk 145: `[text_content:h4×1]` (freq=1)
  - Chunk 146: `[text_content:h4×1]` (freq=1)
  - Chunk 147: `[text_content:h4×1]` (freq=1)
  - Chunk 148: `[text_content:h4×1]` (freq=1)
  - Chunk 149: `[text_content:h4×1]` (freq=1)
  - Chunk 150: `[text_content:h4×1]` (freq=1)
  - Chunk 151: `[text_content:h4×1]` (freq=1)
  - Chunk 152: `[text_content:h4×1]` (freq=1)
  - Chunk 153: `[text_content:h2×1]` (freq=1)
  - Chunk 154: `[text_content:h4×1]` (freq=1)
  - Chunk 155: `[text_content:h4×1]` (freq=1)
  - Chunk 156: `[text_content:h4×1]` (freq=1)
  - Chunk 157: `[text_content:h4×1]` (freq=1)
  - Chunk 158: `[text_content:h4×1]` (freq=1)
  - Chunk 159: `[text_content:h4×1]` (freq=1)
  - Chunk 160: `[text_content:h4×1]` (freq=1)
  - Chunk 161: `[text_content:h4×1]` (freq=1)
  - Chunk 162: `[text_content:h4×1]` (freq=1)
  - Chunk 163: `[text_content:h4×1]` (freq=1)
  - Chunk 164: `[text_content:h2×1]` (freq=1)
  - Chunk 165: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: crystalvaults_comcrystalguide.html ===
Chunks: 166 (structural=4, functional=9, text=153)
Categories: {'card': 3, 'structural': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 153, 'menu_item': 7}
Content: 471 tagged, 382 preserved (81%)
Leaks: 89 total, 50 high-importance

--- Chunk 0: div.bg.col ---
  type=card freq=136 excl=0.80 LEAKS=1
  pattern_xpath: ///div[contains(@class,'bg')][contains(@class,'color')][contains(@class,'small')][contains(@class,'col')][contains(@class,'node')]
  tree_sig: div(div(div(div(div(div(a))))))
  content: [ATTR=2 HREF=1 IMG=1 TEXT=1]
  LEAKS (high):
    [IMG] https://www.crystalvaults.com/wp-content/uploads/2021/12/red-tourmaline.jpg (img URL not in rendered)
  LEAKS (medium):
    [TEXT] <img width="150" height="150" decoding="async" class="fl-photo-img" sr

--- Chunk 1: span.fl.icon ---
  type=card freq=10 excl=0.55
  pattern_xpath: ///div[contains(@class,'icon')][contains(@class,'group')]/span[contains(@class,'icon')][contains(@class,'fl')]
  tree_sig: span(a(i,span))
  content: [HREF=1 TEXT=1]

--- Chunk 2: li.children.custom ---
  type=structural freq=2 excl=0.27
  pattern_xpath: ///li[contains(@class,'children')][contains(@class,'has')][contains(@class,'submenu')][contains(@class,'custom')][contains(@class,'item')]
  tree_sig: li(div(a,span),ul(li(a),li(a),li(a),li(a)))
  content: [ATTR=1 HREF=5 TEXT=5]

--- Chunk 3: p ---
  type=card freq=3 excl=0.00
  pattern_xpath: ///p
  tree_sig: p(span(a))
  content: [HREF=1 TEXT=1]

--- Chunk 4: [search_inputs] ---
  type=search_input freq=11 excl=1.00
  pattern_xpath: ///input[contains(@autocomplete,'off')]
  content: [ATTR=1]

--- Chunk 5: [pagination_buttons] ---
  type=pagination freq=12 excl=0.00 OUTLIER=4.0x
  pattern_xpath: ///button
  content: [ATTR=1]

--- Chunk 6: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.27
  pattern_xpath: ///li[contains(@class,'children')][contains(@class,'has')][contains(@class,'submenu')][contains(@class,'custom')][contains(@class,'item')]
  content: [ATTR=2 HREF=12 TEXT=12]

--- Chunk 7: [text_content:h2×2] ---
  type=text_singleton freq=1 excl=0.53 LEAKS=49
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'col')][contains(@class,'node')][contains(@class,'fl')]
  content: [ATTR=36 HREF=41 IMG=26 TEXT=53]
  LEAKS (high):
    [HREF] https://www.crystalvaults.com/crystal-encyclopedia/adamite/ (href not in rendered output)
    [IMG] https://www.crystalvaults.com/wp-content/uploads/2019/06/192197b-150x150.jpg (img URL not in rendered)
    [IMG] https://www.crystalvaults.com/wp-content/uploads/2019/06/192197b-150x150.jpg (img URL not in rendered)
    [HREF] https://crystalvaults.com/crystal-encyclopedia/blue-fluorite (href not in rendered output)
    [HREF] https://crystalvaults.com/crystal-encyclopedia/brandberg-amethyst (href not in rendered output)
  LEAKS (medium):
    [TEXT] <img width="150" height="150" decoding="async" class="fl-photo-img" sr
    [TEXT] AdamiteAegirineAgateAlmandineAmazoniteAmethystAmberAndraditeAquamarine
    [TEXT] The Stone of Playful NatureThe Stone of ConvictionThe Stone of Inner S

--- Chunk 8: [nav_content:p×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 9: [nav_content:p×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 10: [nav_content:p×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 11: [nav_content:li×17] ---
  type=menu_item freq=17 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 12: [nav_content:li×9] ---
  type=menu_item freq=9 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 13: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 14: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.17
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 15: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h4[contains(@class,'heading')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 18: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'fl')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 24: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 32: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 38: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 40: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 41: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 42: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 43: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 44: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 46: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 47: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 48: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 49: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 50: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 51: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 52: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 53: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 54: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 55: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 56: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 57: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 58: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 59: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 60: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 61: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 62: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 63: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 64: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 65: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 66: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 67: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 68: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 69: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=4 TEXT=5]

--- Chunk 70: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 71: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 72: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 73: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 74: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 75: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 76: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 77: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 78: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 79: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 80: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 81: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=2]

--- Chunk 82: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 83: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 84: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=4 TEXT=5]

--- Chunk 85: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 86: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 87: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 88: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 89: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 90: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 91: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 92: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 93: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 94: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 95: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 96: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 97: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 98: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 99: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 100: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 101: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 102: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 103: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 104: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 105: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 106: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 107: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 108: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 109: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 110: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 111: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 112: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 113: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 114: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 115: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 116: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 117: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 118: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 119: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 120: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 121: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 122: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 123: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 124: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 125: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 126: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 127: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 128: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 129: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 130: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 131: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 132: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 133: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 134: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 135: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 136: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 137: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 138: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 139: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 140: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=1 TEXT=1]

--- Chunk 141: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 142: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 143: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 144: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 145: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 146: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 147: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 148: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 149: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 150: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 151: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 152: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 153: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 154: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=5 TEXT=6]

--- Chunk 155: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 156: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 157: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 158: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 159: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 160: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 161: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 162: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 163: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [TEXT=1]

--- Chunk 164: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///div[contains(@role,'figure')][contains(@class,'photo')][contains(@class,'align')]/h2[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=21 TEXT=23]

--- Chunk 165: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///div[contains(@role,'figure')][contains(@class,'photo')][contains(@class,'align')]/h4[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')]
  content: [HREF=7 TEXT=12]

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
4. Use filename `crystalvaults_comcrystalguide.html` in all `_distill()` calls
5. Name the module `test_crystalvaults_comcrystalguide_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
