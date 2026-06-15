# Test Generation Task: copykat_com.html

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

- **Total chunks:** 17
- **Structural chunks:** 6
- **Text/Nav chunks:** 9
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.widget.wrap` (freq=12, pq_sig=`section(div(h3,a(img,noscript)))`)
  - Chunk 1: `article.article.butter` (freq=4, pq_sig=`article(a(img,noscript),div(p),header(h2(a)))`)
  - Chunk 2: `article.article.category` (freq=4, pq_sig=`article(a(img,noscript),div(p),header(h2(a)))`)
  - Chunk 3: `header.entry.header` (freq=15, pq_sig=`header(h2(a))`)
  - Chunk 4: `li.category.item` (freq=30, pq_sig=`li(a(span))`)
  - Chunk 5: `a.com.copykatrecipes` (freq=8, pq_sig=`a(svg(title,use))`)

**Text/Nav chunks:**
  - Chunk 8: `[text_content:p×3]` (freq=3)
  - Chunk 9: `[text_content:h2×1]` (freq=1)
  - Chunk 10: `[text_content:h3×1]` (freq=1)
  - Chunk 11: `[text_content:h3×1]` (freq=1)
  - Chunk 12: `[text_content:h3×1]` (freq=1)
  - Chunk 13: `[text_content:h3×1]` (freq=1)
  - Chunk 14: `[text_content:h3×1]` (freq=1)
  - Chunk 15: `[text_content:h3×1]` (freq=1)
  - Chunk 16: `[text_content:h3×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: copykat_com.html ===
Chunks: 17 (structural=6, functional=2, text=9)
Categories: {'card': 4, 'menu_item': 2, 'search_input': 1, 'pagination': 1, 'text_singleton': 9}
Content: 45 tagged, 41 preserved (91%)
Leaks: 4 total, 0 high-importance

--- Chunk 0: div.widget.wrap ---
  type=card freq=12 excl=0.56
  pattern_xpath: ///div[contains(@class,'area')][contains(@class,'home')][contains(@class,'middle')]//div[contains(@class,'wrap')][contains(@class,'widget')]
  tree_sig: section(div(h3,a(img,noscript)))
  content: [HREF=1 IMG=1 TEXT=2]
  LEAKS (medium):
    [TEXT] <img width="300" height="300" src="https://copykat.com/wp-content/uplo

--- Chunk 1: article.article.butter ---
  type=card freq=4 excl=1.00
  pattern_xpath: ///article[contains(@class,'recipes')][contains(@class,'cookies')][contains(@class,'copycat')][contains(@class,'diy')][contains(@class,'fast')]
  tree_sig: article(a(img,noscript),div(p),header(h2(a)))
  content: [ATTR=3 HREF=2 IMG=1 TEXT=3]
  LEAKS (medium):
    [TEXT] <img width="250" height="310" src="https://copykat.com/wp-content/uplo

--- Chunk 2: article.article.category ---
  type=card freq=4 excl=1.00
  pattern_xpath: ///article[contains(@class,'odd')][contains(@class,'appetizers')][contains(@class,'carb')][contains(@class,'day')][contains(@class,'dipssauces')]
  tree_sig: article(a(img,noscript),div(p),header(h2(a)))
  content: [ATTR=3 HREF=2 IMG=1 TEXT=3]
  LEAKS (medium):
    [TEXT] <img width="250" height="310" src="https://copykat.com/wp-content/uplo

--- Chunk 3: header.entry.header ---
  type=card freq=15 excl=0.67
  pattern_xpath: ///header[contains(@class,'header')][contains(@class,'entry')]
  tree_sig: header(h2(a))
  content: [HREF=1 TEXT=1]

--- Chunk 4: li.category.item ---
  type=menu_item freq=30 excl=1.00
  pattern_xpath: ///li[contains(@class,'item')][contains(@class,'menu')][contains(@class,'object')][contains(@id,'item')][contains(@id,'menu')]
  tree_sig: li(a(span))
  content: [HREF=1 TEXT=1]

--- Chunk 5: a.com.copykatrecipes ---
  type=menu_item freq=8 excl=0.00
  pattern_xpath: ///a
  tree_sig: a(svg(title,use))
  content: [HREF=1 TEXT=1]

--- Chunk 6: [search_inputs] ---
  type=search_input freq=18 excl=0.00
  pattern_xpath: ///input
  content: [ATTR=2]

--- Chunk 7: [pagination_buttons] ---
  type=pagination freq=14 excl=0.00
  pattern_xpath: ///form
  content: [ATTR=1 HREF=1 IMG=1 TEXT=1]
  LEAKS (medium):
    [TEXT] <img width="668" height="209" alt="Copykat" src="https://copykat.com/w

--- Chunk 8: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.00
  pattern_xpath: ///p
  content: [HREF=1 TEXT=2]

--- Chunk 9: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'genesis')][contains(@class,'reader')][contains(@class,'screen')][contains(@class,'sidebar')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 10: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'title')][contains(@class,'widget')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'title')][contains(@class,'widget')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'title')][contains(@class,'widget')]
  content: [TEXT=1]

--- Chunk 13: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'title')][contains(@class,'widget')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'title')][contains(@class,'widget')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'title')][contains(@class,'widget')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///h3[contains(@class,'widgettitle')][contains(@class,'title')][contains(@class,'widget')]
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
4. Use filename `copykat_com.html` in all `_distill()` calls
5. Name the module `test_copykat_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
