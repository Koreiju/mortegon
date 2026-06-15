# Mortegon Integration Scheme

A compiled, sequenced specification for the unified 3D ↔ 2D click-and-stick framework that has emerged across the recent design sessions. Every paragraph here corresponds to one or more of the user's iterative requests; this is the canonical reference the code should converge to.

The name "Mortegon" denotes the **mortise-and-tenon joint** between the 3D DOM scanner (the spatial scene) and the 2D concept-graph editor (the symbolic computation surface). The two surfaces must interlock seamlessly — a node hovered in the 3D scene becomes the same panel that sticks in the 2D editor when clicked; a `{var}` reference typed in the 2D editor resolves to a 3D scene actor; a UMAP-derived layout flows into a force-directed update loop that constrains the 3D scene against the same per-URL collider radii used for the 2D placement.

This document is the synthesis of every design directive in the recent sessions. It is structured so each item can be implemented or referenced independently.

> **⚠ Status: HISTORICAL ANALYSIS-PLAN — SUPERSEDED (2026-05-30, see `USER_REQUIREMENTS_VERBATIM.md` §O.17).** The canonical design now lives in [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) + the [`frontend/`](frontend/) suite + `USER_REQUIREMENTS_VERBATIM.md` §M/§N/§O. This scheme's **additive operational details have been lifted into the design docs as features**: the UMAP target-sphere fit + hard collider + 1D-radial force (§2.1–§2.2 → `DOMAIN_MODEL.md` §6.1 / `frontend/projector.md` + `frontend/scan_streaming.md`); the 2D-UMAP-of-nomic ray-constrained layout (§6.4 → §7.3.2 / `frontend/editor.md`); the `↳` continuation rows + forward-truncated field names (§1.1 → §4.6 / `frontend/field_tree.md`, consistent with §O.4). **Outdated — do not implement:** the multi-section contenteditable panel anatomy of §1.1 (superseded by the dissolved **field-tree**, §4.5 / §9.6.1 — the panel is one recursive `name: value` tree, not separate html/rendered/fields/compiled sections); the **arrowhead** on the 2D↔3D "arrow" of §6.3 (now a **headless** yellow line, §O.16); the `cp/*.js` **Concrete File Surfaces** (§11) and **Implementation Order** (§12) (superseded by `FRONTEND_REDESIGN.md` §11 — the redesign assumes **no prior frontend code**). Read this doc for historical operational reasoning only, never as the implementation target.

---

## 1. The Unified Knowledge Panel

> Hovering over nodes and clicking them should stick the **exact same** knowledge panel that appeared when hovered, in the **exact same place** where it was hovering.

### 1.1 Panel anatomy (final)

*(Superseded §O.17: the separate sections below are replaced by the single **dissolved field-tree** — one recursive `name: value` tree — per `DOMAIN_MODEL.md` §4.5 / §9.6.1. The list below is historical; the forward-truncated field name + the `↳` continuation-row-for-deduplicated-aliases idea survive and are lifted into §4.6.)*

The knowledge panel is **one** widget with one anatomy, used identically for hover preview and click-pinning:

- **Header** — coloured by the node's hash hue; carries the panel title (URL-shortened or chunk last-2-xpath-segments).
- **xpath section** — monospace, breakable, slate-grey.
- **Content-distilled HTML** — preformatted, scrollable, **contenteditable** so the user can type `{var}` references.
- **Rendered text** — preformatted, scrollable, contenteditable.
- **Content-structure summary (fields)** — `<forward-truncated-xpath>: <value>` lines with `↳` continuation rows for deduplicated value aliases. Contenteditable.
- **Compiled rendering** — hidden until first Compile press; shows the post-substitution output of every editable section.
- **Footer** — `Compile` button + `Visit source` link.

The hover billboard (`#billboard`) renders this anatomy. The click-pinned panel renders the **same** anatomy. The transition from hover→pin is a freeze: the pinned panel materialises at the exact screen position the hover panel was occupying when the click fired.

### 1.2 Hover → click sequence

1. Mouse enters a 3D node → hover billboard appears next to the projected screen position, with the node's data.
2. Mouse moves to a different node → hover billboard updates in place, follows.
3. Mouse leaves all nodes → hover billboard hides.
4. Mouse clicks a node → the hover billboard's CURRENT screen rect is captured; a new draggable, multi-pinnable panel is spawned at that exact `(top, left)` with identical content; the hover billboard is then reset so it can preview a different node without conflict.
5. The pinned panel is independent: drag header, resize via corner handle, minimize, close, Compile.

### 1.3 Multi-pin stack

Each chunk click adds a new pinned panel. Clicking the **same** chunk twice doesn't duplicate — it raises the existing panel's z-order and un-minimises it.

### 1.4 Resize

Every pinned panel has `resize: both; overflow: hidden` on the outer container with `overflow: auto` on the body, so the user can drag the bottom-right corner to resize. Header/footer stay anchored; the editable `<pre>` blocks shrink/grow inside the body's flex column.

### 1.5 Curly-brace reference parsing

The user can type `{some_concept}` into any of the editable sections (html, rendered_text, fields). On `Compile`, every `{slug-shaped-ref}` is resolved against the live concept-graph (`_compileConceptNode(slug)`), with cycle-safe recursion. Unresolved refs are left literal.

### 1.6 Recursive structure decomposition

Compile must support **recursive decomposition of arbitrary nested data structures** — JSON, HTML element trees, indented key/value blocks — irrespective of syntax. The implementation: a single recursive descent that recognises:

- JSON-like blocks (`{`/`[` start, balanced delimiters) — parse as JSON, decompose top-level keys into child concept cards keyed by `<panel_id>__<key>`, rewrite parent's value as `{child}` references.
- Indented tree blocks (no syntax, just key/value lines with deeper indentation) — parse as a tree, same decomposition.
- Plain text — no decomposition, leave as-is.

The Compile button on the pinned panel walks the editable sections, decomposes any structured payload, and prints the post-substitution rendering to the read-only Compiled section.

---

## 2. 3D Layout: UMAP-Linear-Radial Force-Directed (Replaces Concentric Spheres Entirely)

> Our 3D concentric layout is still producing very uneven spheres for very large nodes.
>
> Umap only applies at the very end. We want the UMAP-forced-linear-radius layout to completely replace the concentric spheres entirely.

The previous Fibonacci-sphere / concentric-sphere layout is **removed**. Hub clusters interfered when their radii overlapped, and per-URL clustering couldn't account for cross-URL semantic structure. The replacement is the two-stage UMAP-linear-radial hybrid.

### 2.1 Stage A — UMAP as the layout initializer

Whenever the live TF-IDF store has ≥ 8 chunks, `/api/recompute_umap` produces a 3D coord per chunk. These coords are the **initial 3D positions** for those chunks — no Fibonacci, no hash. The current "Recompute UMAP" button effectively becomes the layout initialiser; in the final form, the same recompute fires automatically at the tail of every scan.

Coords are post-processed by:
1. **Fit to target sphere** — scale uniformly so the farthest point sits on a sphere of `TARGET_RADIUS` (configurable, default 25 units).
2. **Collider repulsion pass** — N iterations of pairwise push-apart with a uniform Lagrange-multiplier-style enforcement: every pair separated by less than `2·R · safety` gets pushed equally along their connecting vector. R is the billboard collider radius. No tail beyond hard collision distance.

### 2.2 Stage B — Force-directed along root-URL rays

After UMAP places chunks, each chunk is logically constrained to move only along the ray from its **root URL position** to its **initial UMAP position**. The constraint reduces the force-directed update to a 1D problem per chunk: a radial coordinate `r(t)` from the root URL.

Repulsive forces between chunk pairs are projected onto each chunk's ray and updated incrementally. New scans append chunks to the layout without disturbing earlier chunks' radial positions unless physically forced to.

This gives:
- **Stable positions** for already-laid-out chunks across scans (a chunk's azimuth/elevation from its root never changes once UMAP fixed it).
- **Collision-aware separation** — any new chunk that lands too close to an existing one is pushed along its own ray, not perpendicular.

### 2.3 Stage C — Per-URL bounding radius drives multi-scan placement

> All scans share a common root URL coordinate at the origin, which is incorrect.

Each URL workspace has its own root coordinate. The radius of the workspace (largest `r(t)` across its chunks) is tracked per-URL. When a new URL is scanned:

1. Compute the new URL's bounding radius from its initial UMAP layout.
2. Place the new URL's root coordinate at a distance equal to `existing_workspace_max_radius + new_workspace_radius + safety_gap` from the existing workspace centroid, along a direction chosen to minimise visual overlap (greedy: pick the direction least populated by existing workspaces).
3. Camera tweens to the new URL's root coordinate; the existing workspace stays at its absolute position.

### 2.4 Hard-boundary repulsion

> Adequate repulsive forces between node boundaries that are very sharp, such that the repulsion doesn't persist for some 1-sigma distance beyond the billboard lengths.

The repulsion in §2.1 is **hard** — exact push-to-collider-distance, no soft falloff tail. Two chunks at separation ≥ `2·R` exert zero force on each other; below that, they exert exactly enough force to reach `2·R · safety` in one step. The collider radius is a single shared constant so the inter-node spacing is URL-independent.

### 2.5 Latency handling

> Latency inconsistencies between UMAP updates to new chunks and streaming to the GUI and from the scanner are also handled gracefully throughout any edge cases.

Three streams converge at the GUI:
- **Chunk stream** (WebSocket) — new chunks arriving from the scanner.
- **UMAP coord stream** — `/api/recompute_umap` response after each scan finishes.
- **Force-directed update loop** — continuous on the client.

Rules:
- Chunks arrive with an initial **hash-direction placeholder** (a unit direction from the URL root sampled by , plus a radial distance that grows with chunk count). The placeholder is purely transient. Force-directed runs on whatever positions exist.
- A UMAP coord update replaces the placeholder for any matched chunk; UMAP-locked chunks (already received a UMAP coord) are skipped on subsequent placeholder relayouts.
- A chunk that arrives mid-UMAP gets the placeholder; the NEXT scan-end UMAP includes it. The user sees "snap" only at scan-end UMAP, never mid-stream.

---

## 3. Camera

> Camera zooms far too inwards into the dom and there are no proper bounds on the camera perspective to ensure that the entire scan is visible on the screen.

### 3.1 Hard zoom limits

- `minDistance` is `0.6 × clusterRadius` of the WORKSPACE under the orbit target (not a fixed 6). When the user dollies in, the camera stops at a distance where the cluster's surface is still visible.
- `maxDistance` is `3.0 × outermost_node_radius` (recomputed every frame from `init.position` extents) so the user can always pull back enough to frame everything but can never escape to infinity.

### 3.2 Frame-on-new-scan

On every scan completion, the camera tweens to:
- Centre point: the new URL workspace's root coordinate.
- Distance: `1.8 × new_workspace_bounding_radius`.

If `_userHasInteracted` is true AND the new scan's centre is still inside the camera's current view frustum, the tween is suppressed (don't yank a focused user).

### 3.3 Adaptive resize

The 3D canvas must resize with the viewport at the same rate the 2D overlay does:
- `window.resize` event → rAF-coalesced `onResize`.
- `ResizeObserver` on `#projector-panel` → same path.
- `setSize(w, h, updateStyle=false)` so the CSS rule `width:100%;height:100%` continues to drive layout.
- No no-change guard (the `updateStyle=false` setting breaks the historical ResizeObserver feedback loop at the source).

---

## 4. Retrieval Interaction

> Retrieval has a ton of bugs.

### 4.1 Hover preview

Hovering over a search result row shows the **same unified knowledge panel** (§1.1) for that chunk, positioned near the result row. No "root summary." If the hovered result is a doc-hub (page card), the panel shows the doc-hub's data (which includes URL, chunk_count, detected search field). If the result is a chunk-instance row, the panel shows that chunk's data.

The hover panel is shared across all hover sources (3D node hover, sidebar hover, search-row hover). One `#billboard` instance, content swapped on hover.

### 4.2 Click on a URL in the sidebar

> When I click on a url in the sidebar, all nodes explode outward.

A URL click on the workspace/domain sidebar does **two** things:
1. Toggles the doc-hub's collapse state — if currently collapsed (chunks folded into hub), uncollapses; if expanded, recollapses.
2. **Only the chunks of THAT URL** are affected. Other URLs' clusters stay in their current collapse state.

Crucially, the uncollapse is **scoped to visible retrieval rows** when a search is active: only chunks whose corresponding `.instance-row` is currently in the scroll viewport (via the `IntersectionObserver` spine) get popped. Chunks off-screen stay folded. When no search is active, the entire URL's cluster expands.

### 4.3 Visibility toggle (eye button)

> URL scan visibility buttons in the workspace 2D sidebar on the left do not hide/reveal the scanned DOMs.

The eye button calls `toggleUrlVisibility(wsId, url)`. The current bug: visibility is set via `_setInstanceVisible(id, false)` which writes `scale=0` to the instance matrix; the animate loop then over-writes that scale every frame based on frustum + sprite-replacement. So the hide is invisible.

Fix: track a per-URL `hidden` flag in workspace state; the animate loop reads this flag and forces `scale=0` for any node whose URL is hidden. The toggle just flips the flag — no need to touch the mesh directly.

### 4.4 Click on a search result row → fly + pin

Click on an `.instance-row` in the results panel:
1. Set `chunkCollapseTarget[id] = 0` so the chunk pops out of its hub (if collapsed).
2. Fly the camera to that chunk's 3D position.
3. Pin the chunk's knowledge panel using the unified click-and-stick mechanism.

Click on a `.page-card`:
1. Fly the camera to the doc-hub.
2. Drill down into the per-URL instance list (existing behavior).
3. Pin the doc-hub's knowledge panel.

### 4.5 Scroll-spine

Spine effect still applies — only chunks whose `.instance-row` is currently in the scroll viewport are popped out of their hub via `chunkCollapseTarget`. Rows off-screen → chunks fold back.

---

## 5. Workspace Sidebar

> Url scan visibility buttons in the workspace 2D sidebar on the left do not hide/reveal the scanned DOMs they are associated with.

### 5.1 URL row interactions (final)

- Click on URL label → toggle doc-hub collapse (§4.2).
- Click on eye button → toggle URL visibility (§4.3).
- Click on × button → remove URL from workspace AND purge from 3D scene (existing `_purgeUrlFromScene`).
- Hover on URL row → highlight matching hub sphere, show hover knowledge panel.

### 5.2 Domain section

The Domains accordion (`.domainTree`) lists every URL that's been scanned at least once, grouped by hostname. Clicking a URL there toggles its doc-hub collapse (same as workspace URL click).

### 5.3 Workspace switching

Switching the active workspace hides all hubs whose URL isn't in the new active workspace's `urls`. The animate loop respects the per-workspace `hidden` set just like the visibility toggle does.

---

## 6. 2D Concept Editor (interaction model)

> When I go to stick the combined node editor/knowledge panel to the 2D editor gui, I should be able to then click, drag, and resize the panels.

### 6.1 Pinned panel chrome

Same chrome as §1.1, plus:
- **Drag** — header is the drag handle.
- **Resize** — bottom-right corner via CSS `resize: both`. Outer panel has `overflow: hidden`, body has `overflow: auto` so resize compresses the body's editable `<pre>` blocks rather than letting them spill.
- **Minimise** — collapses the body, leaves only the header bar.
- **Close** — unpins from scene; the underlying 3D node remains.

### 6.2 Concept-graph edges

Solid SVG lines connect concept cards that reference each other via `{var}`. Lines update every frame via `_drawConceptEdges`.

### 6.3 3D ↔ 2D link arrows

Every pinned panel carries `data-3d-node-id="<chunk-id>"`. The animate loop calls `_drawConcept3DLinks` every frame, which projects each linked node's world position to screen coords and draws a solid yellow SVG **line (no arrowhead — §O.16)** from the panel's nearest border to the projected screen point. Off-frustum nodes hide their line. *(Updated §O.17: the 2D↔3D connector is a **headless** line, not an arrow.)*

### 6.4 Ray-constrained 2D concept-graph layout

When the user spawns multiple concept cards manually (via `+ New Concept`), the 2D editor lands them by a 2D UMAP of the concept-graph nomic vectors, recentred around the focal card. Each card's only degree of freedom is its radial distance from the focal card along the ray from focal to its UMAP position; azimuth comes from UMAP and never changes. Force-directed adjustment pushes overlapping cards apart along their individual rays — never tangentially. This mirrors the 3D approach in §2.2 exactly.

The hash-direction placeholder of §2.5 is the only surviving Fibonacci-style angular sampling in the system, and it is a transient by construction (used until the next UMAP refit). There are no concentric rings, no `R1`/`R2` radii, no depth-indexed shells.

---

## 7. Compile (recursive structure decomposition)

> Compile button on our duplicate knowledge panel cards … does not work.

### 7.1 Single recursive descent

The Compile button on any pinned panel or concept card runs a single recursive descent over the union of editable text in the panel:

1. Walk every `{slug-shaped-ref}` in every editable section.
2. For each, look up the referenced concept node in the 2D graph. If found, substitute its compiled value (recursive).
3. After substitution, check if the result is a JSON-like or tree-like nested structure.
4. If yes: decompose top-level into child concept cards keyed by `<panel_id>__<key>`. Rewrite the panel's relevant section as `{child_key}` placeholders. The next Compile press will substitute through the child cards.
5. If no: print the substituted result into the Compiled section.

### 7.2 Syntax independence

The decomposer is syntax-agnostic — same routine handles:
- JSON: `{ "key": value, … }` → child per key, value as child's data.
- Bracketed lists: `[a, b, c]` → child per index, value as child's data.
- Indented trees (no syntax, just indentation):
  ```
  parent
    child1: value
    child2
      grandchild: value
  ```
  Same decomposition.
- HTML element tree (parsed via the existing media-extraction parser): each element node → child, attributes folded as `@attr` children, text content as leaf.

The user never needs to think about syntax. The Compile just walks the structure.

---

## 8. Image Persistence (final)

> Images keep having to reload and are not properly persisted in their data stores.

### 8.1 Single-fetch path

The image loader does one fetch per URL per session-miss:
1. In-memory cache hit (`_imageTextureCache: Map<url, THREE.Texture>`) → return.
2. IndexedDB cache hit (`wfh_texture_cache.textures`) → blob → object URL → texture → return.
3. Network: `fetch(proxy_url)` once → blob → texture from blob's object URL; same blob saved to IDB.
4. On proxy failure, retry direct; on both failures, no-op.

The `X-Image-Proxy-Note` header signals the transparent-PNG fallback; the loader does NOT cache that as a "successful" image.

### 8.2 Texture sharing

Two chunks pointing at the same image URL share a single `THREE.Texture` instance — no duplicate decode, no duplicate GPU upload.

### 8.3 Image-billboard spacing

Sprite spacing is enforced by the same collider repulsion in §2.1. Billboards are guaranteed to be at least `2·R · safety` apart along any pair of nodes in the same workspace.

---

## 9. Multi-Scan Workspace Independence

> All scans share a common root url coordinate at the origin, which is incorrect.

### 9.1 Per-URL workspace state

Each scanned URL maintains its own:
- `root_position`: the 3D coordinate of its doc-hub.
- `bounding_radius`: max chunk distance from root_position.
- `umap_locked`: set of chunk-ids whose positions came from UMAP.

### 9.2 Independent placement

When a new URL is scanned:
1. Initialise its chunks at hash-direction placeholder positions around a temporary local origin.
2. Compute its bounding radius.
3. Determine the new root_position: somewhere outside every existing workspace's bounding sphere with a `safety_gap`. Choose the direction with the most empty space.
4. Translate every node of the new workspace by `new_root_position - 0` (since they were laid out around local origin).
5. Camera tweens to `new_root_position`.

### 9.3 Layout updates respect ownership

The placeholder/UMAP relayout for one URL never touches another URL's node positions. The `_umapLocked` mechanism plus the per-URL workspace state guarantees this.

---

## 10. Streaming Edge Cases

### 10.1 Chunk arrives mid-UMAP

Treated as a fresh chunk; gets a hash-direction placeholder position around its root URL. The next scan-end UMAP includes it.

### 10.2 UMAP returns no coord for a known chunk

Skip that chunk; its position is unchanged. (Backend skipped the chunk for vocab reasons.)

### 10.3 UMAP backend errors

Return early from `_applyUmapCoords`; no position is touched. The placeholder layout for the scan remains in place until the next successful UMAP.

### 10.4 Resize during scan

Resize handler runs synchronously per `window.resize` event; UMAP and chunk-add paths queue independently. No race — both write to `init.position` Maps with last-write-wins, and the animate loop reads `init.position` each frame.

---

## 11. Concrete File Surfaces

| File | Responsibility |
|---|---|
| `cp/animation.js` | Animate loop, camera bounds, resize, 2D↔3D arrow draw |
| `cp/instance_manager.js` | Node ordinals, hash-direction placeholder layout (transient only), per-doc relayout, scene-recenter |
| `cp/scanner.js` | WS stream → chunk events → addNodesIncrementally; UMAP recompute + post-processing |
| `cp/billboard.js` | Hover billboard + pinned panel (unified anatomy); pinBillboard freezes at hover position; Compile button |
| `cp/concept_graph.js` | Concept-graph editor, `{var}` parsing, _compileConceptNode, 2D↔3D arrow draw |
| `cp/search.js` | Retrieval panel, page-card click, instance-row click, spine observer |
| `cp/workspace.js` | Sidebar, URL visibility toggle, domain tree, workspace switching, `_purgeUrlFromScene` |
| `cp/interaction.js` | Raycasting, hover, selectNode, hover-billboard updates |
| `cp/sprite_manager.js` | Image loader (single fetch), IDB cache, collider-aware billboard spacing |
| `cp/layout.js` | `hashDirection` (placeholder direction only — previous `fibSphereUnit` / `docShellRadius` / `clusterRadius` are removed) |

---

## 12. Implementation Order (recommended next sprint)

1. **Unified hover ↔ click panel** — single template, freeze-at-hover-position on click.
2. **3D canvas resize** — verify ResizeObserver path actually fires on every viewport change.
3. **Camera zoom bounds** — proper min/max per-frame.
4. **Resizable pinned panel** — CSS resize handle + body overflow handling.
5. **URL visibility toggle** — per-URL hidden flag honored by animate loop.
6. **Retrieval cleanup** — no root summary, hover preview uses unified panel, URL click toggles only visible chunks.
7. **Recursive compile** — syntax-independent decomposition.
8. **Multi-scan independent origins** — per-URL `root_position`, camera tweens to newest.
9. **Force-directed + UMAP hybrid (replacing concentric spheres entirely)** — UMAP initialises, force-directed converges along root-rays. The hash-direction placeholder is the only transient.

Each item is independently testable. The order is roughly impact-descending: items 1–7 fix the visible bugs reported across the recent sessions; items 8–9 are the architectural rewrite that closes the open layout-quality complaint.

---

## 13. Acceptance Criteria (per item)

| Item | Acceptance |
|---|---|
| Unified panel | Clicking a node hover-billboard freezes a draggable panel at the same screen rect; content is identical pre/post click. |
| 3D resize | Window resize → `#projector-panel` size changes → canvas framebuffer changes → camera aspect updates → scene re-renders at the new aspect every animate frame. |
| Camera bounds | Cannot zoom inside any sphere; cannot pull farther than 3× outermost node radius. |
| Resizable panel | Drag bottom-right corner shrinks/grows panel; body overflow scrolls; header stays. |
| URL visibility | Eye-off → every chunk and hub of that URL has `scale=0` next frame and stays so until eye-on. |
| Retrieval | URL click toggles its hub's collapse state without touching others; result hover shows unified panel near the row; row click flies + pins. |
| Recursive compile | A panel with JSON-like data compiles into N child concept cards, each one further compileable; the parent's Compiled rendering recomposes byte-equivalent to the original JSON. |
| Multi-scan | Two scans of different URLs sit in two separated regions with no overlap; camera tweens to the most recent scan. |
| Force-directed/UMAP | After scan-end, every pair of nodes is at least `2·R · safety` apart; chunks move only along their root-ray (no tangential drift). |
