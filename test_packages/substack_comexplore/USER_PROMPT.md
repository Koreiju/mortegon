# Test Generation Task: substack_comexplore.html

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

- **Total chunks:** 15
- **Structural chunks:** 7
- **Text/Nav chunks:** 6
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.align.column` (freq=3, pq_sig=`div(div(button,button),h4,p)`)
  - Chunk 1: `div.auto.border` (freq=10, pq_sig=`div(picture(img,source))`)
  - Chunk 2: `div.display.false` (freq=14, pq_sig=`div(div(picture(img,source)))`)
  - Chunk 3: `a.animate.auto` (freq=18, pq_sig=`a(span(div(div(picture(img,source)))))`)
  - Chunk 4: `button.align.auto` (freq=20, pq_sig=`button(svg(g(path,title)))`)
  - Chunk 5: `span.cl.color` (freq=6, pq_sig=`span(a(span))`)
  - Chunk 6: `span.closed` (freq=5, pq_sig=`span(span(a))`)

**Text/Nav chunks:**
  - Chunk 9: `[text_content:h4×2]` (freq=1)
  - Chunk 10: `[text_content:p×2]` (freq=2)
  - Chunk 11: `[text_content:p×3]` (freq=3)
  - Chunk 12: `[nav_content:a×15]` (freq=15)
  - Chunk 13: `[text_content:h4×1]` (freq=1)
  - Chunk 14: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: substack_comexplore.html ===
Chunks: 15 (structural=7, functional=3, text=5)
Categories: {'card': 6, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 5, 'menu_item': 1}
Content: 319 tagged, 307 preserved (96%)
Leaks: 12 total, 8 high-importance

--- Chunk 0: div.align.column ---
  type=card freq=3 excl=0.45
  pattern_xpath: ///div[contains(@class,'start')][contains(@class,'column')][contains(@class,'direction')][contains(@class,'gap')][contains(@class,'items')]
  tree_sig: div(div(button,button),h4,p)
  content: [TEXT=4]

--- Chunk 1: div.auto.border ---
  type=card freq=10 excl=0.11
  pattern_xpath: ///div[contains(@class,'flex')][contains(@class,'display')][contains(@class,'pencraft')][contains(@class,'reset')][contains(@class,'pc')]
  tree_sig: div(picture(img,source))
  content: [IMG=49]

--- Chunk 2: div.display.false ---
  type=card freq=14 excl=0.28
  pattern_xpath: ///div[contains(@class,'position')][contains(@class,'relative')][contains(@class,'flex')][contains(@class,'display')][contains(@class,'pencraft')]
  tree_sig: div(div(picture(img,source)))
  content: [ATTR=2 IMG=43]

--- Chunk 3: a.animate.auto ---
  type=card freq=18 excl=1.00
  pattern_xpath: ///a[contains(@class,'animate')][contains(@class,'em')][contains(@class,'focus')][contains(@class,'jx')][contains(@class,'show')]
  tree_sig: a(span(div(div(picture(img,source)))))
  content: [ATTR=2 HREF=1 IMG=43]

--- Chunk 4: button.align.auto ---
  type=button freq=20 excl=1.00
  pattern_xpath: ///button[contains(@class,'ge')][contains(@class,'ik')][contains(@class,'ld')][contains(@class,'left')][contains(@class,'min')]
  tree_sig: button(svg(g(path,title)))
  content: [ATTR=1]

--- Chunk 5: span.cl.color ---
  type=card freq=6 excl=1.00
  pattern_xpath: ///span[contains(@class,'cl')][contains(@class,'decoration')][contains(@class,'dvrm')][contains(@class,'hover')][contains(@class,'ls')]
  tree_sig: span(a(span))
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 6: span.closed ---
  type=card freq=5 excl=1.00
  pattern_xpath: ///span[contains(@data-state,'closed')]
  tree_sig: span(span(a))
  content: [HREF=1 TEXT=1]

--- Chunk 7: [search_inputs] ---
  type=search_input freq=3 excl=1.00
  pattern_xpath: ///input[contains(@autocomplete,'off')][contains(@class,'input')][contains(@class,'nv')][contains(@name,'search')][contains(@type,'search')]
  content: [ATTR=2]

--- Chunk 8: [pagination_buttons] ---
  type=pagination freq=64 excl=0.50
  pattern_xpath: ///button[contains(@class,'base')][contains(@class,'button')][contains(@class,'gck')][contains(@class,'gk')][contains(@class,'priority')]
  content: [IMG=25]

--- Chunk 9: [text_content:h4×2] ---
  type=text_singleton freq=1 excl=0.21 LEAKS=8
  pattern_xpath: ///div[contains(@class,'column')][contains(@class,'direction')][contains(@class,'flex')][contains(@class,'display')][contains(@class,'pencraft')]
  content: [IMG=131 TEXT=4]
  LEAKS (high):
    [IMG] w_546 (img URL not in rendered)
    [IMG] https://substackcdn.com/image/fetch/$s_!u9e1!,w_100,c_limit,f_auto,q_auto:good,fl_progress (img URL not in rendered)
    [IMG] https://substackcdn.com/image/fetch/$s_!u9e1! (img URL not in rendered)
    [IMG] fl_progressive:steep/https%3A%2F%2Fsubstack.com%2Fimg%2Fapp_page%2Fhighlight-2-v5.png (img URL not in rendered)
    [IMG] https://substackcdn.com/image/fetch/$s_!u9e1! (img URL not in rendered)
  LEAKS (medium):
    [TEXT] You made it, you own itGrow your publication on SubstackWorld-class wr
    [TEXT] You always own your intellectual property, mailing list, and subscribe
    [TEXT] Learn moreGet started

--- Chunk 10: [text_content:p×2] ---
  type=text_singleton freq=2 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 11: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.00 OUTLIER=3.7x
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 12: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.64
  pattern_xpath: ///a[contains(@class,'bpto')][contains(@class,'li')][contains(@class,'link')][contains(@class,'pencraft')][contains(@class,'reset')]
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 13: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.60
  pattern_xpath: ///h4[contains(@class,'zd')][contains(@class,'bci')][contains(@class,'font')][contains(@class,'gwiv')][contains(@class,'heavy')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.60
  pattern_xpath: ///h4[contains(@class,'index')][contains(@class,'bci')][contains(@class,'font')][contains(@class,'ggp')][contains(@class,'gwiv')]
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
4. Use filename `substack_comexplore.html` in all `_distill()` calls
5. Name the module `test_substack_comexplore_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
