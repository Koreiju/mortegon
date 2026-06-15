# Spec — Frontend / Real Organ (Projector · chunk_field · texture_cache)

> Deepens [`code_architecture/frontend/real.md`](../../code_architecture/frontend/real.md). Modules: `fe/real/{projector,chunk_field,texture_cache}.ts`. Constants: [`../constants.md`](../constants.md) §1/§8. Renders the backend's `Vec6` — computes no layout.
>
> **Realized form (cp/*.js).** Greenfield `fe/real/*.ts`; realized in `chunk_projector.js` + `cp/animation.js` (Three.js scene/RAF, black background, camera-azimuth content-HSV hue rotation via `setHSL`), `cp/instance_manager.js` (InstancedMesh pools + `umapHsl` content-HSV), `cp/hsv_color.js` (pure 6-vector→HSL + azimuth→phase maths, unit-tested), `cp/node_loader.js`, `cp/sprite_manager.js` (image billboards / IDB texture cache), `cp/force_layout.js` (consumes `umap_canonical` 6-vectors) — see `frontend/{projector,scan_streaming}.md`. Verified via `6d-umap-format`, `node cp/hsv_color.test.mjs`, `scan-streaming-routes-to-workspace-ws`.

---

## §1 — `Projector`

```ts
class Projector {
  animate(): void                    // ONE rAF tick (called by pulse/raf.ts)
  project(world: [number,number,number]): { x: number; y: number }   // 3D → screen px
  raycastHover(px: number, py: number): ChunkId | null
}
```
- **`animate` (per frame):**
```
Tweens.advance(now)                                              # pulse.md
cameraNear = CAMERA_MIN_FACTOR * clusterRadius
cameraFar  = CAMERA_MAX_FACTOR * max(|pos|)
for each chunk mesh m keyed by ChunkId:
   v6 = store.layout.per_chunk[id]
   m.hue = (cameraAzimuth + v6[3]) mod 1 ; m.sat = v6[4]; m.val = v6[5]    # HSV phase
hard collider pass (HARD_COLLIDER_SAFETY_FE) to match backend frame
for url in store.layout.per_url: if store.ui.hidden_urls has url → set member scale 0 (NEVER remove mesh, §6.3)
dominance collapse (§6.6.5/§7.3.5, Q.3–Q.5): for (node_id, dc) in store.ui.dominance_collapse where dc.collapsed:
   for hid in dc.hidden_set → set scale 0 (the isolate; NEVER remove mesh)
   fold dc.folded_set into the dominator node_id (root-URL hub or bisector compute node)
   # re-expand = entry cleared → meshes return next frame; fold-state preserved (M.6)
spine extrusion: for id in store.ui.viewport_visible_rows.ordered → extrude radially from doc-hub; others retract
agent-output perimeter: provenance==AGENT_OUT → render on outer shell (radial set by backend, layout.md)
```
- **`project`** — standard camera projection; feeds the 2D↔3D connector (membranes.md), recomputed each frame.
- **Right-click dominance collapse (§6.6.5, Q.3–Q.5)** — a right-click raycast (`raycastHover` reused on the contextmenu event) that lands on a **dominator** mesh (root-URL doc-hub or bisector compute node) fires `ui-dominance-collapse`/`-expand` (gesture_gateway.md); the resulting `dominance_collapse` mirror drives the animate-loop `scale=0` isolate above. A right-click on a non-dominator chunk is a no-op (only dominators carry a dominated set). Distinct from the sidebar left-click (§18.12).
- **Theme exception** — chunk meshes + billboards are the **only** filled/colored pixels (frontend/theme.md).

---

## §2 — `ChunkField`

```ts
class ChunkField { upsert(id: ChunkId, frame: { v6: Vec6; image_url?: string; provenance: Provenance }): void;
                   remove(id: ChunkId): void }
```
- Keys instances by the **stable integer `ChunkId`** (§9.4) → reconciliation is minimal (501st chunk doesn't touch the first 500, pulse.md). On `upsert`: ensure mesh exists; `Tweens.to(mesh.position, v6[:3])` (retarget, never snap); request texture (`TextureCache.get(image_url)`).
- On `chunk_added` (preliminary placeholder) → enter at placeholder this frame; on `umap_canonical` → retarget from current position (real-time scan stream, §18.1/§18.2).

---

## §3 — `TextureCache`

```ts
class TextureCache { get(url: string): Promise<Texture> }
```
- **Single fetch path:** mem `Map` → IndexedDB (`IDB_TEXTURE_STORE`) → CORS proxy → direct. On success: cache in mem + IDB. **On failure: return the transparent-PNG fallback but NEVER cache it** (§11.2, errors.md §2) — so a transient failure re-resolves next request.

---

## §4 — Excluded
HSV palette / theme (`frontend/theme.md`); the layout algorithm (backend/layout.md — client renders + collides to match); the Real-register philosophy.
