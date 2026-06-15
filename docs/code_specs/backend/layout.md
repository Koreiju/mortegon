# Spec — Backend / LayoutService

> Deepens [`code_architecture/backend/layout.md`](../../code_architecture/backend/layout.md). File: `layout_service.py`. Types: [`../types.md`](../types.md) §4. Constants: [`../constants.md`](../constants.md) §1. The **only** authority for 3D placement; emits `Vec6` (3 pos + 3 HSV).

---

## §1 — Incremental chunk indexing (realized as a split, not one LayoutService method)

There is **no** `LayoutService.index_chunk_incremental` method in the realized code. The incremental path is split across the two sibling pipelines (§2.3 backend-services): the scanner / `output_projection` adds a chunk's rendering to **`GlobalTfidfStore.add_chunks`** (retrieval.md / persistence.md), and a joint LayoutService refit is then scheduled (debounced). LayoutService's own entry points are the JOINT fits (`recompute` / `recompute_and_broadcast`, §2) — never a per-chunk index call.

- **Behaviour** — add a chunk's rendering to the TF-IDF index; the chunk gets a transient placeholder position (hash-direction, §18.2) until the next joint refit lands its canonical 6-vec.
- **Idempotent** — yes on `chunk_id` (`GlobalTfidfStore` dedups by content hash + chunk-id).
- **Realized algorithm:** `GlobalTfidfStore.add_chunks([text], [meta])`; the scanner/output-projection path schedules `LayoutService.recompute_and_broadcast(...)` (debounced) which assigns the canonical coords.

---

## §2 — `recompute_and_broadcast` (the layout fit)

```python
# Realized signature (layout_service.py:680). The fit itself is `recompute`;
# `recompute_and_broadcast` delegates to it then emits the frame. There is no
# `final` flag — mid-scan vs scan-end is determined by WHEN the caller invokes
# it (per debounced batch vs at scan-end), not by a parameter.
def recompute(self, *, min_docs: int = 8, workspace_id: str = "") -> Optional[LayoutFrame]
def recompute_and_broadcast(self, *, snapshot_id: int, workspace_id: str = "",
                            min_docs: int = 8) -> Optional[LayoutFrame]
```
- **Does** — the full UMAP-linear-radial-force fit (`recompute`); write `LayoutFrame`; broadcast `umap_canonical` (`recompute_and_broadcast`).
- **Returns** — the new `LayoutFrame`. **Idempotent** — yes (pure function of the current index; re-running yields the same frame ± UMAP seed).
- **Complexity** — O(N·d) UMAP + O(N²) collider over the workspace's chunk set (joint, debounced — not per-chunk).
- **Raises** — `SubsystemDownError` only if the embedder is needed for a new graph-output point and is dead.

**Algorithm:**
```
M = GlobalTfidfStore.matrix(workspace_id)                       # every chunk + URL + graph-output row
1. coords6 = UMAP(n_components=UMAP_DIM).fit_transform(M)        # 6-vec each: (x,y,z, h,s,v)
2. scale = TARGET_RADIUS / max(||coords6[:, :3]||);  coords6[:, :3] *= scale          # sphere-fit
3. for _ in range(COLLIDER_ITERS):                              # HARD Lagrange collider
       for (a,b) in pairs where dist(a,b) < 2*R*COLLIDER_SAFETY:
            push a,b apart EQUALLY to exactly 2*R*COLLIDER_SAFETY     # no soft tail
4. per_url = {}                                                 # per-URL post-process
   for url, members in group_by_url(coords6):
       root = centroid(members[:, :3]); radius = max dist(member, root)
       if url is NEW: root = place_at(existing_max_radius + radius + URL_SAFETY_GAP, emptiest_direction)   # old URLs DON'T move (§18.20)
       per_url[url] = UrlRoot(url, root, radius, umap_locked=set(member_ids), hidden=hidden_urls.get(url,False), accessor_dict)
5. for each chunk: project its motion onto its (root→chunk) RAY only;                 # 1D-radial settle (§O.17)
       resolve pair repulsions along that ray
6. for chunk where provenance==AGENT_OUT (or scanner graph-output):                   # perimeter rescale (§6.6.1)
       keep angular; rescale radial to the outer envelope shell
7. frame = LayoutFrame(workspace_id, per_chunk=coords6_as_dict, per_url, updated_at=now)
   LayoutFrameStore.put(frame)
   broadcaster.emit(UmapCanonicalFrame, route=WORKSPACE)   # DUAL-ROUTE: workspace ws + per-snapshot ws (§18.1)
   return frame
```
- **Mid-scan vs final** — `final=False` runs after each debounced batch of arrivals; `final=True` at scan-end. Each emits a fresh canonical frame the client tweens toward **from current position** (real.md §3.2).
- **HSV** — `h,s,v` are part of the single fit (not a separate computation); the client applies the camera-azimuth phase at render (real.md), the service just carries the base HSV.

---

## §3 — manifold-nearest / output-projection (realized locations)

```python
# Realized: the k-nearest-in-manifold lives on ApparitionService (it READS the
# LayoutFrame), NOT LayoutService; the output-projection SCHEDULE lives in the
# lifecycle dispatcher (concept_lifecycle.py), NOT LayoutService.
ApparitionService.manifold_nearest(focal_id, *, workspace_id, k) -> list[ApparitionCandidate]   # reads LayoutFrame coords
concept_lifecycle.schedule_output_projection(workspace_id, ge, *, push_fn) -> None              # debounced; UNCONDITIONAL
```
- **`manifold_nearest`** (apparition_service.py) — k nearest in the 6-vec manifold (position subspace), reading the LayoutFrame; feeds the §8.2.1.1 ray-projection halo coupling (retrieval.md §3.2).
- **`schedule_output_projection`** (concept_lifecycle.py, called per mutation, §lifecycle §1 step 5) — runs UNCONDITIONALLY; the LayoutService `_perimeter_rescale` (step 6 of §2) then keeps `agent-output` chunks on the outer-envelope shell. The peripheral selection + `agent-authored → agent-output` provenance mapping is in `output_projection`, not gated in the dispatcher.

```python
# §6.6.4 — compute-graph projector overlay (UMAP-INDEPENDENT; data_schemas.md §4.5)
def place_compute_graph_node(workspace_id: str, graph_id: str,
                             input_ids: list[ConceptId], output_ids: list[ConceptId]) -> ComputeGraphPlacement
def compute_projector_links(workspace_id: str, graph_id: str, *,
                            input_ids: list[ConceptId], readout_ids: list[ConceptId],
                            url_sample_map: dict[str, list[ConceptId]]) -> list[ProjectorLink]
```
- **`place_compute_graph_node`** (§6.6.4, P.10) — `in_c = mean(LayoutFrame.pos[i] for i in input_ids)`; `out_c = mean(LayoutFrame.pos[o] for o in output_ids)` (the readout-perimeter coords, compute.md §4); `pos = (in_c + out_c) / 2` (the bisector midpoint); `hsv = LayoutFrame.hsv[input nearest to in_c]`. Returns `ComputeGraphPlacement(graph_id, pos, hsv, settle_seq++)`. **Neither centroid is emitted — only the node** (§18.34). **Called on every readout delta** (`out_c` moves → the node slides, §7.8.3). **Pre** — `input_ids`/`output_ids` resolve in the LayoutFrame. **Post** — exactly one placement; `settle_seq` strictly increases per `graph_id`. **Complexity** — O(|inputs|+|outputs|).
- **`compute_projector_links`** (§6.6.4, P.8/P.9) — build the **coordinate-free** adjacency from the **caller-supplied** graph data: `url_to_sample` (each `url_sample_map` root → its chunk-sample nodes), `input_to_graph` (each `input_ids` member → the graph node), `readout_to_graph` (each `readout_ids` member → the graph node). Returns `list[ProjectorLink]`. **Never reads or writes UMAP coords** — coupling the link network to the fit is the §18.34 regression. The **editor owns the graph topology** (inputs / readouts / url roots) and passes it in; LayoutService does not walk edges here (so it stays a pure, side-effect-free projection). **Complexity** — O(inputs+samples+readouts).

---

## §4 — Migration / Dependencies / Excluded
**Migration:** a legacy 3-vec `LayoutFrame` on first load → re-fit HSV from the chunk's TF-IDF (one-time). **Calls:** `GlobalTfidfStore` (retrieval.md), UMAP, broadcaster. **Called by:** scanner (per-chunk + scan-end), lifecycle.md, `POST /api/recompute_umap`. **Sibling, never nested** with ConceptIndexService. **Excluded:** the camera/HSV render (real.md); the Real-register framing; forbidden Fibonacci/hyperbolic (migration.md).
