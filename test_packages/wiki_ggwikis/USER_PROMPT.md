# Test Generation Task: wiki_ggwikis.html

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
  - Chunk 0: `div.comp.content` (freq=20, pq_sig=`div(div(div(a(wow-image(img))),div(p(span(span(spa`)
  - Chunk 1: `a.arrows.button` (freq=4, pq_sig=`a(svg(path))`)

**Text/Nav chunks:**
  (none)

## Quality Report Summary

```
=== QUALITY REPORT: wiki_ggwikis.html ===
Chunks: 4 (structural=2, functional=2, text=0)
Categories: {'card': 1, 'button': 1, 'search_input': 1, 'pagination': 1}
Content: 7 tagged, 7 preserved (100%)
Leaks: 0 total, 0 high-importance

--- Chunk 0: div.comp.content ---
  type=card freq=20 excl=1.00
  pattern_xpath: ///div[contains(@data-mesh-id,'comp')][contains(@data-mesh-id,'content')][contains(@data-testid,'content')][contains(@data-testid,'inline')]
  tree_sig: div(div(div(a(wow-image(img))),div(p(span(span(span))))))
  content: [ATTR=1 HREF=1 IMG=1 TEXT=1]

--- Chunk 1: a.arrows.button ---
  type=button freq=4 excl=0.70
  pattern_xpath: ///a[contains(@aria-disabled,'false')][contains(@data-testid,'next')][contains(@class,'arrows')][contains(@class,'button')][contains(@class,'nav')]
  tree_sig: a(svg(path))
  content: [ATTR=1]

--- Chunk 2: [search_inputs] ---
  type=search_input freq=1 excl=1.00
  pattern_xpath: ///input[contains(@aria-invalid,'false')][contains(@aria-required,'false')][contains(@autocomplete,'off')][contains(@class,'custom')][contains(@class,'focus')]
  content: [ATTR=1]

--- Chunk 3: [pagination_buttons] ---
  type=pagination freq=248 excl=0.90
  pattern_xpath: ///div[contains(@class,'strip')][contains(@class,'page')][contains(@aria-hidden,'true')][contains(@class,'current')][contains(@class,'pagination')]
  content: [ATTR=1]

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
4. Use filename `wiki_ggwikis.html` in all `_distill()` calls
5. Name the module `test_wiki_ggwikis_gen.py`
6. Output ONLY the Python code — no markdown fences, no explanation
