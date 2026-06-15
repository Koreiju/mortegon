# Test Generation Task: asccybernetics_orgdefinitions.html

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

- **Total chunks:** 14
- **Structural chunks:** 0
- **Text/Nav chunks:** 12
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**


**Text/Nav chunks:**
  - Chunk 2: `[text_content:p×110]` (freq=110)
  - Chunk 3: `[text_content:li×2]` (freq=2)
  - Chunk 4: `[text_content:li×6]` (freq=6)
  - Chunk 5: `[text_content:li×4]` (freq=4)
  - Chunk 6: `[text_content:li×2]` (freq=2)
  - Chunk 7: `[nav_content:a×17]` (freq=17)
  - Chunk 8: `[nav_content:li×18]` (freq=18)
  - Chunk 9: `[nav_content:li×8]` (freq=8)
  - Chunk 10: `[nav_content:li×7]` (freq=7)
  - Chunk 11: `[text_content:h2×1]` (freq=1)
  - Chunk 12: `[text_content:h2×1]` (freq=1)
  - Chunk 13: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: asccybernetics_orgdefinitions.html ===
Chunks: 14 (structural=0, functional=6, text=8)
Categories: {'search_input': 1, 'pagination': 1, 'text_singleton': 8, 'menu_item': 4}
Content: 32 tagged, 31 preserved (97%)
Leaks: 1 total, 1 high-importance

--- Chunk 0: [search_inputs] ---
  type=search_input freq=3 excl=0.00 OUTLIER=8.0x
  pattern_xpath: ///input

--- Chunk 1: [pagination_buttons] ---
  type=pagination freq=3 excl=1.00 OUTLIER=3.0x
  pattern_xpath: ///link[contains(@rel,'alternate')][contains(@type,'application')][contains(@type,'rss')][contains(@type,'xml')]
  content: [ATTR=1 HREF=1]

--- Chunk 2: [text_content:p×110] ---
  type=text_singleton freq=110 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 3: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=1]

--- Chunk 4: [text_content:li×6] ---
  type=text_singleton freq=6 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=1]

--- Chunk 5: [text_content:li×4] ---
  type=text_singleton freq=4 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=1]

--- Chunk 6: [text_content:li×2] ---
  type=text_singleton freq=2 excl=0.44 LEAKS=1
  pattern_xpath: ///li[contains(@class,'container')][contains(@class,'widget')][contains(@id,'block')][contains(@class,'block')]
  content: [ATTR=1 IMG=1 TEXT=3]
  LEAKS (high):
    [IMG] https://www.paypalobjects.com/en_US/i/scr/pixel.gif (img URL not in rendered)

--- Chunk 7: [nav_content:a×17] ---
  type=menu_item freq=17 excl=1.00
  pattern_xpath: ///a[contains(@rel,'noopener')][contains(@target,'new')]
  content: [HREF=1 TEXT=1]

--- Chunk 8: [nav_content:li×18] ---
  type=menu_item freq=18 excl=0.33
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')][contains(@id,'item')]
  content: [HREF=1 TEXT=1]

--- Chunk 9: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.33
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'page')][contains(@class,'post')]
  content: [HREF=1 TEXT=1]

--- Chunk 10: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.33
  pattern_xpath: ///li[contains(@class,'custom')][contains(@class,'current')][contains(@class,'ancestor')]//li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')][contains(@id,'item')]
  content: [HREF=1 TEXT=1]

--- Chunk 11: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.42
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'wp')][contains(@class,'block')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.42
  pattern_xpath: ///h2[contains(@class,'heading')][contains(@class,'wp')][contains(@class,'block')]
  content: [TEXT=1]

--- Chunk 13: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.44
  pattern_xpath: ///li[contains(@class,'container')][contains(@class,'widget')][contains(@id,'block')][contains(@class,'block')]
  content: [ATTR=1 HREF=1 IMG=1 TEXT=8]

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
4. Use filename `asccybernetics_orgdefinitions.html` in all `_distill()` calls
5. Name the module `test_asccybernetics_orgdefinitions_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
