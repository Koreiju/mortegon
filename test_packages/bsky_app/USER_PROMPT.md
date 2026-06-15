# Test Generation Task: bsky_app.html

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

- **Total chunks:** 22
- **Structural chunks:** 19
- **Text/Nav chunks:** 1
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `button.background.button` (freq=10, pq_sig=`div(div(button(div(div(img)),div)))`)
  - Chunk 1: `button.background.button` (freq=4, pq_sig=`button(div(div(img)),div(div(img)))`)
  - Chunk 2: `div.css.flex` (freq=10, pq_sig=`div(div,div(div(div,img)),div(div(img)))`)
  - Chunk 3: `div.border.bottom` (freq=8, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 4: `div.border.bottom` (freq=7, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 5: `div.border.bottom` (freq=5, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 6: `div.border.bottom` (freq=4, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 7: `div.border.bottom` (freq=4, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 8: `div.border.bottom` (freq=3, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 9: `div.border.bottom` (freq=2, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 10: `div.border.bottom` (freq=2, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 11: `div.border.bottom` (freq=2, pq_sig=`div(div,div(div(div(div(a(div)))),div(div(div(a(sp`)
  - Chunk 12: `div.avatar.background` (freq=150, pq_sig=`div(div(img))`)
  - Chunk 13: `div.atk.bnwqim` (freq=26, pq_sig=`div(div(div(a(div(div,div(div))))))`)
  - Chunk 14: `div.align.bottom` (freq=11, pq_sig=`div(div(a(span),div(div(div(a,a)))))`)
  - Chunk 15: `a.align.app` (freq=5, pq_sig=`a(div(div,div))`)
  - Chunk 16: `div.awgt.bnwqim` (freq=4, pq_sig=`div(div(div(a(span),div(div(div(a,a,div))))),div(d`)
  - Chunk 17: `div.bottom.css` (freq=8, pq_sig=`div(div(a(div(div(div(div,div),div(div,div)),div(d`)
  - Chunk 18: `div.align.bottom` (freq=4, pq_sig=`div(div(a(span),div(div(div(a,a,div(svg))))))`)

**Text/Nav chunks:**
  - Chunk 21: `[nav_content:a×8]` (freq=8)

## Quality Report Summary

```
=== QUALITY REPORT: bsky_app.html ===
Chunks: 22 (structural=19, functional=3, text=0)
Categories: {'button': 2, 'card': 16, 'menu_item': 2, 'search_input': 1, 'pagination': 1}
Content: 333 tagged, 277 preserved (83%)
Leaks: 56 total, 28 high-importance

--- Chunk 0: button.background.button ---
  type=button freq=10 excl=0.31 LEAKS=1
  pattern_xpath: ///button[contains(@role,'button')][contains(@style,'hidden')][contains(@style,'overflow')][contains(@type,'button')][contains(@class,'otgn')]
  tree_sig: div(div(button(div(div(img)),div)))
  content: [ATTR=1 IMG=1]
  LEAKS (high):
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:23uofpgtghr7zykdraahcdee/bafkreidxej (img URL not in rendered)

--- Chunk 1: button.background.button ---
  type=button freq=4 excl=0.31 LEAKS=2
  pattern_xpath: ///button[contains(@role,'button')][contains(@style,'hidden')][contains(@style,'overflow')][contains(@type,'button')][contains(@class,'otgn')]
  tree_sig: button(div(div(img)),div(div(img)))
  content: [ATTR=1 IMG=2]
  LEAKS (high):
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:23uofpgtghr7zykdraahcdee/bafkreidxej (img URL not in rendered)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:23uofpgtghr7zykdraahcdee/bafkreibnpo (img URL not in rendered)

--- Chunk 2: div.css.flex ---
  type=card freq=10 excl=0.07
  pattern_xpath: ///div[contains(@style,'flex')][contains(@class,'jx')][contains(@class,'css')]
  tree_sig: div(div,div(div(div,img)),div(div(img)))
  content: [ATTR=2 IMG=2 TEXT=1]

--- Chunk 3: div.border.bottom ---
  type=card freq=8 excl=0.10 LEAKS=1
  pattern_xpath: ///div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=10 HREF=4 IMG=2 TEXT=6]
  LEAKS (high):
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:2ae3i5lqa367zvp7nsgy75la/bafkreigiov (img URL not in rendered)
  LEAKS (medium):
    [TEXT] I’m sat here at the waters edge. Sipping coffee , taking in the view,w

--- Chunk 4: div.border.bottom ---
  type=card freq=7 excl=0.10 LEAKS=1
  pattern_xpath: ///div[contains(@role,'link')][contains(@data-feed-context,'sports')][contains(@data-feed-context,'blip')]/div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=11 HREF=5 IMG=1 TEXT=8]
  LEAKS (high):
    [HREF] /hashtag/OlympicsHockey (href not in rendered output)
  LEAKS (medium):
    [TEXT] Congratulations to Team Canada 🇨🇦 
They had an amazing Olympics. Canad

--- Chunk 5: div.border.bottom ---
  type=card freq=5 excl=0.10 LEAKS=3
  pattern_xpath: ///div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=13 HREF=5 IMG=3 TEXT=8]
  LEAKS (high):
    [HREF] /hashtag/birding (href not in rendered output)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:23uofpgtghr7zykdraahcdee/bafkreidxej (img URL not in rendered)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:23uofpgtghr7zykdraahcdee/bafkreibnpo (img URL not in rendered)
  LEAKS (medium):
    [TEXT] A big fuckin hawk came for a visit

--- Chunk 6: div.border.bottom ---
  type=card freq=4 excl=0.10 LEAKS=3
  pattern_xpath: ///div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=11 HREF=7 IMG=2 TEXT=11]
  LEAKS (high):
    [HREF] https://moritherapy.wixsite.com/murielsjourney/post/canadian-poets-submit-your-work (href not in rendered output)
    [HREF] /profile/did:plc:iglylvszwquvv4u4wjewspw4 (href not in rendered output)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:25shgfpev7lvcyxcfrhqlb5p/bafkreife32 (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Can I invite you to submit here, and/or let others know about this opp
    [TEXT] moritherapy.wixsite.com/murielsjourn...
    [TEXT] Canadian Poets! Submit your work!

--- Chunk 7: div.border.bottom ---
  type=card freq=4 excl=0.10 LEAKS=5
  pattern_xpath: ///div[contains(@role,'link')][contains(@data-feed-context,'art')][contains(@data-feed-context,'blip')]/div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=14 HREF=8 IMG=2 TEXT=11]
  LEAKS (high):
    [HREF] /hashtag/art (href not in rendered output)
    [HREF] /hashtag/drawing (href not in rendered output)
    [HREF] /hashtag/charcoal (href not in rendered output)
    [HREF] /hashtag/darkart (href not in rendered output)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:27gjzmtnjhbxs2norvrojqzj/bafkreidgmr (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Scribble from last year ✍️

--- Chunk 8: div.border.bottom ---
  type=card freq=3 excl=0.10 LEAKS=5
  pattern_xpath: ///div[contains(@role,'link')][contains(@data-feed-context,'pets')][contains(@data-feed-context,'blip')]/div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=14 BG=1 HREF=8 IMG=1 TEXT=11]
  LEAKS (high):
    [HREF] /hashtag/winterTO (href not in rendered output)
    [HREF] /hashtag/snowTO (href not in rendered output)
    [HREF] /hashtag/dogsofbluesky (href not in rendered output)
    [HREF] /hashtag/SpringerSpaniel (href not in rendered output)
    [BG] https://video.bsky.app/watch/did%3Aplc%3A24mnsbrqf2z3eois4q4yxenw/bafkreia4x4iz3if3iasj2hz (bg URL not in rendered)
  LEAKS (medium):
    [TEXT] The snowcaine addict gets her fix.

--- Chunk 9: div.border.bottom ---
  type=card freq=2 excl=0.10 LEAKS=2
  pattern_xpath: ///div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=14 HREF=4 IMG=3 TEXT=9]
  LEAKS (high):
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:244rweryfrdebb7wexabbtda/bafkreicafu (img URL not in rendered)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:244rweryfrdebb7wexabbtda/bafkreigz6h (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Enjoying every sentence in Shadow Ticket by Thomas Pynchon set in 1932

--- Chunk 10: div.border.bottom ---
  type=card freq=2 excl=0.10 LEAKS=2
  pattern_xpath: ///div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=11 HREF=6 IMG=2 TEXT=9]
  LEAKS (high):
    [HREF] https://on.wsj.com/4tPRrK6 (href not in rendered output)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:i3fhjvvkbmirhyu4aeihhrnv/bafkreige44 (img URL not in rendered)
  LEAKS (medium):
    [TEXT] How to stop feeling bad about your sleep and get a good night’s rest.
    [TEXT] The Problem With Sleep Right Now Is Shame About Sleep
    [TEXT] How to stop feeling bad about your sleep and get a good night’s rest.

--- Chunk 11: div.border.bottom ---
  type=card freq=2 excl=0.10 LEAKS=2
  pattern_xpath: ///div[contains(@class,'cjt')][contains(@class,'hfyk')][contains(@class,'ry')][contains(@style,'top')][contains(@style,'border')]
  tree_sig: div(div,div(div(div(div(a(div)))),div(div(div(a(span),div(div))),div(div(button(
  content: [ATTR=11 HREF=5 IMG=2 TEXT=8]
  LEAKS (high):
    [HREF] https://buff.ly/fZSoUnZ (href not in rendered output)
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:7exlcsle4mjfhu3wnhcgizz6/bafkreibpc6 (img URL not in rendered)
  LEAKS (medium):
    [TEXT] Arturia’s FX Collection 6 adds two new effects and a $99 intro version
    [TEXT] Arturia’s FX Collection 6 adds two new effects and a $99 intro version
    [TEXT] ﻿EFX Ambient and Pitch Shifter-910 bring more quirky weirdness to the 

--- Chunk 12: div.avatar.background ---
  type=card freq=150 excl=0.42
  pattern_xpath: ///div[contains(@data-expoimage,'true')][contains(@style,'radius')][contains(@style,'hidden')][contains(@style,'overflow')][contains(@style,'width')]
  tree_sig: div(div(img))
  content: [IMG=1]

--- Chunk 13: div.atk.bnwqim ---
  type=card freq=26 excl=0.71
  pattern_xpath: ///div[contains(@class,'atk')][contains(@class,'pre')][contains(@class,'qfoi')][contains(@class,'bnwqim')][contains(@class,'jx')]
  tree_sig: div(div(div(a(div(div,div(div))))))
  content: [ATTR=1 HREF=1 IMG=1]

--- Chunk 14: div.align.bottom ---
  type=card freq=11 excl=0.27
  pattern_xpath: ///div[contains(@style,'gap')][contains(@style,'index')][contains(@style,'direction')][contains(@style,'row')][contains(@style,'align')]
  tree_sig: div(div(a(span),div(div(div(a,a)))))
  content: [ATTR=3 HREF=3 TEXT=3]

--- Chunk 15: a.align.app ---
  type=menu_item freq=5 excl=0.47
  pattern_xpath: ///div[contains(@style,'position')][contains(@style,'fixed')][contains(@style,'left')]//a[contains(@aria-pressed,'false')][contains(@role,'link')][contains(@style,'self')][contains(@style,'start')][contains(@style,'content')]
  tree_sig: a(div(div,div))
  content: [ATTR=1 HREF=1 TEXT=2]

--- Chunk 16: div.awgt.bnwqim ---
  type=card freq=4 excl=0.40 LEAKS=1
  pattern_xpath: ///div[contains(@class,'awgt')][contains(@class,'bnwqim')][contains(@class,'jx')][contains(@class,'css')]
  tree_sig: div(div(div(a(span),div(div(div(a,a,div))))),div(div(button(svg(path)),div(butto
  content: [ATTR=10 HREF=4 IMG=1 TEXT=9]
  LEAKS (high):
    [IMG] https://cdn.bsky.app/img/feed_thumbnail/plain/did:plc:a67zdrt4nl2tv2qojpngogbq/bafkreidhdb (img URL not in rendered)

--- Chunk 17: div.bottom.css ---
  type=card freq=8 excl=0.06
  pattern_xpath: ///div[contains(@style,'bottom')][contains(@style,'padding')][contains(@style,'px')][contains(@class,'jx')][contains(@class,'css')]
  tree_sig: div(div(a(div(div(div(div,div),div(div,div)),div(div(img))))))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=3]

--- Chunk 18: div.align.bottom ---
  type=card freq=4 excl=0.27
  pattern_xpath: ///div[contains(@style,'gap')][contains(@style,'index')][contains(@style,'direction')][contains(@style,'row')][contains(@style,'align')]
  tree_sig: div(div(a(span),div(div(div(a,a,div(svg))))))
  content: [ATTR=3 HREF=3 TEXT=3]

--- Chunk 19: [search_inputs] ---
  type=search_input freq=3 excl=1.00 OUTLIER=14.0x
  pattern_xpath: ///input[contains(@autocapitalize,'none')][contains(@autocomplete,'off')][contains(@autocorrect,'off')][contains(@class,'aywtz')][contains(@class,'taxm')]
  content: [ATTR=2]

--- Chunk 20: [pagination_buttons] ---
  type=pagination freq=1 excl=0.60
  pattern_xpath: ///button[contains(@style,'scale')][contains(@style,'transform')][contains(@role,'button')][contains(@style,'content')][contains(@style,'justify')]
  content: [ATTR=1]

--- Chunk 21: [nav_content:a×8] ---
  type=menu_item freq=8 excl=1.00
  pattern_xpath: ///a[contains(@aria-haspopup,'menu')][contains(@class,'jxf')][contains(@id,'radix')][contains(@style,'arial')][contains(@style,'contextual')]
  content: [ATTR=1 HREF=1 TEXT=1]

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
4. Use filename `bsky_app.html` in all `_distill()` calls
5. Name the module `test_bsky_app_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
