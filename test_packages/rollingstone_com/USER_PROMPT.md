# Test Generation Task: rollingstone_com.html

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

- **Total chunks:** 61
- **Structural chunks:** 12
- **Text/Nav chunks:** 47
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div` (freq=6, pq_sig=`li(div(div(div(div(div)),div(h3(a),p,ul,ul(li(div)`)
  - Chunk 1: `a.amazon.block` (freq=4, pq_sig=`li(div(a(div(div(img)),div(div(svg(g)),h3,time))))`)
  - Chunk 2: `a.black.blank` (freq=5, pq_sig=`a(span,svg(use))`)
  - Chunk 3: `a.awards.college` (freq=7, pq_sig=`div(a(div(div(div(img))),div(div(div),h3)))`)
  - Chunk 4: `div` (freq=5, pq_sig=`li(div(div(div(div(div(a),div)),div(h3(a),ul(li(sp`)
  - Chunk 5: `li.//.collapsed` (freq=2, pq_sig=`li(div(a),ul(li(a),li(a),li(a),li(a),li(a)))`)
  - Chunk 6: `li.//.collapsed` (freq=2, pq_sig=`li(div(a),ul(li(a),li(a),li(a),li(a)))`)
  - Chunk 7: `li.//.collapsed` (freq=2, pq_sig=`li(div(a),ul)`)
  - Chunk 8: `div.border.effect` (freq=10, pq_sig=`div(div(img))`)
  - Chunk 9: `div.image.lazy` (freq=25, pq_sig=`div(a(div(img)))`)
  - Chunk 10: `a.bob.com` (freq=7, pq_sig=`a(div(img))`)
  - Chunk 11: `div.//.author` (freq=6, pq_sig=`div(div(a),span)`)

**Text/Nav chunks:**
  - Chunk 14: `[text_content:li×7]` (freq=7)
  - Chunk 15: `[text_content:p×8]` (freq=1)
  - Chunk 16: `[nav_content:li×5]` (freq=5)
  - Chunk 17: `[nav_content:a×41]` (freq=41)
  - Chunk 18: `[nav_content:li×9]` (freq=9)
  - Chunk 19: `[nav_content:li×5]` (freq=5)
  - Chunk 20: `[nav_content:li×5]` (freq=5)
  - Chunk 21: `[nav_content:h3×7]` (freq=7)
  - Chunk 24: `[nav_content:a×13]` (freq=13)
  - Chunk 25: `[nav_content:a×15]` (freq=15)
  - Chunk 24: `[nav_content:a×13]` (freq=13)
  - Chunk 25: `[nav_content:a×15]` (freq=15)
  - Chunk 26: `[text_content:h2×1]` (freq=1)
  - Chunk 27: `[text_content:h3×1]` (freq=1)
  - Chunk 28: `[text_content:h2×1]` (freq=1)
  - Chunk 29: `[text_content:h2×1]` (freq=1)
  - Chunk 30: `[text_content:h3×1]` (freq=1)
  - Chunk 31: `[text_content:h4×1]` (freq=1)
  - Chunk 32: `[text_content:h3×1]` (freq=1)
  - Chunk 33: `[text_content:h1×1]` (freq=1)
  - Chunk 34: `[text_content:h3×1]` (freq=1)
  - Chunk 35: `[text_content:h3×1]` (freq=1)
  - Chunk 36: `[text_content:h3×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h4×1]` (freq=1)
  - Chunk 39: `[text_content:h4×1]` (freq=1)
  - Chunk 40: `[text_content:h4×1]` (freq=1)
  - Chunk 41: `[text_content:h4×1]` (freq=1)
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
  - Chunk 52: `[text_content:h4×1]` (freq=1)
  - Chunk 53: `[text_content:h4×1]` (freq=1)
  - Chunk 54: `[text_content:h3×1]` (freq=1)
  - Chunk 55: `[text_content:h3×1]` (freq=1)
  - Chunk 56: `[text_content:h3×1]` (freq=1)
  - Chunk 57: `[text_content:h3×1]` (freq=1)
  - Chunk 58: `[text_content:h3×1]` (freq=1)
  - Chunk 59: `[text_content:h3×1]` (freq=1)
  - Chunk 60: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: rollingstone_com.html ===
Chunks: 61 (structural=12, functional=12, text=37)
Categories: {'card': 8, 'menu_item': 11, 'structural': 3, 'search_input': 1, 'pagination': 1, 'text_singleton': 37}
Content: 175 tagged, 172 preserved (98%)
Leaks: 3 total, 0 high-importance

--- Chunk 0: div ---
  type=card freq=6 excl=0.00
  pattern_xpath: ///div
  tree_sig: li(div(div(div(div(div)),div(h3(a),p,ul,ul(li(div))))))
  content: [HREF=2 TEXT=4]

--- Chunk 1: a.amazon.block ---
  type=card freq=4 excl=0.15
  pattern_xpath: ///a[contains(@rel,'nofollow')][contains(@class,'link')][contains(@class,'unstyle')][contains(@class,'block')][contains(@class,'display')]
  tree_sig: li(div(a(div(div(img)),div(div(svg(g)),h3,time))))
  content: [ATTR=1 HREF=1 IMG=2 TEXT=2]

--- Chunk 2: a.black.blank ---
  type=menu_item freq=5 excl=0.84
  pattern_xpath: ///div[contains(@class,'social')][contains(@class,'vertical')][contains(@class,'middle')]//a[contains(@class,'radius')][contains(@rel,'noopener')][contains(@rel,'noreferrer')][contains(@target,'blank')][contains(@class,'black')]
  tree_sig: a(span,svg(use))
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 3: a.awards.college ---
  type=card freq=7 excl=0.26
  pattern_xpath: ///a[contains(@class,'flex')][contains(@class,'lrv')]
  tree_sig: div(a(div(div(div(img))),div(div(div),h3)))
  content: [ATTR=1 HREF=1 IMG=2 TEXT=2]

--- Chunk 4: div ---
  type=card freq=5 excl=0.00
  pattern_xpath: ///div
  tree_sig: li(div(div(div(div(div(a),div)),div(h3(a),ul(li(span)),ul))))
  content: [ATTR=1 HREF=2 IMG=2 TEXT=2]

--- Chunk 5: li.//.collapsed ---
  type=structural freq=2 excl=0.27
  pattern_xpath: ///li[contains(@class,'parent')][contains(@data-collapsible,'collapsed')][contains(@class,'mega')][contains(@class,'menu')][contains(@class,'//')]
  tree_sig: li(div(a),ul(li(a),li(a),li(a),li(a),li(a)))
  content: [HREF=6 TEXT=6]

--- Chunk 6: li.//.collapsed ---
  type=structural freq=2 excl=0.27
  pattern_xpath: ///li[contains(@class,'parent')][contains(@data-collapsible,'collapsed')][contains(@class,'mega')][contains(@class,'menu')][contains(@class,'//')]
  tree_sig: li(div(a),ul(li(a),li(a),li(a),li(a)))
  content: [HREF=4 TEXT=5]

--- Chunk 7: li.//.collapsed ---
  type=structural freq=2 excl=0.27
  pattern_xpath: ///li[contains(@class,'parent')][contains(@data-collapsible,'collapsed')][contains(@class,'mega')][contains(@class,'menu')][contains(@class,'//')]
  tree_sig: li(div(a),ul)
  content: [HREF=1 TEXT=1]

--- Chunk 8: div.border.effect ---
  type=card freq=10 excl=0.52
  pattern_xpath: ///div[contains(@class,'effect')][contains(@class,'fade')][contains(@class,'image')][contains(@class,'lazy')][contains(@class,'border')]
  tree_sig: div(div(img))
  content: [ATTR=1 IMG=2]

--- Chunk 9: div.image.lazy ---
  type=card freq=25 excl=0.16
  pattern_xpath: ///div[contains(@class,'image')][contains(@class,'lazy')][contains(@class,'border')][contains(@class,'lrv')]
  tree_sig: div(a(div(img)))
  content: [ATTR=1 HREF=1 IMG=2]

--- Chunk 10: a.bob.com ---
  type=card freq=7 excl=0.16
  pattern_xpath: ///a[contains(@class,'image')][contains(@class,'lazy')][contains(@class,'link')][contains(@class,'unstyle')][contains(@class,'lrv')]
  tree_sig: a(div(img))
  content: [ATTR=1 HREF=1 IMG=3]

--- Chunk 11: div.//.author ---
  type=card freq=6 excl=0.32
  pattern_xpath: ///div[contains(@class,'author')][contains(@class,'basic')][contains(@class,'//')][contains(@class,'xs')][contains(@class,'color')]
  tree_sig: div(div(a),span)
  content: [HREF=1 TEXT=2]

--- Chunk 12: [search_inputs] ---
  type=search_input freq=8 excl=0.75
  pattern_xpath: ///input[contains(@id,'search')][contains(@type,'text')]
  content: [ATTR=2]

--- Chunk 13: [pagination_buttons] ---
  type=pagination freq=43 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1]

--- Chunk 14: [text_content:li×7] ---
  type=text_singleton freq=7 excl=0.00
  pattern_xpath: ///li
  content: [HREF=2 TEXT=4]

--- Chunk 15: [text_content:p×8] ---
  type=text_singleton freq=1 excl=0.79
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'grpcntr')][contains(@class,'txt')][contains(@class,'ot')]
  content: [TEXT=10]

--- Chunk 16: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=3 IMG=2 TEXT=5]

--- Chunk 17: [nav_content:a×41] ---
  type=menu_item freq=41 excl=0.05
  pattern_xpath: ///a[contains(@class,'color')][contains(@class,'lrv')]
  content: [HREF=1 TEXT=1]

--- Chunk 18: [nav_content:li×9] ---
  type=menu_item freq=9 excl=0.34
  pattern_xpath: ///li[contains(@class,'child')][contains(@class,'mega')][contains(@class,'menu')][contains(@class,'item')][contains(@class,'list')]
  content: [HREF=1 TEXT=1]

--- Chunk 19: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.12
  pattern_xpath: ///li[contains(@class,'nav')][contains(@class,'item')][contains(@class,'list')]
  content: [HREF=1 TEXT=1]

--- Chunk 20: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.12
  pattern_xpath: ///div[contains(@class,'account')][contains(@class,'hidden')][contains(@class,'tooltip')]//li[contains(@class,'nav')][contains(@class,'item')][contains(@class,'list')]
  content: [HREF=1 TEXT=1]

--- Chunk 21: [nav_content:h3×7] ---
  type=menu_item freq=7 excl=0.09
  pattern_xpath: ///h3[contains(@class,'xs')][contains(@class,'primary')][contains(@class,'block')][contains(@class,'display')][contains(@id,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:a×13] ---
  type=menu_item freq=13 excl=0.09
  pattern_xpath: ///a[contains(@class,'letter')][contains(@class,'spacing')][contains(@class,'color')][contains(@class,'lrv')]
  content: [HREF=1 TEXT=1]

--- Chunk 25: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.09
  pattern_xpath: ///a[contains(@class,'letter')][contains(@class,'spacing')][contains(@class,'color')][contains(@class,'lrv')]
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:a×13] ---
  type=menu_item freq=13 excl=0.09
  pattern_xpath: ///a[contains(@class,'letter')][contains(@class,'spacing')][contains(@class,'color')][contains(@class,'lrv')]
  content: [HREF=1 TEXT=1]

--- Chunk 25: [nav_content:a×15] ---
  type=menu_item freq=15 excl=0.09
  pattern_xpath: ///a[contains(@class,'letter')][contains(@class,'spacing')][contains(@class,'color')][contains(@class,'lrv')]
  content: [HREF=1 TEXT=1]

--- Chunk 26: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.24
  pattern_xpath: ///h2[contains(@id,'heading')][contains(@id,'section')][contains(@class,'heading')][contains(@class,'larva')][contains(@class,'secondary')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.20
  pattern_xpath: ///h3[contains(@class,'center')][contains(@class,'align')][contains(@class,'heading')][contains(@class,'larva')][contains(@class,'//')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.24
  pattern_xpath: ///div[contains(@class,'span')]//h2[contains(@id,'heading')][contains(@id,'section')][contains(@class,'heading')][contains(@class,'larva')][contains(@class,'secondary')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.40
  pattern_xpath: ///h2[contains(@id,'pc')][contains(@id,'ot')][contains(@id,'title')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.40
  pattern_xpath: ///h3[contains(@id,'category')][contains(@id,'ot')][contains(@id,'title')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.47
  pattern_xpath: ///h4[contains(@id,'pmc')][contains(@class,'after')][contains(@class,'arrow')][contains(@class,'cursor')][contains(@class,'down')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [TEXT=1]

--- Chunk 33: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.63
  pattern_xpath: ///div[contains(@class,'inner')][contains(@class,'background')]//h1[contains(@data-testid,'header')][contains(@data-testid,'logo')][contains(@class,'flex')][contains(@class,'lrv')]
  content: [HREF=2 TEXT=4]
  LEAKS (medium):
    [TEXT] .rs-logo-grey-shadow-st0{fill:#bcbec0}.rs-logo-grey-shadow-st1{fill:#d

--- Chunk 34: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.24
  pattern_xpath: ///div[contains(@class,'flex')][contains(@class,'items')][contains(@class,'baseline')]/h3[contains(@class,'xxs')][contains(@class,'heading')][contains(@class,'larva')][contains(@class,'//')][contains(@class,'theme')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.27
  pattern_xpath: ///h3[contains(@class,'gr')][contains(@class,'xxxs')][contains(@id,'bb')][contains(@class,'desktop')][contains(@class,'body')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.27
  pattern_xpath: ///h3[contains(@class,'gr')][contains(@class,'xxxs')][contains(@id,'bb')][contains(@class,'desktop')][contains(@class,'body')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.27
  pattern_xpath: ///h3[contains(@class,'gr')][contains(@class,'xxxs')][contains(@id,'bb')][contains(@class,'desktop')][contains(@class,'body')]
  content: [TEXT=1]

--- Chunk 38: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.23
  pattern_xpath: ///h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'header')][contains(@id,'id')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.23
  pattern_xpath: ///h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'header')][contains(@id,'id')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 40: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.23
  pattern_xpath: ///div[contains(@class,'acc')][contains(@class,'hdr')][contains(@class,'always')]/h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'header')][contains(@id,'id')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 41: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.23
  pattern_xpath: ///h4[contains(@class,'cat')][contains(@class,'header')][contains(@id,'header')][contains(@id,'id')][contains(@class,'ot')]
  content: [TEXT=1]

--- Chunk 42: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.29
  pattern_xpath: ///div[contains(@class,'special')][contains(@class,'coverage')][contains(@class,'logo')]/h2[contains(@class,'brand')][contains(@id,'heading')][contains(@id,'section')][contains(@class,'xl')][contains(@class,'heading')]
  content: [TEXT=1]

--- Chunk 43: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.70
  pattern_xpath: ///h3[contains(@id,'all')][contains(@id,'time')][contains(@id,'best')][contains(@id,'of')][contains(@id,'songs')]
  content: [HREF=1 TEXT=1]

--- Chunk 44: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.38
  pattern_xpath: ///h3[contains(@id,'ffe')][contains(@class,'family')][contains(@class,'ellipsis')][contains(@class,'truncate')][contains(@class,'tb')]
  content: [TEXT=1]

--- Chunk 45: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.38
  pattern_xpath: ///h3[contains(@id,'ffdf')][contains(@class,'family')][contains(@class,'ellipsis')][contains(@class,'truncate')][contains(@class,'tb')]
  content: [TEXT=1]

--- Chunk 46: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///h3[contains(@class,'stories')][contains(@class,'stroke')][contains(@id,'century')][contains(@id,'st')][contains(@id,'best')]
  content: [HREF=1 TEXT=1]

--- Chunk 47: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h3[contains(@id,'african')][contains(@id,'black')][contains(@id,'grey')][contains(@id,'market')][contains(@id,'parrot')]
  content: [HREF=1 TEXT=1]

--- Chunk 48: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///h3[contains(@id,'band')][contains(@id,'disappeared')][contains(@id,'nashville')][contains(@id,'perry')][contains(@id,'the')]
  content: [HREF=1 TEXT=1]

--- Chunk 49: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.50
  pattern_xpath: ///h3[contains(@id,'busy')][contains(@id,'creek')][contains(@id,'dawsons')][contains(@id,'philipps')][contains(@id,'tribute')]
  content: [HREF=1 TEXT=1]

--- Chunk 50: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.40
  pattern_xpath: ///h3[contains(@id,'hollywood')][contains(@id,'tributes')][contains(@id,'beek')][contains(@id,'der')][contains(@id,'james')]
  content: [HREF=1 TEXT=1]

--- Chunk 51: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.50
  pattern_xpath: ///h3[contains(@id,'and')][contains(@id,'bud')][contains(@id,'cort')][contains(@id,'dead')][contains(@id,'harold')]
  content: [HREF=1 TEXT=1]

--- Chunk 52: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.67
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'menus')][contains(@class,'flex')]//h4[contains(@id,'rolling')][contains(@id,'stone')][contains(@class,'remove')][contains(@id,'menu')][contains(@class,'after')]
  content: [TEXT=1]

--- Chunk 53: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.53
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'menus')][contains(@class,'flex')]//h4[contains(@id,'legal')][contains(@class,'remove')][contains(@id,'menu')][contains(@class,'after')][contains(@class,'arrow')]
  content: [TEXT=1]

--- Chunk 54: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.22
  pattern_xpath: ///div[contains(@class,'none')]//h3[contains(@class,'tablet')][contains(@class,'center')][contains(@class,'align')][contains(@class,'basic')][contains(@class,'letter')]
  content: [TEXT=1]

--- Chunk 55: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.42
  pattern_xpath: ///section[contains(@class,'footer')][contains(@class,'newsletter')][contains(@class,'flex')]/h3[contains(@class,'left')][contains(@class,'bold')][contains(@class,'weight')][contains(@class,'align')][contains(@class,'height')]
  content: [TEXT=1]

--- Chunk 56: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.33
  pattern_xpath: ///h3[contains(@id,'cf')][contains(@class,'decoration')][contains(@class,'underline')][contains(@class,'body')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 57: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.33
  pattern_xpath: ///h3[contains(@id,'cff')][contains(@class,'decoration')][contains(@class,'underline')][contains(@class,'body')][contains(@class,'text')]
  content: [TEXT=1]

--- Chunk 58: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h3[contains(@class,'decoration')][contains(@class,'underline')][contains(@class,'body')][contains(@class,'text')][contains(@class,'hover')]
  content: [TEXT=1]

--- Chunk 59: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h3[contains(@class,'decoration')][contains(@class,'underline')][contains(@class,'body')][contains(@class,'text')][contains(@class,'hover')]
  content: [TEXT=1]

--- Chunk 60: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///li
  content: [ATTR=1 HREF=3 IMG=2 TEXT=9]

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
4. Use filename `rollingstone_com.html` in all `_distill()` calls
5. Name the module `test_rollingstone_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
