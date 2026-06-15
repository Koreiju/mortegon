# Test Generation Task: neocities_orgbrowse.html

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

- **Total chunks:** 16
- **Structural chunks:** 10
- **Text/Nav chunks:** 4
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `li.inkcaps.username` (freq=41, pq_sig=`li(a(span(img)),div(a),div(div(a(i)),div(a(span(i)`)
  - Chunk 1: `li.ranfren.username` (freq=34, pq_sig=`li(a(span(img)),div(a),div(div(a(i(i))),div(a(span`)
  - Chunk 2: `li.foggybear.username` (freq=10, pq_sig=`li(a(span(img)),div(a),div(div(a(i(i))),div(a(span`)
  - Chunk 3: `li.bunny.lazer` (freq=6, pq_sig=`li(a(span(img)),div(a),div(div(a(i)),div(a(span(i)`)
  - Chunk 4: `li.fairygore.username` (freq=2, pq_sig=`li(a(span(img)),div(a),div(div(a(i)),div(a(span(i)`)
  - Chunk 5: `li.unit.username` (freq=2, pq_sig=`li(a(span(img)),div(a),div(div(a(i)),div(a(span(i)`)
  - Chunk 6: `li.bonkiscoolsite.username` (freq=2, pq_sig=`li(a(span(img)),div(a),div(div(a(i)),div(a(span(i)`)
  - Chunk 7: `li.larvapuppy.username` (freq=2, pq_sig=`li(a(span(img)),div(a),div(div(a(i(i))),div(a(span`)
  - Chunk 8: `a.https.neo` (freq=100, pq_sig=`a(span(img))`)
  - Chunk 9: `div.hide.mobile` (freq=100, pq_sig=`div(a(span(i)))`)

**Text/Nav chunks:**
  - Chunk 12: `[nav_content:a×17]` (freq=17)
  - Chunk 13: `[text_content:h3×1]` (freq=1)
  - Chunk 14: `[text_content:h3×1]` (freq=1)
  - Chunk 15: `[text_content:h1×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: neocities_orgbrowse.html ===
Chunks: 16 (structural=10, functional=3, text=3)
Categories: {'card': 10, 'search_input': 1, 'pagination': 1, 'menu_item': 1, 'text_singleton': 3}
Content: 242 tagged, 242 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: li.inkcaps.username ---
  type=card freq=41 excl=0.12
  pattern_xpath: ///li[contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i)),div(a(span(i))),div(i,a,a,a,a,a,a(i,span(i)
  content: [ATTR=8 BG=1 HREF=11 IMG=1 TEXT=11]

--- Chunk 1: li.ranfren.username ---
  type=card freq=34 excl=0.12
  pattern_xpath: ///li[contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i(i))),div(a(span(i))),div(i,a,a,a,a,a,a(i(i),s
  content: [ATTR=8 BG=1 HREF=11 IMG=1 TEXT=11]

--- Chunk 2: li.foggybear.username ---
  type=card freq=10 excl=0.12
  pattern_xpath: ///li[contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i(i))),div(a(span(i))),div(i,a,a,a,a,a(i(i),spa
  content: [ATTR=8 BG=1 HREF=10 IMG=1 TEXT=10]

--- Chunk 3: li.bunny.lazer ---
  type=card freq=6 excl=0.12
  pattern_xpath: ///li[contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i)),div(a(span(i))),div(i,a,a,a,a,a(i,span(i)))
  content: [ATTR=8 BG=1 HREF=10 IMG=1 TEXT=10]

--- Chunk 4: li.fairygore.username ---
  type=card freq=2 excl=0.71
  pattern_xpath: ///li[contains(@id,'arkmsworld')][contains(@id,'fairygore')][contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i)),div(a(span(i))),div(a(i,span(i))),a))
  content: [ATTR=7 BG=1 HREF=6 IMG=1 TEXT=6]

--- Chunk 5: li.unit.username ---
  type=card freq=2 excl=0.78
  pattern_xpath: ///li[contains(@id,'neighborhoods')][contains(@id,'neo')][contains(@id,'unit')][contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i)),div(a(span(i))),div(i,a,a,a,a(i,span(i))),a
  content: [ATTR=8 BG=1 HREF=9 IMG=1 TEXT=9]

--- Chunk 6: li.bonkiscoolsite.username ---
  type=card freq=2 excl=0.71
  pattern_xpath: ///li[contains(@id,'bonkiscoolsite')][contains(@id,'ruralrose')][contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i)),div(a(span(i))),div(i,a,a,a(i,span(i))),a))
  content: [ATTR=8 BG=1 HREF=8 IMG=1 TEXT=8]

--- Chunk 7: li.larvapuppy.username ---
  type=card freq=2 excl=0.71
  pattern_xpath: ///li[contains(@id,'feelingmachine')][contains(@id,'larvapuppy')][contains(@id,'username')]
  tree_sig: li(a(span(img)),div(a),div(div(a(i(i))),div(a(span(i))),div(i,a,a,a,a(i(i),span(
  content: [ATTR=8 BG=1 HREF=9 IMG=1 TEXT=9]

--- Chunk 8: a.https.neo ---
  type=card freq=100 excl=1.00
  pattern_xpath: ///a[contains(@class,'neo')][contains(@class,'screen')][contains(@class,'shot')]
  tree_sig: a(span(img))
  content: [ATTR=2 BG=1 HREF=1 IMG=1]

--- Chunk 9: div.hide.mobile ---
  type=card freq=100 excl=1.00
  pattern_xpath: ///div[contains(@class,'hide')][contains(@class,'mobile')][contains(@class,'on')][contains(@class,'site')][contains(@class,'stats')]
  tree_sig: div(a(span(i)))
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 10: [search_inputs] ---
  type=search_input freq=15 excl=0.00 OUTLIER=11.0x
  pattern_xpath: ///input

--- Chunk 11: [pagination_buttons] ---
  type=pagination freq=28 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1]

--- Chunk 12: [nav_content:a×17] ---
  type=menu_item freq=17 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 13: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 14: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.50
  pattern_xpath: ///h3[contains(@class,'center')][contains(@class,'txt')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h1
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
4. Use filename `neocities_orgbrowse.html` in all `_distill()` calls
5. Name the module `test_neocities_orgbrowse_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
