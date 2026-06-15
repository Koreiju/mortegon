# Test Generation Task: youtube_comwatchvuIHfJSPFec.html

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

- **Total chunks:** 40
- **Structural chunks:** 6
- **Text/Nav chunks:** 32
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.details.item` (freq=9, pq_sig=`div(a(h4),div)`)
  - Chunk 1: `span.listlabel.modern` (freq=12, pq_sig=`span(span,span(span))`)
  - Chunk 2: `span.expander.inline` (freq=2, pq_sig=`span`)
  - Chunk 3: `a.content.false` (freq=47, pq_sig=`a(yt-thumbnail-view-model(div(img),yt-thumbnail-ov`)
  - Chunk 4: `yt-icon.height.icon` (freq=31, pq_sig=`yt-icon(span(div(svg(path))))`)
  - Chunk 5: `a.endpoint.false` (freq=19, pq_sig=`a(div(div,h4,h4),div(div,yt-img-shadow(img)))`)

**Text/Nav chunks:**
  - Chunk 8: `[nav_content:a×37]` (freq=37)
  - Chunk 9: `[nav_content:a×6]` (freq=6)
  - Chunk 10: `[text_content:h1×1]` (freq=1)
  - Chunk 11: `[text_content:h2×1]` (freq=1)
  - Chunk 12: `[text_content:h2×1]` (freq=1)
  - Chunk 13: `[text_content:h2×1]` (freq=1)
  - Chunk 14: `[text_content:h2×1]` (freq=1)
  - Chunk 15: `[text_content:h2×1]` (freq=1)
  - Chunk 16: `[text_content:h2×1]` (freq=1)
  - Chunk 17: `[text_content:h2×1]` (freq=1)
  - Chunk 18: `[text_content:h3×1]` (freq=1)
  - Chunk 19: `[text_content:h4×1]` (freq=1)
  - Chunk 20: `[text_content:h4×1]` (freq=1)
  - Chunk 21: `[text_content:h4×1]` (freq=1)
  - Chunk 22: `[text_content:h4×1]` (freq=1)
  - Chunk 23: `[text_content:h4×1]` (freq=1)
  - Chunk 24: `[text_content:h4×1]` (freq=1)
  - Chunk 25: `[text_content:h4×1]` (freq=1)
  - Chunk 26: `[text_content:h4×1]` (freq=1)
  - Chunk 27: `[text_content:h4×1]` (freq=1)
  - Chunk 28: `[text_content:h3×1]` (freq=1)
  - Chunk 29: `[text_content:h3×1]` (freq=1)
  - Chunk 30: `[text_content:h3×1]` (freq=1)
  - Chunk 31: `[text_content:h4×1]` (freq=1)
  - Chunk 32: `[text_content:h4×1]` (freq=1)
  - Chunk 33: `[text_content:h4×1]` (freq=1)
  - Chunk 34: `[text_content:h4×1]` (freq=1)
  - Chunk 35: `[text_content:h4×1]` (freq=1)
  - Chunk 36: `[text_content:h4×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h1×1]` (freq=1)
  - Chunk 39: `[text_content:h1×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: youtube_comwatchvuIHfJSPFec.html ===
Chunks: 40 (structural=6, functional=4, text=30)
Categories: {'card': 5, 'structural': 1, 'search_input': 1, 'pagination': 1, 'menu_item': 2, 'text_singleton': 30}
Content: 257 tagged, 189 preserved (74%)
Leaks: 68 total, 34 high-importance

--- Chunk 0: div.details.item ---
  type=card freq=9 excl=0.26
  pattern_xpath: ///div[contains(@id,'details')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')][contains(@class,'item')]
  tree_sig: div(a(h4),div)
  content: [ATTR=1 HREF=1 TEXT=2]

--- Chunk 1: span.listlabel.modern ---
  type=card freq=12 excl=1.00
  pattern_xpath: ///a[contains(@class,'modern')][contains(@class,'set')][contains(@class,'still')][contains(@class,'suggestion')][contains(@class,'videowall')]
  tree_sig: span(span,span(span))
  content: [ATTR=1 BG=1 HREF=1 TEXT=14]

--- Chunk 2: span.expander.inline ---
  type=structural freq=2 excl=0.51
  pattern_xpath: ///ytd-text-inline-expander[contains(@id,'description')][contains(@id,'inline')][contains(@id,'expander')]//span[contains(@id,'ellipsis')][contains(@class,'expander')][contains(@class,'inline')][contains(@class,'text')][contains(@class,'scope')]
  tree_sig: span

--- Chunk 3: a.content.false ---
  type=card freq=47 excl=0.63
  pattern_xpath: ///a[contains(@aria-hidden,'true')][contains(@class,'image')][contains(@class,'content')][contains(@aria-haspopup,'false')][contains(@style,'width')]
  tree_sig: a(yt-thumbnail-view-model(div(img),yt-thumbnail-overlay-badge-view-model(yt-thum
  content: [HREF=1 IMG=1 TEXT=1]

--- Chunk 4: yt-icon.height.icon ---
  type=card freq=31 excl=1.00
  pattern_xpath: ///yt-icon[contains(@class,'merch')][contains(@class,'merchant')][contains(@class,'shelf')][contains(@icon,'in')][contains(@icon,'new')]
  tree_sig: yt-icon(span(div(svg(path))))

--- Chunk 5: a.endpoint.false ---
  type=card freq=19 excl=0.82
  pattern_xpath: ///ytd-macro-markers-list-item-renderer[contains(@class,'horizontal')][contains(@class,'card')][contains(@layout,'macro')]/a[contains(@class,'endpoint')][contains(@class,'simple')][contains(@draggable,'false')][contains(@id,'endpoint')][contains(@class,'yt')]
  tree_sig: a(div(div,h4,h4),div(div,yt-img-shadow(img)))
  content: [ATTR=2 HREF=1 TEXT=3]

--- Chunk 6: [search_inputs] ---
  type=search_input freq=7 excl=0.29 OUTLIER=3.7x
  pattern_xpath: ///tp-yt-paper-listbox[contains(@role,'listbox')][contains(@class,'yt')][contains(@class,'scope')][contains(@class,'style')]
  content: [ATTR=1]

--- Chunk 7: [pagination_buttons] ---
  type=pagination freq=189 excl=1.00
  pattern_xpath: ///button[contains(@class,'button')][contains(@class,'next')][contains(@class,'shape')][contains(@class,'spec')][contains(@class,'backdrop')]
  content: [ATTR=2 HREF=1]

--- Chunk 8: [nav_content:a×37] ---
  type=menu_item freq=37 excl=0.22
  pattern_xpath: ///a[contains(@aria-haspopup,'false')][contains(@rel,'nofollow')][contains(@class,'lockup')][contains(@class,'metadata')][contains(@class,'model')]
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 9: [nav_content:a×6] ---
  type=menu_item freq=6 excl=0.90
  pattern_xpath: ///a[contains(@class,'attributed')][contains(@class,'color')][contains(@class,'core')][contains(@class,'string')][contains(@class,'action')]
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 10: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.26
  pattern_xpath: ///h1[contains(@class,'watch')][contains(@class,'metadata')][contains(@class,'scope')][contains(@class,'style')][contains(@class,'ytd')]
  content: [ATTR=1 TEXT=1]

--- Chunk 11: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h2[contains(@class,'engagement')][contains(@class,'header')][contains(@class,'panel')][contains(@class,'title')][contains(@id,'title')]
  content: [ATTR=2 TEXT=2]

--- Chunk 12: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h2[contains(@class,'engagement')][contains(@class,'header')][contains(@class,'panel')][contains(@class,'title')][contains(@id,'title')]
  content: [ATTR=2 TEXT=1]

--- Chunk 13: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h2[contains(@class,'engagement')][contains(@class,'header')][contains(@class,'panel')][contains(@class,'title')][contains(@id,'title')]
  content: [ATTR=2 TEXT=1]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h2[contains(@class,'engagement')][contains(@class,'header')][contains(@class,'panel')][contains(@class,'title')][contains(@id,'title')]
  content: [ATTR=3 TEXT=1]

--- Chunk 15: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.14
  pattern_xpath: ///h2[contains(@class,'engagement')][contains(@class,'header')][contains(@class,'panel')][contains(@class,'title')][contains(@id,'title')]
  content: [ATTR=2 TEXT=1]

--- Chunk 16: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.45
  pattern_xpath: ///h2[contains(@class,'comments')][contains(@id,'count')][contains(@class,'header')][contains(@class,'renderer')][contains(@class,'scope')]
  content: [TEXT=2]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.62
  pattern_xpath: ///h2[contains(@class,'card')][contains(@class,'horizontal')][contains(@id,'header')][contains(@class,'list')][contains(@class,'renderer')]
  content: [ATTR=1 TEXT=2]

--- Chunk 18: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.57
  pattern_xpath: ///h3[contains(@class,'description')][contains(@class,'infocards')][contains(@class,'section')][contains(@class,'video')][contains(@id,'title')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 20: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 21: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 22: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 23: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 24: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 25: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 26: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 27: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.09
  pattern_xpath: ///h4[contains(@class,'problem')][contains(@class,'walkthroughs')][contains(@class,'macro')][contains(@class,'markers')][contains(@class,'list')]
  content: [ATTR=1 TEXT=1]

--- Chunk 28: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.30
  pattern_xpath: ///h3[contains(@class,'heading')][contains(@class,'reset')][contains(@class,'lockup')][contains(@class,'metadata')][contains(@class,'model')]
  content: [ATTR=2 HREF=1 TEXT=1]

--- Chunk 29: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.30 LEAKS=31
  pattern_xpath: ///div[contains(@class,'menu')][contains(@class,'button')]/h3[contains(@class,'heading')][contains(@class,'reset')][contains(@class,'lockup')][contains(@class,'metadata')][contains(@class,'model')]
  content: [ATTR=41 HREF=40 TEXT=40]
  LEAKS (high):
    [HREF] /watch?v=jYtqhtK2q1E (href not in rendered output)
    [HREF] /watch?v=IrsXPZ_z_KM (href not in rendered output)
    [HREF] /watch?v=sI6Kjn_XOpI&pp=0gcJCYcKAYcqIYzv (href not in rendered output)
    [HREF] /watch?v=lbU3_IYhqYE (href not in rendered output)
    [HREF] /watch?v=qnxiB39lJlo (href not in rendered output)
  LEAKS (medium):
    [TEXT] Trump Attorney General Pam Bondi Gets Hammered on Epstein & MAGA Coali
    [TEXT] RICHARD KIND Talks Coen Brothers, Death, And George Clooney
    [TEXT] Why Kal Penn is Disillusioned with Democrats

--- Chunk 30: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.39
  pattern_xpath: ///h3[contains(@class,'attributes')][contains(@class,'section')][contains(@class,'video')][contains(@class,'model')][contains(@class,'view')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h4[contains(@id,'product')][contains(@class,'product')][contains(@id,'title')][contains(@class,'list')][contains(@class,'item')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h4[contains(@id,'product')][contains(@class,'product')][contains(@id,'title')][contains(@class,'list')][contains(@class,'item')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h4[contains(@id,'product')][contains(@class,'product')][contains(@id,'title')][contains(@class,'list')][contains(@class,'item')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h4[contains(@id,'product')][contains(@class,'product')][contains(@id,'title')][contains(@class,'list')][contains(@class,'item')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h4[contains(@id,'product')][contains(@class,'product')][contains(@id,'title')][contains(@class,'list')][contains(@class,'item')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.10
  pattern_xpath: ///h4[contains(@id,'product')][contains(@class,'product')][contains(@id,'title')][contains(@class,'list')][contains(@class,'item')]
  content: [TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.16 LEAKS=3
  pattern_xpath: ///h3[contains(@class,'comment')][contains(@class,'model')][contains(@class,'view')][contains(@class,'scope')][contains(@class,'style')]
  content: [HREF=20 TEXT=20]
  LEAKS (high):
    [HREF] /@imaboy. (href not in rendered output)
    [HREF] /@tyaustin9936 (href not in rendered output)
    [HREF] /@michaelonmichaelonmichael (href not in rendered output)
  LEAKS (medium):
    [TEXT] @michaelonmichaelonmichael

--- Chunk 38: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.21
  pattern_xpath: ///h1[contains(@class,'attribute')][contains(@class,'video')][contains(@class,'model')][contains(@class,'view')][contains(@class,'yt')]
  content: [TEXT=1]

--- Chunk 39: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.21
  pattern_xpath: ///h1[contains(@class,'attribute')][contains(@class,'video')][contains(@class,'model')][contains(@class,'view')][contains(@class,'yt')]
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
4. Use filename `youtube_comwatchvuIHfJSPFec.html` in all `_distill()` calls
5. Name the module `test_youtube_comwatchvuIHfJSPFec_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
