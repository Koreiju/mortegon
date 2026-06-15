# Test Generation Task: foreignobjekt_comartists.html

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

- **Total chunks:** 11
- **Structural chunks:** 7
- **Text/Nav chunks:** 3
- **Search input found:** False
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `section.classic.comp` (freq=4, pq_sig=`section(div(div(div(div(div(div),div(div),div(div)`)
  - Chunk 1: `section.classic.comp` (freq=2, pq_sig=`section(div(div,div),div(div(div(div(div(div),div(`)
  - Chunk 2: `div.absolute.auto` (freq=3, pq_sig=`div(div,div(div(div(div(div(div,div),div(div,span)`)
  - Chunk 3: `div.bg.comp` (freq=26, pq_sig=`div(div,div(wow-image(img)))`)
  - Chunk 4: `div.comp.false` (freq=40, pq_sig=`div(a(span))`)
  - Chunk 5: `li.comp.data` (freq=4, pq_sig=`li(a(img))`)
  - Chunk 6: `div.common.float` (freq=3, pq_sig=`div(div(div(div(div(div(a,div),div(div)),div(div(a`)

**Text/Nav chunks:**
  - Chunk 8: `[text_content:h6×1]` (freq=1)
  - Chunk 9: `[text_content:h6×1]` (freq=1)
  - Chunk 10: `[text_content:h6×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: foreignobjekt_comartists.html ===
Chunks: 11 (structural=7, functional=1, text=3)
Categories: {'card': 6, 'structural': 1, 'pagination': 1, 'text_singleton': 3}
Content: 340 tagged, 227 preserved (67%)
Leaks: 113 total, 88 high-importance

--- Chunk 0: section.classic.comp ---
  type=card freq=4 excl=0.70 LEAKS=8
  pattern_xpath: ///section[contains(@class,'lwvevxtc')][contains(@id,'lwvevxtc')][contains(@class,'oqnisf')][contains(@class,'section')][contains(@data-block-level-container,'classic')]
  tree_sig: section(div(div(div(div(div(div),div(div),div(div),div(div))))),div(div,div))
  content: [ATTR=13 HREF=7 IMG=7 TEXT=19]
  LEAKS (high):
    [IMG] https://static.wixstatic.com/media/f0a2e7_dde5acbfb2354cbca6dd806ce2fa8b9a~mv2.jpg/v1/fill (img URL not in rendered)
    [HREF] https://www.foreignobjekt.com/eunsol-lee-kimberly-lee (href not in rendered output)
    [IMG] https://static.wixstatic.com/media/f0a2e7_968c6c077f054945a6c04801cd08ba5c~mv2.jpg/v1/fill (img URL not in rendered)
    [HREF] https://www.foreignobjekt.com/bassem-saad (href not in rendered output)
    [IMG] https://static.wixstatic.com/media/f0a2e7_ca7973285b4b42c18bf5c8cb03a559c7~mv2_d_3383_3312 (img URL not in rendered)

--- Chunk 1: section.classic.comp ---
  type=structural freq=2 excl=0.70 LEAKS=6
  pattern_xpath: ///section[contains(@class,'lwvevxtd')][contains(@id,'lwvevxtd')][contains(@class,'oqnisf')][contains(@class,'section')][contains(@data-block-level-container,'classic')]
  tree_sig: section(div(div,div),div(div(div(div(div(div),div(div),div(div),div(div))))))
  content: [ATTR=14 BG=2 HREF=7 IMG=3 TEXT=19]
  LEAKS (high):
    [HREF] https://www.foreignobjekt.com (href not in rendered output)
    [HREF] https://www.foreignobjekt.com/post/diane-edwards (href not in rendered output)
    [IMG] https://static.wixstatic.com/media/f0a2e7_c1e8764128e14f6796cec4fdbe536d03~mv2.jpg/v1/fill (img URL not in rendered)
    [HREF] https://www.foreignobjekt.com/beyond-woke-and-problematic (href not in rendered output)
    [IMG] https://static.wixstatic.com/media/f0a2e7_d7f4628c4ab149188fb8d0243689949c~mv2.png/v1/fill (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Narcissus as Narcosis
    [TEXT] The Dichotomy of Cyberspace and the FacadeNarcissus as Narcosis
    [TEXT] 𝐁𝐞𝐲𝐨𝐧𝐝 𝐖𝐨𝐤𝐞 𝐚𝐧𝐝 𝐏𝐫𝐨𝐛𝐥𝐞𝐦𝐚𝐭𝐢𝐜

--- Chunk 2: div.absolute.auto ---
  type=card freq=3 excl=1.00 LEAKS=19
  pattern_xpath: ///div[contains(@class,'container')][contains(@class,'custom')][contains(@class,'focus')][contains(@class,'has')][contains(@class,'regular')]
  tree_sig: div(div,div(div(div(div(div(div,div),div(div,span)))),div(div(picture(img,source
  content: [ATTR=14 HREF=6 IMG=109 TEXT=12]
  LEAKS (high):
    [IMG] https://static.wixstatic.com/media/f0a2e7_28eccfb1cde94446b006aa0867a6dc76~mv2.jpg/v1/fill (img URL not in rendered)
    [IMG] h_355 (img URL not in rendered)
    [IMG] q_90 (img URL not in rendered)
    [IMG] q_90 (img URL not in rendered)
    [IMG] https://static.wixstatic.com/media/f0a2e7_28eccfb1cde94446b006aa0867a6dc76~mv2.jpg/v1/fill (img URL not in rendered)
  LEAKS (medium):
    [TEXT] 2,938 views2 comments
    [TEXT] Apr 30, 20256 min read
    [TEXT] 25 likes. Post not marked as liked

--- Chunk 3: div.bg.comp ---
  type=card freq=26 excl=1.00
  pattern_xpath: ///div[contains(@class,'iwv')][contains(@class,'mw')][contains(@data-hook,'bg')][contains(@data-hook,'layers')][contains(@data-motion-part,'bg')]
  tree_sig: div(div,div(wow-image(img)))
  content: [IMG=1]

--- Chunk 4: div.comp.false ---
  type=card freq=40 excl=0.73
  pattern_xpath: ///div[contains(@aria-disabled,'false')][contains(@class,'fub')][contains(@class,'tgk')][contains(@class,'comp')][contains(@id,'item')]
  tree_sig: div(a(span))
  content: [HREF=1]

--- Chunk 5: li.comp.data ---
  type=card freq=4 excl=0.87
  pattern_xpath: ///li[contains(@class,'kw')][contains(@class,'rn')][contains(@id,'data')][contains(@id,'khnxgaf')][contains(@id,'item')]
  tree_sig: li(a(img))
  content: [ATTR=2 HREF=1 IMG=15]

--- Chunk 6: div.common.float ---
  type=card freq=3 excl=1.00 LEAKS=55
  pattern_xpath: ///div[contains(@class,'common')][contains(@class,'info')][contains(@class,'object')][contains(@class,'outer')][contains(@style,'float')]
  tree_sig: div(div(div(div(div(div(a,div),div(div)),div(div(a,div),span)))),div(div(picture
  content: [ATTR=11 HREF=6 IMG=55 TEXT=12]
  LEAKS (high):
    [IMG] https://static.wixstatic.com/media/f0a2e7_28eccfb1cde94446b006aa0867a6dc76~mv2.jpg/v1/fill (img URL not in rendered)
    [IMG] h_250 (img URL not in rendered)
    [IMG] fp_0.50_0.50 (img URL not in rendered)
    [IMG] q_30 (img URL not in rendered)
    [IMG] blur_30 (img URL not in rendered)
  LEAKS (medium):
    [TEXT] 25 likes. Post not marked as liked

--- Chunk 7: [pagination_buttons] ---
  type=pagination freq=2 excl=1.00
  pattern_xpath: ///link[contains(@as,'fetch')][contains(@crossorigin,'anonymous')][contains(@id,'master')][contains(@id,'page')][contains(@position,'post')]
  content: [HREF=1]

--- Chunk 8: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.43
  pattern_xpath: ///h6[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')][contains(@class,'font')][contains(@class,'rich')]
  content: [TEXT=1]

--- Chunk 9: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.43
  pattern_xpath: ///div[contains(@id,'ni')][contains(@id,'pleqw')][contains(@class,'ml')]/h6[contains(@style,'align')][contains(@style,'center')][contains(@style,'text')][contains(@class,'font')][contains(@class,'rich')]
  content: [TEXT=1]

--- Chunk 10: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.33
  pattern_xpath: ///div[contains(@id,'rspz')][contains(@id,'pleqw')][contains(@class,'ml')]/h6[contains(@class,'font')][contains(@class,'rich')][contains(@class,'text')][contains(@style,'font')][contains(@style,'size')]
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
4. Use filename `foreignobjekt_comartists.html` in all `_distill()` calls
5. Name the module `test_foreignobjekt_comartists_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
