# Test Generation Task: tarot_comsearchqlove&sizen_20_n.html

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

- **Total chunks:** 13
- **Structural chunks:** 7
- **Text/Nav chunks:** 4
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `row.body.result` (freq=5, pq_sig=`li(row(column(a(img,img)),column(li(a,span,a,span,`)
  - Chunk 1: `row.body.result` (freq=4, pq_sig=`li(row(column(a(img,img)),column(li(a,span,a,span,`)
  - Chunk 2: `row.body.result` (freq=3, pq_sig=`li(row(column(a(img,img)),column(li(a,span,a,span,`)
  - Chunk 3: `li` (freq=6, pq_sig=`li(a,nav-submenu(div(a,ul(li(a),li(a),li(a),li(a),`)
  - Chunk 4: `column.bottom.has` (freq=20, pq_sig=`column(a(img,img))`)
  - Chunk 5: `div.category.full` (freq=12, pq_sig=`div(a,ul(li(a),li(a),li(a),li(a),li(a)))`)
  - Chunk 6: `column.is.mobile` (freq=24, pq_sig=`column(a(row(column(img),column(p))))`)

**Text/Nav chunks:**
  - Chunk 9: `[nav_content:li×6]` (freq=6)
  - Chunk 10: `[nav_content:li×6]` (freq=6)
  - Chunk 11: `[nav_content:li×6]` (freq=6)
  - Chunk 12: `[nav_content:li×6]` (freq=6)

## Quality Report Summary

```
=== QUALITY REPORT: tarot_comsearchqlove&sizen_20_n.html ===
Chunks: 13 (structural=7, functional=6, text=0)
Categories: {'card': 7, 'search_input': 1, 'pagination': 1, 'menu_item': 4}
Content: 135 tagged, 127 preserved (94%)
Leaks: 8 total, 7 high-importance

--- Chunk 0: row.body.result ---
  type=card freq=5 excl=0.26 LEAKS=1
  pattern_xpath: ///row[contains(@class,'body')][contains(@class,'result')][contains(@class,'sui')]
  tree_sig: li(row(column(a(img,img)),column(li(a,span,a,span,a,span,a),li(a(h3(em),p(em))))
  content: [ATTR=2 HREF=6 IMG=2 TEXT=10]
  LEAKS (high):
    [IMG] https://gfx.tarot.com/images/feeds/625x625/couple-smile-love-625x625.jpg (img URL not in rendered)

--- Chunk 1: row.body.result ---
  type=card freq=4 excl=0.26 LEAKS=1
  pattern_xpath: ///row[contains(@class,'body')][contains(@class,'result')][contains(@class,'sui')]
  tree_sig: li(row(column(a(img,img)),column(li(a,span,a,span,a,span,a),li(a(h3(em),p)))))
  content: [ATTR=2 HREF=6 IMG=2 TEXT=8]
  LEAKS (high):
    [IMG] https://gfx.tarot.com/images/feeds/625x625/beach-water-hands-625x625.jpg (img URL not in rendered)

--- Chunk 2: row.body.result ---
  type=card freq=3 excl=0.26 LEAKS=1
  pattern_xpath: ///row[contains(@class,'body')][contains(@class,'result')][contains(@class,'sui')]
  tree_sig: li(row(column(a(img,img)),column(li(a,span,a,span,a,span,a),li(a(h3(em),p(em,em)
  content: [ATTR=2 HREF=6 IMG=2 TEXT=12]
  LEAKS (high):
    [IMG] https://gfx.tarot.com/images/feeds/625x625/couple-smiling-625x625.jpg (img URL not in rendered)

--- Chunk 3: li ---
  type=card freq=6 excl=0.00 LEAKS=3
  pattern_xpath: ///li
  tree_sig: li(a,nav-submenu(div(a,ul(li(a),li(a),li(a),li(a),li(a))),div(a,ul(li(a),li(a),l
  content: [ATTR=4 HREF=18 IMG=4 TEXT=18]
  LEAKS (high):
    [IMG] https://gfx.tarot.com/images/feeds/50x50/morgan-greer-table-50x50.jpg (img URL not in rendered)
    [IMG] https://gfx.tarot.com/images/feeds/50x50/house-general-50x50.jpg (img URL not in rendered)
    [IMG] https://gfx.tarot.com/images/feeds/50x50/tarot-hand-50x50.jpg (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Get Powerful Advice with a Daily Reflection Tarot Reading

--- Chunk 4: column.bottom.has ---
  type=card freq=20 excl=0.62 LEAKS=1
  pattern_xpath: ///ul[contains(@class,'results')][contains(@class,'container')]//column[contains(@class,'image')][contains(@class,'left')][contains(@class,'mobile')][contains(@class,'is')][contains(@class,'result')]
  tree_sig: column(a(img,img))
  content: [ATTR=2 HREF=1 IMG=2]
  LEAKS (high):
    [IMG] https://gfx.tarot.com/images/feeds/625x625/couple-candles-625x625.jpg (img URL not in rendered)

--- Chunk 5: div.category.full ---
  type=card freq=12 excl=1.00
  pattern_xpath: ///div[contains(@class,'category')][contains(@class,'full')][contains(@class,'nav')][contains(@class,'submenu')]
  tree_sig: div(a,ul(li(a),li(a),li(a),li(a),li(a)))
  content: [HREF=6 TEXT=6]

--- Chunk 6: column.is.mobile ---
  type=card freq=24 excl=0.71
  pattern_xpath: ///column[contains(@class,'portrait')][contains(@class,'tablet')][contains(@class,'mobile')][contains(@class,'is')]
  tree_sig: column(a(row(column(img),column(p))))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=1]

--- Chunk 7: [search_inputs] ---
  type=search_input freq=9 excl=0.00
  pattern_xpath: ///input
  content: [ATTR=1]

--- Chunk 8: [pagination_buttons] ---
  type=pagination freq=40 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1]

--- Chunk 9: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.20
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

--- Chunk 10: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.20
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

--- Chunk 11: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.20
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

--- Chunk 12: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.20
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

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
4. Use filename `tarot_comsearchqlove&sizen_20_n.html` in all `_distill()` calls
5. Name the module `test_tarot_comsearchqlove&sizen_20_n_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
