# Object: LayoutService

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §6.1 (UMAP-linear-radial layout pipeline), §6.6.1 (perimeter-encompassing agent outputs), §6.6.4 (bisector computation-graph node placement + projector link network), §8.2.1.1 (ray-projection for halo), §8.2.1.2 (6D UMAP — 3 position + 3 HSV rotating), §9.3 – §9.7 (per-URL placement, hard collider repulsion), §10.3 (Layout Service in streaming architecture), §17.1 (scan sequence).

**Status.** Realised — `layout_service.py` fits **6D UMAP** (`_UMAP_DIM_TOTAL=6` = 3 position + 3 HSV; `n_components=6` with a 3D fallback for tiny corpora) and applies the **perimeter-encompassing rescale** for agent-output/emission nodes (so synthesis lands on the bounding-sphere perimeter, §6.6.1) over the `DEFAULT_TARGET_RADIUS=40` sphere with hard collider repulsion (`COLLIDER_SAFETY=2.2`, §9.7). The 6D contract (3 position + 3 HSV) is asserted by the `6d-umap-format` scenario. The §8.2.1.1 ray-projection coupling is wired: `ApparitionService.manifold_nearest` reads this service's `LayoutFrame.coords` to find a focal's manifold-nearest cards and augments the halo with them (route `?ray_project=1`) — verified offline (correct nearest order + apex-near §O.18 transport).

---

## §1 — What it is

The Layout Service owns chunk-side spatial computation. It fits a 6-dimensional UMAP per chunk (3 position + 3 HSV) over the workspace's full TF-IDF index, post-processes the result with per-URL centroid translation + bounding-radius scaling + hard collider repulsion + agent-output perimeter rescaling, persists the canonical coordinates in a per-workspace LayoutFrame, and broadcasts `umap_canonical` frames to every connected frontend. The service is one of the two sibling services owning the workspace's progressive vectorisation (the other being [`ConceptIndexService.md`](ConceptIndexService.md) for concept-side embeddings + PageRank).

The §1.5 framing places LayoutService at the **Real register's** core — it builds the spatial geometry the projector renders. Its outputs determine where chunks appear in the manifold, what colour they carry (via the HSV components), and how the halo's ray-projection lands collapsed singular phantoms on the conic surface (§8.2.1.1).

---

## §2 — Shape

### §2.1 LayoutFrame (the persisted record — see [`LayoutFrame.md`](LayoutFrame.md))

```python
@dataclass
class LayoutFrame:
    workspace_id:    str
    coords:          dict[chunk_id, tuple[float, float, float, float, float, float]]   # (x, y, z, h, s, v)
    url_roots:       dict[url, tuple[float, float, float]]                              # per-URL root position
    bounding_radii:  dict[url, float]
    umap_locked:     set[chunk_id]                                                      # chunks with canonical coords
    provenance:      dict[chunk_id, str]                                                # for perimeter-vs-interior placement
    frame_seq:       int
    updated_at:      str
```

### §2.2 Key methods

| Method | Purpose |
|---|---|
| `recompute(workspace_id, *, min_docs=8)` | Fit UMAP over the full TF-IDF index; return LayoutFrame |
| `recompute_and_broadcast(snapshot_id, workspace_id, min_docs=8)` | Fit + emit `umap_canonical` to the workspace WS |
| `get_frame(workspace_id)` | Return the current LayoutFrame (for WS bootstrap on subscribe) |
| `save_frame(workspace_id)` | Persist the LayoutFrame to disk |
| `apply_perimeter_rescale(frame, provenance_map)` | Rescale agent-output chunks to the outer envelope per §6.6.1 |
| `place_compute_graph_node(frame, input_ids, output_ids)` | Position the collapsed computation-graph node on the linear **bisector** between the input 6D-UMAP centroid and the **dynamically-updated** output centroid (§6.6.4, P.10); both centroids hidden, only the node shown — recomputed as perimeter readouts stream in (§7.8.3) |
| `nearest_chunks(workspace_id, chunk_id, k)` | Read-only: return the K projector-nearest chunks for halo ray-projection (§8.2.1.1) |

---

## §3 — Lifecycle

### §3.1 The 6D UMAP fit

At scan-end (and on `/api/recompute_umap` manual triggers, and on graph-state-change deltas with the ~800 ms projection debounce of §9.12), the service:

1. Collects the workspace's full TF-IDF index — every chunk from every URL plus every graph-emitted output.
2. Calls UMAP with `n_components=6` to produce one 6-vector per chunk. **Position + colour are jointly the UMAP fit**, sharing the same neighbour-preservation guarantees; there is no separate colour UMAP call. The fit is *incremental when feasible* (warm-started from the prior UMAP embedding for chunks already indexed) and *cold otherwise*.
3. Post-processes the 6-vectors:
   - For each URL, compute the centroid of its chunks' position triplets; translate so the centroid sits at the URL's stored `root_position` (or, for a freshly-discovered URL, allocate a fresh `root_position` per §9.5).
   - Scale uniformly within each URL so the largest in-workspace chunk-to-root distance equals the URL's chosen `bounding_radius`.
   - Run N iterations of hard collider repulsion: any pair of chunks (within the URL or across URLs) closer than `2 · R_collider · safety` is pushed apart along their connecting vector by exactly the deficit. No soft falloff.
   - Calibrate the HSV phase origin so the workspace's brightest hue cluster sits at the canonical hue origin; the renderer applies a phase offset proportional to current camera azimuth at render time.
4. Applies the **perimeter-encompassing rescale** for any chunk whose `provenance` is `agent-output` (§6.6.1): the chunk's radial coordinate is rescaled so it lands on the convex hull of the URL workspaces' bounding spheres (the projector's outer envelope), preserving the angular position from the UMAP fit. The perimeter shell is a thin band of thickness `~1.2 · R_collider`.
5. Persists the LayoutFrame.
6. Emits `umap_canonical` on the workspace WS carrying the full coord map + url_roots + bounding_radii.

### §3.2 Incremental refits during scan

The service also runs incremental refits mid-scan as new chunks accumulate, not just at scan-end:

- After every K new chunks arrive (default K=64), an incremental refit fires.
- The result is broadcast as another `umap_canonical` frame.
- The frontend tweens chunks from their preliminary radial positions to the new canonical positions; the tween is fast (~600 ms with ease-in-out).

This is what makes the live UMAP updates *live*: the user sees chunks settle into their canonical positions as the scan progresses, not just at the end.

### §3.3 Camera-azimuth HSV phase loop

The Layout Service does *not* run the HSV rotation phase loop itself — that's a frontend renderer responsibility (§8.2.1.2). What the service guarantees is that:

- Every chunk's HSV triplet is stable across animation frames (the HSV state doesn't change per-frame).
- The phase offset the renderer applies is `(camera_azimuth_radians / (2π)) * rotation_period_factor`.
- The phase calibration step (§3.1.3) ensures the brightest hue cluster sits at the canonical origin, so the rotation produces visually coherent transitions across the full hue circle.

### §3.4 Ray-projection support

When the frontend halo opens around a focal panel, the halo renderer calls `nearest_chunks(workspace_id, focal_chunk_id, k)` to get the K projector-nearest chunks for ray-projection (§8.2.1.1). LayoutService returns the chunk records carrying their 6-vectors (position + HSV); the frontend computes the conic-surface intersection and renders the collapsed singular phantoms.

---

## §4 — Persistence

| Artefact | Storage |
|---|---|
| LayoutFrame per workspace | Backend persistent JSON file + in-memory cache |
| Per-chunk coords | Inside the LayoutFrame |
| Per-URL roots + bounding radii | Inside the LayoutFrame |
| Provenance map | Inside the LayoutFrame |
| `frame_seq` counter | In-memory; resets on workspace purge |

Persistence is keyed by `workspace_id`. A workspace reload re-reads the persisted file; subscriber WS bootstrap sends the current LayoutFrame as the first frame after `concept_index_update`. The 6-vector format is the current persisted format; legacy 3-vector files are migrated on first load by re-fitting HSV from the TF-IDF index.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`GlobalTfidfStore.md`](GlobalTfidfStore.md) | Reads the full TF-IDF index as the UMAP input |
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | Receives output-projection schedule notifications on `agent-output` mutations |
| [`LayoutFrame.md`](LayoutFrame.md) | The persistent record this service writes |
| [`ApparitionService.md`](ApparitionService.md) | Reads `nearest_chunks` for ray-projection in halo rendering |
| [`WebBrowser.md`](WebBrowser.md) | Each emitted chunk triggers a preliminary radial position assignment, then participates in incremental + scan-end refits |
| [`Projector.md`](Projector.md) | Frontend renderer reads the LayoutFrame and applies HSV phase per animate frame |
| [`Halo.md`](Halo.md) | Frontend renderer reads `nearest_chunks` for collapsed-singular phantom placement |

---

## §6 — Cross-references

- Feature touchpoints — [`features/6d_umap.md`](../features/6d_umap.md), [`features/perimeter_outputs.md`](../features/perimeter_outputs.md), [`features/halo_retrieval.md`](../features/halo_retrieval.md), [`features/live_scan_streaming.md`](../features/live_scan_streaming.md), [`features/multi_scan_layout.md`](../features/multi_scan_layout.md).
- Code constraints — [`streaming.md`](../code_constraints/streaming.md) (dual-routing, incremental cadence), [`backend_services.md`](../code_constraints/backend_services.md) (singleton, eager init), [`persistence.md`](../code_constraints/persistence.md) (LayoutFrame storage).
- Sequence reference — DOMAIN_MODEL §17.1 (scan), §17.1.5 (halo ray-projection).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Fitting UMAP with `n_components=3` (position only) | §1.2.2 specifies 6D; legacy 3D-only fits break the HSV state requirement | The fit always uses `n_components=6`; legacy LayoutFrames migrate on first load |
| Running a separate UMAP for colour | Position + colour are jointly the fit; running separately breaks the neighbour-preservation co-locality | One UMAP call produces the full 6-vector |
| Skipping the perimeter rescale for `agent-output` chunks | §18.23 violates the Imaginary → Real return contract | The post-processing step always runs the rescale for `provenance=="agent-output"` |
| Emitting `umap_canonical` only at scan-end | §18.29 / live-scan severance: incremental refits are part of the live update contract | Incremental refits fire every K chunks; broadcasts are workspace-WS-routed per §18.1 |
| Letting per-URL placement drift on a new URL scan | §18.20 / §USER B.4 — old URLs never move | The per-URL placement allocates fresh roots without mutating existing roots |
| Falling back to a fake LayoutFrame on UMAP failure | Quiet degradation forbidden | UMAP failures emit `error` frames on the workspace WS; the frame is not falsified |
| Broadcasting to the snapshot WS only | §18.1 severance | `recompute_and_broadcast` routes to the workspace WS via `_ws_push`'s dual-router |
| Sharing colour state across HSV phase recomputes between chunks | Each chunk's HSV is independent; the renderer applies a global phase offset only | LayoutService stores per-chunk HSV; the phase is a render-time multiplier |
