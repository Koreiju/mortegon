# Test Generation Task: archive_org.html

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

- **Total chunks:** 35
- **Structural chunks:** 10
- **Text/Nav chunks:** 23
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `a.archive.details` (freq=75, pq_sig=`a(div(div(div,div),div(img)),div(div,div))`)
  - Chunk 1: `div.icon.links` (freq=5, pq_sig=`div(a(img),a(img))`)
  - Chunk 2: `div.featured.links` (freq=4, pq_sig=`div(h4,ul(li(a),li(a),li(a),li(a),li(a)))`)
  - Chunk 3: `div.links.top` (freq=2, pq_sig=`div(h4,ul(li(a),li(a),li(a),li(a),li(a),li(a),li(a`)
  - Chunk 4: `a.details.media` (freq=9, pq_sig=`a(div(img),div(img))`)
  - Chunk 5: `onboarding-tile` (freq=8, pq_sig=`onboarding-tile(div,div(img),template)`)
  - Chunk 6: `a.details.expand` (freq=7, pq_sig=`a(span(svg(title,desc,path)),span(svg(title,desc,p`)
  - Chunk 7: `div.container.count` (freq=105, pq_sig=`div(div(div,div),div(img))`)
  - Chunk 8: `a.archive.details` (freq=15, pq_sig=`a(div(div(div,div),div(img)),div(div,div))`)
  - Chunk 9: `span.icon` (freq=14, pq_sig=`span(svg(desc,path,title))`)

**Text/Nav chunks:**
  - Chunk 12: `[text_content:p×3]` (freq=1)
  - Chunk 13: `[text_content:p×3]` (freq=1)
  - Chunk 14: `[text_content:li×5]` (freq=5)
  - Chunk 15: `[nav_content:a×17]` (freq=17)
  - Chunk 16: `[nav_content:li×7]` (freq=7)
  - Chunk 17: `[nav_content:li×6]` (freq=6)
  - Chunk 18: `[nav_content:li×8]` (freq=8)
  - Chunk 19: `[nav_content:a×74]` (freq=74)
  - Chunk 20: `[nav_content:li×4]` (freq=4)
  - Chunk 21: `[text_content:h1×1]` (freq=1)
  - Chunk 22: `[text_content:h3×1]` (freq=1)
  - Chunk 23: `[text_content:h3×1]` (freq=1)
  - Chunk 24: `[text_content:h3×1]` (freq=1)
  - Chunk 25: `[text_content:h3×1]` (freq=1)
  - Chunk 26: `[text_content:h3×1]` (freq=1)
  - Chunk 27: `[text_content:h3×1]` (freq=1)
  - Chunk 28: `[text_content:h4×1]` (freq=1)
  - Chunk 29: `[text_content:h4×1]` (freq=1)
  - Chunk 30: `[text_content:h4×1]` (freq=1)
  - Chunk 31: `[text_content:h1×1]` (freq=1)
  - Chunk 32: `[text_content:h1×1]` (freq=1)
  - Chunk 33: `[text_content:h4×1]` (freq=1)
  - Chunk 34: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: archive_org.html ===
Chunks: 35 (structural=10, functional=8, text=17)
Categories: {'card': 8, 'structural': 1, 'menu_item': 7, 'search_input': 1, 'pagination': 1, 'text_singleton': 17}
Content: 118 tagged, 117 preserved (99%)
Leaks: 1 total, 0 high-importance

--- Chunk 0: a.archive.details ---
  type=card freq=75 excl=0.00
  pattern_xpath: ///a
  tree_sig: a(div(div(div,div),div(img)),div(div,div))
  content: [ATTR=2 BG=1 HREF=1 TEXT=3]

--- Chunk 1: div.icon.links ---
  type=card freq=5 excl=0.42
  pattern_xpath: ///div[contains(@class,'icon')][contains(@class,'links')]
  tree_sig: div(a(img),a(img))
  content: [HREF=2 IMG=2 TEXT=2]

--- Chunk 2: div.featured.links ---
  type=card freq=4 excl=0.67
  pattern_xpath: ///div[contains(@class,'featured')][contains(@class,'links')]
  tree_sig: div(h4,ul(li(a),li(a),li(a),li(a),li(a)))
  content: [HREF=5 TEXT=6]

--- Chunk 3: div.links.top ---
  type=structural freq=2 excl=0.67
  pattern_xpath: ///div[contains(@class,'top')][contains(@class,'links')]
  tree_sig: div(h4,ul(li(a),li(a),li(a),li(a),li(a),li(a),li(a),li(a),li(a),li(a),li(a),li(a
  content: [HREF=13 TEXT=14]

--- Chunk 4: a.details.media ---
  type=card freq=9 excl=1.00
  pattern_xpath: ///a[contains(@class,'media')][contains(@class,'type')]
  tree_sig: a(div(img),div(img))
  content: [ATTR=3 HREF=1 TEXT=1]

--- Chunk 5: onboarding-tile ---
  type=card freq=8 excl=1.00
  pattern_xpath: ///a[contains(@class,'link')][contains(@class,'onboarding')][contains(@slot,'slide')]
  tree_sig: onboarding-tile(div,div(img),template)
  content: [HREF=1 TEXT=1]

--- Chunk 6: a.details.expand ---
  type=menu_item freq=7 excl=0.73
  pattern_xpath: ///a[contains(@class,'item')][contains(@class,'menu')][contains(@data-event-click-tracking,'menu')][contains(@data-event-click-tracking,'nav')][contains(@data-event-click-tracking,'top')]
  tree_sig: a(span(svg(title,desc,path)),span(svg(title,desc,path)))
  content: [ATTR=1 HREF=1 TEXT=5]

--- Chunk 7: div.container.count ---
  type=card freq=105 excl=1.00
  pattern_xpath: ///div[contains(@id,'container')][contains(@id,'count')][contains(@id,'item')]
  tree_sig: div(div(div,div),div(img))
  content: [ATTR=1 TEXT=2]

--- Chunk 8: a.archive.details ---
  type=card freq=15 excl=0.00
  pattern_xpath: ///a
  tree_sig: a(div(div(div,div),div(img)),div(div,div))
  content: [ATTR=2 BG=1 HREF=1 TEXT=3]

--- Chunk 9: span.icon ---
  type=card freq=14 excl=0.00
  pattern_xpath: ///span
  tree_sig: span(svg(desc,path,title))
  content: [TEXT=2]

--- Chunk 10: [search_inputs] ---
  type=search_input freq=8 excl=1.00
  pattern_xpath: ///input[contains(@type,'text')][contains(@id,'url')][contains(@name,'url')]
  content: [ATTR=1]

--- Chunk 11: [pagination_buttons] ---
  type=pagination freq=30 excl=0.33
  pattern_xpath: ///a[contains(@data-event-click-tracking,'nav')][contains(@data-event-click-tracking,'top')]
  content: [HREF=1 TEXT=1]

--- Chunk 12: [text_content:p×3] ---
  type=text_singleton freq=1 excl=0.50
  pattern_xpath: ///form[contains(@data-event-submit-tracking,'nav')][contains(@data-event-submit-tracking,'page')][contains(@data-event-submit-tracking,'save')][contains(@data-event-submit-tracking,'submit')][contains(@data-event-submit-tracking,'top')]
  content: [ATTR=1 TEXT=4]

--- Chunk 13: [text_content:p×3] ---
  type=text_singleton freq=1 excl=0.50
  pattern_xpath: ///form[contains(@data-event-submit-tracking,'nav')][contains(@data-event-submit-tracking,'page')][contains(@data-event-submit-tracking,'save')][contains(@data-event-submit-tracking,'submit')][contains(@data-event-submit-tracking,'top')]
  content: [ATTR=1 TEXT=4]

--- Chunk 14: [text_content:li×5] ---
  type=text_singleton freq=5 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=1]

--- Chunk 15: [nav_content:a×17] ---
  type=menu_item freq=17 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 16: [nav_content:li×7] ---
  type=menu_item freq=7 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 17: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 18: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 19: [nav_content:a×74] ---
  type=menu_item freq=74 excl=0.33
  pattern_xpath: ///a[contains(@data-event-click-tracking,'nav')][contains(@data-event-click-tracking,'top')]
  content: [HREF=1 TEXT=1]

--- Chunk 20: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 21: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h1
  content: [TEXT=1]

--- Chunk 22: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 23: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 24: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 25: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 26: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 27: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 28: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
  content: [TEXT=1]

--- Chunk 29: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
  content: [TEXT=1]

--- Chunk 30: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
  content: [TEXT=1]

--- Chunk 31: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h1[contains(@id,'whoweare')]
  content: [TEXT=2]

--- Chunk 32: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h1
  content: [TEXT=1]

--- Chunk 33: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
  content: [TEXT=1]

--- Chunk 34: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h4
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
4. Use filename `archive_org.html` in all `_distill()` calls
5. Name the module `test_archive_org_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
