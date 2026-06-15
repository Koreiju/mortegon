# Theme — Black Core, Silver Outline

> **Status: realised (cp/*.js + css).** The black-core / silver-outline visual system is carried by `cp/ui_utils.js::initMaroniteTheme` (de-rainbowed silver palette: `--surface-base #000`, `--border-light #b8c0c8`, `--text-primary #d7dde2`) + `backend/static/css/styles.css` (`:root` black/silver tokens) + `cp/animation.js` (black scene background). The only colour is the 3D HSV nodes (theme exception zone, `projector.md`) + the yellow `#ffd700` 2D↔3D connector + `--accent-error` red; no arrowheads/dashes (§O.16). See §11 (Realized Implementation).
>
> **The one rule.** *Everything is black. Every UI object border **and** every glyph is rendered as a **black core traced by a silver outline** — black in the middle, silver outline around — on a black ground.* The silver never fills; it only ever outlines a black shape. The single exception is the Projector's 3D nodes and billboards (`projector.md`), which alone carry filled colour (the 6D-UMAP HSV fill, §8.2.1.2) and imagery (cached image textures, §11.2). Against an interface that is otherwise pure black edged in silver, those 3D nodes are the only filled, chromatic things in view.

---

## §1 — Identity

The interface is a field of black objects edged in silver, floating on black. Panels, the sidebar, the result list, field-trees, halo rings, links, buttons, scrollbars, tooltips, the agent panel — every one of them is a **black fill bounded by a silver outline**; and the words on them are the same — **black letterforms traced by a silver outline**, not silver-filled text. Nothing lifts to grey, nothing glows, nothing casts a shadow; the only ink is the silver that draws the edges of black shapes, and the only filled colour anywhere is the perceptual HSV of the 3D Real register. This is minimalism taken to the form the user specified: *everything black, all borders black with silver outlines, words just the same — black in the middle with silver outlines around.*

This document defines the tokens, the outline treatment that applies uniformly to borders and glyphs, the state model, motion, and the 3D exception. Every surface doc's *Theme* section (template §10) cites these tokens; the tokens are defined here as **outline intensities around black**, so a per-doc reference like "border `--steel-700`" means *a black edge traced in `--steel-700` silver*, and "text in `--text-primary`" means *black glyphs traced in the primary silver outline*.

---

## §2 — Colour Tokens

### §2.1 Black (the universal fill and ground)

There is one fill, and it is black. Panel interiors, button interiors, the letterform interiors, the editor field, the void behind everything, the Projector clear-colour — all black.

| Token | Value | Use |
|---|---|---|
| `--black` | `#000000` | The universal fill: every border core, every glyph interior, every panel body, the ground, the Projector clear-colour |
| `--black-edit` | `#050608` | An open textarea's fill — an *imperceptible* lift (a hair off pure black) so a live field is felt, not seen; still reads as black |
| `--bg-void` / `--bg-panel` / `--bg-recess` | `#000000` (= `--black`) | Aliases retained so the per-surface docs need no rewrite — every one is **pure black**; there is no panel or recess lift |
| `--bg-edit` | `#050608` (= `--black-edit`) | Alias for the open-editor fill |

There are no grey fills and no panel "elevation" fills. If anything reads as grey, it is wrong: every surface is `--black`, distinguished only by the silver outline that traces it.

### §2.2 Silver (the outline — the only ink)

Silver is the entire visible palette, and it appears **only as outlines** tracing black shapes (borders and glyphs alike). It runs from a bright specular edge to a near-merge-with-black. (The `--steel-*` names are retained as aliases so the per-surface docs need no rewrite; "silver" and "steel/stainless" name the same palette — the user's latest word is *silver*.)

| Token (alias) | Value | Use (always as an outline around black) |
|---|---|---|
| `--silver-100` (`--steel-100`) | `#eef0f2` | Specular edge; focus/active 2px outline; the bright line of a brushed edge |
| `--silver-300` (`--steel-300`) | `#c4c9cf` | Primary outline; hover; hard-link stroke; primary glyph outline |
| `--silver-500` (`--steel-500`) | `#9aa0a8` | Mid outline; secondary glyphs; the middle of a brushed edge |
| `--silver-700` (`--steel-700`) | `#5c616a` | Resting outline; default border; halo ring arcs; soft-link stroke |
| `--silver-900` (`--steel-900`) | `#2c2f34` | Faint outline; near-merge dividers; read-only edges |

**The brushed edge.** A silver outline is not a flat line; it reads as a machined edge catching light. Implement as a near-vertical gradient `--silver-100 → --silver-500 → --silver-300` (top→mid→bottom) along the outline, or a base outline with a 1px specular highlight at ~30% on the light-facing side. The brush direction is **global** (≈92° from horizontal) so every silver edge in the interface catches the same imaginary light — which is what makes scattered silver outlines read as one machined surface.

### §2.3 Text — black glyphs, silver outline

Text gets exactly the border treatment: **black letter interiors traced by a silver outline** ("words are just the same; black in the middle with silver outlines around"). It is an outline-font rendering, not silver-fill type. The `--text-*` tokens are *glyph-outline intensities*, paired with the black glyph fill:

| Token | = outline tier | Glyph fill | Use |
|---|---|---|---|
| `--text-primary` | `--silver-300` outline | `--black` | Body text; pure-print field-tree content; panel names |
| `--text-dim` | `--silver-500` outline | `--black` | Labels; secondary chrome; the `:` and `=` separators in `key : Type = value` rows |
| `--text-faint` | `--silver-700` outline | `--black` | Placeholders; faint-memory nodes (§11.5); disabled labels |
| `--text-lock` | `--silver-900` outline | `--black` | The 🔒 glyph and read-only field text |

Implementation: black glyph fill + a silver outline via `-webkit-text-stroke` (≈0.6px at 13px) or an equivalent layered-outline technique. **Legibility note:** the outline must stay thick enough that the black-cored glyph reads against the black ground; at small sizes a glyph may collapse toward a near-solid silver mark, which is acceptable — the *intent* is black-core-silver-edge, and the rendering degrades gracefully toward silver as size drops.

### §2.4 The only non-silver ink (used as outline/stroke, sparingly)

| Token | Value | Use | Justification |
|---|---|---|---|
| `--accent-arrow` | `#ffd700` | The 2D↔3D link arrow only (`link_layer.md`) — a solid yellow **stroke** (a line, no fill, so it sits in the outline grammar) | Mandated solid yellow by §18.7 |
| `--accent-error` | `#c0414a` | Error envelopes, broken `{var}` refs, type-mismatch edges — as a **silver outline replaced by this red outline** | The single warning hue; desaturated to sit in the dark palette |

No other colour appears in the 2D interface. Edge-type and hard/soft-link differentiation (§3.2) is carried by **silver-outline brightness + stroke weight** (links are **undirected lines, no arrowheads** — §O.16), never by hue (`link_layer.md`). Provenance, rank, status, and type are position, outline intensity, glyph, and tooltip text — never a colour badge or fill.

### §2.5 The exception zone (3D only)

Inside the Projector viewport, two element classes carry filled colour and imagery, and the theme **explicitly does not outline-or-blacken them**:

- **3D chunk nodes** — filled with the chunk's 6D-UMAP HSV colour (§8.2.1.2), rotating in phase with camera azimuth. The black ground (`--black`) is the clear colour precisely so these filled HSV points are maximally legible against the all-black, silver-edged interface.
- **Billboards** — image-bearing chunks render their cached texture (§11.2); image-less chunks render the HSV fill.

These are the **only filled, coloured pixels in the entire application.** Ray-projected halo phantoms (`halo.md`) that originate from a 3D chunk **inherit** that chunk's HSV/image (they are billboard-derived); pure soft-link phantoms (no 3D backing) render as black-core silver-outline name chips like any other chrome. That inheritance is the only place the exception leaks onto the 2D plane, and it leaks *from a billboard*, consistent with the one rule.

---

## §3 — The Outline Treatment (borders and glyphs, one grammar)

Borders and glyphs share one treatment: a black core traced by a silver outline.

- **Borders.** A panel/button/field is a `--black` fill bounded by a silver outline (the border is the black edge traced in silver). Weight 1px resting / 2px focus-active. Corners 0–2px (machined, crisp; no pills).
- **Glyphs.** Black letter interiors with a silver outline (§2.3).
- **Elevation.** Read from silver-outline **intensity and weight**, never from shadow. **No `box-shadow`, no glow, no blur** — the black void already provides infinite depth; a focused panel simply brightens its outline to `--silver-100` at 2px.
- **Dividers.** `--silver-900` 1px — present but nearly merged with black, so internal structure is *felt* more than seen.
- **Fills.** Everything is `--black`; the only perceptible deviation is `--black-edit` under an open editor.
- **Scrollbars.** Thin (6px), `--black` track, `--silver-700` outline thumb, `--silver-300` on hover; no arrows.
- **Focus ring.** The 2px `--silver-100` outline *is* the focus ring; no separate halo.

---

## §4 — The State Model

State is expressed by **silver-outline intensity and weight** — never by a fill change, because every surface stays black.

| State | Outline (border + glyph) | Fill | Notes |
|---|---|---|---|
| **Rest** | `--silver-700` 1px | `--black` | The default machined edge |
| **Hover** | `--silver-300` 1px (the outline **brightens**) | `--black` | The latent-interactivity reveal (§4.1.1): the silver edge brightens — **no tint, no fill change**; the reveal is the outline catching more light |
| **Active / Focus / Edit** | `--silver-100` 2px | `--black-edit` (textarea only) | The brushed edge goes specular; the editor field lifts imperceptibly; the caret is `--silver-100` |
| **Read-only (🔒)** | `--silver-900` 1px | `--black` | Dim, near-merged; click is a no-op highlight (frontend_rendering §2.9) |
| **Disabled** | `--silver-900` 1px | `--black` | Recedes toward black |
| **Error / broken ref** | `--accent-error` 1px outline | `--black` | The only non-silver outline state |

The hover reveal — *the silver outline brightening, with no fill tint* — is the single most-used affordance in the suite: a pure-print field token announces it is interactive by its edge catching light, then opens to an editor on click (`field_tree.md` §6). (Where peer docs predating this revision say "10% tint," read it as this outline-brighten — there is no fill tint in the black-core model.)

---

## §5 — Typography

- **Pure-print field-trees** (`field_tree.md`, `object_exploration.md`) — **monospace** (`ui-monospace, "Cascadia Code", "JetBrains Mono", Consolas, monospace`), black glyphs + `--text-primary` silver outline, 13px, line-height 1.5. Monospace is mandatory: the tabs-and-newlines tree alignment depends on a fixed advance width, and the print form *is* the data (§4.5).
- **Chrome labels** (headers, sidebar entries, buttons) — a clean grotesque sans (`Inter, "Segoe UI", system-ui, sans-serif`), black glyphs + `--text-dim` silver outline, 12px, +0.04em tracking on headers.
- **Type slot** (`object_exploration.md`: `: int`, `: WebDriver`, `: {FunctionOutputType}`) — `--text-dim` outline so the type recedes behind key and value without any colour.
- **Tooltips / scores / counts** — monospace, 11px, `--text-dim`, on a `--black` chip with a `--silver-700` outline.
- **Panel name (header)** — sans, `--text-primary`. The per-id hash (§4.1) is **reinterpreted**: instead of a header hue band, the hash drives a subtle **silver-outline-intensity offset** on the header's bottom edge — a machined ID tell, identity without colour or fill (noted in `concept_view.md` §10).

---

## §6 — Motion

Motion is subtle and shares the one frame budget (`liveness.md`). Two idioms, both on the silver outline only:

- **Sheen-on-hover.** A silver outline's brush-gradient angle shifts ~3° over 180ms on hover, so the machined edge appears to catch light as the cursor nears. No fill change, no colour change.
- **Edge-brighten transitions.** State changes (rest→hover→active) tween the outline colour token over 120ms eased, matching the Pulse easing (`liveness.md` §2). The black fills never change.

No bounce, no spring, no parallax. The void does not move; the silver edges catch light; the HSV 3D nodes rotate (exception zone only).

---

## §7 — Per-Surface Application (index)

Each surface's own *Theme* section gives the detail; this is the map. Every cell below is "black fill + silver outline" unless noted.

| Surface | Application | Exception |
|---|---|---|
| Projector (`projector.md`) | clear-colour `--black`; hubs as `--silver-700`-outline wireframe rings; HUD text black+`--text-dim` outline | **Chunk nodes + billboards carry filled HSV/imagery** |
| ConceptView (`concept_view.md`) | black panel, `--silver-700` outline; header silver-intensity ID tell; latch/min/close glyphs black+`--silver-500` outline | none |
| FieldTree / object_exploration | monospace black glyphs + `--text-primary` outline over `--black`; hover = outline brighten; plus-signs + type-slot as outlined glyphs | none |
| Halo (`halo.md`) | ring arcs `--silver-700` outline; phantom name-chips black+silver-outline | **Ray-projected phantoms inherit chunk HSV/image** |
| LinkLayer (`link_layer.md`) | hard link `--silver-300`/2px line; soft link `--silver-700`/1px line — undirected, no arrowheads (§O.16) | **2D↔3D connector is `--accent-arrow` yellow (headless line)** |
| Editor canvas (`editor.md`) | `--black` canvas; panels are black cards edged in silver | none |
| Sidebar / result list (`retrieval_and_sidebar.md`) | `--black`; `--silver-900` row dividers; eye/× glyphs black+`--silver-500` outline | none |
| pattern_map / url_set | field-tree treatment; golden-trio labels in `--text-dim` outline | none |
| Agent panel (`agent_and_rollout.md`) | token stream monospace black+`--text-primary` outline; play/pause glyphs black+`--silver-300` outline | none |

---

## §8 — Behaviours (invariants)

1. **One fill, and it is black** (§2.1). No grey, no elevation fill; the only deviation is the imperceptible `--black-edit`.
2. **Silver is only ever an outline** (§2.2) — it traces black borders and black glyphs; it never fills.
3. **Words are outlined, not filled** (§2.3) — black letterforms, silver edge.
4. **No shadow, no glow, no blur** (§3) — elevation and focus are silver-outline intensity + weight.
5. **Hue appears in exactly three places:** the filled HSV of 3D nodes/billboards (the exception, §2.5), the yellow 2D↔3D arrow stroke, and the desaturated error outline. Nowhere else, and never as a fill except the 3D exception.
6. **State is silver-outline intensity, not colour or tint** (§4).
7. **The brush direction is global** (§2.2) — every silver edge catches the same light.
8. **Monospace is reserved for print** (§5); chrome is sans; both are black-core silver-outline.

---

## §9 — REPL Mirroring

The theme carries no backend mirror field. Its REPL obligation: the in-place activity viewer (`repl_mirroring.md`, §11.8) adopts the same restraint in the terminal — a black background, dim silver rule-lines `─` (the analogue of `--silver-900` dividers), foreground text in the silver tiers, and the single error red — so the Symbolic register is visually self-similar to the black-and-silver Imaginary it mirrors (§14 transcendental permanence).

---

## §10 — References

- `DOMAIN_MODEL.md`: §1.5 (registers), §4.1 (panel chrome / header hash → reinterpreted §5), §4.1.1 (hover reveal → §4), §8.2.1.2 (HSV 3D exception), §11.2 (image textures), §18.7 (yellow arrow).
- `code_constraints/frontend_rendering.md`: §1.6 (no dashes — links are silver/yellow solid), §1.7 (name-only phantom), §2.9 (read-only no-op highlight).
- Peer: every surface doc's §10 *Theme* section applies these tokens (now black-core + silver-outline).

---

## §11 — Realized Implementation (the shipped `cp/` theme)

> **Status: implemented + verified live.** §1–§10 are the *ideal*; this section records the **shipped** theme as it actually runs in the existing frontend, so doc and code agree (doc-first discipline). Verified during real Selenium scans of example.com, Hacker News, and **archive.org (149 chunks)** with no console errors.

**Where the theme lives.** The authoritative runtime theme is injected by **`backend/static/js/cp/ui_utils.js::initMaroniteTheme()`** as an `!important` stylesheet, layered over **`backend/static/css/styles.css`** (whose `:root` is also remapped to black/silver). Both agree: black surfaces, silver edges. The `!important` layer wins where they overlap — so the *realized* token values below are the operative ones.

**Realized glyph treatment.** The ideal is black-core + silver-**outline** glyphs (§2.3); the shipped form renders **silver-filled** glyphs (`--text-primary #d7dde2`) in a **VHS/VCR monospace** face, uppercased, on black. This is the documented graceful degradation of the outline font (§2.3 legibility note — the outline collapses toward a silver fill at UI sizes). The monospace-uppercase character is the realized "machined" identity; CSS **ridge/outset** borders are the realized "brushed edge" (§2.2). Realized tokens: `--surface-base #000`, `--border-light #b8c0c8`, `--text-primary #d7dde2`, `--text-secondary #9aa3ab`, `--text-muted #7c858d`, `--accent-pastel #b8c0c8` (input-focus edge, de-neoned), square corners (radius 0).

**The de-rainbow correction (this pass).** The single biggest fix: the Maronite layer formerly applied `animation: rainbow-text … !important` to nearly all text and `rainbow-bg` on hover, plus an HSV-rotating sidebar border in `styles.css`. These **overrode every glyph colour with cycling neon**, violating §2.3/§4. All are now neutralised to **static silver** (`animation: none`); state is read from silver intensity/weight per §4, not hue.

**3D (the exception zone, §2.5) — realized.** `cp/animation.js::initBackground` now sets `scene.background = #000` (the full-bleed **waterfall video plane was removed**) so chunk HSV spheres are the only filled colour. The **2D↔3D connector** is a **headless solid yellow** line (`#ffd700` = `--accent-arrow`; the `<marker>` arrowhead was deleted from `index.html` and `concept_graph.js`). **Concept edges** are **undirected solid silver** lines — `_edgeStyleForType` recoloured to silver tiers (type = brightness + width), with `marker-end` and `stroke-dasharray` removed (§2.4/§3.2/§O.16). Concept **cards** are black + silver outline + silver header text; the former per-id **hue header band was removed** (reinterpreted as identity-without-colour, §5).

**Cache-bust workflow (operational).** `cp/*` modules are imported by `chunk_projector.js` with a literal `?v=NN`. `backend/main.py::_asset_version()` stamps `styles.css`, the top-level `chunk_projector.js`, and `index.html` by mtime — **but not the inner ES-import URLs**. So after editing any `cp/*` module, **bump `?v=NN`** in `chunk_projector.js` (a single shared integer across all `cp/*` import URLs, bumped on every `cp/*` edit — do not pin the literal value in prose, it goes stale each bump) to force the browser to refetch it.

**Known residue (tracked, non-blocking).**
- A transient scan/UMAP status string can briefly overlap the sidebar search header (cosmetic positioning).
- The right-sidebar `sidefall.mp4` video remains as a confined, glass-dimmed accent — the one non-black 2D element retained pending an explicit call to blacken it for strict "everything black."
