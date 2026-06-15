# Frontend — Real Organ (Projector · chunk_field · texture_cache)

> **Owns:** the 3D canvas, the scan-streaming render pipeline, and the image cache. Modules: `fe/real/projector.ts`, `chunk_field.ts`, `texture_cache.ts`. Design: §5 / §6.6 / §11.2 / §18.1 / §18.2 + `frontend/{projector,scan_streaming}.md`. Realises `code_constraints/frontend_rendering.md`. **Renders the backend's 6-vectors — computes no layout** (backend/layout.md).

---

## §1 — Responsibility

Project the workspace's chunks into the Real register (Three.js). Consume `chunk_added` / `umap_canonical` frames and animate toward the canonical 6-vectors. Render the HSV phase, the hard collider, viewport-driven spine extrusion, and the agent-output perimeter. **3D nodes + billboards are the only filled/colored pixels** in the whole UI (the theme exception — everything else is black-core + silver-outline, `frontend/theme.md`).

---

## §2 — Public Surface

```ts
Projector.animate(): void                 // one rAF tick (driven by pulse/raf.ts)
Projector.project(world_pos): ScreenPoint // 3D → screen (drives the 2D↔3D connector, membranes.md)
ChunkField.upsert(chunk_id, frame_data): void   // keyed by STABLE integer chunk_id (§9.4)
TextureCache.get(url): Promise<Texture>
```

---

## §3 — Internal Logic

### §3.1 The animate tick (per frame, §5.5)
```
advance interruptible tweens (pulse/tweens.ts)
recompute camera bounds: min = 0.6·cluster_radius, max = 3·max|pos|
apply HSV phase: hue = (camera_azimuth + chunk_hsv_h) ; s,v from the 6-vector
hard collider pass (SAFETY ≥ 2) — match the backend's collider so frames agree
visibility flags: hidden_urls → scale 0 (NEVER mutate/remove the mesh, §6.3)
spine extrusion: viewport_visible_rows → extrude those chunks radially from the doc-hub; scroll-past re-hides
agent-output perimeter: provenance==agent-output → outer-envelope render (backend rescaled radial, layout.md)
```

### §3.2 Scan streaming (§18.1 / §18.2)
```
chunk_added  → Reconciler enter at the preliminary radial placeholder THIS frame (pulse.md)
umap_canonical → RETARGET tweens FROM the current interpolated position (never restart, never snap)
```
The placeholder hash-direction position is transient only; the canonical 6-vector is authoritative the moment it arrives. Frames are dual-routed to the workspace socket (spine.md / backend layout.md §3) — the projector never depends on a per-snapshot socket.

### §3.3 chunk_field + texture_cache
`ChunkField` keys instances by the **stable integer chunk_id** (§9.4) so reconciliation is minimal (adding the 501st chunk doesn't touch the first 500, pulse.md). `TextureCache` is a single fetch path: **mem → IndexedDB (`wfh_texture_cache.textures`) → proxy → direct**; **never cache the transparent-PNG fallback** (§11.2) so a transient failure can re-resolve.

---

## §4 — Dependencies

- **Calls:** the store (`chunks`, `layout`, `ui` slices — read-only), `pulse/` (tweens + raf + reconciler), Three.js.
- **Called by:** `pulse/raf.ts` (the single loop drives `animate`); `Billboard` reads hover hits from the projector's raycast (membranes.md).

---

## §5 — Excluded

- The HSV/theme palette derivation (`frontend/theme.md`); the layout algorithm (backend/layout.md — the client only renders + collides to match). The Real-register philosophy.
