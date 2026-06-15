# Test Generation Task: posthumanschool_com.html

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

- **Total chunks:** 28
- **Structural chunks:** 19
- **Text/Nav chunks:** 8
- **Search input found:** False
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.aa.absolute` (freq=2, pq_sig=`div(div(div,div(div(div(div(div),div(picture)))),d`)
  - Chunk 1: `div.ab.absolute` (freq=2, pq_sig=`div(div(div,div(div(div(div(div),div(picture)))),d`)
  - Chunk 2: `div.aa.absolute` (freq=2, pq_sig=`div(div(div,div(div(div(picture(source,source,img)`)
  - Chunk 3: `div.absolute.auto` (freq=3, pq_sig=`div(div(div,div(div(div(picture(source,source,img)`)
  - Chunk 4: `div.absolute.ac` (freq=2, pq_sig=`div(div(div,div(div(div(div(div),div(picture)))),d`)
  - Chunk 5: `div.absolute.auto` (freq=2, pq_sig=`div(div(div,div(div(div(div(div),div(picture)))),d`)
  - Chunk 6: `div.absolute.auto` (freq=2, pq_sig=`div(div(div,div(div(div(picture(source,source,img)`)
  - Chunk 7: `div.absolute.auto` (freq=2, pq_sig=`div(div(div,div(div(div(picture(source,source,img)`)
  - Chunk 8: `div.absolute.ac` (freq=3, pq_sig=`div(div,div(div(div(div(div(div)))),div(div(pictur`)
  - Chunk 9: `div.absolute.auto` (freq=3, pq_sig=`div(div,div(div(div(div(div(div)))),div(div(pictur`)
  - Chunk 10: `div.absolute.ad` (freq=3, pq_sig=`div(div,div(div(div(div(div(div)))),div(div(div(di`)
  - Chunk 11: `div.absolute.auto` (freq=2, pq_sig=`div(div(div,div(div(div(picture(source,source,img)`)
  - Chunk 12: `div.absolute.ae` (freq=2, pq_sig=`div(div(div,div(div(div(div(div),div(picture)))),d`)
  - Chunk 13: `div.border.bottom` (freq=48, pq_sig=`div(div(div(div(div(a(div))))))`)
  - Chunk 14: `a.com.depth` (freq=16, pq_sig=`a(div(span))`)
  - Chunk 15: `div.box.column` (freq=3, pq_sig=`div(div(div(ul(li(div(a))))))`)
  - Chunk 16: `button.accessibility.icon` (freq=3, pq_sig=`button(svg(path))`)
  - Chunk 17: `div.box.common` (freq=17, pq_sig=`div(div(div(div(div(div(a))))),div(div(picture(img`)
  - Chunk 18: `div.box.common` (freq=3, pq_sig=`div(div(div(div(div(div(a))))),div(div(div(div(i(s`)

**Text/Nav chunks:**
  - Chunk 20: `[nav_content:li×4]` (freq=4)
  - Chunk 21: `[text_content:h5×1]` (freq=1)
  - Chunk 22: `[text_content:h2×1]` (freq=1)
  - Chunk 23: `[text_content:h2×1]` (freq=1)
  - Chunk 24: `[text_content:h2×1]` (freq=1)
  - Chunk 25: `[text_content:h2×1]` (freq=1)
  - Chunk 26: `[text_content:h2×1]` (freq=1)
  - Chunk 27: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: posthumanschool_com.html ===
Chunks: 28 (structural=19, functional=2, text=7)
Categories: {'structural': 9, 'card': 8, 'menu_item': 2, 'button': 1, 'pagination': 1, 'text_singleton': 7}
Content: 567 tagged, 567 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.aa.absolute ---
  type=structural freq=2 excl=0.80
  pattern_xpath: ///div[contains(@data-hash,'afe')][contains(@data-id,'afe')][contains(@id,'pgiafe')][contains(@id,'aa')][contains(@data-hash,'eb')]
  tree_sig: div(div(div,div(div(div(div(div),div(picture)))),div(div(div(div(div))),div(div(
  content: [ATTR=5 HREF=1 IMG=10 TEXT=1]

--- Chunk 1: div.ab.absolute ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@data-hash,'bfd')][contains(@data-id,'bfd')][contains(@id,'ab')][contains(@id,'bfd')][contains(@id,'caa')]
  tree_sig: div(div(div,div(div(div(div(div),div(picture)))),div(div(div(div(div))),div(div(
  content: [ATTR=3 HREF=1 IMG=10 TEXT=1]

--- Chunk 2: div.aa.absolute ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@data-hash,'bfa')][contains(@data-hash,'ddd')][contains(@data-id,'bfa')][contains(@data-id,'ddd')][contains(@id,'bfa')]
  tree_sig: div(div(div,div(div(div(picture(source,source,img)))),div(div(div(div(div))),div
  content: [ATTR=3 HREF=1 IMG=54 TEXT=1]

--- Chunk 3: div.absolute.auto ---
  type=card freq=3 excl=0.25
  pattern_xpath: ///div[contains(@data-hash,'fe')][contains(@data-id,'fe')][contains(@class,'container')][contains(@class,'custom')][contains(@class,'focus')]
  tree_sig: div(div(div,div(div(div(picture(source,source,img)))),div(div(div(div(div))),div
  content: [ATTR=3 HREF=1 IMG=50 TEXT=1]

--- Chunk 4: div.absolute.ac ---
  type=structural freq=2 excl=0.90
  pattern_xpath: ///div[contains(@data-hash,'bb')][contains(@data-id,'bb')][contains(@id,'bb')][contains(@id,'dd')][contains(@data-hash,'fe')]
  tree_sig: div(div(div,div(div(div(div(div),div(picture)))),div(div(div(div(div))),div(div(
  content: [ATTR=3 HREF=1 IMG=10 TEXT=1]

--- Chunk 5: div.absolute.auto ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@data-hash,'bdf')][contains(@data-hash,'ebe')][contains(@data-hash,'fb')][contains(@data-id,'bdf')][contains(@data-id,'ebe')]
  tree_sig: div(div(div,div(div(div(div(div),div(picture)))),div(div(div(div(div))),div(div(
  content: [ATTR=3 HREF=1 IMG=10 TEXT=1]

--- Chunk 6: div.absolute.auto ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@data-hash,'bc')][contains(@data-id,'bc')][contains(@id,'bc')][contains(@data-hash,'bfc')][contains(@data-id,'bfc')]
  tree_sig: div(div(div,div(div(div(picture(source,source,img)))),div(div(div(div(div))),div
  content: [ATTR=3 HREF=1 IMG=54 TEXT=1]

--- Chunk 7: div.absolute.auto ---
  type=structural freq=2 excl=0.80
  pattern_xpath: ///div[contains(@data-hash,'dabeb')][contains(@data-id,'dabeb')][contains(@id,'dabeb')][contains(@data-hash,'dc')][contains(@data-id,'dc')]
  tree_sig: div(div(div,div(div(div(picture(source,source,img)))),div(div(div(div(div))),div
  content: [ATTR=3 HREF=1 IMG=50 TEXT=1]

--- Chunk 8: div.absolute.ac ---
  type=card freq=3 excl=0.63
  pattern_xpath: ///div[contains(@data-hash,'cb')][contains(@data-id,'cb')][contains(@id,'cb')][contains(@data-hash,'ac')][contains(@data-id,'ac')]
  tree_sig: div(div,div(div(div(div(div(div)))),div(div(picture(img,source,source)))),div(di
  content: [ATTR=3 HREF=1 IMG=54 TEXT=1]

--- Chunk 9: div.absolute.auto ---
  type=card freq=3 excl=0.63
  pattern_xpath: ///div[contains(@data-hash,'fa')][contains(@data-id,'fa')][contains(@id,'fa')][contains(@class,'container')][contains(@class,'custom')]
  tree_sig: div(div,div(div(div(div(div(div)))),div(div(picture(img,source,source)))),div(di
  content: [ATTR=3 HREF=1 IMG=54 TEXT=1]

--- Chunk 10: div.absolute.ad ---
  type=card freq=3 excl=0.70
  pattern_xpath: ///div[contains(@data-hash,'ad')][contains(@data-id,'ad')][contains(@data-hash,'df')][contains(@data-id,'df')][contains(@id,'df')]
  tree_sig: div(div,div(div(div(div(div(div)))),div(div(div(div(i,i)),div(div(i,i),picture(i
  content: [ATTR=3 HREF=1 IMG=10 TEXT=1]

--- Chunk 11: div.absolute.auto ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@id,'pgif')][contains(@data-hash,'cbc')][contains(@data-hash,'eee')][contains(@data-id,'cbc')][contains(@data-id,'eee')]
  tree_sig: div(div(div,div(div(div(picture(source,source,img)))),div(div(div(div(div))),div
  content: [ATTR=3 HREF=1 IMG=50 TEXT=1]

--- Chunk 12: div.absolute.ae ---
  type=structural freq=2 excl=1.00
  pattern_xpath: ///div[contains(@data-hash,'ae')][contains(@data-hash,'ecc')][contains(@data-id,'ae')][contains(@data-id,'ecc')][contains(@id,'ae')]
  tree_sig: div(div(div,div(div(div(div(div),div(picture)))),div(div(div(div(div))),div(div(
  content: [ATTR=3 HREF=1 IMG=10 TEXT=1]

--- Chunk 13: div.border.bottom ---
  type=card freq=48 excl=0.60
  pattern_xpath: ///div[contains(@class,'bottom')][contains(@style,'border')][contains(@class,'common')][contains(@class,'info')][contains(@style,'box')]
  tree_sig: div(div(div(div(div(a(div))))))
  content: [HREF=1 TEXT=1]

--- Chunk 14: a.com.depth ---
  type=menu_item freq=16 excl=1.00
  pattern_xpath: ///a[contains(@class,'menu')][contains(@class,'root')][contains(@data-item-label,'true')][contains(@data-testid,'element')][contains(@data-testid,'link')]
  tree_sig: a(div(span))
  content: [HREF=1 TEXT=1]

--- Chunk 15: div.box.column ---
  type=card freq=3 excl=1.00
  pattern_xpath: ///div[contains(@class,'box')][contains(@class,'column')][contains(@class,'position')][contains(@data-testid,'box')][contains(@data-testid,'position')]
  tree_sig: div(div(div(ul(li(div(a))))))
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 16: button.accessibility.icon ---
  type=button freq=3 excl=0.64
  pattern_xpath: ///button[contains(@class,'accessibility')][contains(@class,'icon')][contains(@class,'shared')][contains(@class,'item')]
  tree_sig: button(svg(path))
  content: [ATTR=1]

--- Chunk 17: div.box.common ---
  type=card freq=17 excl=0.43
  pattern_xpath: ///div[contains(@class,'object')][contains(@class,'outer')][contains(@style,'content')][contains(@class,'common')][contains(@class,'info')]
  tree_sig: div(div(div(div(div(div(a))))),div(div(picture(img,source,source))))
  content: [ATTR=1 HREF=1 IMG=27 TEXT=1]

--- Chunk 18: div.box.common ---
  type=card freq=3 excl=0.43
  pattern_xpath: ///div[contains(@class,'object')][contains(@class,'outer')][contains(@style,'content')][contains(@class,'common')][contains(@class,'info')]
  tree_sig: div(div(div(div(div(div(a))))),div(div(div(div(i(svg),i(svg))),div(div(i(svg),i(
  content: [ATTR=1 HREF=1 IMG=5 TEXT=1]

--- Chunk 19: [pagination_buttons] ---
  type=pagination freq=4 excl=1.00
  pattern_xpath: ///img[contains(@as,'fetch')][contains(@class,'preloaded')][contains(@crossorigin,'anonymous')][contains(@data-hook,'gallery')][contains(@data-hook,'image')]
  content: [ATTR=1 IMG=1]

--- Chunk 20: [nav_content:li×4] ---
  type=menu_item freq=4 excl=1.00
  pattern_xpath: ///li[contains(@class,'kw')][contains(@class,'rn')][contains(@id,'comp')][contains(@id,'data')][contains(@id,'item')]
  content: [ATTR=2 HREF=1 IMG=15]

--- Chunk 21: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h5[contains(@class,'font')][contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')][contains(@style,'font')]
  content: [TEXT=2]

--- Chunk 22: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'line')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'line')]
  content: [TEXT=1]

--- Chunk 24: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'line')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'line')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'line')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.17
  pattern_xpath: ///h2[contains(@class,'ik')][contains(@class,'nia')][contains(@class,'vt')][contains(@style,'clamp')][contains(@style,'line')]
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
4. Use filename `posthumanschool_com.html` in all `_distill()` calls
5. Name the module `test_posthumanschool_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
