# Scan Streaming — The Live 3D Update Pipeline

> **Status: realised (cp/*.js); implements `FRONTEND_REDESIGN.md` §5.4.** The live-update pipeline is carried by `cp/scanner.js` (`triggerScan` + the per-snapshot WS stream: `chunk_added` → `chunk_instances_partial` → `umap_canonical` → `done`) feeding `cp/node_loader.js::addNodesIncrementally` + `cp/force_layout.js` (the UMAP-linear-radial refit) for the *smooth, fluid, live* 3D updates. Routes to the workspace WS (dual-route §18.1). Verified by `scan-streaming-routes-to-workspace-ws`, `scanner-to-concept-roundtrip`.

---

## §1 — Identity

Scan streaming is the choreography by which a live `WebBrowser.scan` (§9.5.1, §15) becomes smoothly-settling 3D geometry. Its defining property is that it is **incremental, keyed, and interruptible end-to-end**: chunks appear the instant they stream, drift to their semantic UMAP positions as refits land mid-scan, and re-settle without jank when a new URL perturbs the frame. It is not a separate object — it is the `Projector` + `Reconciler` + tween scheduler + `FrameBus` backpressure rules acting together under one frame budget.

---

## §2 — Structure

The pipeline spans: `FrameBus` (ordered/backpressured frame intake, `frame_bus.md`); `WorkspaceStore.chunks` + `.layout` (the growing truth, `workspace_store.md`); the `Reconciler` (keyed enter/update/exit, `liveness.md` §1); the tween scheduler (interruptible eased motion, `liveness.md` §2); the `Projector` animate loop (`projector.md` §5); and `TextureCache` (image billboards, `projector.md` §9). No new state is owned; the pipeline is a discipline over these.

---

## §3 — Composition

| Peer | Role in the pipeline |
|---|---|
| `FrameBus` | delivers `chunk_added`×N → `umap_canonical` (mid-scan + scan-end) → `done`, ordered + backpressured |
| `WorkspaceStore` | accumulates `chunks` and the latest `layout` |
| `Reconciler` | one InstancedMesh *enter* per new chunk; *update* on refit; *exit* on purge |
| tween scheduler | interruptible, retargeting position tweens (the smoothness) |
| `pattern_map_and_url_set.md` | the scan's `pattern_map` output panel materialises live in parallel |
| `retrieval_and_sidebar.md` | result rows render collapsed-hidden; spine extrudes viewport rows |

---

## §4 — Behaviours: the four properties that make it fluid

1. **Instant preliminary placement.** On `chunk_added`, the Reconciler *enters* one InstancedMesh slot at its preliminary radial position **this frame** (`projector.md` §4). Existing instances are untouched (keyed diff, not rebuild) — adding the 501st chunk does not touch the first 500.
2. **Mid-scan refits, not scan-end-only (§16.5).** `umap_canonical` frames arrive *during* the scan as the LayoutFrame refits incrementally, plus a final fit at scan-end. Each retargets affected tweens.
3. **Interruptible retargeting (the anti-jank rule).** A `umap_canonical` that lands mid-tween retargets **from the current interpolated position**, never restarting from preliminary. The motion reads as one continuous settling, not a stutter on every refit (`liveness.md` §2).
4. **Backpressure keeps the freshest layout (§2.4).** Under a fast scan, `FrameBus` drops stale `chunks_partial`/progress frames and keeps the *latest* `umap_canonical` — so the field always tweens toward the freshest fit, never queues through stale ones.
5. **Chunks live in 3D; the 2D references them; the stepper drives 3D focus (§O.6/§O.7).** A scan's per-sample chunk distribution lives in the 3D Real (interior); a 2D compute node renders the **current instance's content** per-instance (the next-up in the `{chunk samples}` queue, §4.6.1), sampled from that 3D set **or** by halo-retrieval (§O.14 corrected / §O.18); the full distribution stays in 3D. Advancing the 2D per-sample signal **drives the 3D focus** — flies/highlights the corresponding chunk — one-way 2D→3D, while the 3D keeps showing the full distribution.
6. **UMAP normalization = target-sphere fit + hard collider + 1D-radial settle (§6.1; lifted from MORTEGON §2.1–§2.2, §O.17).** Each `umap_canonical` is post-processed to a `TARGET_RADIUS`-fit sphere (default 25 units) plus a hard Lagrange collider pass (equal pairwise push to `2·R·safety`, no soft tail); the client tween then moves each chunk **only along its root-ray** (radial, never tangential), so already-locked chunks keep their angles across scans and a newcomer is pushed outward along its own ray.

---

## §5 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Start a scan | `web-scan {url, query?}` | the pipeline below |
| Multi-URL scan | `{urls_panel}` reference (signal-stream, `pattern_map_and_url_set.md`) | one scan signal per URL, accumulating into the same field |
| Manual refit | `recompute-umap` | a fresh `umap_canonical` → retarget tweens |

---

## §6 — Sequence (the full pipeline)

```
gesture: web-scan {url, query?}
   │
   ▼ FrameBus: chunk_added (chunk_id, url, image_url?, provenance) — streamed
   │     ▼ store.chunks[id] = {…}; preliminary radial seeded
   │     ▼ Reconciler ENTER → InstancedMesh slot at hash-direction radial (this frame)
   │     ▼ TextureCache: image billboards load via single-fetch path (projector.md §9)
   │
   ▼ FrameBus: umap_canonical (per-chunk 6-vector x,y,z,h,s,v + per-url roots) — mid-scan refits
   │     ▼ store.layout updated (latest kept under backpressure)
   │     ▼ tween scheduler RETARGET each affected chunk from current pos → canonical (eased ~600 ms)
   │     ▼ HSV (h,s,v) stored; animate loop rotates it by camera azimuth (projector.md §5.3)
   │
   ▼ (repeat chunk_added / umap_canonical interleaved as the scan streams)
   │
   ▼ FrameBus: done
   │     ▼ final joint 6D UMAP fit already arrived as the last umap_canonical
   │     ▼ per-URL post-processing rendered: centroid root, bounding-radius scale, collider, HSV phase calibrated
   │     ▼ camera frame-on-scan tween to new root (suppressed if user interacted & root in frustum, §6.2)
   │
   ▼ pattern_map output panel has been materialising in parallel (pattern_map_and_url_set.md)
   ▼ result rows render collapsed-hidden; scroll-spine extrudes viewport chunks (retrieval_and_sidebar.md)
   ▼ REPL viewer scan row: "<url> search=<query> | N/M chunks | UMAP@scan-end | pattern_map: K patterns"
```

---

## §7 — Data

**Frames in:** `chunk_added` (`{chunk_id:int, url, image_url?, provenance, summary?}`), `chunks_partial` (sheddable progress), `umap_canonical` (`{workspace_id, per_chunk:{id→[x,y,z,h,s,v]}, per_url_roots}`), `done`/`error`. **Store written (by FrameBus):** `chunks`, `layout`. **No outbound** beyond the initiating `web-scan`/`recompute-umap`.

---

## §8 — Results

A manifold that grows and settles live: chunks pop in at radial seeds, drift to semantic positions as refits land, rotate colour with the camera, and never overlap (collider). Per-URL clusters keep their own roots; old URLs never move when a new one is scanned (§18.20). Telemetry: the `scan` viewer row tracks counts + UMAP status; `visible 3D` / `hidden 3D` track the spine (§11.8).

---

## §9 — REPL Mirroring

The pipeline is the canonical §18.1 severance check: `sim_frontend.py watch` must observe `chunk_added`×N → `umap_canonical` (mid-scan **and** scan-end) → `done` **on the workspace WS** (not a snapshot socket). The `scan` viewer row updates in place as counts climb; the `live-scan-real-with-cleanup` probe (§16.5) asserts incremental `umap_canonical` frames and at least one `pattern_map` mutation before `done`. The REPL drives the same scan via `web-scan` and reads back identical frames.

---

## §10 — Theme

All streamed geometry is the **exception zone** (`theme.md` §2.5): chunks carry HSV fill or image texture over the `--bg-void` ground; nothing in the streaming pipeline adds 2D chrome except the scan's `pattern_map` panel (steel-on-black, `pattern_map_and_url_set.md`) and the result list (steel-on-black, `retrieval_and_sidebar.md`). The motion is the eased tween settling — no flash, no colour pulse; the only "liveness colour" is the HSV the chunks already carry, rotating with the camera.

---

## §11 — References

- `DOMAIN_MODEL.md`: §6.1 (placement states, 6D), §9.3 (joint fit), §10.3 (Layout Service), §16.5 (live-scan + cleanup probe), §17.1 (scan sequence); anti-goals §18.1/§18.2/§18.3/§18.20/§18.29.
- Peers: `projector.md`, `liveness.md`, `frame_bus.md`, `pattern_map_and_url_set.md`, `retrieval_and_sidebar.md`.
