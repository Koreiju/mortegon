# Test Generation Task: emastered_comblogwhatisneurofunk.html

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

- **Total chunks:** 36
- **Structural chunks:** 3
- **Text/Nav chunks:** 31
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `a.block.blog` (freq=32, pq_sig=`a(div(div,div(h4)))`)
  - Chunk 1: `div.collection.dyn` (freq=18, pq_sig=`div(a(div))`)
  - Chunk 2: `figure.align.bottom` (freq=6, pq_sig=`figure(div(lite-youtube(div(button,picture(slot(im`)

**Text/Nav chunks:**
  - Chunk 5: `[text_content:p×23]` (freq=23)
  - Chunk 6: `[text_content:h1×4]` (freq=1)
  - Chunk 7: `[text_content:h1×1]` (freq=1)
  - Chunk 8: `[text_content:h4×1]` (freq=1)
  - Chunk 9: `[text_content:h4×1]` (freq=1)
  - Chunk 10: `[text_content:h4×1]` (freq=1)
  - Chunk 11: `[text_content:h4×1]` (freq=1)
  - Chunk 12: `[text_content:h4×1]` (freq=1)
  - Chunk 13: `[text_content:h4×1]` (freq=1)
  - Chunk 14: `[text_content:h4×1]` (freq=1)
  - Chunk 15: `[text_content:h4×1]` (freq=1)
  - Chunk 16: `[text_content:h4×1]` (freq=1)
  - Chunk 17: `[text_content:h4×1]` (freq=1)
  - Chunk 18: `[text_content:h4×1]` (freq=1)
  - Chunk 19: `[text_content:h4×1]` (freq=1)
  - Chunk 20: `[text_content:h4×1]` (freq=1)
  - Chunk 21: `[text_content:h4×1]` (freq=1)
  - Chunk 22: `[text_content:h4×1]` (freq=1)
  - Chunk 23: `[text_content:h4×1]` (freq=1)
  - Chunk 24: `[text_content:h4×1]` (freq=1)
  - Chunk 25: `[text_content:h4×1]` (freq=1)
  - Chunk 26: `[text_content:h4×1]` (freq=1)
  - Chunk 27: `[text_content:h4×1]` (freq=1)
  - Chunk 28: `[text_content:h4×1]` (freq=1)
  - Chunk 29: `[text_content:h4×1]` (freq=1)
  - Chunk 30: `[text_content:h4×1]` (freq=1)
  - Chunk 31: `[text_content:h4×1]` (freq=1)
  - Chunk 32: `[text_content:h4×1]` (freq=1)
  - Chunk 33: `[text_content:h4×1]` (freq=1)
  - Chunk 34: `[text_content:h4×1]` (freq=1)
  - Chunk 35: `[text_content:h4×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: emastered_comblogwhatisneurofunk.html ===
Chunks: 36 (structural=3, functional=2, text=31)
Categories: {'card': 2, 'button': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 31}
Content: 501 tagged, 241 preserved (48%)
Leaks: 260 total, 148 high-importance

--- Chunk 0: a.block.blog ---
  type=card freq=32 excl=0.60
  pattern_xpath: ///a[contains(@class,'link')][contains(@class,'block')][contains(@class,'collection')][contains(@class,'inline')][contains(@class,'item')]
  tree_sig: a(div(div,div(h4)))
  content: [BG=1 HREF=1 TEXT=1]

--- Chunk 1: div.collection.dyn ---
  type=button freq=18 excl=0.75
  pattern_xpath: ///div[contains(@class,'dyn')][contains(@role,'listitem')][contains(@class,'collection')][contains(@class,'item')]
  tree_sig: div(a(div))
  content: [HREF=1 TEXT=1]

--- Chunk 2: figure.align.bottom ---
  type=card freq=6 excl=1.00 LEAKS=3
  pattern_xpath: ///figure[contains(@class,'align')][contains(@class,'center')][contains(@class,'figure')][contains(@class,'richtext')][contains(@class,'type')]
  tree_sig: figure(div(lite-youtube(div(button,picture(slot(img,source,source))),noscript,st
  content: [ATTR=4 IMG=3 TEXT=2]
  LEAKS (high):
    [IMG] https://i.ytimg.com/vi_webp/CvjA-ZVaJO4/hqdefault.webp (img URL not in rendered)
    [IMG] https://i.ytimg.com/vi/CvjA-ZVaJO4/hqdefault.jpg (img URL not in rendered)
    [IMG] https://i.ytimg.com/vi/CvjA-ZVaJO4/hqdefault.jpg (img URL not in rendered)
  LEAKS (medium):
    [TEXT] <iframe credentialless frameborder="0" title="Video"
  allow="accelero

--- Chunk 3: [search_inputs] ---
  type=search_input freq=6 excl=0.00 OUTLIER=11.0x
  pattern_xpath: ///input

--- Chunk 4: [pagination_buttons] ---
  type=pagination freq=34 excl=1.00
  pattern_xpath: ///img[contains(@class,'more')][contains(@class,'read')]
  content: [ATTR=1 IMG=1]

--- Chunk 5: [text_content:p×23] ---
  type=text_singleton freq=23 excl=0.00
  pattern_xpath: ///p
  content: [TEXT=1]

--- Chunk 6: [text_content:h1×4] ---
  type=text_singleton freq=1 excl=0.83 LEAKS=145
  pattern_xpath: ///div[contains(@class,'footer')][contains(@class,'down')]//div[contains(@class,'column')][contains(@class,'row')][contains(@class,'footer')]
  content: [ATTR=27 BG=88 HREF=128 IMG=30 TEXT=182]
  LEAKS (high):
    [HREF] https://emastered.com/blog (href not in rendered output)
    [IMG] https://static.emastered.com/images/blog-assets/7711.webp?v=VjOwR4s (img URL not in rendered)
    [IMG] https://static.emastered.com/images/blog-assets/7716.webp?v=0lSU_Fz (img URL not in rendered)
    [IMG] https://static.emastered.com/images/blog-assets/7711.webp?v=VjOwR4s (img URL not in rendered)
    [HREF] https://emastered.com/?utm_source=newblog&utm_medium=newblog1&utm_campaign=newblog1 (href not in rendered output)
  LEAKS (medium):
    [TEXT] What is Neurofunk?Bring your songs to life with professional quality m
    [TEXT] In today's world of genre-bending music, there is a lot to keep track 
    [TEXT] Understanding NeurofunkHow Was Neurofunk Created?Neurofunk ExamplesApp

--- Chunk 7: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h1[contains(@class,'post')]
  content: [TEXT=1]

--- Chunk 8: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 9: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 10: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 11: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 12: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 13: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 14: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 15: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 16: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 17: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 18: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 19: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 20: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 21: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 22: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 23: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 24: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 25: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 26: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 27: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 28: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 29: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 30: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 31: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 32: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 33: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 34: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
  content: [TEXT=1]

--- Chunk 35: [text_content:h4×1] ---
  type=text_singleton freq=1 excl=0.04
  pattern_xpath: ///h4[contains(@class,'dropdown')][contains(@class,'menu')]
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
4. Use filename `emastered_comblogwhatisneurofunk.html` in all `_distill()` calls
5. Name the module `test_emastered_comblogwhatisneurofunk_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
