# Test Generation Task: tastedive_commovieslikeBat21.html

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

- **Total chunks:** 192
- **Structural chunks:** 4
- **Text/Nav chunks:** 186
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.sc.slrv` (freq=332, pq_sig=`div(div(img))`)
  - Chunk 1: `div.icon.kswo` (freq=921, pq_sig=`div(svg(path))`)
  - Chunk 2: `div.ff.hiz` (freq=13, pq_sig=`div(button(img))`)
  - Chunk 3: `div.da.rwrhy` (freq=6, pq_sig=`div(div(img),div(img),div(img))`)

**Text/Nav chunks:**
  - Chunk 6: `[text_content:p×2]` (freq=1)
  - Chunk 7: `[text_content:p×2]` (freq=2)
  - Chunk 8: `[text_content:p×3]` (freq=3)
  - Chunk 9: `[text_content:p×2]` (freq=2)
  - Chunk 10: `[text_content:p×3]` (freq=3)
  - Chunk 11: `[text_content:p×2]` (freq=2)
  - Chunk 12: `[text_content:p×4]` (freq=4)
  - Chunk 13: `[text_content:p×2]` (freq=2)
  - Chunk 14: `[text_content:p×3]` (freq=3)
  - Chunk 15: `[text_content:p×2]` (freq=2)
  - Chunk 16: `[text_content:p×2]` (freq=2)
  - Chunk 17: `[text_content:p×2]` (freq=2)
  - Chunk 18: `[text_content:p×2]` (freq=2)
  - Chunk 19: `[text_content:p×2]` (freq=2)
  - Chunk 20: `[text_content:p×2]` (freq=2)
  - Chunk 21: `[nav_content:a×10]` (freq=10)
  - Chunk 22: `[nav_content:a×13]` (freq=13)
  - Chunk 23: `[nav_content:a×146]` (freq=146)
  - Chunk 24: `[text_content:h2×1]` (freq=1)
  - Chunk 25: `[text_content:h3×1]` (freq=1)
  - Chunk 26: `[text_content:h3×1]` (freq=1)
  - Chunk 27: `[text_content:h2×1]` (freq=1)
  - Chunk 28: `[text_content:h2×1]` (freq=1)
  - Chunk 29: `[text_content:h2×1]` (freq=1)
  - Chunk 30: `[text_content:h2×1]` (freq=1)
  - Chunk 31: `[text_content:h2×1]` (freq=1)
  - Chunk 32: `[text_content:h4×1]` (freq=1)
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
  - Chunk 43: `[text_content:h3×1]` (freq=1)
  - Chunk 44: `[text_content:h3×1]` (freq=1)
  - Chunk 45: `[text_content:h3×1]` (freq=1)
  - Chunk 46: `[text_content:h3×1]` (freq=1)
  - Chunk 47: `[text_content:h3×1]` (freq=1)
  - Chunk 48: `[text_content:h3×1]` (freq=1)
  - Chunk 49: `[text_content:h3×1]` (freq=1)
  - Chunk 50: `[text_content:h3×1]` (freq=1)
  - Chunk 51: `[text_content:h3×1]` (freq=1)
  - Chunk 52: `[text_content:h3×1]` (freq=1)
  - Chunk 53: `[text_content:h3×1]` (freq=1)
  - Chunk 54: `[text_content:h3×1]` (freq=1)
  - Chunk 55: `[text_content:h3×1]` (freq=1)
  - Chunk 56: `[text_content:h3×1]` (freq=1)
  - Chunk 57: `[text_content:h3×1]` (freq=1)
  - Chunk 58: `[text_content:h3×1]` (freq=1)
  - Chunk 59: `[text_content:h3×1]` (freq=1)
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
  - Chunk 81: `[text_content:h3×1]` (freq=1)
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
  - Chunk 128: `[text_content:h3×1]` (freq=1)
  - Chunk 129: `[text_content:h3×1]` (freq=1)
  - Chunk 130: `[text_content:h3×1]` (freq=1)
  - Chunk 131: `[text_content:h3×1]` (freq=1)
  - Chunk 132: `[text_content:h3×1]` (freq=1)
  - Chunk 133: `[text_content:h3×1]` (freq=1)
  - Chunk 134: `[text_content:h3×1]` (freq=1)
  - Chunk 135: `[text_content:h3×1]` (freq=1)
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

## Quality Report Summary

```
=== QUALITY REPORT: tastedive_commovieslikeBat21.html ===
Chunks: 192 (structural=4, functional=5, text=183)
Categories: {'card': 3, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 183, 'menu_item': 3}
Content: 246 tagged, 240 preserved (98%)
Leaks: 6 total, 6 high-importance

--- Chunk 0: div.sc.slrv ---
  type=card freq=332 excl=0.50
  pattern_xpath: ///div[contains(@class,'slrv')][contains(@class,'sc')]
  tree_sig: div(div(img))
  content: [ATTR=1 IMG=3]

--- Chunk 1: div.icon.kswo ---
  type=card freq=921 excl=0.80
  pattern_xpath: ///div[contains(@class,'icon')][contains(@class,'kswo')][contains(@class,'opine')][contains(@class,'wrapper')][contains(@class,'sc')]
  tree_sig: div(svg(path))

--- Chunk 2: div.ff.hiz ---
  type=button freq=13 excl=0.56
  pattern_xpath: ///div[contains(@class,'hiz')][contains(@class,'pc')][contains(@class,'ff')][contains(@class,'sc')]
  tree_sig: div(button(img))
  content: [ATTR=1 IMG=1]

--- Chunk 3: div.da.rwrhy ---
  type=card freq=6 excl=0.67 LEAKS=6
  pattern_xpath: ///div[contains(@class,'da')][contains(@class,'rwrhy')][contains(@class,'sc')]
  tree_sig: div(div(img),div(img),div(img))
  content: [ATTR=3 IMG=9]
  LEAKS (high):
    [IMG] https://images.qloo.com/i/7ff43a30-f1c8-4921-8e88-8ee7b650f5d3-127x180-outside.webp (img URL not in rendered)
    [IMG] https://images.qloo.com/i/7ff43a30-f1c8-4921-8e88-8ee7b650f5d3-126x90-outside.webp (img URL not in rendered)
    [IMG] https://images.qloo.com/i/7ff43a30-f1c8-4921-8e88-8ee7b650f5d3-252x180-outside.webp (img URL not in rendered)
    [IMG] https://images.qloo.com/i/72d0caae-6996-4cee-b11e-7a520b81dd12-127x180-outside.webp (img URL not in rendered)
    [IMG] https://images.qloo.com/i/72d0caae-6996-4cee-b11e-7a520b81dd12-126x90-outside.webp (img URL not in rendered)

--- Chunk 4: [search_inputs] ---
  type=search_input freq=4 excl=1.00
  pattern_xpath: ///input[contains(@id,'search')][contains(@name,'search')][contains(@type,'text')][contains(@autocomplete,'off')][contains(@class,'bw')]
  content: [ATTR=2]

--- Chunk 5: [pagination_buttons] ---
  type=pagination freq=65 excl=0.00
  pattern_xpath: ///script
  content: [ATTR=1 TEXT=1]

--- Chunk 6: [text_content:p×2] ---
  type=text_singleton freq=1 excl=0.83
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'grpcntr')][contains(@class,'txt')][contains(@class,'ot')]
  content: [TEXT=3]

--- Chunk 7: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 8: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 9: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 10: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 11: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 12: [text_content:p×4] ---
  type=text_singleton freq=4 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 13: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 14: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 15: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 16: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 17: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 18: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 19: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 20: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 21: [nav_content:a×10] ---
  type=menu_item freq=10 excl=0.75
  pattern_xpath: ///a[contains(@class,'aj')][contains(@class,'eed')][contains(@class,'gm')][contains(@class,'sc')]
  content: [HREF=1 TEXT=1]

--- Chunk 22: [nav_content:a×13] ---
  type=menu_item freq=13 excl=0.50
  pattern_xpath: ///div[contains(@class,'ca')][contains(@class,'sf')][contains(@class,'hr')]//a[contains(@class,'cn')][contains(@class,'de')][contains(@class,'ed')][contains(@class,'gn')][contains(@class,'ka')]
  content: [ATTR=6 HREF=1 IMG=4 TEXT=5]

--- Chunk 23: [nav_content:a×146] ---
  type=menu_item freq=146 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=9 HREF=1 IMG=6 TEXT=5]

--- Chunk 24: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.58
  pattern_xpath: ///h2[contains(@id,'pc')][contains(@id,'title')][contains(@id,'ot')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.58
  pattern_xpath: ///h3[contains(@id,'category')][contains(@id,'title')][contains(@id,'ot')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 27: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.62
  pattern_xpath: ///h2[contains(@class,'ij')][contains(@class,'ur')][contains(@class,'xd')][contains(@class,'ab')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///div[contains(@class,'ji')][contains(@class,'ku')]/h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.87
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'hdr')][contains(@class,'always')]/h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'header')][contains(@id,'id')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.52
  pattern_xpath: ///h2[contains(@class,'ir')][contains(@class,'syk')][contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.50
  pattern_xpath: ///div[contains(@class,'kru')][contains(@class,'al')]/h2[contains(@class,'difxl')][contains(@class,'hy')][contains(@class,'io')][contains(@class,'nz')][contains(@color,'music')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'eh')][contains(@class,'jy')][contains(@class,'jyq')][contains(@class,'uch')][contains(@color,'shows')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'gicd')][contains(@class,'ii')][contains(@class,'im')][contains(@class,'qvxr')][contains(@color,'books')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'ci')][contains(@class,'gixw')][contains(@class,'sd')][contains(@class,'zp')][contains(@color,'games')]
  content: [TEXT=1]

--- Chunk 38: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'bf')][contains(@class,'gk')][contains(@class,'hat')][contains(@class,'rdp')][contains(@color,'podcasts')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.82
  pattern_xpath: ///h2[contains(@class,'lr')][contains(@class,'ote')][contains(@class,'pq')][contains(@color,'people')][contains(@class,'ab')]
  content: [TEXT=1]

--- Chunk 40: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'bm')][contains(@class,'jc')][contains(@class,'jzwn')][contains(@class,'km')][contains(@class,'sx')]
  content: [TEXT=1]

--- Chunk 41: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'btt')][contains(@class,'iq')][contains(@class,'up')][contains(@class,'vn')][contains(@color,'brands')]
  content: [TEXT=1]

--- Chunk 42: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.50
  pattern_xpath: ///div[contains(@class,'de')][contains(@class,'jhg')][contains(@class,'ji')]/h2[contains(@class,'difxl')][contains(@class,'hy')][contains(@class,'io')][contains(@class,'nz')][contains(@color,'music')]
  content: [TEXT=1]

--- Chunk 43: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.12
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 44: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.12
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.12
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 46: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 47: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 48: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 49: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 50: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 51: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 52: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 53: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 54: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 55: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 56: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 57: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 58: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 59: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 60: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 61: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 62: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 63: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 64: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 65: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 66: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 67: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 68: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 69: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 70: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 71: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 72: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 73: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 74: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 75: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 76: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 77: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 78: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 79: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 80: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 81: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 82: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 83: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 84: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 85: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 86: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 87: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 88: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 89: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 90: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 91: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 92: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 93: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 94: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 95: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 96: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 97: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 98: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 99: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 100: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 101: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 102: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 103: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 104: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 105: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 106: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 107: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 108: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 109: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 110: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 111: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 112: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 113: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 114: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 115: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 116: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 117: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 118: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 119: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 120: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 121: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 122: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 123: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 124: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 125: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 126: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 127: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 128: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 129: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 130: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 131: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 132: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 133: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 134: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 135: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 136: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 137: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 138: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 139: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 140: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 141: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 142: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 143: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 144: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 145: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 146: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 147: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 148: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 149: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 150: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 151: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 152: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 153: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 154: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 155: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 156: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 157: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 158: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 159: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 160: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 161: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 162: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 163: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 164: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 165: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 166: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 167: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 168: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 169: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 170: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 171: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 172: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 173: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 174: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 175: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 176: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 177: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 178: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 179: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 180: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 181: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 182: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 183: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 184: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 185: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 186: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 187: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 188: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 189: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 190: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 191: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.01
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
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
4. Use filename `tastedive_commovieslikeBat21.html` in all `_distill()` calls
5. Name the module `test_tastedive_commovieslikeBat21_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
