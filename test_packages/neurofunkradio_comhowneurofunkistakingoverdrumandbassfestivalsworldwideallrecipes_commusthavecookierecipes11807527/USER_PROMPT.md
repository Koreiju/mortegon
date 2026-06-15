# Test Generation Task: neurofunkradio_comhowneurofunkistakingoverdrumandbassfestivalsworldwideallrecipes_commusthavecookierecipes11807527.html

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

- **Total chunks:** 5
- **Structural chunks:** 1
- **Text/Nav chunks:** 2
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `span.elementor.grid` (freq=9, pq_sig=`span(a(span,svg(path)))`)

**Text/Nav chunks:**
  - Chunk 3: `[text_content:h1×1]` (freq=1)
  - Chunk 4: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: neurofunkradio_comhowneurofunkistakingoverdrumandbassfestivalsworldwideallrecipes_commusthavecookierecipes11807527.html ===
Chunks: 5 (structural=1, functional=2, text=2)
Categories: {'card': 1, 'search_input': 1, 'pagination': 1, 'text_singleton': 2}
Content: 5 tagged, 5 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: span.elementor.grid ---
  type=card freq=9 excl=0.80
  pattern_xpath: ///span[contains(@class,'grid')][contains(@class,'item')][contains(@role,'listitem')][contains(@class,'elementor')]
  tree_sig: span(a(span,svg(path)))
  content: [TEXT=1]

--- Chunk 1: [search_inputs] ---
  type=search_input freq=2 excl=1.00
  pattern_xpath: ///input[contains(@class,'field')][contains(@class,'md')][contains(@class,'textual')][contains(@id,'field')][contains(@id,'form')]

--- Chunk 2: [pagination_buttons] ---
  type=pagination freq=6 excl=0.00
  pattern_xpath: ///link
  content: [ATTR=1 HREF=1]

--- Chunk 3: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.39
  pattern_xpath: ///h1[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
  content: [TEXT=1]

--- Chunk 4: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=0.39
  pattern_xpath: ///h2[contains(@class,'default')][contains(@class,'heading')][contains(@class,'title')][contains(@class,'size')][contains(@class,'elementor')]
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
4. Use filename `neurofunkradio_comhowneurofunkistakingoverdrumandbassfestivalsworldwideallrecipes_commusthavecookierecipes11807527.html` in all `_distill()` calls
5. Name the module `test_neurofunkradio_comhowneurofunkistakingoverdrumandbassfestivalsworldwideallrecipes_commusthavecookierecipes11807527_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
