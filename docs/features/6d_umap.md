# Feature: 6D UMAP (3 Position + 3 HSV Slowly Rotating)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §6.1 (layout pipeline with 6D fit), §8.2.1.2 (the HSV rotation matched to camera azimuth), §1.2.2 verbatim (*"umap projections are supposed to be 6d, 3 for hsv that are then slowly rotated similar to how the 3D rotates"*), §6.6.1 (perimeter-encompassing rescale applies to position triplet), §7.8.3 (passive-state physical + HSV rotation of billboard-less readout nodes).

**Status.** Realised. The UMAP fit is 6D (`n_components=6`, 3 position + 3 HSV) — `LayoutService` emits `umap_canonical` with a 6-vector per chunk + per-URL roots (the legacy 3-vector format migrates on load), and the renderer-side phase loop IS in `animation.js`. The chunk fill colour is now the **UMAP content-HSV** (coords[3:6] → `init.umapHsl`, threaded by `cp/scanner.js::_applyUmapCoords`), rendered via `THREE.Color.setHSL` and rotated each frame by a **camera-azimuth hue phase** (`azimuthToHuePhase`, one hue cycle per orbit; the effective azimuth combines OrbitControls `getAzimuthalAngle()` with the world auto-spin `t·spatialVelocity.y` ≈ 60 s/rev, frozen while a panel is pinned). The phase maths lives in the pure, THREE/DOM-free `cp/hsv_color.js` (`umap6ToHsl`, `azimuthToHuePhase`, `applyHuePhase`, `hslToRgb`). This **replaced** the prior realized state — a time-driven `colorMatrix` RGB-space tumble over a *hash/position-derived* `umapColor` that **discarded** the backend's HSV channels (the `xyz.length !== 3` guard in `_applyUmapCoords` even rejected every 6-vector, stranding chunks at hash-bootstrap). **Verification split (DOMAIN_MODEL §6.1):** the backend 6-vector format + HSV `[0,1]` is locked by `6d-umap-format` (full-smoke); the pure colour maths by `node cp/hsv_color.test.mjs`; the continuous rotation itself is render-only (no REPL observation surface — no scenario claims it).

---

## §1 — What the user sees

Every chunk in the projector has both a position and a colour that come from the same UMAP fit. The position is the chunk's place in the manifold; the colour is its UMAP-derived hue / saturation / value. As the user rotates the projector view by orbiting the camera, the chunk colours rotate slowly with the orbit — relative-colour relationships stay constant at any instant, but the colour encoding shifts continuously across observation angle. A chunk's visual identity is therefore not a static label but a continuous transformation; a chunk's hue at one camera position differs from its hue at another but the *relationships* between chunk hues are preserved.

The HSV rotation also propagates into the halo: collapsed-singular phantoms on the halo's conic surface carry their parent chunk's HSV state, so as the user rotates the projector, the halo phantoms rotate in lockstep with the parent chunks (§8.2.1.2 + §8.2.1.1). This visual continuity makes manifold neighbourhoods recognisable across the dimensional collapse from 3D to 2D and back.

The same HSV rotation is how **type-only readout nodes** — the computation graph's perimeter readouts (§7.8.2 / §7.8.3) that have **no image billboard** — show liveness in **passive state** (P.4): physical + colour rotation from the 4–6 UMAP dims stands in for a billboard. A readout streamed to the projector as a **delta** (§7.8.3 / §6.6.4) is therefore immediately legible as a rotating coloured node even before it carries any image.

---

## §2 — Cross-objects

| Object | Role |
|---|---|
| [`LayoutService`](../object_model/LayoutService.md) | Fits the 6D UMAP; persists the 6-vectors in LayoutFrame |
| [`LayoutFrame`](../object_model/LayoutFrame.md) | Stores per-chunk `(x, y, z, h, s, v)` |
| [`GlobalTfidfStore`](../object_model/GlobalTfidfStore.md) | The TF-IDF input the UMAP fits over |
| [`Projector`](../object_model/Projector.md) | Frontend renderer; applies HSV phase per animate frame |
| [`Halo`](../object_model/Halo.md) | Collapsed-singular phantoms inherit HSV from parent chunks |
| [`ApparitionService`](../object_model/ApparitionService.md) | Annotates ray-projected candidates with HSV state from LayoutFrame |

---

## §3 — Gestures

| Gesture | REPL action | Effect |
|---|---|---|
| Trigger a UMAP refit | `recompute-umap { workspace_id? }` | Layout Service joint 6D fit; `umap_canonical` broadcast |
| (implicit) Scan-end refit | (automatic on every scan completion) | Full 6D fit over the workspace's full TF-IDF index |
| (implicit) Incremental mid-scan refit | (automatic every K chunks during scan) | Incremental 6D fit; `umap_canonical` broadcast |
| (implicit) Camera orbit | (frontend gesture; no REPL mirror — purely visual) | HSV phase rotates per animate frame |

---

## §4 — State machine — the fit

```
trigger (scan-end / incremental K-chunk threshold / manual recompute-umap)
   │
   ▼
GlobalTfidfStore.get_full_index(workspace_id) → matrix
   │
   ▼
UMAP.fit_transform(matrix, n_components=6)
   │
   ▼
post-processing (in order):
   ▼  per-URL centroid translation (position triplet only)
   ▼  per-URL bounding-radius scale (position triplet only)
   ▼  hard collider repulsion N iterations (position triplet only)
   ▼  HSV phase calibration (so brightest hue cluster anchors the canonical origin)
   ▼  perimeter-encompassing rescale for agent-output chunks (§6.6.1; position triplet only)
   │
   ▼
LayoutFrame.coords updated with 6-vectors per chunk
   │
   ▼
LayoutFrame persisted (per-workspace JSON file)
   │
   ▼
WS umap_canonical broadcast carries the 6-vectors to every workspace WS subscriber
   │
   ▼
frontend tween: chunks animate from preliminary positions to canonical positions over ~600 ms
   │     ▼  HSV state stored per chunk; renderer applies phase per animate frame
   │
   ▼
per animate frame (60 Hz):
   ▼  compute camera_azimuth_phase = camera_azimuth_radians / (2π) * rotation_period_factor
   ▼  for each visible chunk: apply (camera_azimuth_phase + chunk_hsv_phase) to fill colour
   ▼  for each visible halo phantom with hsv field: same phase computation
```

---

## §5 — WS frames + telemetry

| Frame | Carries |
|---|---|
| `umap_canonical` | `coords: dict[chunk_id, (x, y, z, h, s, v)]` + `url_roots` + `bounding_radii` |
| (no per-frame WS frame for HSV rotation — purely visual; renderer-driven) | — |

---

## §6 — Acceptance bar

The 6D UMAP feature is realised when:

- `recompute-umap` REPL action triggers a refit and broadcasts a `umap_canonical` frame whose `coords` carry 6 floats per chunk (not 3).
- Inspection of the persisted LayoutFrame file shows the 6-vector format.
- Migrating an existing 3-vector LayoutFrame on first load triggers an HSV-only refit (re-deriving HSV from the TF-IDF index) — no data loss.
- The `live-scan-real-with-cleanup` probe (§16.5) asserts the 6-vector format on every `umap_canonical` frame the scan emits.
- Per-frame inspection of the projector shows chunk fill colours rotating with camera azimuth (the rotation period defaults to 60 seconds; configurable per workspace).
- Halo phantoms with `hsv` annotation rotate in lockstep with their parent chunks (camera-azimuth-driven, not independent).

---

## §7 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| Fitting UMAP with `n_components=3` (position only — legacy) | §18 (the 6D contract is the integration target) |
| Running a separate UMAP for colour | §6.1 — position + colour jointly fit |
| Ray-projection mismatched HSV | §18.26 |
| Skipping the perimeter rescale on the position triplet | §18.23 |

---

## §8 — Code constraints

- [`backend_services.md`](../code_constraints/backend_services.md) — LayoutService 6D fit invariants.
- [`ws_frames.md`](../code_constraints/ws_frames.md) — `umap_canonical` frame schema carries the 6-vector.
- [`frontend_rendering.md`](../code_constraints/frontend_rendering.md) — animate-frame HSV phase loop matched to camera azimuth.
- [`persistence.md`](../code_constraints/persistence.md) — LayoutFrame storage format; legacy migration path.

---

## §9 — Cross-features

- [`halo_retrieval.md`](halo_retrieval.md) — the halo's HSV-rotating phantoms inherit from this feature.
- [`perimeter_outputs.md`](perimeter_outputs.md) — the position triplet's perimeter rescale composes with the 6D fit.
- [`live_scan_streaming.md`](live_scan_streaming.md) — incremental refits during scan emit 6-vector `umap_canonical` frames.
