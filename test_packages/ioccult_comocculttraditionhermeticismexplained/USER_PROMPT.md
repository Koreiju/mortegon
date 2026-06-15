# Test Generation Task: ioccult_comocculttraditionhermeticismexplained.html

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
- **Structural chunks:** 6
- **Text/Nav chunks:** 28
- **Search input found:** False
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `li.block.book` (freq=7, pq_sig=`li(div(div(h4(a),p(span)),div(figure(a(img)))),hr)`)
  - Chunk 1: `figure.aligncenter.block` (freq=2, pq_sig=`figure(img,figcaption)`)
  - Chunk 2: `div.block.container` (freq=8, pq_sig=`div(h4(a),p(span))`)
  - Chunk 3: `figure.block.featured` (freq=8, pq_sig=`figure(a(img))`)
  - Chunk 4: `span.block.icon` (freq=2, pq_sig=`span(svg(path))`)
  - Chunk 5: `ul.actions.block` (freq=2, pq_sig=`ul(li(a(span)))`)

**Text/Nav chunks:**
  - Chunk 7: `[text_content:p×124]` (freq=124)
  - Chunk 8: `[text_content:p×3]` (freq=1)
  - Chunk 9: `[text_content:li×3]` (freq=3)
  - Chunk 10: `[text_content:li×3]` (freq=3)
  - Chunk 11: `[text_content:li×4]` (freq=4)
  - Chunk 12: `[text_content:li×7]` (freq=7)
  - Chunk 13: `[text_content:li×6]` (freq=6)
  - Chunk 14: `[text_content:li×5]` (freq=5)
  - Chunk 15: `[text_content:p×9]` (freq=9)
  - Chunk 16: `[text_content:h3×3]` (freq=1)
  - Chunk 17: `[text_content:li×3]` (freq=3)
  - Chunk 18: `[text_content:h2×2]` (freq=1)
  - Chunk 19: `[text_content:p×2]` (freq=1)
  - Chunk 20: `[text_content:li×4]` (freq=4)
  - Chunk 21: `[text_content:li×4]` (freq=4)
  - Chunk 22: `[text_content:li×8]` (freq=8)
  - Chunk 23: `[nav_content:p×4]` (freq=4)
  - Chunk 24: `[nav_content:p×4]` (freq=4)
  - Chunk 25: `[nav_content:p×4]` (freq=4)
  - Chunk 26: `[nav_content:li×11]` (freq=11)
  - Chunk 27: `[nav_content:a×7]` (freq=7)
  - Chunk 28: `[text_content:h1×1]` (freq=1)
  - Chunk 29: `[text_content:h3×1]` (freq=1)
  - Chunk 30: `[text_content:h3×1]` (freq=1)
  - Chunk 31: `[text_content:h4×1]` (freq=1)
  - Chunk 32: `[text_content:h4×1]` (freq=1)
  - Chunk 33: `[text_content:h4×1]` (freq=1)
  - Chunk 34: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: ioccult_comocculttraditionhermeticismexplained.html ===
Chunks: 34 (structural=5, functional=6, text=23)
Categories: {'card': 3, 'structural': 2, 'pagination': 1, 'text_singleton': 23, 'menu_item': 5}
Content: 944 tagged, 426 preserved (45%)
Leaks: 518 total, 325 high-importance

--- Chunk 0: li.block.book ---
  type=card freq=7 excl=0.47
  pattern_xpath: ///li[contains(@class,'book')][contains(@class,'format')][contains(@class,'occult')][contains(@class,'standard')][contains(@class,'hentry')]
  tree_sig: li(div(div(h4(a),p(span)),div(figure(a(img)))),hr)
  content: [ATTR=1 HREF=2 IMG=3 TEXT=2]

--- Chunk 1: div.block.container ---
  type=card freq=8 excl=0.28
  pattern_xpath: ///div[contains(@class,'core')][contains(@class,'flex')][contains(@class,'vertical')][contains(@class,'container')][contains(@class,'group')]
  tree_sig: div(h4(a),p(span))
  content: [HREF=1 TEXT=2]

--- Chunk 2: figure.block.featured ---
  type=card freq=8 excl=0.34
  pattern_xpath: ///figure[contains(@class,'featured')][contains(@class,'image')][contains(@class,'post')][contains(@class,'block')][contains(@class,'wp')]
  tree_sig: figure(a(img))
  content: [ATTR=1 HREF=1 IMG=5]

--- Chunk 3: span.block.icon ---
  type=structural freq=2 excl=0.39
  pattern_xpath: ///span[contains(@class,'icon')][contains(@class,'submenu')][contains(@class,'navigation')][contains(@class,'block')][contains(@class,'wp')]
  tree_sig: span(svg(path))

--- Chunk 4: ul.actions.block ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///ul[contains(@data-wp-on-async--focus,'actions')][contains(@data-wp-on-async--focus,'focus')][contains(@data-wp-on-async--focus,'menu')][contains(@data-wp-on-async--focus,'on')][contains(@data-wp-on-async--focus,'open')]
  tree_sig: ul(li(a(span)))
  content: [HREF=1 TEXT=1]

--- Chunk 5: [pagination_buttons] ---
  type=pagination freq=6 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 IMG=5]

--- Chunk 6: [text_content:p×124] ---
  type=text_singleton freq=124 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 7: [text_content:p×3] ---
  type=text_singleton freq=1 excl=0.90 LEAKS=130
  pattern_xpath: ///div[contains(@class,'ollie')][contains(@class,'position')][contains(@class,'sticky')][contains(@class,'top')][contains(@class,'alignwide')]
  content: [ATTR=35 HREF=59 IMG=137 TEXT=129]
  LEAKS (high):
    [IMG] https://images.squarespace-cdn.com/content/v1/58c46117d2b8573ccaeaafca/1671068630359-9N78D (img URL not in rendered)
    [IMG] https://ioccult.com/wp-content/uploads/2025/04/Art-Loop-GIF-by-xponentialdesign.gif (img URL not in rendered)
    [IMG] https://ioccult.com/wp-content/uploads/2025/04/giordano-bruno.jpg (img URL not in rendered)
    [IMG] https://ioccult.com/wp-content/uploads/2025/04/giordano-bruno.jpg (img URL not in rendered)
    [IMG] https://ioccult.com/wp-content/uploads/2025/04/giordano-bruno-300x150.jpg (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Core Concepts:Is Hermeticism a religion?Can you be a Christian and a H
    [TEXT] What is Hermeticism? Is it a religion? Is it compatible with Christian
    [TEXT] Since the fall of the Roman Empire, Christianity—specifically Roman Ca

--- Chunk 8: [text_content:li×3] ---
  type=text_singleton freq=3 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=1]

--- Chunk 9: [text_content:li×3] ---
  type=text_singleton freq=3 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 10: [text_content:li×4] ---
  type=text_singleton freq=4 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 11: [text_content:li×7] ---
  type=text_singleton freq=7 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 12: [text_content:li×6] ---
  type=text_singleton freq=6 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 13: [text_content:li×5] ---
  type=text_singleton freq=5 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 14: [text_content:p×9] ---
  type=text_singleton freq=9 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 15: [text_content:h3×3] ---
  type=text_singleton freq=1 excl=0.50 LEAKS=104
  pattern_xpath: ///div[contains(@class,'alignwide')][contains(@class,'ollie')][contains(@class,'sticky')]/div[contains(@class,'constrained')][contains(@class,'global')][contains(@class,'padding')][contains(@style,'border')][contains(@style,'px')]
  content: [ATTR=29 HREF=59 IMG=111 TEXT=69]
  LEAKS (high):
    [HREF] https://ioccult.com/occult-book/the-mystical-qabalah/ (href not in rendered output)
    [HREF] https://ioccult.com/occult-book/between-the-gates-mark-stavish/ (href not in rendered output)
    [HREF] https://ioccult.com/occult-book/the-gnostic-gospels/ (href not in rendered output)
    [HREF] https://ioccult.com/occult-book/meditations-on-the-tarot-a-journey-into-christian-hermetic (href not in rendered output)
    [HREF] https://ioccult.com/occult-book/hermetica-the-greek-corpus-hermeticum-and-the-latin-asclep (href not in rendered output)
  LEAKS (medium):
    [TEXT] Core Concepts:Is Hermeticism a religion?Can you be a Christian and a H
    [TEXT] . There’s no centralized church or dogma.Yes. Christian Hermeticism se
    [TEXT] – The unknowable, divine source of all reality.

--- Chunk 16: [text_content:li×3] ---
  type=text_singleton freq=3 excl=0.00 OUTLIER=3.7x
  pattern_xpath: ///li
  content: [TEXT=1]

--- Chunk 17: [text_content:h2×2] ---
  type=text_singleton freq=1 excl=0.80
  pattern_xpath: ///div[contains(@class,'cb')][contains(@class,'justification')][contains(@class,'left')][contains(@class,'alignwide')][contains(@class,'content')]
  content: [TEXT=3]

--- Chunk 18: [text_content:p×2] ---
  type=text_singleton freq=1 excl=0.67 LEAKS=91
  pattern_xpath: ///div[contains(@class,'alignfull')][contains(@class,'flow')][contains(@class,'query')][contains(@class,'is')][contains(@class,'layout')]
  content: [ATTR=16 HREF=55 IMG=86 TEXT=52]
  LEAKS (high):
    [HREF] https://www.electrikjam.com/buying-guides/ (href not in rendered output)
    [IMG] https://secure.gravatar.com/avatar/7b7e7bbd81ce1b1b5110f1faaa5b443310114c8760968976d3f522f (img URL not in rendered)
    [IMG] https://secure.gravatar.com/avatar/7b7e7bbd81ce1b1b5110f1faaa5b443310114c8760968976d3f522f (img URL not in rendered)
    [IMG] https://secure.gravatar.com/avatar/7b7e7bbd81ce1b1b5110f1faaa5b443310114c8760968976d3f522f (img URL not in rendered)
    [IMG] https://secure.gravatar.com/avatar/7b7e7bbd81ce1b1b5110f1faaa5b443310114c8760968976d3f522f (img URL not in rendered)
  LEAKS (medium):
    [TEXT] What is Hermeticism? Is it a religion? Is it compatible with Christian
    [TEXT] Learn More About Hermeticism, Its Practices & Core Tenets…
    [TEXT] “True magic therefore is the high knowledge of the more subtle powers 

--- Chunk 19: [text_content:li×4] ---
  type=text_singleton freq=4 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 20: [text_content:li×4] ---
  type=text_singleton freq=4 excl=0.00
  pattern_xpath: ///li
  content: [TEXT=2]

--- Chunk 21: [text_content:li×8] ---
  type=text_singleton freq=8 excl=0.33
  pattern_xpath: ///div[contains(@class,'query')][contains(@class,'alignfull')][contains(@class,'flow')]//li[contains(@class,'hentry')][contains(@class,'hermeticism')][contains(@class,'publish')][contains(@class,'status')][contains(@class,'topics')]
  content: [ATTR=1 HREF=3 IMG=5 TEXT=3]

--- Chunk 22: [nav_content:p×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:p×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:p×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=1]

--- Chunk 25: [nav_content:li×11] ---
  type=menu_item freq=11 excl=0.47
  pattern_xpath: ///li[contains(@class,'book')][contains(@class,'format')][contains(@class,'occult')][contains(@class,'standard')][contains(@class,'hentry')]
  content: [ATTR=1 HREF=2 IMG=5 TEXT=2]

--- Chunk 26: [nav_content:a×7] ---
  type=menu_item freq=7 excl=0.39
  pattern_xpath: ///a[contains(@class,'item')][contains(@class,'content')][contains(@class,'navigation')][contains(@class,'block')][contains(@class,'wp')]
  content: [HREF=1 TEXT=1]

--- Chunk 27: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h1[contains(@class,'color')][contains(@class,'ea')][contains(@class,'ef')][contains(@class,'elements')][contains(@class,'main')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h3[contains(@class,'heading')][contains(@class,'block')][contains(@class,'wp')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h3[contains(@class,'family')][contains(@class,'medium')][contains(@class,'narrow')][contains(@style,'font')][contains(@style,'normal')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///h4[contains(@class,'base')][contains(@class,'title')][contains(@class,'font')][contains(@class,'size')][contains(@class,'post')]
  content: [HREF=1 TEXT=1]

--- Chunk 31: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///h4[contains(@class,'base')][contains(@class,'title')][contains(@class,'font')][contains(@class,'size')][contains(@class,'post')]
  content: [HREF=1 TEXT=1]

--- Chunk 32: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///h4[contains(@class,'base')][contains(@class,'title')][contains(@class,'font')][contains(@class,'size')][contains(@class,'post')]
  content: [HREF=1 TEXT=1]

--- Chunk 33: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.16
  pattern_xpath: ///div[contains(@class,'nowrap')]/h4[contains(@class,'base')][contains(@class,'title')][contains(@class,'font')][contains(@class,'size')][contains(@class,'post')]
  content: [HREF=10 TEXT=10]

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
4. Use filename `ioccult_comocculttraditionhermeticismexplained.html` in all `_distill()` calls
5. Name the module `test_ioccult_comocculttraditionhermeticismexplained_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
