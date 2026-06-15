# Projector — The Real Canvas

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §5.** The 3D surface is carried by `chunk_projector.js` + `cp/animation.js` (scene/RAF loop, black background, the per-frame **camera-azimuth content-HSV hue rotation** via `setHSL` from `init.umapHsl` + `azimuthToHuePhase`, with provenance tint lerped on top; pure maths in `cp/hsv_color.js`), `cp/instance_manager.js` (InstancedMesh pools + bootstrap `umapHsl` assignment), `cp/node_loader.js`, `cp/sprite_manager.js` (image billboards / sprite replacement — the theme exception zone), and `cp/force_layout.js` (the UMAP-linear-radial force-directed convergence; `umap_canonical` 6-vectors — position **and** HSV — are consumed in `cp/scanner.js::_applyUmapCoords` → `cp/instance_manager.js`, and force_layout refines positions along the root-URL rays). Verified by `6d-umap-format`, `node cp/hsv_color.test.mjs`, `scan-streaming-routes-to-workspace-ws`, `ui-collapse-toggle`.

---

## §1 — Identity

`Projector` renders the workspace's TF-IDF chunk manifold as live geometry — the **Real register** (§1.5). It shows every chunk the workspace has indexed: scanner-emitted (manifold interior) and computation/agent-emitted (outer perimeter, §6.6.1). **Concept cards never appear in 3D**; the only coupling to the Imaginary is via the membranes (`billboard.md`, `halo.md`, `link_layer.md`). The Projector **computes no coordinates** — it reads canonical 6-vectors from the store's `layout` slice and renders them (§2.1, §1.4-FR.5). It holds the **full per-sample distribution** of every scan; a 2D compute node holds only a **reference** into this 3D-resident set and renders the current signal (§O.6/§O.7, §6.6.3). Advancing the 2D per-sample stepper **drives the 3D focus** (one-way 2D→3D): the corresponding chunk flies/highlights while the projector keeps showing the whole distribution (`scan_streaming.md`).

---

## §2 — Structure

A Three.js scene: an `InstancedMesh` chunk field keyed by **stable integer chunk id** (§9.4); per-URL doc-hub instances; the single hover `Billboard` (`billboard.md`); the camera + orbit controls; the clear-colour `--bg-void`.

**Owns (transient):** per-chunk tween state (current + target positions, eased); the current camera azimuth (drives HSV phase); the active `hidden_urls` set read each frame; per-frame camera bounds. **Reads from `WorkspaceStore`:** `chunks` (url, layout6d, image_url, provenance), `layout` (per-chunk 6-vectors + per-url roots), `ui.hidden_urls`, `ui.viewport_visible_rows`, `ui.pinned_billboards` (to draw the link arrow target). No chunk truth lives here.

---

## §3 — Composition

| Peer | Through |
|---|---|
| `WorkspaceStore` | reads `chunks` / `layout` / `ui.hidden_urls` / `ui.viewport_visible_rows` |
| `scan_streaming.md` | the incremental add + UMAP-tween pipeline this canvas runs |
| `Billboard` (`billboard.md`) | hover preview + the freeze-at-rect capture (Real→Imaginary) |
| `Halo` (`halo.md`) | reads chunk world-positions + HSV for ray-projection |
| `LinkLayer` (`link_layer.md`) | the 2D↔3D yellow arrow targets a chunk's projected screen point |
| `TextureCache` (§9) | image billboards |
| `Reconciler` / tweens (`liveness.md`) | keyed enter/update/exit on the InstancedMesh; interruptible tweens |

---

## §4 — Behaviours: the three placement states (§6.1)

Each chunk moves through three monotone states; the Projector renders only the transitions (the math is backend, §9.3):

| State | Trigger | Render action |
|---|---|---|
| **Preliminary radial** | `chunk_added` arrives | add an instance immediately at `hash(chunk_id)` unit-direction from the URL root, distance `R·(1+n/k)` — no wait for UMAP (instant scan feel, `scan_streaming.md`) |
| **UMAP-locked canonical** | `umap_canonical` frame | tween to canonical `(x,y,z)` over ~600 ms, eased, **interruptible** (`liveness.md` §2) |
| **Radial-slide refined** | collider violation in animate | slide a locked chunk along its root-URL ray to resolve overlap |

The hash-direction placeholder is the only surviving Fibonacci-style angular sampling and is transient by construction (§18.2); no path uses it as final authority.

---

## §5 — Behaviours: the per-frame animate-loop invariants (§5.5-FR)

One rAF tick (shared budget, `liveness.md` §5), in order:

1. **Advance tweens** (interruptible; retarget from current position, never restart — §18.2 / `scan_streaming.md`).
2. **Camera bounds, recomputed per frame (§6.2, §18.18):** `minDistance = 0.6 × cluster_radius(orbit_target)`, `maxDistance = 3 × max(|pos|)`. Scroll-zoom unrestricted; cannot zoom inside a sphere, cannot escape to infinity.
3. **HSV phase (§8.2.1.2, frontend_rendering §1.8):** apply `(camera_azimuth_phase + chunk_hsv_phase)` to every visible chunk's fill and to every HSV-bearing halo phantom; period default 60 s, **workspace-configurable** (frontend_rendering §2.10).
4. **Hard collider repulsion (§18.3):** `COLLIDER_SAFETY ≥ 2.0`; min pair distance `2·R·safety`; collider radius **shared** between image and text billboards.
5. **Visibility flags (§6.3, §18.14):** read `ui.hidden_urls`; write `scale=0` to every chunk/hub of a hidden URL. **Visibility is a flag, never a mesh mutation** — the intrinsic scale is never touched. **Also read `ui.dominance_collapse` (§6.6.5, Q.3–Q.5):** for any `collapsed:true` entry, write `scale=0` to every node in its `hidden_set` (the isolate) and fold its `folded_set` into the dominator — same flag mechanic, never a mesh mutation. Re-expand clears the flags and the chunks/nodes return next frame.
6. **Spine extrusion (§6.4):** read `ui.viewport_visible_rows`; `chunkCollapseTarget=0` for viewport-visible rows extrudes them radially from the doc-hub; off-viewport fold back (`retrieval_and_sidebar.md`).
7. **Perimeter placement (§6.6.1, §18.23):** agent-output chunks render on the outer-envelope shell (angular from UMAP, radial rescaled) so interior reads as observations, perimeter as syntheses.

**Adaptive resize (§6.2, §18.9, frontend_rendering §1.12):** `window.resize` (rAF-coalesced) AND `ResizeObserver` on the projector panel both fire `onResize`; `setSize(w,h,updateStyle=false)`; **no no-change guard**.

---

## §6 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Hover a chunk | `ui-hover` | Billboard preview at projected rect (`billboard.md`) |
| Click a chunk | `ui-pin` | freeze-at-rect pin into the Editor (`billboard.md`, `editor.md`) |
| Orbit / zoom | (local controls) | camera move; bounds per frame; frame-on-scan tween on `umap_canonical` |
| Toggle URL visibility | `ui-url-visibility` | `hidden_urls` flag → `scale=0` next frame |
| **Right-click a dominator node** (root-URL hub or bisector compute node) | `ui-dominance-collapse` / `-expand` | **rank-dominance collapse/isolate** (§6.6.5, Q.3–Q.5): fold the dominator's dominated set + hide every other node (`scale=0`), leaving only the dominator; right-click again → re-expand. Membership = dominated-set over the `ConceptEdge` graph (DOMAIN §8.1.2). **Not** the §6.4/§18.12 sidebar left-click. |
| Recompute UMAP | `recompute-umap` | `umap_canonical` → tween to new positions |
| Open halo on a stuck panel | `ui-halo-focus` | ray-projection of neighbours (`halo.md`) |

---

## §7 — Sequences

### §7.1 Scan (see `scan_streaming.md` for the full pipeline)
```
web-scan → chunk_added × N (preliminary radial, added this frame)
   → umap_canonical (mid-scan + scan-end) → interruptible tween to canonical 6D
   → done → camera frame-on-scan tween (suppressed if user interacted & root in frustum)
```
### §7.2 Visibility toggle (§6.3)
```
ui-url-visibility {url, hidden:true} → ui_state_changed → hidden_urls += url
   → next animate frame writes scale=0 to that URL's chunks/hubs (no mesh mutation)
```
### §7.3 Purge (§6.5)
```
purge_workspace frame → store resets chunks/layout → Reconciler exits every instance → scene empties in one paint (§18.4)
```

---

## §8 — Data

**Reads:** `chunks` (`{url, layout6d:[x,y,z,h,s,v], image_url?, provenance}`), `layout` (per-chunk 6-vec, per-url `{root, radius, locked, hidden, accessors}`), `ui.hidden_urls`, `ui.viewport_visible_rows`. **Frames consumed:** `chunk_added/replaced/removed`, `chunks_partial`, `umap_canonical`, `purge_workspace`. **Emits:** `ui-hover` / `ui-pin` (via Billboard); no concept mutation of its own.

---

## §9 — `TextureCache` (sub-object) — single image fetch path

One path (§11.2, frontend_rendering §1.13, §18.10): in-memory `Map<url, THREE.Texture>` → IndexedDB blob cache → `fetch(proxy_url)` → `fetch(direct_url)`. The `X-Image-Proxy-Note` transparent-PNG fallback is **never cached** as a successful image. Two chunks at the same URL share one `THREE.Texture`. Textures persist for the full layout lifetime — no reload churn.

---

## §10 — Results

A live 3D manifold: HSV-coloured (or image-textured) chunks at canonical positions, doc-hubs, slowly rotating colour in lockstep with camera azimuth, viewport-scoped spine extrusion, agent outputs on the perimeter. Telemetry: hover/pin via the Billboard; the `scan` / `visible 3D` / `hidden 3D` viewer rows are fed from `chunks` + `viewport_visible_rows` (§11.8).

For each compiled computation graph the manifold also carries a single **bisector node** — placed between the (hidden) input 6D-UMAP centroid and the **dynamically-updated** output centroid (§6.6.4, P.10), clickable to open/close the graph in the Editor — plus a **UMAP-independent link network** (plain lines carrying **no** coordinate state, distinct from the `link_layer.md` 2D SVG) tying root urls → their chunk-sample nodes, and root / click-sticked inputs **and** every perimeter readout → the bisector node (P.8 / P.9). Perimeter **readout** nodes (§7.8.2) arrive as **delta updates** to the scene (§7.8.3, async per §7.8.3 / P.6–P.7) and, lacking an image billboard, show liveness by **passive physical + HSV rotation** (P.4, `6d_umap.md`).

---

## §11 — REPL Mirroring

The Projector's observable state feeds three in-place viewer rows (§11.8): `scan` (chunk counts + UMAP status), `visible 3D` (`viewport_visible_rows.ordered`), `hidden 3D` (complement against the chunk set). REPL actions `web-scan`, `recompute-umap`, `ui-url-visibility`, `ui-row-click` drive the same geometry a user would; `sim_frontend.py watch` observes `chunk_added`×N → `umap_canonical` → `done` on the workspace WS (the §18.1 severance check).

---

## §12 — Theme

**The exception zone.** Clear-colour `--bg-void` (true black) so HSV chunks are maximally legible. **Chunk nodes and billboards carry saturated HSV fill / image texture (`theme.md` §2.5) — the only saturated colour and imagery in the whole interface.** Doc-hubs: `--steel-700` wireframe rings (steel, not coloured). Any HUD/overlay text: `--text-dim`, monospace. The 2D↔3D arrow that terminates on a chunk is `--accent-arrow` yellow (drawn by `link_layer.md`). Everything framing the 3D — the panel housing the canvas, the sidebar beside it — is steel-on-black; only inside the viewport, and only the nodes/billboards, break the monochrome.

---

## §13 — References

- `DOMAIN_MODEL.md`: §6 (projector), §6.1 (UMAP-radial-force hybrid + 6D), §6.2 (camera), §6.3 (visibility), §6.4 (spine), §6.6.1 (perimeter), §6.6.4 (bisector compute-graph node + projector link network), §7.8.2 / §7.8.3 (perimeter readout delta-stream + passive rotation), §8.2.1.2 (HSV), §9.4 (stable ids), §11.2 (textures); anti-goals §18.2/§18.3/§18.9/§18.10/§18.14/§18.18/§18.23.
- Object doc: [`../object_model/Projector.md`](../object_model/Projector.md) (reconcile to this).
- Peers: `scan_streaming.md`, `billboard.md`, `halo.md`, `link_layer.md`, `liveness.md`.
