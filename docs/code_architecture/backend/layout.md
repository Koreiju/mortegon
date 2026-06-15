# Backend — LayoutService (the 3D layout authority)

> **Owns:** the chunk-side 6D UMAP fit + the UMAP-linear-radial-force layout + the `umap_canonical` broadcast. File: `layout_service.py`. Design: §6.1 / §8.2.1.2 / §O.17 / §11.1 / §18.1 / §18.20. Realises `code_constraints/layout.md`, `streaming.md`. **This is the only authority for 3D placement** — the frontend computes no layout (§2.1).

---

## §1 — Responsibility

Place every chunk in the Real register via the **UMAP-linear-radial force-directed hybrid** (§6.1): UMAP positions, force-directed converges along root-URL rays, hard collider repulsion. Emit the canonical 6-vector frame (`LayoutFrame`, `data_schemas.md` §4.2) keyed by `workspace_id`. The forbidden alternatives (concentric Fibonacci spheres, hash-direction as final) are not implemented; the hash-direction + radial-distance placeholder is permitted **only** as the transient between chunk arrival and the next refit (§18.2).

---

## §2 — Public Surface

```python
def index_chunk_incremental(chunk: Chunk) -> None              # TF-IDF incremental on arrival (delegates GlobalTfidfStore)
def recompute_and_broadcast(workspace_id: str, *, final: bool = False) -> LayoutFrame
def nearest_chunks(chunk_id: int, k: int) -> list[int]         # manifold neighbours (halo coupling input)
def schedule_output_projection(node: ConceptNode) -> None      # agent-output / scanner-emitted → perimeter (§9.12)

# §6.6.4 compute-graph node + projector link network (UMAP-INDEPENDENT — no embedding coords)
def place_compute_graph_node(workspace_id: str, graph_id: str,
                             input_ids: list[str], output_ids: list[str]) -> ComputeGraphPlacement  # bisector node
def compute_projector_links(workspace_id: str, graph_id: str, *,
                            input_ids: list[str], readout_ids: list[str],
                            url_sample_map: dict[str, list[str]]) -> list[ProjectorLink]   # caller-supplied adjacency
```

---

## §3 — Internal Logic — `recompute_and_broadcast` (§6.1 / §O.17)

```
1. JOINT 6D UMAP fit over the FULL TF-IDF index (every chunk, every URL + graph-output) → 6-vec/chunk
       the 6-vector = (x, y, z, h, s, v): 3 position + 3 HSV, one fit (§8.2.1.2)
2. TARGET-SPHERE fit: scale the cloud so the farthest point sits at TARGET_RADIUS (default 40, raised from 25 per B.3 crowding fix)
3. HARD LAGRANGE collider (N iters): any pair closer than 2·R·safety is pushed apart EQUALLY to 2·R·safety
       hard constraint, no soft spring tail (§O.17)
4. PER-URL post-process:
       centroid of a URL's chunks → root_position; bounding_radius = max chunk distance
       a NEW url is placed at (existing_max_radius + new_radius + safety_gap) in the emptiest angular direction
       OLD urls never move when a new one arrives (§18.20)
5. 1D-RADIAL settle: each chunk moves ONLY along its root→UMAP ray;
       pair repulsions are projected onto that ray (the linear-radial constraint, §O.17)
6. PERIMETER rescale: provenance==agent-output (and scanner-emitted graph output) → outer-envelope shell
       (angular position kept; radial distance rescaled outward, §6.6.1 / §9.12)
7. write LayoutFrame (6-vectors) → broadcast umap_canonical to the WORKSPACE ws  (+ per-snapshot ws) — DUAL-ROUTE (§18.1)
```
- **Dual-routing (§18.1):** `umap_canonical` (and scan `chunk_added`) MUST reach the **workspace** socket, not only a per-snapshot socket — `recompute_and_broadcast` keys on `workspace_id`; `_ws_push` fans to both.
- **Incremental refits** land mid-scan and at scan-end (§16.5); each refit emits a fresh canonical frame the frontend tweens toward **from the current position** (never a restart — `frontend/real.md` §3).
- Legacy 3-vector frames are migrated on first load by re-fitting HSV from TF-IDF (`data_schemas.md` §4.2).

### §3.1 Compute-graph node placement + projector link network (§6.6.4)

Distinct from the chunk cloud (§3), a compiled computation graph gets **one collapsed node** plus a link set, **neither part of the UMAP fit** (coupling them to the fit is the §18.34 regression):

- **`place_compute_graph_node`** — position = the midpoint of the **linear bisector** between (a) the centroid of the **input** nodes' 6-vector **position** triple (xyz) and (b) the **dynamically-updated** centroid of the **readout-perimeter** outputs' xyz (`compute.md` §3.5 / §7.8.2). **Recomputed whenever a readout delta lands** (§7.8.3) so the node *slides* toward the current input↔output balance; **neither centroid is emitted — only the node** (§18.34, P.10). HSV is carried from the input centroid (drives the passive rotation, §7.8.3).
- **`compute_projector_links`** — the **UMAP-independent** adjacency (carries **no coordinates**): `root_url → chunk_sample` nodes; `(input roots ∪ click-sticked inputs) → graph_node`; `every readout → graph_node` (§6.6.4, P.8 / P.9). Emitted as `ProjectorLink` records (`data_schemas.md`); the 3D projector draws plain lines (`frontend/projector.md` — the 2D `frontend/link_layer.md` SVG is editor-only and untouched).

Both ride a **`compute_graph_layout`** delta (`contracts.md`) emitted **alongside** the readout `chunk_*` deltas, **not folded into `umap_canonical`** (no embedding coords). The readout *chunks* themselves still land on the perimeter through the §3 step-6 rescale (their provenance is a graph output), so the perimeter shell and the bisector node stay geometrically consistent.

---

## §4 — Dependencies

- **Calls:** `GlobalTfidfStore` (the TF-IDF index it fits over — retrieval.md), UMAP, WS broadcaster.
- **Called by:** ConceptLifecycle (`schedule_output_projection`, lifecycle.md §3.1 step 6), the scanner (per-chunk incremental + scan-end final, scanner.md), `POST /api/recompute_umap`.
- **Sibling, never nested:** the concept-side pipeline (ConceptIndexService) — the two run independently (§2.3).

---

## §5 — Excluded

- The Real-register / transcendental-permanence framing; the camera/HSV-phase *rendering* (that is the frontend Projector, `frontend/real.md`). This service emits the 6-vectors; the client renders the HSV phase against the camera azimuth.
