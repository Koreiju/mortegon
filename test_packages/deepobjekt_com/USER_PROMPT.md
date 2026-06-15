# Test Generation Task: deepobjekt_com.html

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

- **Total chunks:** 10
- **Structural chunks:** 1
- **Text/Nav chunks:** 8
- **Search input found:** False
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `p.font.px` (freq=2, pq_sig=`p(span(span(a)))`)

**Text/Nav chunks:**
  - Chunk 2: `[text_content:p×3]` (freq=3)
  - Chunk 3: `[text_content:h3×18]` (freq=18)
  - Chunk 4: `[text_content:li×5]` (freq=5)
  - Chunk 5: `[text_content:li×6]` (freq=6)
  - Chunk 6: `[nav_content:li×8]` (freq=8)
  - Chunk 7: `[text_content:h3×1]` (freq=1)
  - Chunk 8: `[text_content:h3×1]` (freq=1)
  - Chunk 9: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: deepobjekt_com.html ===
Chunks: 10 (structural=1, functional=2, text=7)
Categories: {'structural': 1, 'pagination': 1, 'text_singleton': 7, 'menu_item': 1}
Content: 15 tagged, 13 preserved (87%)
Leaks: 2 total, 0 high-importance

--- Chunk 0: p.font.px ---
  type=structural freq=2 excl=0.19
  pattern_xpath: ///p[contains(@class,'font')][contains(@style,'font')][contains(@style,'px')][contains(@style,'size')][contains(@class,'rich')]
  tree_sig: p(span(span(a)))
  content: [HREF=1 TEXT=2]
  LEAKS (medium):
    [TEXT] - Philosophy and art research laboratories and residency

--- Chunk 1: [pagination_buttons] ---
  type=pagination freq=4 excl=1.00
  pattern_xpath: ///link[contains(@aria-current,'page')][contains(@as,'fetch')][contains(@class,'label')][contains(@class,'lv')][contains(@class,'qu')]
  content: [HREF=1]

--- Chunk 2: [text_content:p×3] ---
  type=text_singleton freq=3 excl=0.48
  pattern_xpath: ///p[contains(@style,'right')][contains(@style,'align')][contains(@style,'text')][contains(@class,'font')][contains(@style,'font')]
  content: [HREF=1 TEXT=2]
  LEAKS (medium):
    [TEXT] - Technology, Philosophy, and Art Research Laboratories & Residency

--- Chunk 3: [text_content:h3×18] ---
  type=text_singleton freq=18 excl=0.19
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'maypxmpg')][contains(@class,'ku')]/h3[contains(@class,'font')][contains(@style,'font')][contains(@style,'px')][contains(@style,'size')][contains(@class,'rich')]
  content: [TEXT=1]

--- Chunk 4: [text_content:li×5] ---
  type=text_singleton freq=5 excl=0.13
  pattern_xpath: ///li[contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')]
  content: [TEXT=1]

--- Chunk 5: [text_content:li×6] ---
  type=text_singleton freq=6 excl=0.13
  pattern_xpath: ///li[contains(@class,'rich')][contains(@class,'text')][contains(@class,'wixui')]
  content: [TEXT=1]

--- Chunk 6: [nav_content:li×8] ---
  type=menu_item freq=8 excl=0.70
  pattern_xpath: ///li[contains(@class,'dxs')][contains(@class,'wv')][contains(@class,'item')][contains(@class,'menu')][contains(@class,'vertical')]
  content: [HREF=1 TEXT=1]

--- Chunk 7: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.19
  pattern_xpath: ///div[contains(@id,'comp')][contains(@id,'bgmynq')][contains(@class,'ku')]/h3[contains(@class,'font')][contains(@style,'font')][contains(@style,'px')][contains(@style,'size')][contains(@class,'rich')]
  content: [TEXT=1]

--- Chunk 8: [text_content:h3×1] ---
  type=text_singleton freq=1 excl=0.80
  pattern_xpath: ///h3[contains(@style,'em')][contains(@style,'height')][contains(@style,'left')][contains(@style,'align')][contains(@style,'line')]
  content: [TEXT=1]

--- Chunk 9: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
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
4. Use filename `deepobjekt_com.html` in all `_distill()` calls
5. Name the module `test_deepobjekt_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
