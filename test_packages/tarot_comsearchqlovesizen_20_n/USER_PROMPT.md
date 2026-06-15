# Test Generation Task: tarot_comsearchqlovesizen_20_n.html

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

- **Total chunks:** 26
- **Structural chunks:** 4
- **Text/Nav chunks:** 20
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `li` (freq=6, pq_sig=`li(a,nav-submenu(div(a,ul(li(a),li(a),li(a),li(a),`)
  - Chunk 1: `a.celtic.com` (freq=3, pq_sig=`a(h3(em),p(em,em,em))`)
  - Chunk 2: `div.category.full` (freq=12, pq_sig=`div(a,ul(li(a),li(a),li(a),li(a),li(a)))`)
  - Chunk 3: `column.is.mobile` (freq=24, pq_sig=`column(a(row(column(img),column(p))))`)

**Text/Nav chunks:**
  - Chunk 6: `[text_content:h3×2]` (freq=1)
  - Chunk 7: `[text_content:h3×2]` (freq=1)
  - Chunk 8: `[text_content:h3×2]` (freq=1)
  - Chunk 9: `[text_content:h3×2]` (freq=1)
  - Chunk 10: `[text_content:h3×2]` (freq=1)
  - Chunk 11: `[text_content:h3×2]` (freq=1)
  - Chunk 12: `[text_content:h3×2]` (freq=1)
  - Chunk 13: `[text_content:h3×2]` (freq=1)
  - Chunk 14: `[text_content:h3×2]` (freq=1)
  - Chunk 15: `[text_content:h3×2]` (freq=1)
  - Chunk 16: `[text_content:h3×2]` (freq=1)
  - Chunk 17: `[text_content:h3×2]` (freq=1)
  - Chunk 18: `[text_content:h3×2]` (freq=1)
  - Chunk 19: `[text_content:h3×2]` (freq=1)
  - Chunk 20: `[text_content:h3×2]` (freq=1)
  - Chunk 21: `[nav_content:li×6]` (freq=6)
  - Chunk 22: `[nav_content:li×6]` (freq=6)
  - Chunk 23: `[nav_content:li×6]` (freq=6)
  - Chunk 24: `[nav_content:li×6]` (freq=6)
  - Chunk 25: `[text_content:li×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: tarot_comsearchqlovesizen_20_n.html ===
Chunks: 26 (structural=4, functional=6, text=16)
Categories: {'card': 4, 'search_input': 1, 'pagination': 1, 'text_singleton': 16, 'menu_item': 4}
Content: 453 tagged, 311 preserved (69%)
Leaks: 142 total, 68 high-importance

--- Chunk 0: li ---
  type=card freq=6 excl=0.00 LEAKS=4
  pattern_xpath: ///li
  tree_sig: li(a,nav-submenu(div(a,ul(li(a),li(a),li(a),li(a),li(a))),div(a,ul(li(a),li(a),l
  content: [ATTR=4 HREF=18 IMG=4 TEXT=18]
  LEAKS (high):
    [HREF] /tarot/about-the-celtic-cross-spread (href not in rendered output)
    [IMG] https://gfx.tarot.com/images/feeds/50x50/pyramid-view-space-50x50.jpg (img URL not in rendered)
    [IMG] https://gfx.tarot.com/images/feeds/50x50/3-card-contemporary-50x50.jpg (img URL not in rendered)
    [IMG] https://gfx.tarot.com/images/feeds/50x50/3-swords-glacier-50x50.jpg (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Learn to Read Tarot: Tarot Card Spreads and Tips for
                 
    [TEXT] Get Guidance for Any Situation with a Celtic Cross Tarot
             

--- Chunk 1: a.celtic.com ---
  type=card freq=3 excl=0.06
  pattern_xpath: ///a[contains(@class,'hover')][contains(@class,'no')][contains(@class,'underline')][contains(@data-info,'love')][contains(@data-info,'search')]
  tree_sig: a(h3(em),p(em,em,em))
  content: [HREF=1 TEXT=9]

--- Chunk 2: div.category.full ---
  type=card freq=12 excl=1.00
  pattern_xpath: ///div[contains(@class,'category')][contains(@class,'full')][contains(@class,'nav')][contains(@class,'submenu')]
  tree_sig: div(a,ul(li(a),li(a),li(a),li(a),li(a)))
  content: [HREF=6 TEXT=6]

--- Chunk 3: column.is.mobile ---
  type=card freq=24 excl=0.88
  pattern_xpath: ///column[contains(@class,'mobile')][contains(@class,'portrait')][contains(@class,'tablet')][contains(@class,'is')]
  tree_sig: column(a(row(column(img),column(p))))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=1]

--- Chunk 4: [search_inputs] ---
  type=search_input freq=8 excl=0.00
  pattern_xpath: ///input
  content: [ATTR=1]

--- Chunk 5: [pagination_buttons] ---
  type=pagination freq=22 excl=1.00
  pattern_xpath: ///a[contains(@data-action,'click')][contains(@data-category,'footer')][contains(@data-info,'footer')][contains(@data-info,'insight')][contains(@data-info,'more')]
  content: [HREF=1 TEXT=1]

--- Chunk 6: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.70
  pattern_xpath: ///li[contains(@class,'left')][contains(@class,'mobile')][contains(@class,'right')]/a[contains(@data-info,'according')][contains(@data-label,'according')][contains(@data-info,'astrology')][contains(@data-info,'compatibility')][contains(@data-info,'tarot')]
  content: [HREF=1 TEXT=7]

--- Chunk 7: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///li[contains(@class,'left')][contains(@class,'mobile')][contains(@class,'right')]/a[contains(@data-info,'signs')][contains(@data-info,'venus')][contains(@data-label,'signs')][contains(@data-label,'venus')][contains(@data-info,'about')]
  content: [HREF=1 TEXT=6]

--- Chunk 8: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///li[contains(@class,'left')][contains(@class,'mobile')][contains(@class,'right')]/a[contains(@data-info,'by')][contains(@data-info,'calculator')][contains(@data-label,'by')][contains(@data-label,'calculator')][contains(@data-info,'compatibility')]
  content: [HREF=1 TEXT=5]

--- Chunk 9: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'aries')][contains(@data-info,'direct')][contains(@data-info,'spontaneous')][contains(@data-label,'aries')][contains(@data-label,'direct')]
  content: [HREF=1 TEXT=6]

--- Chunk 10: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'patient')][contains(@data-info,'sensual')][contains(@data-info,'taurus')][contains(@data-label,'patient')][contains(@data-label,'sensual')]
  content: [HREF=1 TEXT=6]

--- Chunk 11: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'clever')][contains(@data-info,'flirtatious')][contains(@data-info,'gemini')][contains(@data-label,'clever')][contains(@data-label,'flirtatious')]
  content: [HREF=1 TEXT=6]

--- Chunk 12: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'cancer')][contains(@data-info,'nurturing')][contains(@data-info,'protective')][contains(@data-info,'sensitive')][contains(@data-label,'cancer')]
  content: [HREF=1 TEXT=4]

--- Chunk 13: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///li[contains(@class,'left')][contains(@class,'mobile')][contains(@class,'right')]/a[contains(@data-info,'leo')][contains(@data-info,'playful')][contains(@data-label,'leo')][contains(@data-label,'playful')][contains(@data-info,'giving')]
  content: [HREF=1 TEXT=8]

--- Chunk 14: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.70
  pattern_xpath: ///li[contains(@class,'left')][contains(@class,'mobile')][contains(@class,'right')]/a[contains(@data-info,'virgo')][contains(@data-label,'virgo')][contains(@data-info,'giving')][contains(@data-info,'loyal')][contains(@data-info,'respectful')]
  content: [HREF=1 TEXT=8]

--- Chunk 15: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///li[contains(@class,'left')][contains(@class,'mobile')][contains(@class,'right')]/a[contains(@data-info,'charming')][contains(@data-info,'libra')][contains(@data-label,'charming')][contains(@data-label,'libra')][contains(@data-info,'supportive')]
  content: [HREF=1 TEXT=4]

--- Chunk 16: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'magnetic')][contains(@data-info,'mysterious')][contains(@data-info,'scorpio')][contains(@data-label,'magnetic')][contains(@data-label,'mysterious')]
  content: [HREF=1 TEXT=4]

--- Chunk 17: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'exciting')][contains(@data-info,'open')][contains(@data-info,'sagittarius')][contains(@data-label,'exciting')][contains(@data-label,'open')]
  content: [HREF=1 TEXT=6]

--- Chunk 18: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'capricorn')][contains(@data-info,'classy')][contains(@data-info,'devoted')][contains(@data-label,'capricorn')][contains(@data-label,'classy')]
  content: [HREF=1 TEXT=4]

--- Chunk 19: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///a[contains(@data-info,'aquarius')][contains(@data-info,'conversational')][contains(@data-info,'friendly')][contains(@data-info,'unique')][contains(@data-label,'aquarius')]
  content: [HREF=1 TEXT=6]

--- Chunk 20: [text_content:h3×2] ---
  type=text_singleton freq=1 excl=0.90
  pattern_xpath: ///li[contains(@class,'left')][contains(@class,'mobile')][contains(@class,'right')]/a[contains(@data-info,'pisces')][contains(@data-info,'sweet')][contains(@data-label,'pisces')][contains(@data-label,'sweet')][contains(@data-info,'supportive')]
  content: [HREF=1 TEXT=8]

--- Chunk 21: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.22
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

--- Chunk 22: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.22
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

--- Chunk 23: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.22
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

--- Chunk 24: [nav_content:li×6] ---
  type=menu_item freq=6 excl=0.22
  pattern_xpath: ///li[contains(@class,'bottom')][contains(@class,'has')][contains(@class,'padding')]
  content: [HREF=1 TEXT=1]

--- Chunk 25: [text_content:li×1] ---
  type=text_singleton freq=1 excl=0.47 LEAKS=64
  pattern_xpath: ///ul[contains(@class,'sui')][contains(@class,'results')][contains(@class,'container')]/li[contains(@class,'result')][contains(@class,'sui')][contains(@class,'has')][contains(@class,'padding')]
  content: [ATTR=42 HREF=53 IMG=42 TEXT=132]
  LEAKS (high):
    [HREF] https://www.tarot.com/daily-love-horoscope (href not in rendered output)
    [HREF] https://www.tarot.com/astrology/venus-signs (href not in rendered output)
    [HREF] https://www.tarot.com/astrology/compatibility/love (href not in rendered output)
    [HREF] https://www.tarot.com/readings-reports/i-ching/free/love (href not in rendered output)
    [HREF] https://www.tarot.com/love-and-compatibility/aries (href not in rendered output)
  LEAKS (medium):
    [TEXT] ASTROLOGYLOVE AND COMPATIBILITY
    [TEXT] LEARN
                                            ASTROLOGY
    [TEXT] COMPATIBILITYSIGNS
                                            IN LOVE

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
4. Use filename `tarot_comsearchqlovesizen_20_n.html` in all `_distill()` calls
5. Name the module `test_tarot_comsearchqlovesizen_20_n_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
