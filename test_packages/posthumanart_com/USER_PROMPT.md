# Test Generation Task: posthumanart_com.html

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

- **Total chunks:** 37
- **Structural chunks:** 11
- **Text/Nav chunks:** 25
- **Search input found:** False
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.absolute.auto` (freq=6, pq_sig=`div(div(div,div(div(div(picture(source,source,img)`)
  - Chunk 1: `div.absolute.auto` (freq=2, pq_sig=`div(div(div,div(div(div(picture(source,source,img)`)
  - Chunk 2: `div.at.button` (freq=18, pq_sig=`div(div(div(canvas,wix-video(img,svg(defs(filter))`)
  - Chunk 3: `a.com.depth` (freq=70, pq_sig=`a(div(span))`)
  - Chunk 4: `button.accessibility.icon` (freq=9, pq_sig=`button(svg(path))`)
  - Chunk 5: `a.com.https` (freq=152, pq_sig=`a(div(div(h2)))`)
  - Chunk 6: `p.em.font` (freq=7, pq_sig=`p(span(span(span(span(span(span))))))`)
  - Chunk 7: `div.box.common` (freq=26, pq_sig=`div(div(div(div(div(div(a,div),div(a,div))))),div(`)
  - Chunk 8: `div.box.common` (freq=30, pq_sig=`div(div(div(div(div(div(a,div),div(a,div))))),div(`)
  - Chunk 9: `div.content.gallery` (freq=19, pq_sig=`div(picture(img,source,source),picture(img,source,`)
  - Chunk 10: `div.blog.bt` (freq=39, pq_sig=`div(a(div(div(h2))),div(div(div(div),span(span)),s`)

**Text/Nav chunks:**
  - Chunk 12: `[text_content:p×3]` (freq=3)
  - Chunk 13: `[nav_content:a×115]` (freq=115)
  - Chunk 14: `[text_content:h2×1]` (freq=1)
  - Chunk 15: `[text_content:h4×1]` (freq=1)
  - Chunk 16: `[text_content:h4×1]` (freq=1)
  - Chunk 17: `[text_content:h2×1]` (freq=1)
  - Chunk 18: `[text_content:h2×1]` (freq=1)
  - Chunk 19: `[text_content:h4×1]` (freq=1)
  - Chunk 20: `[text_content:h2×1]` (freq=1)
  - Chunk 21: `[text_content:h2×1]` (freq=1)
  - Chunk 22: `[text_content:h2×1]` (freq=1)
  - Chunk 23: `[text_content:h2×1]` (freq=1)
  - Chunk 24: `[text_content:h2×1]` (freq=1)
  - Chunk 25: `[text_content:h2×1]` (freq=1)
  - Chunk 26: `[text_content:h2×1]` (freq=1)
  - Chunk 27: `[text_content:h2×1]` (freq=1)
  - Chunk 28: `[text_content:h2×1]` (freq=1)
  - Chunk 29: `[text_content:h2×1]` (freq=1)
  - Chunk 30: `[text_content:h2×1]` (freq=1)
  - Chunk 31: `[text_content:h2×1]` (freq=1)
  - Chunk 32: `[text_content:h2×1]` (freq=1)
  - Chunk 33: `[text_content:h2×1]` (freq=1)
  - Chunk 34: `[text_content:h2×1]` (freq=1)
  - Chunk 35: `[text_content:h2×1]` (freq=1)
  - Chunk 36: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: posthumanart_com.html ===
Chunks: 37 (structural=11, functional=2, text=24)
Categories: {'card': 7, 'structural': 1, 'button': 2, 'menu_item': 2, 'pagination': 1, 'text_singleton': 24}
Content: 453 tagged, 407 preserved (90%)
Leaks: 46 total, 45 high-importance

--- Chunk 0: div.absolute.auto ---
  type=card freq=6 excl=0.50 LEAKS=18
  pattern_xpath: ///div[contains(@class,'container')][contains(@class,'custom')][contains(@class,'focus')][contains(@class,'has')][contains(@data-hook,'container')]
  tree_sig: div(div(div,div(div(div(picture(source,source,img),picture(source,source,img))))
  content: [ATTR=8 HREF=2 IMG=117 TEXT=5]
  LEAKS (high):
    [IMG] https://static.wixstatic.com/media/2c940f_ab0f2dcfcc1049ceacabf9edf0dfd6b7~mv2.png/v1/fill (img URL not in rendered)
    [IMG] h_219 (img URL not in rendered)
    [IMG] q_95 (img URL not in rendered)
    [IMG] q_95 (img URL not in rendered)
    [IMG] https://static.wixstatic.com/media/2c940f_ab0f2dcfcc1049ceacabf9edf0dfd6b7~mv2.png/v1/fill (img URL not in rendered)

--- Chunk 1: div.absolute.auto ---
  type=structural freq=2 excl=1.00 LEAKS=18
  pattern_xpath: ///div[contains(@data-hash,'ccb')][contains(@data-hash,'cdca')][contains(@data-hash,'fb')][contains(@data-id,'ccb')][contains(@data-id,'cdca')]
  tree_sig: div(div(div,div(div(div(picture(source,source,img),picture(source,source,img)),i
  content: [ATTR=9 HREF=2 IMG=116 TEXT=5]
  LEAKS (high):
    [IMG] https://static.wixstatic.com/media/59ea15_a61ec8b9413e4ca2a88a0bf70d2db07ef000.jpg/v1/fill (img URL not in rendered)
    [IMG] h_219 (img URL not in rendered)
    [IMG] q_90 (img URL not in rendered)
    [IMG] q_90 (img URL not in rendered)
    [IMG] https://static.wixstatic.com/media/59ea15_a61ec8b9413e4ca2a88a0bf70d2db07ef000.jpg/v1/fill (img URL not in rendered)

--- Chunk 2: div.at.button ---
  type=button freq=18 excl=1.00
  pattern_xpath: ///div[contains(@aria-pressed,'true')][contains(@class,'at')][contains(@class,'fzb')][contains(@class,'yk')][contains(@role,'button')]
  tree_sig: div(div(div(canvas,wix-video(img,svg(defs(filter)),video))))
  content: [ATTR=1 IMG=16]

--- Chunk 3: a.com.depth ---
  type=menu_item freq=70 excl=1.00
  pattern_xpath: ///a[contains(@class,'depth')][contains(@class,'menu')][contains(@class,'root')][contains(@data-item-label,'true')][contains(@data-testid,'element')]
  tree_sig: a(div(span))
  content: [HREF=1 TEXT=1]

--- Chunk 4: button.accessibility.icon ---
  type=button freq=9 excl=0.66
  pattern_xpath: ///button[contains(@class,'accessibility')][contains(@class,'icon')][contains(@class,'shared')][contains(@class,'item')]
  tree_sig: button(svg(path))
  content: [ATTR=1]

--- Chunk 5: a.com.https ---
  type=card freq=152 excl=1.00
  pattern_xpath: ///a[contains(@class,'kgi')][contains(@class,'lyd')][contains(@class,'me')][contains(@class,'pu')][contains(@class,'xe')]
  tree_sig: a(div(div(h2)))
  content: [HREF=1 TEXT=1]

--- Chunk 6: p.em.font ---
  type=card freq=7 excl=0.19
  pattern_xpath: ///p[contains(@style,'em')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')]
  tree_sig: p(span(span(span(span(span(span))))))
  content: [TEXT=1]

--- Chunk 7: div.box.common ---
  type=card freq=26 excl=0.50 LEAKS=9
  pattern_xpath: ///div[contains(@class,'common')][contains(@class,'info')][contains(@class,'object')][contains(@class,'outer')][contains(@style,'box')]
  tree_sig: div(div(div(div(div(div(a,div),div(a,div))))),div(div(picture(img,source,source)
  content: [ATTR=4 HREF=2 IMG=54 TEXT=5]
  LEAKS (high):
    [IMG] https://static.wixstatic.com/media/93a60d_6ea9f1f6e8204fbaab6d7587bdbd960a~mv2.jpg/v1/fill (img URL not in rendered)
    [IMG] h_219 (img URL not in rendered)
    [IMG] q_90 (img URL not in rendered)
    [IMG] q_90 (img URL not in rendered)
    [IMG] https://static.wixstatic.com/media/93a60d_6ea9f1f6e8204fbaab6d7587bdbd960a~mv2.jpg/v1/fill (img URL not in rendered)

--- Chunk 8: div.box.common ---
  type=card freq=30 excl=0.50
  pattern_xpath: ///div[contains(@class,'common')][contains(@class,'info')][contains(@class,'object')][contains(@class,'outer')][contains(@style,'box')]
  tree_sig: div(div(div(div(div(div(a,div),div(a,div))))),div(div(picture(img,source,source)
  content: [ATTR=3 HREF=2 IMG=25 TEXT=5]

--- Chunk 9: div.content.gallery ---
  type=card freq=19 excl=1.00
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'image')][contains(@class,'preloaded')][contains(@class,'video')][contains(@data-hook,'image')]
  tree_sig: div(picture(img,source,source),picture(img,source,source))
  content: [ATTR=2 IMG=10]

--- Chunk 10: div.blog.bt ---
  type=card freq=39 excl=1.00
  pattern_xpath: ///div[contains(@class,'blog')][contains(@class,'bt')][contains(@class,'description')][contains(@class,'dkn')][contains(@class,'header')]
  tree_sig: div(a(div(div(h2))),div(div(div(div),span(span)),span(div(span(span(wow-image)))
  content: [ATTR=3 HREF=1 IMG=1 TEXT=3]

--- Chunk 11: [pagination_buttons] ---
  type=pagination freq=3 excl=1.00
  pattern_xpath: ///link[contains(@as,'fetch')][contains(@crossorigin,'anonymous')][contains(@id,'master')][contains(@id,'page')][contains(@position,'post')]
  content: [HREF=1]

--- Chunk 12: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.11
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'thuuay')][contains(@class,'ku')]/p[contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')][contains(@style,'font')]
  content: [HREF=2 TEXT=6]

--- Chunk 13: [nav_content:a×115] ---
  type=menu_item freq=115 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=3]

--- Chunk 14: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'waqbw')][contains(@class,'ku')]/h2[contains(@style,'normal')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')]
  content: [HREF=1 TEXT=1]

--- Chunk 15: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'cl')][contains(@class,'ku')]/h4[contains(@style,'normal')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')]
  content: [TEXT=2]

--- Chunk 16: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'dnu')][contains(@class,'ku')]/h4[contains(@style,'normal')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')]
  content: [TEXT=2]

--- Chunk 17: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.19
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'thcjtx')][contains(@class,'ku')]/h2[contains(@style,'em')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')]
  content: [TEXT=2]

--- Chunk 18: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'lbfqwdzf')][contains(@class,'ku')]/h2[contains(@style,'normal')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')]
  content: [TEXT=2]

--- Chunk 19: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'bft')][contains(@id,'bc')]/h4[contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')][contains(@style,'font')]
  content: [TEXT=3]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.13
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'libz')][contains(@id,'ba')]/h2[contains(@style,'normal')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@class,'font')]
  content: [TEXT=4]

--- Chunk 21: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 24: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
  content: [TEXT=1]

--- Chunk 36: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.06
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'webkit')]
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
4. Use filename `posthumanart_com.html` in all `_distill()` calls
5. Name the module `test_posthumanart_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
