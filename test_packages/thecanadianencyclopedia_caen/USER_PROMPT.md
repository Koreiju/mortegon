# Test Generation Task: thecanadianencyclopedia_caen.html

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

- **Total chunks:** 38
- **Structural chunks:** 5
- **Text/Nav chunks:** 31
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.carousel.slide` (freq=4, pq_sig=`div(div(img),div(h6,h3,span))`)
  - Chunk 1: `div.date.description` (freq=3, pq_sig=`div(div(a),h3,h6,span)`)
  - Chunk 2: `a.ca.contact` (freq=2, pq_sig=`a`)
  - Chunk 3: `div.callout.split` (freq=2, pq_sig=`article(div(div(img),div(span,h3(a),div,p)))`)
  - Chunk 4: `div.heading.menu` (freq=6, pq_sig=`div(a,button(span))`)

**Text/Nav chunks:**
  - Chunk 7: `[text_content:h3×3]` (freq=1)
  - Chunk 8: `[text_content:h3×2]` (freq=1)
  - Chunk 9: `[text_content:h1×2]` (freq=1)
  - Chunk 10: `[text_content:h1×2]` (freq=1)
  - Chunk 11: `[nav_content:li×5]` (freq=5)
  - Chunk 12: `[nav_content:li×5]` (freq=5)
  - Chunk 13: `[nav_content:li×4]` (freq=4)
  - Chunk 16: `[nav_content:a×19]` (freq=19)
  - Chunk 17: `[nav_content:a×17]` (freq=17)
  - Chunk 16: `[nav_content:a×19]` (freq=19)
  - Chunk 17: `[nav_content:a×17]` (freq=17)
  - Chunk 18: `[nav_content:li×4]` (freq=4)
  - Chunk 19: `[nav_content:li×4]` (freq=4)
  - Chunk 20: `[text_content:h2×1]` (freq=1)
  - Chunk 21: `[text_content:h2×1]` (freq=1)
  - Chunk 22: `[text_content:h3×1]` (freq=1)
  - Chunk 23: `[text_content:h6×1]` (freq=1)
  - Chunk 24: `[text_content:h6×1]` (freq=1)
  - Chunk 25: `[text_content:h4×1]` (freq=1)
  - Chunk 26: `[text_content:h2×1]` (freq=1)
  - Chunk 27: `[text_content:h3×1]` (freq=1)
  - Chunk 28: `[text_content:h3×1]` (freq=1)
  - Chunk 29: `[text_content:h3×1]` (freq=1)
  - Chunk 30: `[text_content:h3×1]` (freq=1)
  - Chunk 31: `[text_content:h1×1]` (freq=1)
  - Chunk 32: `[text_content:h3×1]` (freq=1)
  - Chunk 33: `[text_content:h3×1]` (freq=1)
  - Chunk 34: `[text_content:h3×1]` (freq=1)
  - Chunk 35: `[text_content:h3×1]` (freq=1)
  - Chunk 36: `[text_content:h3×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: thecanadianencyclopedia_caen.html ===
Chunks: 38 (structural=5, functional=11, text=22)
Categories: {'card': 3, 'structural': 1, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 22, 'menu_item': 9}
Content: 571 tagged, 323 preserved (57%)
Leaks: 248 total, 69 high-importance

--- Chunk 0: div.carousel.slide ---
  type=card freq=4 excl=0.56
  pattern_xpath: ///div[contains(@class,'slide')][contains(@class,'carousel')][contains(@class,'vue')]
  tree_sig: div(div(img),div(h6,h3,span))
  content: [ATTR=2 IMG=1 TEXT=3]

--- Chunk 1: div.date.description ---
  type=card freq=3 excl=1.00
  pattern_xpath: ///div[contains(@class,'date')][contains(@class,'description')][contains(@class,'event')]
  tree_sig: div(div(a),h3,h6,span)
  content: [HREF=1 TEXT=4]

--- Chunk 2: a.ca.contact ---
  type=structural freq=2 excl=0.61
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'canada')][contains(@class,'logos')]/a[contains(@target,'blank')][contains(@class,'primary')][contains(@class,'md')]
  tree_sig: a
  content: [HREF=1 TEXT=1]

--- Chunk 3: div.callout.split ---
  type=card freq=2 excl=0.69
  pattern_xpath: ///div[contains(@class,'split')][contains(@class,'even')][contains(@class,'callout')]
  tree_sig: article(div(div(img),div(span,h3(a),div,p)))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=3]

--- Chunk 4: div.heading.menu ---
  type=button freq=6 excl=0.25
  pattern_xpath: ///div[contains(@class,'heading')][contains(@class,'menu')][contains(@class,'sub')]
  tree_sig: div(a,button(span))
  content: [ATTR=2 HREF=1 TEXT=1]

--- Chunk 5: [search_inputs] ---
  type=search_input freq=7 excl=0.00 OUTLIER=11.0x
  pattern_xpath: ///input

--- Chunk 6: [pagination_buttons] ---
  type=pagination freq=18 excl=0.00 OUTLIER=3.7x
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 7: [text_content:h3×3] ---
  type=text_singleton freq=1 excl=0.67
  pattern_xpath: ///div[contains(@class,'body')][contains(@class,'login')][contains(@class,'popup')]
  content: [ATTR=7 HREF=4 IMG=2 TEXT=10]

--- Chunk 8: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.80 LEAKS=65
  pattern_xpath: ///div[contains(@class,'callouts')][contains(@class,'layout')][contains(@class,'main')][contains(@class,'full')][contains(@class,'grid')]
  content: [ATTR=51 HREF=79 IMG=35 TEXT=256]
  LEAKS (high):
    [IMG] https://d14fiu1i7ba797.cloudfront.net/1420x500/!feature-img-thumbnails/viola-des-feat.jpg (img URL not in rendered)
    [IMG] https://d14fiu1i7ba797.cloudfront.net/950x579/media/studyguides/thumbnails/00-BHM-guide-th (img URL not in rendered)
    [IMG] https://d14fiu1i7ba797.cloudfront.net/720x439/media/media/a23e5818-7604-48c4-86a6-fa0a0dba (img URL not in rendered)
    [HREF] https://thecanadianencyclopedia.ca/en/educators (href not in rendered output)
    [IMG] https://d14fiu1i7ba797.cloudfront.net/340x207/dim-sum.png (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Feb
        
            12
        quiztimelineFind resources for tea
    [TEXT] Take this QuizExplore the timeline
    [TEXT] But now she loved winter. Winter was beautiful "up back" - almost into

--- Chunk 9: [text_content:h1×2] ---
  type=text_singleton freq=1 excl=0.42
  pattern_xpath: ///article[contains(@class,'module')][contains(@class,'template')][contains(@class,'featured')]//div[contains(@class,'banner')][contains(@class,'content')]
  content: [ATTR=1 HREF=1 TEXT=4]

--- Chunk 10: [text_content:h1×2] ---
  type=text_singleton freq=1 excl=0.08 LEAKS=4
  pattern_xpath: ///div[contains(@class,'item')][contains(@class,'callout')]
  content: [ATTR=3 HREF=10 IMG=6 TEXT=16]
  LEAKS (high):
    [IMG] https://d14fiu1i7ba797.cloudfront.net/340x207/dim-sum.png (img URL not in rendered)
    [IMG] https://d14fiu1i7ba797.cloudfront.net/340x207/!feature-img-thumbnails/Won-Alexander-Cumyow (img URL not in rendered)
    [IMG] https://d14fiu1i7ba797.cloudfront.net/340x207/media/new_article_images/Force136/force-136- (img URL not in rendered)
    [IMG] https://d14fiu1i7ba797.cloudfront.net/340x207/richardsutton/richardsuttoncropped.jpg (img URL not in rendered)

--- Chunk 11: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 12: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 13: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.25
  pattern_xpath: ///li[contains(@class,'heading')][contains(@class,'menu')][contains(@class,'sub')]
  content: [HREF=1 TEXT=1]

--- Chunk 16: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 17: [nav_content:a×17] ---
  type=menu_item freq=17 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 16: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 17: [nav_content:a×17] ---
  type=menu_item freq=17 excl=0.00
  pattern_xpath: ///a
  content: [ATTR=1 HREF=1 TEXT=1]

--- Chunk 18: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 19: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00 OUTLIER=2.8x
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 20: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.35
  pattern_xpath: ///div[contains(@class,'search')][contains(@class,'panel')][contains(@class,'head')]/h2[contains(@class,'panel')][contains(@class,'search')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.28
  pattern_xpath: ///div[contains(@class,'popup')][contains(@class,'connect')]/h2[contains(@class,'popup')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h3[contains(@class,'below')][contains(@class,'child')][contains(@class,'offset')][contains(@class,'section')][contains(@class,'space')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h6
  content: [TEXT=1]

--- Chunk 24: [text_content:h6×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h6
  content: [TEXT=1]

--- Chunk 25: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.69
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'socials')]/h4[contains(@class,'footer')][contains(@class,'socials')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.07
  pattern_xpath: ///div[contains(@class,'learning')][contains(@class,'info')]/h2[contains(@class,'callout')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 28: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 29: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 30: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 31: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.30
  pattern_xpath: ///h1[contains(@class,'banner')][contains(@class,'content')][contains(@class,'title')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=3 TEXT=3]

--- Chunk 33: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 34: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 35: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 36: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=1 TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.08
  pattern_xpath: ///div[contains(@class,'image')][contains(@class,'container')]/h3[contains(@class,'item')][contains(@class,'callout')][contains(@class,'title')]
  content: [HREF=4 TEXT=4]

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
4. Use filename `thecanadianencyclopedia_caen.html` in all `_distill()` calls
5. Name the module `test_thecanadianencyclopedia_caen_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
