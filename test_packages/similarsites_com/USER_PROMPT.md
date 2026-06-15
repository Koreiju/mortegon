# Test Generation Task: similarsites_com.html

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

- **Total chunks:** 3
- **Structural chunks:** 1
- **Text/Nav chunks:** 0
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `div.com.fm` (freq=5, pq_sig=`div(div,div(img),img)`)

**Text/Nav chunks:**
  (none)

## Quality Report Summary

```
=== QUALITY REPORT: similarsites_com.html ===
Chunks: 3 (structural=1, functional=2, text=0)
Categories: {'card': 1, 'search_input': 1, 'pagination': 1}
Content: 4 tagged, 4 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.com.fm ---
  type=card freq=5 excl=1.00
  pattern_xpath: ///div[contains(@class,'fm')][contains(@class,'homepage')][contains(@class,'popular')][contains(@class,'re')][contains(@class,'site')]
  tree_sig: div(div,div(img),img)
  content: [IMG=2 TEXT=1]

--- Chunk 1: [search_inputs] ---
  type=search_input freq=2 excl=1.00
  pattern_xpath: ///input[contains(@class,'bar')][contains(@class,'cykhd')][contains(@class,'input')][contains(@class,'kvsvu')][contains(@class,'search')]
  content: [ATTR=1]

--- Chunk 2: [pagination_buttons] ---
  type=pagination freq=19 excl=0.00
  pattern_xpath: ///link

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
4. Use filename `similarsites_com.html` in all `_distill()` calls
5. Name the module `test_similarsites_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
