# Code Constraint: Frontend Rendering Rules

**Surface scope.** `backend/static/js/cp/*.js` — every frontend component that draws to the GUI.

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §4 (unified panel), §4.1.1 (click-to-edit), §4.5 (compact representation), §4.6 (plus-signs), §4.6.1 (signal-stream), §6 (3D projector), §6.1 (6D UMAP + HSV phase), §6.6.1 (perimeter rendering), §6.6.2 (2D/3D separation), §7.3 (compile/collapse), §8.2.1 (halo concentric), §8.2.1.1 (ray-projection), §8.2.1.2 (HSV rotation), §18 (anti-goals).

---

## §1 — Must hold

### §1.1 One panel template

`_buildPanelDom(data, opts)` (the design name; **realized as `_renderPanel` in `cp/billboard.js`**) is the SINGLE template for every panel surface — hover billboard, click-pinned panel, halo phantom (collapsed form), compiled-graph child. Different opts (collapsed/expanded, halo/pinned) produce variants of the same DOM shape; the body anatomy is identical across variants. The hover↔pin identity (freeze-at-rect: the pinned panel IS the hover billboard at the same screen rect) is the structural guard against §18.11 — verified by `unified-node-view-states` + `hover-to-stick-rect-parity`.

**Anti-goal anchor.** §18.11 (two different knowledge panels).

### §1.2 Freeze-at-hover-rect on click

On click of a 3D node while the hover billboard is visible, the billboard's CURRENT `getBoundingClientRect()` is captured; the new pinned panel materialises with `style.top/.left/.width/.height` set to those exact values; the hover billboard is then reset so the next hover can preview a different node.

**Anti-goal anchor.** §18.8 (click-pinned panel in wrong place).

### §1.3 Pure-print rendering with hidden-overlay edit buttons

Editable fields render in pure print by default — tabs and newlines indented for structure; no JSON braces; no HTML angle brackets; no YAML dashes; no per-row chrome. Above each print-token layout region, a transparent button is positioned with the matching bounding rect; on hover it reveals a subtle outline / tint indicator; on click it materialises a textarea in place.

**Anti-goal anchor.** §4.1.1 spec violation.

### §1.4 Shift-Enter inserts newline, Enter commits

In a multi-line textarea: Shift-Enter inserts a literal newline; Enter commits the value through the lifecycle. Escape discards. Blur commits identically to Enter.

### §1.5 Plus-signs appear in edit state on right and bottom

When a singular key:value field is in edit state, `+→` (right; child row indented one level) and `+↓` (bottom; sibling row at same nesting level) appear as cutout templates concatenated into the print tree structure. Click materialises a new editable row.

### §1.6 No dashed or dotted lines anywhere

Every SVG element in `cp/` carries `stroke` but never `stroke-dasharray`. The 2D↔3D link arrow is solid yellow (`stroke="#ffd700"`, `stroke-width="2"`). Hard/soft link distinction is via stroke colour + weight + arrowhead glyph, not dashes.

**Anti-goal anchor.** §18.7 (stray dotted lines).

### §1.7 Halo phantom shows name only

The halo phantom DOM contains the candidate's name only. No score chips, no description preview, no rendering snippet. Scores live in a `title` attribute (slow-hover tooltip).

**Anti-goal anchor.** §18.21 (compact-form regression).

### §1.8 HSV phase rotation

Per animate frame, each visible chunk's content-HSV hue rotates. **Realised** (`cp/animation.js`): the chunk's base colour is the UMAP content-HSV (`init.umapHsl` = `{h,s,l}` from coords[3:6], set on add by `cp/instance_manager.js` as the hash-family bootstrap and overwritten by `cp/scanner.js::_applyUmapCoords` with the canonical channels). Each frame the hue is rotated by `huePhase = azimuthToHuePhase(camera_azimuth + t·spatialVelocity.y)` and written via `setHSL` (`newColor.setHSL(applyHuePhase(h, huePhase), s, l)`); provenance tint lerps 25 % on top. This is **orbit-locked**: one hue cycle per camera revolution, with the world auto-spin (~60 s/rev) advancing the phase even at rest and freezing while a panel is pinned. The phase + colour maths is the pure, unit-tested `cp/hsv_color.js`. This **replaced** the prior time-driven `colorMatrix = makeRotationFromEuler(t · colorVelocity)` RGB tumble (which rotated a hash/position-derived `umapColor` and discarded the real HSV). The load-bearing invariant — chunk and ray-projected phantom share ONE phase source so they never desync (§18.26) — holds: both read `ChunkProjector._currentHuePhase` (the chunk in this loop, the phantom in `concept_graph.js::_updateHaloPhantomHues`). The continuous rotation is render-only (outside the REPL surface, §6.1 split); the pure maths is locked by `node cp/hsv_color.test.mjs` and the 6-vector format by `6d-umap-format`.

**Anti-goal anchor.** §18.26 (ray-projection mismatched HSV).

### §1.9 Visibility flag, never mesh mutation

URL eye-button toggles `workspace.hidden_urls : Set[str]`. The animate loop reads this set every frame and writes `scale=0` to every chunk and hub of every hidden URL. The mesh's intrinsic scale is never touched directly.

**Anti-goal anchor.** §18.14 (eye button doesn't hide chunks).

### §1.10 Spine viewport scoping

The retrieval result list's `IntersectionObserver` flips `chunkCollapseTarget[id] = 0` for rows currently in the scroll viewport; off-viewport rows fold back. URL click toggles only that URL's chunks, scoped to viewport when a search is active.

**Anti-goal anchor.** §18.12 (URL click explodes all nodes).

### §1.11 Per-frame camera bounds recompute

`minDistance = 0.6 × cluster_radius(orbit_target)` and `maxDistance = 3 × max(|chunk.position|)` are recomputed PER FRAME. Scroll-zoom is unrestricted.

**Anti-goal anchor.** §18.18 (camera zooms too far in / no bounds).

### §1.12 Adaptive resize

`window.resize` (rAF-coalesced) AND `ResizeObserver` on `#projector-panel` both fire `onResize`. `setSize(w, h, updateStyle=false)`. No no-change guard.

**Anti-goal anchor.** §18.9 (3D UI resize stuck).

### §1.13 Single image fetch path

`Map<url, THREE.Texture>` cache → IndexedDB blob cache → `fetch(proxy_url)` → `fetch(direct_url)`. The `X-Image-Proxy-Note` transparent-PNG fallback is NEVER cached as a successful image.

**Anti-goal anchor.** §18.10 (images stopped displaying).

### §1.14 Signal-stream display

When a field carries an iterable, render only the current signal (`signal_stream[card_id::field_path].signal_index`). Suppressed iterable elements stay in storage/queue; for chunk iterables the full distribution lives in 3D (§O.14) and the panel renders the **current instance's content** per-instance (the next-up in the queue), sampled from the 3D env or by halo-retrieval (§O.18). The renderer does not display the suppressed elements.

**Anti-goal anchor.** §18.24 (signal-stream constraint violated).

### §1.15 Ray-projected halo phantoms inherit HSV

Halo phantoms annotated with `ray_target` + `hsv` from `apparition_service.surface_for_projector` carry the parent chunk's HSV state; the per-frame rotation phase is the same as the parent chunk's.

**Anti-goal anchor.** §18.26.

### §1.16 2D/3D coordinate independence

The 2D pin coordinates (top, left, width, height in viewport pixels) NEVER read from or write to 3D world coordinates. The `data-3d-node-id` solid arrow updates per-frame from the 3D node's projected screen position, but the panel itself doesn't move with the 3D node.

**Anti-goal anchor.** §18.31.

---

## §2 — Must not

### §2.1 Render different panel shapes for hover vs click

§18.11 — single template only.

### §2.2 Show score chips / description previews on halo phantoms

§18.21.

### §2.3 Use `stroke-dasharray` on any line in cp/

§18.7. Hard/soft distinction is via colour + weight + arrowhead, never dashes.

### §2.4 Render a field's full iterable in the panel

§18.24. Signal-stream constraint forbids full-iterable rendering.

### §2.5 Mutate the mesh's intrinsic scale to hide chunks

§18.14. Use the per-URL hidden set + animate-loop scale=0 instead.

### §2.6 Add a no-change guard on resize

§18.9. `setSize(w, h, updateStyle=false)` breaks the historical feedback loop at the source.

### §2.7 Show JSON / HTML / YAML syntax in print form

§4.1.1, §1.2.1 spec — the print form integrates tabs and newlines into the parent tree's indentation.

### §2.8 Allow the pinned panel to follow the 3D node's motion

§18.31. The pin is anchored to a screen rect, not to a 3D coord.

### §2.9 Allow edit on read-only python-native fields

§9.6. Read-only fields don't enter edit on click; they briefly highlight to signal the constraint.

### §2.10 Bake the HSV rotation period into a constant the user can't override

Per workspace configurable; default 60s but the user must be able to adjust.

---

## §3 — Code anchors

| File | Responsibility |
|---|---|
| `backend/static/js/cp/billboard.js` | `_renderPanel` (the design's `_buildPanelDom`); freeze-at-hover-rect pin; hidden-overlay edit buttons |
| `backend/static/js/cp/concept_graph.js` | Concept-graph rendering; plus-signs; signal-stream display; field-tree |
| `backend/static/js/cp/concept_graph.js` (`_populateHalo`) | Concentric-circle halo renderer; ray-projection (cone radial + along-ray); HSV rotation on phantoms; autoregressive walk |
| `backend/static/js/cp/scanner.js` | Chunk addition with HSV state per chunk |
| `backend/static/js/cp/animation.js` | Per-frame camera bounds; resize handler; HSV phase loop; 2D↔3D arrow draw |
| `backend/static/js/cp/search.js` | Result list; IntersectionObserver spine; row click fly+pin |
| `backend/static/js/cp/workspace.js` | URL sidebar; eye toggle; domain tree; per-URL hidden set |
| `backend/static/js/cp/sprite_manager.js` | Single image fetch path; IDB cache |
| `backend/static/js/cp/telemetry.js` | Frontend → backend telemetry posting |

---

## §4 — Anti-goal anchors (the §18 entries this surface guards)

| Constraint | Anti-goal |
|---|---|
| §1.1 (one panel template) | §18.11 |
| §1.2 (freeze-at-rect) | §18.8 |
| §1.6 (no dashed lines) | §18.7 |
| §1.7 (halo phantom name only) | §18.21 |
| §1.8 (HSV rotation matched) | §18.26 |
| §1.9 (visibility flag) | §18.14 |
| §1.10 (spine viewport scoping) | §18.12 |
| §1.11 (camera bounds per frame) | §18.18 |
| §1.12 (adaptive resize) | §18.9 |
| §1.13 (single image fetch) | §18.10 |
| §1.14 (signal-stream display) | §18.24 |
| §1.16 (2D/3D coord independence) | §18.31 |

---

## §5 — Feature touchpoints

Every Imaginary-register and Real-register feature with a frontend surface:
- [`click_and_stick.md`](../features/click_and_stick.md)
- [`click_to_edit.md`](../features/click_to_edit.md)
- [`plus_sign_field_tree.md`](../features/plus_sign_field_tree.md)
- [`halo_retrieval.md`](../features/halo_retrieval.md)
- [`6d_umap.md`](../features/6d_umap.md)
- [`visibility_spine.md`](../features/visibility_spine.md)
- [`signal_stream.md`](../features/signal_stream.md)
- [`pattern_map.md`](../features/pattern_map.md)
- [`compile_collapse_dialectic.md`](../features/compile_collapse_dialectic.md)
- [`autoregressive_halo.md`](../features/autoregressive_halo.md)
- [`perimeter_outputs.md`](../features/perimeter_outputs.md)
- [`2d_3d_separation.md`](../features/2d_3d_separation.md)
