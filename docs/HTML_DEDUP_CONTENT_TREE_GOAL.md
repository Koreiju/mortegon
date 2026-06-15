# GOAL — The HTML Deduplicated Content Tree (2026-06-13)

> **Status: GOAL / binding, build-exactly.** Source: `USER_REQUIREMENTS_VERBATIM.md` §U (the user's
> second `/goal` of 2026-06-13). The user's mandate: build this *"exactly and perfectly before we
> proceed,"* *"reflect this everywhere; design docs and codebase,"* *"explicit and all-encompassing,"*
> affecting *"every portion of related features and functionality."* This doc is the authoritative,
> self-contained spec. It is a companion to `BLACK_SLATE_GOAL.md`: that doc defines the slate; **this
> doc defines exactly what an HTML chunk slate's body *is*.** Where it diverges from the design suite,
> this doc wins and the suite is reconciled (§7).
>
> Verification is the REPL / scenario harness in a later pass (this turn is code-analysis + design
> only). The §U worked example is the **golden I/O test**.

---

## 0 — The Requirement In One Paragraph

When a scanned HTML chunk sticks to the 2D editor, its slate body is **its deduplicated content,
printed as a pure-text tree that mirrors the HTML's structure after deduplication** (U.1). Raw markup,
wrapper nesting, shadow-DOM templates, structural attributes, and repeated strings all dissolve; what
survives is the *content* — element text plus content-bearing attribute values (`href`, `src`,
`title`, `alt`, `aria-label`) — each meaningful unit once, indented by the depth of the surviving
tree. This is the literal realisation of T.2 ("a stuck card is just the panel summary from the
scanned-rendered sample") and the realisation of the long-deferred **HtmlStrategy** of the §E.1
syntax-agnostic compile. The transform is a **backend** computation (backend computes, frontend
renders); the slate prints the resulting tree through the §3 slate grammar with no special-casing.

---

## 1 — The Golden Example, Decoded Rule-By-Rule (U.2 is binding I/O)

The §U input `<article>` (archive.org result card; declarative shadow DOM; nested wrappers; repeated
text; content-bearing attrs) must produce **exactly**:

```
/details/princetonuniver01librgoog
https://archive.org/services/img/princetonuniver01librgoog
Princeton University Library : American Library Association visit, June 29, 1916
by Princeton University Library
Item Stats
Mediatype: Text
450 all-time views
0 favorites
0 reviews
Press Down Arrow to preview item details
```

Each output line, traced to its rule (the rules are §2):

| # | Output line | Source in the HTML | Rule(s) applied |
|---|---|---|---|
| 1 | `/details/princetonuniver01librgoog` | `<a href="…">` | URL unit (href surfaced as content; §2.1-URL) — emitted at the ancestor before descending |
| 2 | `https://archive.org/services/img/princetonuniver01librgoog` | `<img src="…" alt="">` | URL unit (src surfaced); `alt=""` empty → no label unit |
| 3 | `Princeton University Library : American Library Association visit, June 29, 1916` | `<a aria-label>` **=** `<h3 title>` **=** `<h3>` text | three identical units → **deduped to one** (§2.3 token-set equality) |
| 4 | `by Princeton University Library` | `<span title="Princeton University Library">by Princeton University Library</span>` | text token-set ⊋ title token-set → **text (superset) wins**, title dropped (§2.3) |
| 5 | `Item Stats` | `<p>Item Stats</p>` | text unit |
| 6 | `Mediatype: Text` | `<li>` → `<p>Mediatype:</p>` + `<p>Text</p>` | two inline-level units under one block → **inline-joined with a space** (§2.4); `<li>` had no title |
| 7 | `450 all-time views` | `<li title="450 all-time views">` content `all-time views: 450` | title token-set **==** content token-set → **label (attr) surface form preferred** (§2.3) |
| 8 | `0 favorites` | `<li title="0 favorites">` content `favorites: 0` | same as #7 (label preferred on token-equality) |
| 9 | `0 reviews` | `<li title="0 reviews">` content `reviews: 0` | same as #7 |
| 10 | `Press Down Arrow to preview item details` | trailing `<div>` text | text unit |

Dissolved entirely (contentless): `<tile-dispatcher>`, `<template shadowrootmode>`, every wrapper
`<div>`, `<item-tile>`, `<image-block>`, `<item-image>`, `<tile-stats>`, `<tile-mediatype-icon>`,
`<ul>`; and the structural attrs `aria-posinset`, `aria-setsize`, `data-cell-index`, `data-rendered`,
`enablehoverpane`, `aria-describedby`, `aria-haspopup`, `class`/`id`. (Note: the output here is *flat*
because the surviving content collapses to a near-linear chain; genuinely branching surviving content
indents — §2.5.)

---

## 1.5 — LIVE-GROUNDED: build the tree from the existing `fields` extraction (verified 2026-06-13)

A real archive.org scan (161 chunks, ~13–15s, `all_real:true`) captured the §U card live as chunk
`c_6d63d79b_00576934` ("Princeton University Library Chronicle 1950-1951 Vol 12"). Its
`ChunkInstanceRender.fields` (the **existing content-extraction ruleset's** output, V.2) already
contains the entire §U substrate as `{xpath : value}`:
```
/…/a/@aria-label   = The Princeton University Library Chronicle 1950 - 1951: Vol 12 …
/…/a/@href         = /details/sim_princeton-university-library-chronicle_1950-1951_12_…
/…/h3/@title       = The Princeton University Library Chronicle … (== aria-label)
/…/h3/text()       = The Princeton University Library Chronicle … (== aria-label, 3rd copy)
/…/span/text()     = Volume 12 , Issue CONTENTS
/…/img/@src        = https://archive.org/services/img/sim_princeton-…
/…/tile-stats/…/p/text()              = Item Stats
/…/li/@title                          = 0 reviews
/…/li/p/span/text() = reviews:   ;   /…/li/p/text() = 0
/…/tile-mediatype-icon/…/p/text()     = Text
/…/div/text()      = Press Down Arrow to preview item details
```
Meanwhile the chunk's current `rendered_text` is a flat 175-char blob that **drops `@href`/`@src`**,
**garbles stat order**, and is **not a tree** — the precise §3 gap. **Decision:** the content tree is
built from this **`fields` dict** (xpath keys give structure + the @attr/text kind; values are the
content units), *not* by re-parsing `html_raw`. This is the most faithful realisation of "use the
existing ruleset" (V.2): the §2 phases (collapse / dedup / inline-join / print) operate over `fields`,
with `html_raw` kept only for the internalizable `{raw html}` ref. The xpath key supplies: the tree
depth (after collapsing contentless steps), the node kind (`@href`/`@src` → URL unit; `@title`/
`@aria-label`/`@alt` → LABEL; `text()` → TEXT), and document order.

## 2 — The Algorithm (exact; backend transform `fields → content_tree`, over the existing extraction)

Six phases over the shadow-inclusive DOM (`backend/dom/shadow_html_parser.ShadowDOM` already parses
declarative shadow roots and exposes `node.text`, `.children`, `.shadow_root`, `.tail`, `.get_attr`).

### 2.1 Phase 1 — Content-unit extraction (per node)
Each node yields zero+ **content units**, each tagged by kind:
- **TEXT** — `node.text`, whitespace-collapsed + trimmed; emit if non-empty.
- **URL** — content-bearing URL attributes, priority `href`, `src` (also `srcset`, `data-src`,
  `poster`, `action`, `xlink:href`). Each non-empty value is a URL unit. **URLs are data:** kept
  verbatim, never collapsed against TEXT/LABEL; only *identical* URLs dedupe.
- **LABEL** — human-text attributes `title`, `aria-label`, `alt`, `placeholder`,
  `aria-roledescription`; emit each non-empty value (length > 1).
- **Dropped:** `script`, `style`, `template` markup (after shadow hoist), `svg` internals; and all
  structural/identifier attributes (`id`, `class`, `data-*` except content-bearing, `aria-posinset`,
  `aria-setsize`, `aria-describedby`, `aria-haspopup`, `data-cell-index`, `data-rendered`,
  `enablehoverpane`, role plumbing). `alt=""` → nothing.

### 2.2 Phase 2 — Structural collapse
A node survives iff its subtree yields ≥ 1 content unit. A node with **no own units and exactly one
surviving child** is spliced out (the child rises). Contentless wrappers (`<div>` chains, custom
elements, shadow `<template>`s, `<ul>`) therefore vanish, leaving the **minimal tree that carries all
content**.

### 2.3 Phase 3 — Deduplication (the core new behaviour; chunk-scoped)
Normalize each TEXT/LABEL unit to a token multiset (lowercase, punctuation-folded, whitespace-split).
Then, over all TEXT/LABEL units in the chunk:
- If unit A's token-set **⊆** unit B's, **drop A** (B subsumes it). Identical strings → keep one.
- On token-set **equality** between a TEXT and a LABEL (attribute) unit → **prefer the LABEL's surface
  form** (yields line 7 `450 all-time views`, not `all-time views: 450`).
- TEXT strictly-superset of LABEL → **TEXT wins** (line 4 `by Princeton University Library`).
- URL units dedupe only against identical URLs.
- Scope is the whole chunk, so the title across `aria-label` + `<h3 title>` + `<h3>` text → **one
  line** (line 3).

> The DOM-extract JS already attaches a per-node `data-content-hash` over `textContent`
> (`dom_deep_serializer.py`); that hash is a cheap pre-filter for identical-subtree dedup, but the
> token-set subsumption above is the authoritative rule (it catches the title/aria-label/`title`-attr
> permutations the hash misses).

### 2.4 Phase 4 — Inline combination
Content units that are **inline-level siblings under one block-level parent** join into **one line**
with a single space (line 6 `Mediatype: Text`; a `<span>` + tail within a `<p>`). Block-level units
stay on separate lines. (Inline set = the existing `_INLINE_TAGS`; everything else is block.)

### 2.5 Phase 5 — Pure-text tree print
Walk the surviving content tree in document order; emit one line per content unit / inline-joined run;
**indentation (one `\t` per surviving level) reflects the post-collapse tree depth**; a node's own
units print before its children's; **no** HTML/JSON/markdown syntax, **no** blank-line padding, **no**
escaped-newline glyphs (consistent with §8D.20 tree-pretty-print and the §3 slate grammar). The result
round-trips through the slate's `parse`/`print` (names-may-contain-spaces, tab+newline tree).

---

## 3 — What's There Now vs. What's Needed (code-grounded gap)

Today the closest transform is `backend/mapper/chunk_render.py::html_to_rendered_text` + `_render_node`
([:224](backend/mapper/chunk_render.py:224), [:264](backend/mapper/chunk_render.py:264)), producing a
chunk's `rendered_text` (a markdown-lite flatten for embedding). Measured against §2:

| Behaviour | `html_to_rendered_text` today | §2 requirement | Gap |
|---|---|---|---|
| Anchor `href` | **dropped** ("No URL retained", [:229](backend/mapper/chunk_render.py:229)) — only anchor text inlined | surfaced as a URL content line (line 1) | **yes** |
| `<img src>` | **dropped** (leaf fallback does `alt`/`placeholder`/`title` only, [:312](backend/mapper/chunk_render.py:312)) | surfaced as a URL line (line 2) | **yes** |
| Dedup of repeated strings | **none** — every text run emitted | token-set subsumption; chunk-scoped; title→one line | **yes** (the core) |
| Title-attr vs content choice | emits text content (`all-time views: 450`) | prefer curated label on token-equality (`450 all-time views`) | **yes** |
| Output shape | paragraph-broken prose (`\n\n` between blocks) | tab-indented **tree**, one unit/line, no blank padding | **yes** |
| Contentless wrappers | leave blank-line residue (block breaks) | fully collapse (spliced out) | **yes** |
| Shadow roots / inline-join | hoisted ✓ / partial ✓ | keep; formalize inline-join | partial |

So this is **not a tweak of `html_to_rendered_text`** — it is a new `html_to_content_tree(html) →
str` (or a rewrite of that function plus a dedup pass), producing the §2 tree. The existing inter-chunk
boilerplate distillation (`backend/dom/web_distiller_freq.py`, `content_distiller_simple.py`,
`mapper/dedup_logging.py`) is **upstream and complementary** — it removes structure repeated *across*
the 200 result cards; this transform deduplicates content *within* one card. The new transform runs on
the distilled `html_raw`.

---

## 4 — Impact Map (all-encompassing, per U.3 — every portion of related functionality)

### 4.1 Backend (computes the tree)
- **`backend/mapper/chunk_render.py`** — the primary site: new `html_to_content_tree` (the §2 phases) +
  the dedup pass; `ChunkInstanceRender` gains a `content_tree` field (and `rendered_text` for embedding
  is **derived from it**, so retrieval embeds clean content, not noisy flatten).
- **`backend/dom/shadow_html_parser.py`** — the walk substrate (already shadow-aware); the new renderer
  walks `ShadowNode`.
- **`backend/dom/{content_distiller_simple,web_distiller_freq,content_tagger}.py`** — confirm the
  intra-chunk tree runs *downstream* of inter-chunk distillation; no double-dedup or content loss.
- **Persistence + ConceptNode** — the chunk node's **`data`** (the slate's pure-text body) **is** the
  content tree; **`rendering`** (TF-IDF-indexed, §8D.20) is the same clean text. `html_raw` survives
  under-the-hood (internalizable via a `{raw html}` `{ref}`, per BLACK_SLATE_GOAL §3/§6) but is not the
  default slate body.
- **`/api/chunk_details(_batch)`, `/api/chunk_nodes`, `/api/chunk_search`** — the payload the slate
  pins must carry `content_tree`; retrieval ranks over the clean text.
- **`/api/conceptual/compile` + `/api/compile_pipeline`** — see §4.3 (the HtmlStrategy).

### 4.2 Frontend (renders the tree)
- The HTML chunk **slate body = the content tree** (BLACK_SLATE_GOAL §A1). The fractured
  `billboard-html` / `billboard-rendered-text` / `billboard-fields` sections (the thing T.1 rejects)
  are replaced by this single pure-text tree.
- The slate's `parse`/`print` must accept it (it is a valid tab+newline tree; names with spaces).
- **Internalize/externalize:** raw HTML becomes a foldable `{raw html}` `{ref}` — internalize to see
  the bytes; the default is the dedup tree.

### 4.3 Compile — this **realises** the §E.1 HtmlStrategy
`field_tree.md` lists `HtmlStrategy` as *"greenfield — not yet realised."* This goal **is** its
realisation: the HTML detector of the one syntax-agnostic recursive descent
(`_try_parse_structured` / `decompose_recursive` on the backend; `_decomposeValue` mirror on the
frontend) parses HTML into the §2 content tree, so an HTML-valued field decomposes/compiles exactly
like JSON/indent-tree/list inputs. The `syntax-agnostic-compile` scenario (§E.1) gains the HTML arm.

### 4.4 Verification
- New env-scenario **`html-dedup-content-tree`**: the §U input `<article>` → **exactly** the §U output,
  asserted against the live stack (golden I/O).
- `scripts/probe_live_archive_scan.py` asserts a real archive.org result card renders the dedup tree.
- REPL `watch-activity` chunk view reflects the content tree, not raw html.

### 4.5 Design docs to reconcile (doc-first trickle-down)
`DOMAIN_MODEL.md` §4.1 (chunk node `data`/`rendering` = content tree), §4.5 (compact representation),
§7.1 / §E.1 (HTML compile strategy realised), §8D.20 (tree-pretty-print), the scanner/chunk-render
section; `docs/frontend/field_tree.md` (HtmlStrategy → realised), `billboard.md`, `concept_view.md`,
`scan_streaming.md`; `docs/code_specs/backend/scanner.md` (+ a `content_tree` spec); `docs/code_specs/
frontend/*` (slate body); `object_model/ChunkPatternSchema.md`, `FieldTree.md`; cross-link from
`BLACK_SLATE_GOAL.md` §A1/§3.

---

## 5 — Plan (build order; doc-first per A.1)
1. **Doc-first (this turn):** §U verbatim ✓; this goal ✓; reconcile the §4.5 design docs on go-ahead.
2. **Backend transform:** implement `html_to_content_tree` (the §2 six phases) in `chunk_render.py`;
   derive `rendered_text` from it; add `content_tree` to `ChunkInstanceRender` + the chunk node `data`.
   Unit-test against the §U golden I/O.
3. **Compile arm:** wire the HtmlStrategy (§4.3) so HTML fields decompose via the same transform.
4. **API + persistence:** surface `content_tree` through `/api/chunk_details(_batch)`; index `rendering`.
5. **Frontend (with the slate rebuild):** the HTML chunk slate prints `content_tree`; `{raw html}` ref
   internalizes the bytes.
6. **Verify (later pass):** the `html-dedup-content-tree` scenario + probe, all-real, REPL-mirrored.

---

## 6 — Acceptance Criteria
1. **Golden I/O:** the §U `<article>` produces **exactly** the §U 10-line output (byte-for-byte, modulo
   trailing whitespace) — the binding test.
2. **Dedup:** a string appearing in `aria-label` + `title` + element text appears **once**; a
   `title`-attr that restates its content (token-equal) yields the **label** surface form; a text that
   supersets a label yields the **text**.
3. **Attributes surfaced:** `href` and `src` appear as content lines; `alt=""` contributes nothing.
4. **Structure:** contentless wrappers/custom-elements/templates fully collapse; surviving branching
   indents by tab; no blank-line padding, no HTML/JSON/markdown syntax, no escaped newlines.
5. **It is the slate body:** the HTML chunk slate renders this tree (not the fractured sections); it
   round-trips through the slate `parse`/`print`; raw HTML is reachable only by internalizing `{raw html}`.
6. **Compile parity:** an HTML-valued field decomposes through the same transform as the §E.1 strategies.
7. **Retrieval:** TF-IDF/nomic embed the clean content tree, not the noisy flatten.
8. **All-real, REPL-mirrored** verification (Q.1 / R.8); backend-computed, frontend-rendered.

---

## 7 — Traceability
- Verbatim: `USER_REQUIREMENTS_VERBATIM.md` §U (incl. the binding golden example).
- Companion: `BLACK_SLATE_GOAL.md` (the slate this fills); the content tree is its HTML chunk body.
- This doc is authoritative for the HTML→content-tree transform; the design suite is reconciled to it
  (§4.5).
