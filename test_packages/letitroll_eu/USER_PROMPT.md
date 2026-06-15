# Test Generation Task: letitroll_eu.html

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

- **Total chunks:** 32
- **Structural chunks:** 5
- **Text/Nav chunks:** 25
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.con.inner` (freq=8, pq_sig=`div(div(div(div(img),div(h4),div(p),div(a(span(spa`)
  - Chunk 1: `a.blank.com` (freq=4, pq_sig=`span(a(span,svg(path)))`)
  - Chunk 2: `div.group.margin` (freq=23, pq_sig=`div(div(div(div(img))))`)
  - Chunk 3: `div.bd.default` (freq=2, pq_sig=`div(a(img))`)
  - Chunk 4: `div.ch.content` (freq=2, pq_sig=`div(h2,p,p(a))`)

**Text/Nav chunks:**
  - Chunk 7: `[nav_content:li×10]` (freq=10)
  - Chunk 8: `[nav_content:li×22]` (freq=22)
  - Chunk 9: `[nav_content:li×4]` (freq=4)
  - Chunk 10: `[nav_content:li×5]` (freq=5)
  - Chunk 11: `[nav_content:li×4]` (freq=4)
  - Chunk 12: `[nav_content:li×5]` (freq=5)
  - Chunk 13: `[text_content:h1×1]` (freq=1)
  - Chunk 14: `[text_content:h2×1]` (freq=1)
  - Chunk 15: `[text_content:h2×1]` (freq=1)
  - Chunk 16: `[text_content:h2×1]` (freq=1)
  - Chunk 17: `[text_content:h2×1]` (freq=1)
  - Chunk 18: `[text_content:h2×1]` (freq=1)
  - Chunk 19: `[text_content:h4×1]` (freq=1)
  - Chunk 20: `[text_content:h4×1]` (freq=1)
  - Chunk 21: `[text_content:h4×1]` (freq=1)
  - Chunk 22: `[text_content:h4×1]` (freq=1)
  - Chunk 23: `[text_content:h4×1]` (freq=1)
  - Chunk 24: `[text_content:h4×1]` (freq=1)
  - Chunk 25: `[text_content:h4×1]` (freq=1)
  - Chunk 26: `[text_content:h4×1]` (freq=1)
  - Chunk 27: `[text_content:h4×1]` (freq=1)
  - Chunk 28: `[text_content:h4×1]` (freq=1)
  - Chunk 29: `[text_content:h4×1]` (freq=1)
  - Chunk 30: `[text_content:h4×1]` (freq=1)
  - Chunk 31: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: letitroll_eu.html ===
Chunks: 32 (structural=5, functional=8, text=19)
Categories: {'card': 4, 'structural': 1, 'search_input': 1, 'pagination': 1, 'menu_item': 6, 'text_singleton': 19}
Content: 72 tagged, 72 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.con.inner ---
  type=card freq=8 excl=1.00
  pattern_xpath: ///div[contains(@class,'con')][contains(@class,'inner')]
  tree_sig: div(div(div(div(img),div(h4),div(p),div(a(span(span))))))
  content: [ATTR=1 HREF=1 IMG=3 TEXT=3]

--- Chunk 1: a.blank.com ---
  type=card freq=4 excl=0.73
  pattern_xpath: ///a[contains(@class,'icon')][contains(@class,'repeater')][contains(@class,'social')][contains(@target,'blank')][contains(@class,'item')]
  tree_sig: span(a(span,svg(path)))
  content: [HREF=1 TEXT=1]

--- Chunk 2: div.group.margin ---
  type=card freq=23 excl=1.00
  pattern_xpath: ///div[contains(@aria-roledescription,'slide')][contains(@class,'slide')][contains(@role,'group')][contains(@style,'margin')][contains(@style,'px')]
  tree_sig: div(div(div(div(img))))
  content: [ATTR=3 IMG=3]

--- Chunk 3: div.bd.default ---
  type=card freq=2 excl=1.00
  pattern_xpath: ///div[contains(@class,'bd')][contains(@class,'element')][contains(@class,'initial')][contains(@class,'logo')][contains(@class,'mobile')]
  tree_sig: div(a(img))
  content: [HREF=1 IMG=1]

--- Chunk 4: div.ch.content ---
  type=structural freq=2 excl=0.88
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'dialog')][contains(@class,'morespace')][contains(@class,'ch')]
  tree_sig: div(h2,p,p(a))
  content: [HREF=1 TEXT=3]

--- Chunk 5: [search_inputs] ---
  type=search_input freq=2 excl=1.00
  pattern_xpath: ///input[contains(@class,'field')][contains(@class,'md')][contains(@id,'field')][contains(@id,'form')][contains(@name,'field')]

--- Chunk 6: [pagination_buttons] ---
  type=pagination freq=16 excl=0.52
  pattern_xpath: ///div[contains(@class,'element')][contains(@class,'widget')][contains(@data-element_type,'widget')]/div[contains(@class,'button')][contains(@class,'elementor')]
  content: [ATTR=1 IMG=4]

--- Chunk 7: [nav_content:li×10] ---
  type=menu_item freq=10 excl=0.16
  pattern_xpath: ///li[contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')][contains(@class,'item')]
  content: [HREF=4 TEXT=5]

--- Chunk 8: [nav_content:li×22] ---
  type=menu_item freq=22 excl=0.16
  pattern_xpath: ///li[contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')][contains(@class,'item')]
  content: [HREF=4 TEXT=5]

--- Chunk 9: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.20
  pattern_xpath: ///li[contains(@class,'akce')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'post')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 10: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.17
  pattern_xpath: ///li[contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')][contains(@class,'page')][contains(@class,'post')]
  content: [HREF=1 TEXT=1]

--- Chunk 11: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.20 OUTLIER=2.8x
  pattern_xpath: ///li[contains(@class,'akce')][contains(@class,'menu')][contains(@class,'object')][contains(@class,'post')][contains(@class,'type')]
  content: [HREF=1 TEXT=1]

--- Chunk 12: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.17
  pattern_xpath: ///li[contains(@class,'menu')][contains(@class,'object')][contains(@class,'type')][contains(@class,'page')][contains(@class,'post')]
  content: [HREF=1 TEXT=1]

--- Chunk 13: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h1[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 18: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h2[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 24: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.05
  pattern_xpath: ///h4[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
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
4. Use filename `letitroll_eu.html` in all `_distill()` calls
5. Name the module `test_letitroll_eu_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
