# Test Generation Task: criterion_comsearchqzizek.html

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
- **Structural chunks:** 0
- **Text/Nav chunks:** 3
- **Search input found:** False
- **Pagination found:** True

**Structural chunks:**


**Text/Nav chunks:**
  - Chunk 1: `[text_content:h2×2]` (freq=1)
  - Chunk 2: `[text_content:h1×1]` (freq=1)
  - Chunk 3: `[text_content:h2×1]` (freq=1)

## Quality Report Summary

```
=== QUALITY REPORT: criterion_comsearchqzizek.html ===
Chunks: 4 (structural=0, functional=1, text=3)
Categories: {'pagination': 1, 'text_singleton': 3}
Content: 7 tagged, 6 preserved (86%)
Leaks: 1 total, 0 high-importance

--- Chunk 0: [pagination_buttons] ---
  type=pagination freq=1 excl=0.00
  pattern_xpath: ///script

--- Chunk 1: [text_content:h2×2] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///div[contains(@class,'content')][contains(@class,'main')]
  content: [TEXT=5]
  LEAKS (medium):
    [TEXT] <div class="h2"><span id="challenge-error-text">Enable JavaScript and 

--- Chunk 2: [text_content:h1×1] ---
  type=text_singleton freq=1 excl=0.00
  pattern_xpath: ///h1
  content: [TEXT=1]

--- Chunk 3: [text_content:h2×1] ---
  type=text_singleton freq=1 excl=1.00
  pattern_xpath: ///h2[contains(@class,'spacer')][contains(@class,'top')][contains(@id,'challenge')][contains(@id,'success')][contains(@id,'text')]
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
4. Use filename `criterion_comsearchqzizek.html` in all `_distill()` calls
5. Name the module `test_criterion_comsearchqzizek_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
