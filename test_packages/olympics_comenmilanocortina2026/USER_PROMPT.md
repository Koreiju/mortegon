# Test Generation Task: olympics_comenmilanocortina2026.html

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

- **Total chunks:** 245
- **Structural chunks:** 27
- **Text/Nav chunks:** 216
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `a.com.cortina` (freq=71, pq_sig=`div(div(a(div(div(picture(source,source,source,sou`)
  - Chunk 1: `a.canada.com` (freq=5, pq_sig=`li(div(a(div(div(picture(source,source,source,sour`)
  - Chunk 2: `a.britain.bronze` (freq=2, pq_sig=`div(div(a(div(div(picture(source,source,source,sou`)
  - Chunk 3: `a.all.basketball` (freq=2, pq_sig=`div(div(a(div(div(picture(source,source,source,sou`)
  - Chunk 4: `div.ac.bdqb` (freq=8, pq_sig=`div(div(div(div(div(div(picture),div(div,div))))))`)
  - Chunk 5: `a.bdu.blank` (freq=6, pq_sig=`a(img,span(span))`)
  - Chunk 6: `blaze-widget-item.blaze.button` (freq=13, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 7: `li.bv.gix` (freq=3, pq_sig=`li(div(div,div),div(a(div(span(span(div)),div),spa`)
  - Chunk 8: `blaze-widget-item.blaze.button` (freq=7, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 9: `blaze-widget-item.blaze.button` (freq=4, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 10: `blaze-widget-item.bbd.blaze` (freq=3, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 11: `blaze-widget-item.ad.bdc` (freq=3, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 12: `blaze-widget-item.bf.blaze` (freq=2, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 13: `blaze-widget-item.ace.af` (freq=2, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 14: `blaze-widget-item.af.be` (freq=2, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 15: `blaze-widget-item.ac.bcc` (freq=2, pq_sig=`blaze-widget-item(blaze-div(blaze-div(blaze-chip,b`)
  - Chunk 16: `div.ac.da` (freq=109, pq_sig=`div(picture(img,source,source,source,source,source`)
  - Chunk 17: `div.card.position` (freq=56, pq_sig=`div(picture(img,source,source,source,source,source`)
  - Chunk 18: `div.bad.container` (freq=37, pq_sig=`div(div(svg(path)))`)
  - Chunk 19: `div` (freq=23, pq_sig=`div(div(a(picture(img,source,source,source,source,`)
  - Chunk 20: `div` (freq=20, pq_sig=`div(div(a(div(div(div(div,div)),div(picture(img,so`)
  - Chunk 21: `li.ab.irezc` (freq=32, pq_sig=`li(a(span))`)
  - Chunk 22: `div.be.sc` (freq=9, pq_sig=`div(a(div(div(span),h2)))`)
  - Chunk 23: `div.aacf.cli` (freq=3, pq_sig=`div(picture(img,source,source,source,source))`)
  - Chunk 24: `a.com.ef` (freq=9, pq_sig=`a(picture(img,source,source,source,source,source))`)
  - Chunk 25: `div.gzi.sc` (freq=2, pq_sig=`div(a(section(picture(img,source,source,source,sou`)
  - Chunk 26: `li` (freq=2, pq_sig=`li(a(img))`)

**Text/Nav chunks:**
  - Chunk 29: `[text_content:li×4]` (freq=4)
  - Chunk 30: `[text_content:p×8]` (freq=1)
  - Chunk 31: `[text_content:li×10]` (freq=10)
  - Chunk 32: `[text_content:li×4]` (freq=4)
  - Chunk 33: `[text_content:li×4]` (freq=4)
  - Chunk 34: `[text_content:p×2]` (freq=2)
  - Chunk 35: `[text_content:p×2]` (freq=2)
  - Chunk 36: `[text_content:p×2]` (freq=2)
  - Chunk 37: `[text_content:h3×4]` (freq=4)
  - Chunk 38: `[nav_content:li×4]` (freq=4)
  - Chunk 39: `[nav_content:a×11]` (freq=11)
  - Chunk 40: `[nav_content:li×4]` (freq=4)
  - Chunk 42: `[nav_content:a×15]` (freq=15)
  - Chunk 42: `[nav_content:a×15]` (freq=15)
  - Chunk 43: `[nav_content:a×21]` (freq=21)
  - Chunk 44: `[nav_content:li×5]` (freq=5)
  - Chunk 45: `[nav_content:li×6]` (freq=6)
  - Chunk 46: `[nav_content:li×5]` (freq=5)
  - Chunk 47: `[nav_content:li×8]` (freq=8)
  - Chunk 48: `[nav_content:li×5]` (freq=5)
  - Chunk 49: `[nav_content:a×4]` (freq=4)
  - Chunk 50: `[nav_content:a×4]` (freq=4)
  - Chunk 51: `[nav_content:a×4]` (freq=4)
  - Chunk 52: `[nav_content:a×4]` (freq=4)
  - Chunk 53: `[text_content:h2×1]` (freq=1)
  - Chunk 54: `[text_content:h2×1]` (freq=1)
  - Chunk 55: `[text_content:h3×1]` (freq=1)
  - Chunk 56: `[text_content:h3×1]` (freq=1)
  - Chunk 57: `[text_content:h2×1]` (freq=1)
  - Chunk 58: `[text_content:h4×1]` (freq=1)
  - Chunk 59: `[text_content:h4×1]` (freq=1)
  - Chunk 60: `[text_content:h4×1]` (freq=1)
  - Chunk 61: `[text_content:h4×1]` (freq=1)
  - Chunk 62: `[text_content:h2×1]` (freq=1)
  - Chunk 63: `[text_content:h2×1]` (freq=1)
  - Chunk 64: `[text_content:h2×1]` (freq=1)
  - Chunk 65: `[text_content:h2×1]` (freq=1)
  - Chunk 66: `[text_content:h2×1]` (freq=1)
  - Chunk 67: `[text_content:h2×1]` (freq=1)
  - Chunk 68: `[text_content:h2×1]` (freq=1)
  - Chunk 69: `[text_content:h2×1]` (freq=1)
  - Chunk 70: `[text_content:h2×1]` (freq=1)
  - Chunk 71: `[text_content:h2×1]` (freq=1)
  - Chunk 72: `[text_content:h2×1]` (freq=1)
  - Chunk 73: `[text_content:h2×1]` (freq=1)
  - Chunk 74: `[text_content:h2×1]` (freq=1)
  - Chunk 75: `[text_content:h2×1]` (freq=1)
  - Chunk 76: `[text_content:h2×1]` (freq=1)
  - Chunk 77: `[text_content:h2×1]` (freq=1)
  - Chunk 78: `[text_content:h3×1]` (freq=1)
  - Chunk 79: `[text_content:h2×1]` (freq=1)
  - Chunk 80: `[text_content:h2×1]` (freq=1)
  - Chunk 81: `[text_content:h2×1]` (freq=1)
  - Chunk 82: `[text_content:h2×1]` (freq=1)
  - Chunk 83: `[text_content:h2×1]` (freq=1)
  - Chunk 84: `[text_content:h2×1]` (freq=1)
  - Chunk 85: `[text_content:h2×1]` (freq=1)
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
  - Chunk 102: `[text_content:h2×1]` (freq=1)
  - Chunk 103: `[text_content:h2×1]` (freq=1)
  - Chunk 104: `[text_content:h2×1]` (freq=1)
  - Chunk 105: `[text_content:h2×1]` (freq=1)
  - Chunk 106: `[text_content:h2×1]` (freq=1)
  - Chunk 107: `[text_content:h2×1]` (freq=1)
  - Chunk 108: `[text_content:h2×1]` (freq=1)
  - Chunk 109: `[text_content:h3×1]` (freq=1)
  - Chunk 110: `[text_content:h3×1]` (freq=1)
  - Chunk 111: `[text_content:h3×1]` (freq=1)
  - Chunk 112: `[text_content:h3×1]` (freq=1)
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
  - Chunk 127: `[text_content:h3×1]` (freq=1)
  - Chunk 128: `[text_content:h4×1]` (freq=1)
  - Chunk 129: `[text_content:h4×1]` (freq=1)
  - Chunk 130: `[text_content:h4×1]` (freq=1)
  - Chunk 131: `[text_content:h4×1]` (freq=1)
  - Chunk 132: `[text_content:h4×1]` (freq=1)
  - Chunk 133: `[text_content:h4×1]` (freq=1)
  - Chunk 134: `[text_content:h4×1]` (freq=1)
  - Chunk 135: `[text_content:h4×1]` (freq=1)
  - Chunk 136: `[text_content:h3×1]` (freq=1)
  - Chunk 137: `[text_content:h3×1]` (freq=1)
  - Chunk 138: `[text_content:h3×1]` (freq=1)
  - Chunk 139: `[text_content:h3×1]` (freq=1)
  - Chunk 140: `[text_content:h3×1]` (freq=1)
  - Chunk 141: `[text_content:h3×1]` (freq=1)
  - Chunk 142: `[text_content:h3×1]` (freq=1)
  - Chunk 143: `[text_content:h3×1]` (freq=1)
  - Chunk 144: `[text_content:h3×1]` (freq=1)
  - Chunk 145: `[text_content:h3×1]` (freq=1)
  - Chunk 146: `[text_content:h3×1]` (freq=1)
  - Chunk 147: `[text_content:h3×1]` (freq=1)
  - Chunk 148: `[text_content:h3×1]` (freq=1)
  - Chunk 149: `[text_content:h3×1]` (freq=1)
  - Chunk 150: `[text_content:h3×1]` (freq=1)
  - Chunk 151: `[text_content:h3×1]` (freq=1)
  - Chunk 152: `[text_content:h3×1]` (freq=1)
  - Chunk 153: `[text_content:h3×1]` (freq=1)
  - Chunk 154: `[text_content:h3×1]` (freq=1)
  - Chunk 155: `[text_content:h3×1]` (freq=1)
  - Chunk 156: `[text_content:h3×1]` (freq=1)
  - Chunk 157: `[text_content:h3×1]` (freq=1)
  - Chunk 158: `[text_content:h3×1]` (freq=1)
  - Chunk 159: `[text_content:h3×1]` (freq=1)
  - Chunk 160: `[text_content:h3×1]` (freq=1)
  - Chunk 161: `[text_content:h3×1]` (freq=1)
  - Chunk 162: `[text_content:h3×1]` (freq=1)
  - Chunk 163: `[text_content:h3×1]` (freq=1)
  - Chunk 164: `[text_content:h3×1]` (freq=1)
  - Chunk 165: `[text_content:h3×1]` (freq=1)
  - Chunk 166: `[text_content:h3×1]` (freq=1)
  - Chunk 167: `[text_content:h3×1]` (freq=1)
  - Chunk 168: `[text_content:h3×1]` (freq=1)
  - Chunk 169: `[text_content:h3×1]` (freq=1)
  - Chunk 170: `[text_content:h3×1]` (freq=1)
  - Chunk 171: `[text_content:h3×1]` (freq=1)
  - Chunk 172: `[text_content:h3×1]` (freq=1)
  - Chunk 173: `[text_content:h3×1]` (freq=1)
  - Chunk 174: `[text_content:h3×1]` (freq=1)
  - Chunk 175: `[text_content:h3×1]` (freq=1)
  - Chunk 176: `[text_content:h3×1]` (freq=1)
  - Chunk 177: `[text_content:h3×1]` (freq=1)
  - Chunk 178: `[text_content:h3×1]` (freq=1)
  - Chunk 179: `[text_content:h3×1]` (freq=1)
  - Chunk 180: `[text_content:h3×1]` (freq=1)
  - Chunk 181: `[text_content:h3×1]` (freq=1)
  - Chunk 182: `[text_content:h3×1]` (freq=1)
  - Chunk 183: `[text_content:h3×1]` (freq=1)
  - Chunk 184: `[text_content:h3×1]` (freq=1)
  - Chunk 185: `[text_content:h3×1]` (freq=1)
  - Chunk 186: `[text_content:h3×1]` (freq=1)
  - Chunk 187: `[text_content:h3×1]` (freq=1)
  - Chunk 188: `[text_content:h3×1]` (freq=1)
  - Chunk 189: `[text_content:h3×1]` (freq=1)
  - Chunk 190: `[text_content:h3×1]` (freq=1)
  - Chunk 191: `[text_content:h3×1]` (freq=1)
  - Chunk 192: `[text_content:h3×1]` (freq=1)
  - Chunk 193: `[text_content:h3×1]` (freq=1)
  - Chunk 194: `[text_content:h3×1]` (freq=1)
  - Chunk 195: `[text_content:h3×1]` (freq=1)
  - Chunk 196: `[text_content:h3×1]` (freq=1)
  - Chunk 197: `[text_content:h3×1]` (freq=1)
  - Chunk 198: `[text_content:h3×1]` (freq=1)
  - Chunk 199: `[text_content:h3×1]` (freq=1)
  - Chunk 200: `[text_content:h3×1]` (freq=1)
  - Chunk 201: `[text_content:h3×1]` (freq=1)
  - Chunk 202: `[text_content:h3×1]` (freq=1)
  - Chunk 203: `[text_content:h3×1]` (freq=1)
  - Chunk 204: `[text_content:h3×1]` (freq=1)
  - Chunk 205: `[text_content:h3×1]` (freq=1)
  - Chunk 206: `[text_content:h3×1]` (freq=1)
  - Chunk 207: `[text_content:h3×1]` (freq=1)
  - Chunk 208: `[text_content:h3×1]` (freq=1)
  - Chunk 209: `[text_content:h3×1]` (freq=1)
  - Chunk 210: `[text_content:h3×1]` (freq=1)
  - Chunk 211: `[text_content:h3×1]` (freq=1)
  - Chunk 212: `[text_content:h3×1]` (freq=1)
  - Chunk 213: `[text_content:h3×1]` (freq=1)
  - Chunk 214: `[text_content:h3×1]` (freq=1)
  - Chunk 215: `[text_content:h3×1]` (freq=1)
  - Chunk 216: `[text_content:h3×1]` (freq=1)
  - Chunk 217: `[text_content:h3×1]` (freq=1)
  - Chunk 218: `[text_content:h3×1]` (freq=1)
  - Chunk 219: `[text_content:h3×1]` (freq=1)
  - Chunk 220: `[text_content:h3×1]` (freq=1)
  - Chunk 221: `[text_content:h3×1]` (freq=1)
  - Chunk 222: `[text_content:h3×1]` (freq=1)
  - Chunk 223: `[text_content:h3×1]` (freq=1)
  - Chunk 224: `[text_content:h3×1]` (freq=1)
  - Chunk 225: `[text_content:h3×1]` (freq=1)
  - Chunk 226: `[text_content:h3×1]` (freq=1)
  - Chunk 227: `[text_content:h3×1]` (freq=1)
  - Chunk 228: `[text_content:h3×1]` (freq=1)
  - Chunk 229: `[text_content:h3×1]` (freq=1)
  - Chunk 230: `[text_content:h3×1]` (freq=1)
  - Chunk 231: `[text_content:h3×1]` (freq=1)
  - Chunk 232: `[text_content:h3×1]` (freq=1)
  - Chunk 233: `[text_content:h3×1]` (freq=1)
  - Chunk 234: `[text_content:h3×1]` (freq=1)
  - Chunk 235: `[text_content:h3×1]` (freq=1)
  - Chunk 236: `[text_content:h3×1]` (freq=1)
  - Chunk 237: `[text_content:h3×1]` (freq=1)
  - Chunk 238: `[text_content:h3×1]` (freq=1)
  - Chunk 239: `[text_content:h3×1]` (freq=1)
  - Chunk 240: `[text_content:h3×1]` (freq=1)
  - Chunk 241: `[text_content:h3×1]` (freq=1)
  - Chunk 242: `[text_content:h3×1]` (freq=1)
  - Chunk 243: `[text_content:h3×1]` (freq=1)
  - Chunk 244: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: olympics_comenmilanocortina2026.html ===
Chunks: 245 (structural=27, functional=17, text=201)
Categories: {'card': 22, 'structural': 4, 'menu_item': 16, 'search_input': 1, 'pagination': 1, 'text_singleton': 201}
Content: 750 tagged, 699 preserved (93%)
Leaks: 51 total, 51 high-importance

--- Chunk 0: a.com.cortina ---
  type=card freq=71 excl=0.10
  pattern_xpath: ///a[contains(@target,'self')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')][contains(@data-cy,'link')]
  tree_sig: div(div(a(div(div(picture(source,source,source,source,source,img),span),div(div(
  content: [HREF=1 IMG=22 TEXT=2]

--- Chunk 1: a.canada.com ---
  type=card freq=5 excl=0.10
  pattern_xpath: ///ul[contains(@class,'mbpf')]//a[contains(@target,'self')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')][contains(@data-cy,'link')]
  tree_sig: li(div(a(div(div(picture(source,source,source,source,source,img)),div(div(div,di
  content: [HREF=1 IMG=22 TEXT=2]

--- Chunk 2: a.britain.bronze ---
  type=card freq=2 excl=0.10
  pattern_xpath: ///a[contains(@target,'self')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')][contains(@data-cy,'link')]
  tree_sig: div(div(a(div(div(picture(source,source,source,source,source,img),span),div(div(
  content: [HREF=1 IMG=22 TEXT=1]

--- Chunk 3: a.all.basketball ---
  type=card freq=2 excl=0.10
  pattern_xpath: ///a[contains(@target,'self')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')][contains(@data-cy,'link')]
  tree_sig: div(div(a(div(div(picture(source,source,source,source,source,img)),div(div(div,d
  content: [HREF=1 IMG=22 TEXT=2]

--- Chunk 4: div.ac.bdqb ---
  type=card freq=8 excl=0.40
  pattern_xpath: ///div[contains(@class,'bdqb')][contains(@class,'ia')][contains(@class,'ac')][contains(@class,'da')][contains(@class,'sc')]
  tree_sig: div(div(div(div(div(div(picture),div(div,div))))))
  content: [IMG=22 TEXT=3]

--- Chunk 5: a.bdu.blank ---
  type=card freq=6 excl=0.23
  pattern_xpath: ///div[contains(@data-cy,'action')][contains(@data-cy,'collection')][contains(@data-cy,'wrapper')]//a[contains(@class,'bdu')][contains(@class,'kn')][contains(@target,'blank')][contains(@class,'sc')]
  tree_sig: a(img,span(span))
  content: [HREF=1 IMG=2 TEXT=1]

--- Chunk 6: blaze-widget-item.blaze.button ---
  type=card freq=13 excl=0.14
  pattern_xpath: ///blaze-widget-item[contains(@style,'none')][contains(@aria-haspopup,'dialog')][contains(@aria-keyshortcuts,'enter')][contains(@aria-roledescription,'item')][contains(@aria-roledescription,'widget')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 7: li.bv.gix ---
  type=card freq=3 excl=0.34
  pattern_xpath: ///li[contains(@class,'bv')][contains(@class,'gix')][contains(@class,'sc')]
  tree_sig: li(div(div,div),div(a(div(span(span(div)),div),span)))
  content: [HREF=1 TEXT=2]

--- Chunk 8: blaze-widget-item.blaze.button ---
  type=card freq=7 excl=0.11
  pattern_xpath: ///blaze-widget-item[contains(@aria-haspopup,'dialog')][contains(@aria-keyshortcuts,'enter')][contains(@aria-roledescription,'item')][contains(@aria-roledescription,'widget')][contains(@data-testid,'blaze')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 9: blaze-widget-item.blaze.button ---
  type=card freq=4 excl=0.39
  pattern_xpath: ///blaze-widget-item[contains(@data-testid,'ee')][contains(@data-testid,'cd')][contains(@style,'none')][contains(@aria-haspopup,'dialog')][contains(@aria-keyshortcuts,'enter')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 10: blaze-widget-item.bbd.blaze ---
  type=card freq=3 excl=0.29
  pattern_xpath: ///blaze-widget-item[contains(@data-testid,'fc')][contains(@aria-haspopup,'dialog')][contains(@aria-keyshortcuts,'enter')][contains(@aria-roledescription,'item')][contains(@aria-roledescription,'widget')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 11: blaze-widget-item.ad.bdc ---
  type=card freq=3 excl=0.64
  pattern_xpath: ///blaze-widget-item[contains(@data-testid,'ad')][contains(@data-testid,'bdc')][contains(@data-testid,'ff')][contains(@aria-haspopup,'dialog')][contains(@aria-keyshortcuts,'enter')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 12: blaze-widget-item.bf.blaze ---
  type=structural freq=2 excl=0.82
  pattern_xpath: ///blaze-widget-item[contains(@data-testid,'bf')][contains(@data-testid,'cad')][contains(@data-testid,'dca')][contains(@data-testid,'ec')][contains(@aria-haspopup,'dialog')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 13: blaze-widget-item.ace.af ---
  type=structural freq=2 excl=0.75
  pattern_xpath: ///blaze-widget-item[contains(@data-testid,'abe')][contains(@data-testid,'ace')][contains(@data-testid,'da')][contains(@data-testid,'af')][contains(@style,'none')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 14: blaze-widget-item.af.be ---
  type=structural freq=2 excl=0.52
  pattern_xpath: ///blaze-widget-item[contains(@data-testid,'be')][contains(@data-testid,'af')][contains(@data-testid,'cd')][contains(@data-testid,'de')][contains(@aria-haspopup,'dialog')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 15: blaze-widget-item.ac.bcc ---
  type=structural freq=2 excl=0.82
  pattern_xpath: ///blaze-widget-item[contains(@data-testid,'ce')][contains(@data-testid,'ac')][contains(@data-testid,'bcc')][contains(@data-testid,'dcc')][contains(@aria-haspopup,'dialog')]
  tree_sig: blaze-widget-item(blaze-div(blaze-div(blaze-chip,blaze-chip,blaze-div,blaze-imag
  content: [ATTR=3 IMG=2 TEXT=1]

--- Chunk 16: div.ac.da ---
  type=card freq=109 excl=0.30
  pattern_xpath: ///div[contains(@class,'ji')][contains(@class,'pn')][contains(@class,'qy')][contains(@class,'ac')][contains(@class,'da')]
  tree_sig: div(picture(img,source,source,source,source,source),span)
  content: [IMG=22]

--- Chunk 17: div.card.position ---
  type=card freq=56 excl=0.01
  pattern_xpath: ///div[contains(@class,'sc')]
  tree_sig: div(picture(img,source,source,source,source,source))
  content: [IMG=22]

--- Chunk 18: div.bad.container ---
  type=card freq=37 excl=0.70
  pattern_xpath: ///div[contains(@class,'container')][contains(@class,'eazsw')][contains(@class,'icon')][contains(@class,'bad')][contains(@class,'sc')]
  tree_sig: div(div(svg(path)))

--- Chunk 19: div ---
  type=card freq=23 excl=0.00
  pattern_xpath: ///div
  tree_sig: div(div(a(picture(img,source,source,source,source,source))))
  content: [ATTR=1 HREF=1 IMG=22]

--- Chunk 20: div ---
  type=card freq=20 excl=0.00
  pattern_xpath: ///div
  tree_sig: div(div(a(div(div(div(div,div)),div(picture(img,source,source,source,source,sour
  content: [HREF=1 IMG=22 TEXT=2]

--- Chunk 21: li.ab.irezc ---
  type=menu_item freq=32 excl=0.15
  pattern_xpath: ///ul[contains(@class,'xvqm')][contains(@class,'column')]/li[contains(@class,'irezc')][contains(@class,'ab')][contains(@class,'sc')]
  tree_sig: li(a(span))
  content: [HREF=1 TEXT=1]

--- Chunk 22: div.be.sc ---
  type=card freq=9 excl=0.75
  pattern_xpath: ///div[contains(@class,'be')][contains(@class,'tnk')][contains(@data-cy,'wrapper')][contains(@class,'sc')]
  tree_sig: div(a(div(div(span),h2)))
  content: [ATTR=1 HREF=1 TEXT=2]

--- Chunk 23: div.aacf.cli ---
  type=card freq=3 excl=0.38
  pattern_xpath: ///div[contains(@class,'aacf')][contains(@class,'cli')][contains(@class,'iay')][contains(@class,'sc')]
  tree_sig: div(picture(img,source,source,source,source))
  content: [IMG=9]

--- Chunk 24: a.com.ef ---
  type=card freq=9 excl=0.10
  pattern_xpath: ///a[contains(@target,'self')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')][contains(@data-cy,'link')]
  tree_sig: a(picture(img,source,source,source,source,source))
  content: [ATTR=1 HREF=1 IMG=22]

--- Chunk 25: div.gzi.sc ---
  type=card freq=2 excl=0.67
  pattern_xpath: ///div[contains(@class,'gzi')][contains(@class,'yn')][contains(@class,'sc')]
  tree_sig: div(a(section(picture(img,source,source,source,source,source),span)))
  content: [ATTR=1 HREF=1 IMG=22 TEXT=1]

--- Chunk 26: li ---
  type=card freq=2 excl=0.00 LEAKS=1
  pattern_xpath: ///li
  tree_sig: li(a(img))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=1]
  LEAKS (high):
    [HREF] https://tickets.milanocortina2026.org/en/?utm_medium=ioc_website&utm_source=olympics.com&u (href not in rendered output)

--- Chunk 27: [search_inputs] ---
  type=search_input freq=17 excl=0.13
  pattern_xpath: ///div[contains(@data-cy,'list')][contains(@data-cy,'dropdown')][contains(@class,'bz')]/div[contains(@class,'ea')][contains(@class,'sc')]
  content: [ATTR=2]

--- Chunk 28: [pagination_buttons] ---
  type=pagination freq=142 excl=0.00
  pattern_xpath: ///script
  content: [ATTR=1 TEXT=1]

--- Chunk 29: [text_content:li×4] ---
  type=text_singleton freq=4 excl=1.00
  pattern_xpath: ///li[contains(@class,'bcee')][contains(@class,'fsph')][contains(@class,'mm')][contains(@class,'disabled')][contains(@class,'mobile')]
  content: [TEXT=1]

--- Chunk 30: [text_content:p×8] ---
  type=text_singleton freq=1 excl=0.79
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'grpcntr')][contains(@class,'txt')][contains(@class,'ot')]
  content: [ATTR=4 TEXT=14]

--- Chunk 31: [text_content:li×10] ---
  type=text_singleton freq=10 excl=0.85
  pattern_xpath: ///li[contains(@class,'accordion')][contains(@class,'lidmc')][contains(@data-cy,'accordion')][contains(@data-cy,'item')][contains(@class,'item')]
  content: [TEXT=3]

--- Chunk 32: [text_content:li×4] ---
  type=text_singleton freq=4 excl=0.37 LEAKS=3
  pattern_xpath: ///li[contains(@aria-hidden,'true')][contains(@class,'carousel')][contains(@class,'multi')][contains(@class,'react')][contains(@style,'auto')]
  content: [ATTR=6 HREF=4 IMG=4 TEXT=4]
  LEAKS (high):
    [IMG] https://gstatic.olympics.com/s3/mc2026/pictograms/oly/dark/big/BTH.svg (img URL not in rendered)
    [IMG] https://gstatic.olympics.com/s3/mc2026/pictograms/oly/dark/big/BOB.svg (img URL not in rendered)
    [IMG] https://gstatic.olympics.com/s3/mc2026/pictograms/oly/dark/big/CCS.svg (img URL not in rendered)

--- Chunk 33: [text_content:li×4] ---
  type=text_singleton freq=4 excl=0.37 LEAKS=3
  pattern_xpath: ///div[contains(@class,'dff')][contains(@class,'fr')][contains(@class,'kz')]//li[contains(@aria-hidden,'true')][contains(@class,'carousel')][contains(@class,'multi')][contains(@class,'react')][contains(@style,'auto')]
  content: [ATTR=9 HREF=7 IMG=4 TEXT=7]
  LEAKS (high):
    [IMG] https://gstatic.olympics.com/s3/mc2026/pictograms/oly/dark/big/BTH.svg (img URL not in rendered)
    [IMG] https://gstatic.olympics.com/s3/mc2026/pictograms/oly/dark/big/BOB.svg (img URL not in rendered)
    [IMG] https://gstatic.olympics.com/s3/mc2026/pictograms/oly/dark/big/CCS.svg (img URL not in rendered)

--- Chunk 34: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 35: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 36: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 37: [text_content:h3×4] ---
  type=text_singleton freq=4 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 38: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.25
  pattern_xpath: ///li[contains(@class,'dhz')][contains(@class,'sc')]
  content: [ATTR=1 HREF=1 IMG=6]

--- Chunk 39: [nav_content:a×11] ---
  type=menu_item freq=11 excl=0.80
  pattern_xpath: ///a[contains(@class,'kj')][contains(@class,'lzlb')][contains(@data-cy,'olympics')][contains(@data-cy,'element')][contains(@data-cy,'grid')]
  content: [ATTR=1 HREF=1 IMG=6]

--- Chunk 40: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.15
  pattern_xpath: ///li[contains(@class,'irezc')][contains(@class,'ab')][contains(@class,'sc')]
  content: [HREF=1 TEXT=1]

--- Chunk 42: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 IMG=2 TEXT=1]

--- Chunk 42: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 IMG=2 TEXT=1]

--- Chunk 43: [nav_content:a×21] ---
  type=menu_item freq=21 excl=0.01
  pattern_xpath: ///a[contains(@class,'sc')]
  content: [ATTR=1 HREF=1 IMG=3]

--- Chunk 44: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.15
  pattern_xpath: ///div[contains(@aria-labelledby,'ed')][contains(@aria-labelledby,'ff')][contains(@aria-labelledby,'daaed')]//li[contains(@class,'irezc')][contains(@class,'ab')][contains(@class,'sc')]
  content: [HREF=1 TEXT=1]

--- Chunk 45: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.15
  pattern_xpath: ///li[contains(@class,'irezc')][contains(@class,'ab')][contains(@class,'sc')]
  content: [ATTR=2 HREF=1 IMG=1]

--- Chunk 46: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 47: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.01
  pattern_xpath: ///ul[contains(@class,'fafc')][contains(@class,'pulz')]//li[contains(@class,'sc')]
  content: [HREF=1 TEXT=1]

--- Chunk 48: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.34
  pattern_xpath: ///li[contains(@class,'bv')][contains(@class,'gix')][contains(@class,'sc')]
  content: [HREF=1 TEXT=2]

--- Chunk 49: [nav_content:a×4] ---
  type=menu_item freq=4 excl=0.16
  pattern_xpath: ///a[contains(@class,'hxv')][contains(@class,'jis')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')]
  content: [HREF=1]

--- Chunk 50: [nav_content:a×4] ---
  type=menu_item freq=4 excl=0.16
  pattern_xpath: ///a[contains(@class,'hxv')][contains(@class,'jis')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')]
  content: [HREF=1]

--- Chunk 51: [nav_content:a×4] ---
  type=menu_item freq=4 excl=0.16
  pattern_xpath: ///a[contains(@class,'hxv')][contains(@class,'jis')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')]
  content: [HREF=1]

--- Chunk 52: [nav_content:a×4] ---
  type=menu_item freq=4 excl=0.16
  pattern_xpath: ///a[contains(@class,'hxv')][contains(@class,'jis')][contains(@class,'ef')][contains(@class,'ewn')][contains(@class,'fop')]
  content: [HREF=1]

--- Chunk 53: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.40
  pattern_xpath: ///h2[contains(@id,'pc')][contains(@id,'ot')][contains(@id,'title')]
  content: [TEXT=1]

--- Chunk 54: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.73
  pattern_xpath: ///h2[contains(@id,'links')][contains(@id,'skip')][contains(@id,'to')][contains(@class,'only')][contains(@class,'sr')]
  content: [TEXT=1]

--- Chunk 55: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.40
  pattern_xpath: ///h3[contains(@id,'category')][contains(@id,'ot')][contains(@id,'title')]
  content: [TEXT=1]

--- Chunk 56: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 57: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.68
  pattern_xpath: ///h2[contains(@id,'onetrust')][contains(@id,'policy')][contains(@id,'title')]
  content: [TEXT=1]

--- Chunk 58: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.22
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'hdr')][contains(@class,'always')]/h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'id')][contains(@id,'header')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 59: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.22
  pattern_xpath: ///h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'id')][contains(@id,'header')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 60: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.22
  pattern_xpath: ///h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'id')][contains(@id,'header')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 61: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.22
  pattern_xpath: ///h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'id')][contains(@id,'header')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 62: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 63: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 64: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///h2[contains(@class,'ml')][contains(@class,'yh')][contains(@class,'hvhjw')][contains(@data-cy,'module')][contains(@data-cy,'text')]
  content: [TEXT=1]

--- Chunk 65: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///h2[contains(@class,'ml')][contains(@class,'yh')][contains(@class,'hvhjw')][contains(@data-cy,'module')][contains(@data-cy,'text')]
  content: [TEXT=1]

--- Chunk 66: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.33
  pattern_xpath: ///div[contains(@data-cy,'action')][contains(@data-cy,'collection')][contains(@data-cy,'wrapper')]/h2[contains(@class,'ae')][contains(@class,'myq')][contains(@class,'ra')][contains(@data-cy,'module')][contains(@data-cy,'text')]
  content: [TEXT=1]

--- Chunk 67: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 68: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 69: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.33
  pattern_xpath: ///div[contains(@class,'aacf')][contains(@class,'hs')][contains(@class,'cdb')]/h2[contains(@class,'ae')][contains(@class,'myq')][contains(@class,'ra')][contains(@data-cy,'module')][contains(@data-cy,'text')]
  content: [TEXT=1]

--- Chunk 70: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.63
  pattern_xpath: ///h2[contains(@class,'dcm')][contains(@class,'iv')][contains(@class,'fa')][contains(@class,'ff')][contains(@class,'hvhjw')]
  content: [TEXT=1]

--- Chunk 71: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 72: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 73: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 74: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 75: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///div[contains(@dir,'ltr')]/h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 76: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.47
  pattern_xpath: ///h2[contains(@id,'nav')][contains(@class,'only')][contains(@class,'sr')][contains(@id,'header')]
  content: [TEXT=1]

--- Chunk 77: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///div[contains(@data-box-info-infowrapper,'true')][contains(@class,'njsu')]//h2[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 78: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.62
  pattern_xpath: ///div[contains(@class,'bcf')][contains(@class,'ij')][contains(@class,'zp')]//h3[contains(@class,'qq')][contains(@class,'vh')][contains(@data-cy,'territories')][contains(@class,'fd')][contains(@class,'lh')]
  content: [TEXT=1]

--- Chunk 79: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///div[contains(@data-box-info-infowrapper,'true')][contains(@class,'uvq')][contains(@class,'yz')]//h2[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 80: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h2[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 81: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///div[contains(@data-box-info-infowrapper,'true')][contains(@class,'mre')][contains(@class,'wm')]//h2[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 82: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h2[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 83: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///div[contains(@data-cy,'section')][contains(@data-cy,'viewed')][contains(@data-cy,'tracking')]/h2[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=5]

--- Chunk 84: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.56
  pattern_xpath: ///div[contains(@class,'aa')][contains(@class,'hsc')][contains(@class,'drb')]//h2[contains(@id,'quicklinks')][contains(@class,'only')][contains(@class,'sr')]
  content: [TEXT=1]

--- Chunk 85: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h2[contains(@class,'gr')][contains(@class,'mw')][contains(@class,'nk')][contains(@class,'fd')][contains(@data-cy,'module')]
  content: [TEXT=1]

--- Chunk 86: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 87: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 88: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 89: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 90: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 91: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 92: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 93: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 94: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 95: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 96: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 97: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 98: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 99: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 100: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 101: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h3[contains(@class,'wjpxd')][contains(@id,'card')][contains(@id,'discipline')][contains(@id,'title')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 102: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h2[contains(@class,'hp')][contains(@class,'xjf')][contains(@data-cy,'adjustable')][contains(@class,'nn')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 103: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h2[contains(@class,'hp')][contains(@class,'xjf')][contains(@data-cy,'adjustable')][contains(@class,'nn')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 104: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h2[contains(@class,'hp')][contains(@class,'xjf')][contains(@data-cy,'adjustable')][contains(@class,'nn')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 105: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h2[contains(@class,'hp')][contains(@class,'xjf')][contains(@data-cy,'adjustable')][contains(@class,'nn')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 106: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h2[contains(@class,'hp')][contains(@class,'xjf')][contains(@data-cy,'adjustable')][contains(@class,'nn')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 107: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h2[contains(@class,'hp')][contains(@class,'xjf')][contains(@data-cy,'adjustable')][contains(@class,'nn')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 108: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h2[contains(@class,'hp')][contains(@class,'xjf')][contains(@data-cy,'adjustable')][contains(@class,'nn')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 109: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 110: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 111: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 112: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 113: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 114: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 115: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 116: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 117: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 118: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 119: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 120: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 121: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 122: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=1]

--- Chunk 123: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=3]

--- Chunk 124: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=3]

--- Chunk 125: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///div[contains(@data-cy,'image')][contains(@class,'dd')][contains(@class,'cj')]//h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=3]

--- Chunk 126: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=3]

--- Chunk 127: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h3[contains(@class,'ird')][contains(@class,'jfp')][contains(@class,'ow')][contains(@class,'vr')][contains(@data-cy,'box')]
  content: [TEXT=3]

--- Chunk 128: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 129: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 130: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 131: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 132: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 133: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 134: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 135: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'bold')][contains(@class,'small')][contains(@class,'zm')][contains(@class,'zq')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 136: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 137: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 138: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 139: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 140: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 141: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 142: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 143: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 144: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 145: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 146: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 147: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 148: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 149: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 150: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 151: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 152: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 153: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 154: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 155: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 156: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 157: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 158: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 159: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 160: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 161: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 162: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 163: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 164: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 165: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 166: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 167: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 168: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 169: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 170: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 171: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 172: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 173: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 174: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 175: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 176: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 177: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 178: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 179: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 180: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 181: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 182: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 183: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 184: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 185: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 186: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 187: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 188: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 189: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 190: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 191: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 192: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 193: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 194: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 195: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 196: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 197: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 198: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 199: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 200: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 201: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 202: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 203: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 204: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 205: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 206: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 207: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 208: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 209: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 210: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 211: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 212: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 213: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 214: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 215: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 216: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 217: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 218: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 219: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 220: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 221: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 222: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 223: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 224: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 225: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 226: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 227: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 228: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 229: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 230: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 231: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 232: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 233: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 234: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 235: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 236: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 237: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 238: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 239: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 240: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 241: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 242: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 243: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'lh')][contains(@class,'qf')][contains(@class,'semibold')][contains(@class,'te')][contains(@class,'fmsh')]
  content: [TEXT=1]

--- Chunk 244: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.33 LEAKS=44
  pattern_xpath: ///li[contains(@aria-hidden,'false')][contains(@class,'active')][contains(@class,'carousel')][contains(@class,'multi')][contains(@class,'react')]
  content: [ATTR=2 HREF=3 IMG=66 TEXT=5]
  LEAKS (high):
    [IMG] https://img.olympics.com/images/image/private/t_16-9_760/f_auto/primary/cxoddiomgqtbmcsmte (img URL not in rendered)
    [IMG] https://img.olympics.com/images/image/private/t_16-9_1280/f_auto/primary/cxoddiomgqtbmcsmt (img URL not in rendered)
    [IMG] https://img.olympics.com/images/image/private/t_16-9_760/f_auto/primary/cxoddiomgqtbmcsmte (img URL not in rendered)
    [IMG] https://img.olympics.com/images/image/private/t_16-9_1280/f_auto/primary/cxoddiomgqtbmcsmt (img URL not in rendered)
    [IMG] https://img.olympics.com/images/image/private/t_16-9_760/f_auto/primary/cxoddiomgqtbmcsmte (img URL not in rendered)

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
4. Use filename `olympics_comenmilanocortina2026.html` in all `_distill()` calls
5. Name the module `test_olympics_comenmilanocortina2026_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
