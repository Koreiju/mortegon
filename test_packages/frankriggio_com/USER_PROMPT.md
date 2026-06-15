# Test Generation Task: frankriggio_com.html

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

- **Total chunks:** 4
- **Structural chunks:** 2
- **Text/Nav chunks:** 0
- **Search input found:** True
- **Pagination found:** True

**Structural chunks:**
  - Chunk 0: `li.item.level` (freq=8, pq_sig=`li(a(span,span))`)
  - Chunk 1: `div.item.socials` (freq=5, pq_sig=`div(a(i,span))`)

**Text/Nav chunks:**
  (none)

## Quality Report Summary

```
=== QUALITY REPORT: frankriggio_com.html ===
Chunks: 4 (structural=2, functional=2, text=0)
Categories: {'menu_item': 1, 'card': 1, 'search_input': 1, 'pagination': 1}
Content: 12 tagged, 12 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: li.item.level ---
  type=menu_item freq=8 excl=1.00
  pattern_xpath: ///li[contains(@class,'level')][contains(@class,'menu')][contains(@class,'nav')][contains(@class,'object')][contains(@class,'type')]
  tree_sig: li(a(span,span))
  content: [HREF=1 TEXT=1]

--- Chunk 1: div.item.socials ---
  type=card freq=5 excl=0.75
  pattern_xpath: ///div[contains(@class,'socials')][contains(@class,'item')]
  tree_sig: div(a(i,span))
  content: [ATTR=2 HREF=1]

--- Chunk 2: [search_inputs] ---
  type=search_input freq=4 excl=1.00
  pattern_xpath: ///input[contains(@id,'form')][contains(@id,'search')][contains(@id,'us')][contains(@type,'text')]
  content: [ATTR=2]

--- Chunk 3: [pagination_buttons] ---
  type=pagination freq=40 excl=1.00
  pattern_xpath: ///img[contains(@class,'image')][contains(@class,'wp')][contains(@decoding,'async')][contains(@loading,'lazy')][contains(@sizes,'auto')]
  content: [IMG=5]

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
4. Use filename `frankriggio_com.html` in all `_distill()` calls
5. Name the module `test_frankriggio_com_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
