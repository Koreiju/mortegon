# Test Generation Task: democracynow_org.html

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

- **Total chunks:** 54
- **Structural chunks:** 13
- **Text/Nav chunks:** 39
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `li` (freq=5, pq_sig=`li(div(div(img,span,span),div(a)),a(picture(source`)
  - Chunk 1: `a.autostart.headlines` (freq=2, pq_sig=`a`)
  - Chunk 2: `div.image.large` (freq=3, pq_sig=`div(h5,a(img),h3(a),p)`)
  - Chunk 3: `li.col.lg` (freq=2, pq_sig=`li(div,div(a(span)),div(a(img),a(img)))`)
  - Chunk 4: `li.col.lg` (freq=2, pq_sig=`li(div,div(a),div(a(img),a(img)))`)
  - Chunk 5: `ul.col.md` (freq=2, pq_sig=`ul(li(a),li(a),li(a),li(a))`)
  - Chunk 6: `ul.col.md` (freq=2, pq_sig=`ul(li(a),li(a))`)
  - Chunk 7: `div.content` (freq=2, pq_sig=`div(div(a),div(div,div(a),div,a))`)
  - Chunk 8: `div.button.color` (freq=8, pq_sig=`div(div(div),svg(path))`)
  - Chunk 9: `a.congress.header` (freq=37, pq_sig=`a(picture(img,source))`)
  - Chunk 10: `li` (freq=17, pq_sig=`li(a(img))`)
  - Chunk 11: `li.hidden.xs` (freq=16, pq_sig=`li(a(span))`)
  - Chunk 12: `a.congress.home` (freq=8, pq_sig=`a(picture(img))`)

**Text/Nav chunks:**
  - Chunk 15: `[text_content:h1×2]` (freq=1)
  - Chunk 16: `[text_content:h5×2]` (freq=1)
  - Chunk 17: `[text_content:p×3]` (freq=1)
  - Chunk 18: `[text_content:h5×2]` (freq=1)
  - Chunk 19: `[nav_content:li×5]` (freq=5)
  - Chunk 20: `[nav_content:li×5]` (freq=5)
  - Chunk 21: `[nav_content:li×4]` (freq=4)
  - Chunk 23: `[nav_content:a×19]` (freq=19)
  - Chunk 23: `[nav_content:a×19]` (freq=19)
  - Chunk 24: `[nav_content:img×10]` (freq=10)
  - Chunk 25: `[nav_content:li×8]` (freq=8)
  - Chunk 26: `[nav_content:li×21]` (freq=21)
  - Chunk 27: `[nav_content:a×60]` (freq=60)
  - Chunk 28: `[text_content:h5×1]` (freq=1)
  - Chunk 29: `[text_content:h5×1]` (freq=1)
  - Chunk 30: `[text_content:h2×1]` (freq=1)
  - Chunk 31: `[text_content:h4×1]` (freq=1)
  - Chunk 32: `[text_content:h5×1]` (freq=1)
  - Chunk 33: `[text_content:h5×1]` (freq=1)
  - Chunk 34: `[text_content:h5×1]` (freq=1)
  - Chunk 35: `[text_content:h3×1]` (freq=1)
  - Chunk 36: `[text_content:h5×1]` (freq=1)
  - Chunk 37: `[text_content:h3×1]` (freq=1)
  - Chunk 38: `[text_content:h3×1]` (freq=1)
  - Chunk 39: `[text_content:h3×1]` (freq=1)
  - Chunk 40: `[text_content:h3×1]` (freq=1)
  - Chunk 41: `[text_content:h3×1]` (freq=1)
  - Chunk 42: `[text_content:h5×1]` (freq=1)
  - Chunk 43: `[text_content:h5×1]` (freq=1)
  - Chunk 44: `[text_content:h5×1]` (freq=1)
  - Chunk 45: `[text_content:h3×1]` (freq=1)
  - Chunk 46: `[text_content:h5×1]` (freq=1)
  - Chunk 47: `[text_content:h5×1]` (freq=1)
  - Chunk 48: `[text_content:h5×1]` (freq=1)
  - Chunk 49: `[text_content:h5×1]` (freq=1)
  - Chunk 50: `[text_content:h5×1]` (freq=1)
  - Chunk 51: `[text_content:h5×1]` (freq=1)
  - Chunk 52: `[text_content:li×1]` (freq=1)
  - Chunk 53: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: democracynow_org.html ===
Chunks: 54 (structural=13, functional=11, text=30)
Categories: {'card': 8, 'structural': 4, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 30, 'menu_item': 9}
Content: 1699 tagged, 1125 preserved (66%)
Leaks: 574 total, 227 high-importance

--- Chunk 0: li ---
  type=card freq=5 excl=0.00
  pattern_xpath: ///li
  tree_sig: li(div(div(img,span,span),div(a)),a(picture(source,img)))
  content: [HREF=2 IMG=4 TEXT=3]

--- Chunk 1: a.autostart.headlines ---
  type=structural freq=2 excl=0.87
  pattern_xpath: ///a[contains(@class,'read')][contains(@class,'watch')][contains(@data-ga-action,'read')][contains(@data-ga-action,'watch')][contains(@data-ga-action,'headlines')]
  tree_sig: a
  content: [HREF=1 TEXT=1]

--- Chunk 2: div.image.large ---
  type=card freq=3 excl=0.44
  pattern_xpath: ///div[contains(@class,'large')][contains(@class,'promotion')][contains(@class,'widget')][contains(@class,'image')]
  tree_sig: div(h5,a(img),h3(a),p)
  content: [HREF=2 IMG=1 TEXT=3]

--- Chunk 3: li.col.lg ---
  type=card freq=2 excl=0.36 LEAKS=2
  pattern_xpath: ///li[contains(@class,'lg')][contains(@class,'sm')][contains(@class,'md')][contains(@class,'col')]
  tree_sig: li(div,div(a(span)),div(a(img),a(img)))
  content: [HREF=3 IMG=4 TEXT=3]
  LEAKS (high):
    [IMG] https://assets.democracynow.org/assets/icons/twitter_icon-7ada1bbfdd3f271ee243db9b8bab0a7d (img URL not in rendered)
    [IMG] https://assets.democracynow.org/assets/icons/twitter_icon-7ada1bbfdd3f271ee243db9b8bab0a7d (img URL not in rendered)

--- Chunk 4: li.col.lg ---
  type=card freq=2 excl=0.36 LEAKS=2
  pattern_xpath: ///li[contains(@class,'lg')][contains(@class,'sm')][contains(@class,'md')][contains(@class,'col')]
  tree_sig: li(div,div(a),div(a(img),a(img)))
  content: [HREF=3 IMG=4 TEXT=1]
  LEAKS (high):
    [IMG] https://assets.democracynow.org/assets/icons/twitter_icon-7ada1bbfdd3f271ee243db9b8bab0a7d (img URL not in rendered)
    [IMG] https://assets.democracynow.org/assets/icons/twitter_icon-7ada1bbfdd3f271ee243db9b8bab0a7d (img URL not in rendered)

--- Chunk 5: ul.col.md ---
  type=structural freq=2 excl=0.18
  pattern_xpath: ///ul[contains(@class,'md')][contains(@class,'col')][contains(@class,'xs')]
  tree_sig: ul(li(a),li(a),li(a),li(a))
  content: [HREF=4 TEXT=4]

--- Chunk 6: ul.col.md ---
  type=structural freq=2 excl=0.18
  pattern_xpath: ///ul[contains(@class,'md')][contains(@class,'col')][contains(@class,'xs')]
  tree_sig: ul(li(a),li(a))
  content: [HREF=2 TEXT=2]

--- Chunk 7: div.content ---
  type=structural freq=2 excl=0.25
  pattern_xpath: ///div[contains(@class,'content')]
  tree_sig: div(div(a),div(div,div(a),div,a))
  content: [HREF=1 TEXT=4]

--- Chunk 8: div.button.color ---
  type=button freq=8 excl=0.47
  pattern_xpath: ///div[contains(@class,'color')][contains(@class,'icon')][contains(@class,'inline')][contains(@role,'button')][contains(@class,'button')]
  tree_sig: div(div(div),svg(path))
  content: [ATTR=1]

--- Chunk 9: a.congress.header ---
  type=card freq=37 excl=0.50
  pattern_xpath: ///a[contains(@data-ga-action,'story')]
  tree_sig: a(picture(img,source))
  content: [HREF=1 IMG=3]

--- Chunk 10: li ---
  type=card freq=17 excl=0.00
  pattern_xpath: ///li
  tree_sig: li(a(img))
  content: [HREF=1 IMG=2]

--- Chunk 11: li.hidden.xs ---
  type=card freq=16 excl=0.11
  pattern_xpath: ///li[contains(@class,'hidden')][contains(@class,'xs')]
  tree_sig: li(a(span))
  content: [HREF=1 TEXT=3]

--- Chunk 12: a.congress.home ---
  type=card freq=8 excl=0.55
  pattern_xpath: ///a[contains(@class,'vertical')][contains(@class,'media')][contains(@data-ga-action,'image')][contains(@data-ga-action,'story')][contains(@class,'image')]
  tree_sig: a(picture(img))
  content: [HREF=1 IMG=2]

--- Chunk 13: [search_inputs] ---
  type=search_input freq=22 excl=0.00
  pattern_xpath: ///input
  content: [ATTR=1]

--- Chunk 14: [pagination_buttons] ---
  type=pagination freq=47 excl=0.33
  pattern_xpath: ///div[contains(@class,'jw')]
  content: [HREF=1 TEXT=1]

--- Chunk 15: [text_content:h1×2] ---
  type=text_singleton freq=1 excl=0.62
  pattern_xpath: ///div[contains(@class,'variant')][contains(@class,'content')]
  content: [TEXT=3]

--- Chunk 16: [text_content:h5×2] ---
  type=text_singleton freq=1 excl=0.44 LEAKS=81
  pattern_xpath: ///div[contains(@class,'large')][contains(@class,'promotion')][contains(@class,'widget')][contains(@class,'image')]
  content: [ATTR=252 BG=2 HREF=122 IMG=43 TEXT=452]
  LEAKS (high):
    [HREF] /headlines (href not in rendered output)
    [HREF] /donate?campaign=web-sho (href not in rendered output)
    [IMG] https://assets.democracynow.org/assets/icons/newsletter-812b993764242f0a9244411e27fb6ed657 (img URL not in rendered)
    [IMG] https://assets.democracynow.org/assets/icons/newsletter-812b993764242f0a9244411e27fb6ed657 (img URL not in rendered)
    [IMG] https://www.democracynow.org/resources/thumbnails/13/813/DN-30-LOGO-Banner-1400x889-r2-230 (img URL not in rendered)
  LEAKS (medium):
    [TEXT] This is viewer supported news
    [TEXT] 30th Anniversary Event2026 Oscar-NomineesFeatured CoverageGift Catalog
    [TEXT] Wednesday, February 11, 2026HeadlinesSpeaking EventsThe Daily News Dig

--- Chunk 17: [text_content:p×3] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///div[contains(@class,'configurable')]/div[contains(@class,'hidden')][contains(@class,'xs')]
  content: [HREF=1 TEXT=11]

--- Chunk 18: [text_content:h5×2] ---
  type=text_singleton freq=1 excl=0.57 LEAKS=72
  pattern_xpath: ///div[contains(@class,'widget')][contains(@class,'promotion')][contains(@class,'large')]/div[contains(@class,'row')][contains(@class,'share')][contains(@class,'col')][contains(@class,'xs')]
  content: [ATTR=41 HREF=113 IMG=37 TEXT=214]
  LEAKS (high):
    [HREF] /donate?campaign=web-sho (href not in rendered output)
    [HREF] /headlines (href not in rendered output)
    [HREF] https://www.democracynow.org/30 (href not in rendered output)
    [HREF] https://www.democracynow.org/2026/1/22/2026_oscar_nominated_films_on_democracy (href not in rendered output)
    [HREF] https://www.democracynow.org/topics/jeffrey_epstein (href not in rendered output)
  LEAKS (medium):
    [TEXT] This is viewer supported news
    [TEXT] 30th Anniversary Event2026 Oscar-NomineesFeatured CoverageGift Catalog
    [TEXT] Join Amy Goodman, Juan González, Nermeen Shaikh, special guests and th

--- Chunk 19: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 20: [nav_content:li×5] ---
  type=menu_item freq=5 excl=0.00
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 21: [nav_content:li×4] ---
  type=menu_item freq=4 excl=0.00 OUTLIER=2.8x
  pattern_xpath: ///li
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:a×19] ---
  type=menu_item freq=19 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:img×10] ---
  type=menu_item freq=10 excl=0.00
  pattern_xpath: ///img
  content: [HREF=1 TEXT=1]

--- Chunk 25: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.11
  pattern_xpath: ///li[contains(@class,'hidden')][contains(@class,'xs')]
  content: [HREF=1 TEXT=6]

--- Chunk 26: [nav_content:li×21] ---
  type=menu_item freq=21 excl=0.11
  pattern_xpath: ///li[contains(@class,'hidden')][contains(@class,'xs')]
  content: [HREF=1 TEXT=6]

--- Chunk 27: [nav_content:a×60] ---
  type=menu_item freq=60 excl=0.00
  pattern_xpath: ///a
  content: [HREF=1 TEXT=6]

--- Chunk 28: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 29: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.11
  pattern_xpath: ///h5[contains(@class,'hidden')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h2
  content: [TEXT=1]

--- Chunk 31: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.43
  pattern_xpath: ///h4[contains(@id,'news')][contains(@id,'top')][contains(@class,'hidden')][contains(@class,'xs')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 33: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 34: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 35: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [HREF=4 TEXT=4]

--- Chunk 36: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 37: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [HREF=1 TEXT=1]

--- Chunk 38: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [HREF=1 TEXT=1]

--- Chunk 39: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [HREF=1 TEXT=3]

--- Chunk 40: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [HREF=1 TEXT=1]

--- Chunk 41: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [HREF=9 TEXT=19]

--- Chunk 42: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 43: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 44: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 45: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h3
  content: [HREF=4 TEXT=4]

--- Chunk 46: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 47: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 48: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 49: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 50: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 51: [text_content:h5×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h5
  content: [TEXT=1]

--- Chunk 52: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.00 LEAKS=42
  pattern_xpath: ///li
  content: [HREF=38 IMG=54 TEXT=57]
  LEAKS (high):
    [HREF] /categories/web_exclusive (href not in rendered output)
    [HREF] /topics (href not in rendered output)
    [HREF] /categories/weekly_column (href not in rendered output)
    [IMG] https://assets.democracynow.org/assets/icons/chevron-down-cc42e0e5aef921b2e30a8c6a05bcc7eb (img URL not in rendered)
    [IMG] https://assets.democracynow.org/assets/icons/chevron-down-cc42e0e5aef921b2e30a8c6a05bcc7eb (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Browse Web Exclusives
    [TEXT] Protecting Pedophile Predators: Carole Cadwalladr on Jeffrey Epstein &
    [TEXT] StoryFeb 11, 2026Feb 10, 2026

--- Chunk 53: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.00 LEAKS=28
  pattern_xpath: ///li
  content: [HREF=28 IMG=16 TEXT=41]
  LEAKS (high):
    [HREF] /2026/2/11/headlines/fbi_raid_of_fulton_county_election_office_based_on_debunked_claims_fr (href not in rendered output)
    [HREF] /2026/2/11/headlines/federal_grand_jury_declines_to_indict_six_democratic_lawmakers_for_ur (href not in rendered output)
    [HREF] /events/2026/2/celebrate_30_years_of_independent_global_news_with_democracy_now_1605 (href not in rendered output)
    [HREF] http://www.facebook.com/democracynow (href not in rendered output)
    [HREF] http://www.twitter.com/democracynow (href not in rendered output)
  LEAKS (medium):
    [TEXT] At Least Nine People Killed in a Mass Shooting in British Columbia, Ca
    [TEXT] Federal Grand Jury Declines to Indict Six Democratic Lawmakers for Urg
    [TEXT] Raid of Fulton County Election Office Based on Debunked Claims from El

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
4. Use filename `democracynow_org.html` in all `_distill()` calls
5. Name the module `test_democracynow_org_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
