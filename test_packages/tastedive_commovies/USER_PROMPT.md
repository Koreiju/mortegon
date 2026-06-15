# Test Generation Task: tastedive_commovies.html

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

- **Total chunks:** 68
- **Structural chunks:** 4
- **Text/Nav chunks:** 62
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.icon.kswo` (freq=292, pq_sig=`div(svg(path))`)
  - Chunk 1: `div.bs.da` (freq=105, pq_sig=`div(div(img))`)
  - Chunk 2: `div.ff.hiz` (freq=12, pq_sig=`div(button(img))`)
  - Chunk 3: `div.sc.slrv` (freq=24, pq_sig=`div(div(div(img)))`)

**Text/Nav chunks:**
  - Chunk 6: `[text_content:p×2]` (freq=1)
  - Chunk 7: `[nav_content:a×10]` (freq=10)
  - Chunk 8: `[nav_content:a×36]` (freq=36)
  - Chunk 9: `[nav_content:a×16]` (freq=16)
  - Chunk 10: `[text_content:h2×1]` (freq=1)
  - Chunk 11: `[text_content:h3×1]` (freq=1)
  - Chunk 12: `[text_content:h3×1]` (freq=1)
  - Chunk 13: `[text_content:h2×1]` (freq=1)
  - Chunk 14: `[text_content:h2×1]` (freq=1)
  - Chunk 15: `[text_content:h2×1]` (freq=1)
  - Chunk 16: `[text_content:h2×1]` (freq=1)
  - Chunk 17: `[text_content:h2×1]` (freq=1)
  - Chunk 18: `[text_content:h4×1]` (freq=1)
  - Chunk 19: `[text_content:h2×1]` (freq=1)
  - Chunk 20: `[text_content:h3×1]` (freq=1)
  - Chunk 21: `[text_content:h3×1]` (freq=1)
  - Chunk 22: `[text_content:h3×1]` (freq=1)
  - Chunk 23: `[text_content:h3×1]` (freq=1)
  - Chunk 24: `[text_content:h3×1]` (freq=1)
  - Chunk 25: `[text_content:h3×1]` (freq=1)
  - Chunk 26: `[text_content:h3×1]` (freq=1)
  - Chunk 27: `[text_content:h3×1]` (freq=1)
  - Chunk 28: `[text_content:h3×1]` (freq=1)
  - Chunk 29: `[text_content:h3×1]` (freq=1)
  - Chunk 30: `[text_content:h3×1]` (freq=1)
  - Chunk 31: `[text_content:h3×1]` (freq=1)
  - Chunk 32: `[text_content:h3×1]` (freq=1)
  - Chunk 33: `[text_content:h3×1]` (freq=1)
  - Chunk 34: `[text_content:h3×1]` (freq=1)
  - Chunk 35: `[text_content:h3×1]` (freq=1)
  - Chunk 36: `[text_content:h3×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h3×1]` (freq=1)
  - Chunk 39: `[text_content:h3×1]` (freq=1)
  - Chunk 40: `[text_content:h3×1]` (freq=1)
  - Chunk 41: `[text_content:h3×1]` (freq=1)
  - Chunk 42: `[text_content:h3×1]` (freq=1)
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

## Quality Report Summary

```
=== QUALITY REPORT: tastedive_commovies.html ===
Chunks: 68 (structural=4, functional=5, text=59)
Categories: {'card': 3, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 59, 'menu_item': 3}
Content: 113 tagged, 113 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.icon.kswo ---
  type=card freq=292 excl=0.80
  pattern_xpath: ///div[contains(@class,'icon')][contains(@class,'kswo')][contains(@class,'opine')][contains(@class,'wrapper')][contains(@class,'sc')]
  tree_sig: div(svg(path))

--- Chunk 1: div.bs.da ---
  type=card freq=105 excl=0.02
  pattern_xpath: ///div[contains(@class,'sc')]
  tree_sig: div(div(img))
  content: [ATTR=1 IMG=1]

--- Chunk 2: div.ff.hiz ---
  type=button freq=12 excl=0.59
  pattern_xpath: ///div[contains(@class,'hiz')][contains(@class,'pc')][contains(@class,'ff')][contains(@class,'sc')]
  tree_sig: div(button(img))
  content: [ATTR=1 IMG=1]

--- Chunk 3: div.sc.slrv ---
  type=card freq=24 excl=0.51
  pattern_xpath: ///div[contains(@class,'slrv')][contains(@class,'sc')]
  tree_sig: div(div(div(img)))
  content: [ATTR=1 BG=1 IMG=1]

--- Chunk 4: [search_inputs] ---
  type=search_input freq=4 excl=1.00
  pattern_xpath: ///input[contains(@id,'search')][contains(@name,'search')][contains(@type,'text')][contains(@autocomplete,'off')][contains(@class,'bw')]
  content: [ATTR=2]

--- Chunk 5: [pagination_buttons] ---
  type=pagination freq=67 excl=0.00
  pattern_xpath: ///script
  content: [ATTR=1 TEXT=1]

--- Chunk 6: [text_content:p×2] ---
  type=text_singleton freq=1 excl=0.83
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'grpcntr')][contains(@class,'txt')][contains(@class,'ot')]
  content: [TEXT=3]

--- Chunk 7: [nav_content:a×10] ---
  type=menu_item freq=10 excl=0.75
  pattern_xpath: ///a[contains(@class,'aj')][contains(@class,'eed')][contains(@class,'gm')][contains(@class,'sc')]
  content: [HREF=1 TEXT=1]

--- Chunk 8: [nav_content:a×36] ---
  type=menu_item freq=36 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=9 BG=2 HREF=1 IMG=2 TEXT=5]

--- Chunk 9: [nav_content:a×16] ---
  type=menu_item freq=16 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=9 HREF=1 IMG=6 TEXT=4]

--- Chunk 10: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.58
  pattern_xpath: ///h2[contains(@id,'pc')][contains(@id,'title')][contains(@id,'ot')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.58
  pattern_xpath: ///h3[contains(@id,'category')][contains(@id,'title')][contains(@id,'ot')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 13: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.51
  pattern_xpath: ///div[contains(@class,'ld')][contains(@class,'ufr')][contains(@class,'di')]/h2[contains(@class,'godmm')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///div[contains(@class,'ji')][contains(@class,'ku')]/h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 18: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.87
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'hdr')][contains(@class,'always')]/h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'header')][contains(@id,'id')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.15
  pattern_xpath: ///h2[contains(@class,'au')][contains(@class,'tf')][contains(@color,'black')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 24: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 38: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 40: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 41: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 42: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 43: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h3[contains(@class,'uk')][contains(@class,'yv')][contains(@class,'dd')][contains(@class,'gpfsqs')][contains(@class,'sc')]
  content: [TEXT=1]

--- Chunk 44: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 46: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 47: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 48: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 49: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 50: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 51: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 52: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 53: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 54: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 55: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 56: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 57: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 58: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 59: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 60: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 61: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 62: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 63: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 64: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 65: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 66: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
  pattern_xpath: ///h3[contains(@class,'card')][contains(@class,'doy')][contains(@class,'entity')][contains(@class,'hlt')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 67: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.03
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
4. Use filename `tastedive_commovies.html` in all `_distill()` calls
5. Name the module `test_tastedive_commovies_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
