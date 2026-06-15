# Halo — Concentric Radiation, Ray-Projection, HSV Phantoms

> **Status: realised (cp/*.js); greenfield object form in `FRONTEND_REDESIGN.md` §7.2.** The halo membrane is carried by `cp/concept_graph.js`: `_renderApparitionHalo` / `_populateHalo` (name-only phantoms §8D.1.3, undirected silver connectors §O.16), the §O.18 cone-ray projection (radial + `along_ray` depth + camera-angular), the §8.2.2 autoregressive walk (phantom-click → `halo_chain` push + new halo) and HSV inheritance from the ray-projected chunk. Backed by `/api/apparitions?transport=1&ray_project=1` (triple-product + multi-frequency + manifold-nearest §8.2.1.1). Verified by `halo-focus-roundtrip`, `halo-chain-roundtrip`, `apparitions-discover-link`, `apparition-mode-roundtrip`.

---

## §1 — Identity

`Halo` renders, around any focal `ConceptView`, the concentric-circle apparition radiation (§8.2.1) **and** the ray-projection of the focal's projector-neighbours onto the halo's conic surface (§8.2.1.1). Every phantom is simultaneously a soft-link candidate (by triple-product rank) and — for projector-backed phantoms — a manifold-nearest chunk (by 3D geometry). The Halo **fetches** candidates and neighbour positions; it **never ranks or computes coordinates** (§2.1). It is a Real↔Imaginary coupling membrane. **Gating (§O.3):** a halo opens only from a field carrying rendered literal text input (including a blank / in-progress text field); a pure-`{ref}` field opens none; a mixed text+`{ref}` field queries the whole resolved field. **Singular-primitive focals + hover-to-panel (§O.19):** the halo fires for **singular-primitive field representations with links in graph form** (a singular-field graph node is a focal, exactly as a panel is); and a 3D node shows its knowledge-panel representation on hover in *either* base-UMAP or transported-halo form (§O.18), with a click sticking it into the 2D (§4.2).

---

## §2 — Structure

An SVG/2D overlay anchored to the focal panel's centre: concentric ring guides + one `phantom`-mode `ConceptView` per candidate (`concept_view.md`). **Owns (transient):** the focal id; the fetched candidate list + positions; per-phantom HSV phase (mirrored to the parent chunk). **Reads:** `ui.halo_focus` (`{focal_card_id, candidates, opened_at}`), `index[focal]` (similar_to ranks), `layout` (projector-neighbour world positions + HSV), `edges` (to separate committed hard links from soft candidates).

---

## §3 — Behaviours

### §3.1 Concentric radiation (§8.2.1)
Candidates from `apparition_service.surface_for(card_id)` place at polar coordinates around the focal: **angular** by nomic direction, **radial** by `r = r_focal + r_inner + (1 − normalized_score)·r_extent`. Below `min_score_threshold` (default 0.3) a candidate falls off the visible halo (scale-space periphery). Each phantom is **name-only** (`phantom` mode; scores in a slow-hover `title` tooltip) — no score chips (§4.5, frontend_rendering §1.7, §18.21). This is a *retrieval-score visualization*, **not** the forbidden concentric-sphere layout authority (top-of-doc forbidden concepts).

### §3.2 Cone-ray-similarity transport (§8.2.1.1 / §O.18)
The **2D query element** (the focal stuck-node primitive, or one of its singular-field / graph primitives) is the **apex/focus** of a common cone whose focal line is the 2D panel camera's. The 3D nodes that retrieve against it are **transported along that cone by their retrieval similarity** (the triple product; positions + HSV read from `layout` — the frontend *reads*, never computes): normalized similarity sets **both radial and along-ray distance** (more similar → nearer the apex), and the **angular placement** is the projected line of the node's intersection along the **shared cone surface normal** (camera-view dependent). Each transported node lands as a **collapsed singular node**, carrying its **image billboard** (via `TextureCache`) or its **HSV colour** from the 6-vector. **Deleting a halo result transports in the next-most-similar** node from the retrieval-similarity queue, dynamically re-rendering (§O.14). (Supersedes the earlier "project the focal's manifold-nearest neighbours" phrasing — the halo transports any retrieval-similar node, §O.18.)

### §3.3 HSV phantoms rotate with their parent (§8.2.1.2, frontend_rendering §1.8/§1.15, §18.26)
A ray-projected phantom carries the parent chunk's slowly-rotating HSV and applies the **same camera-azimuth phase** as the parent. As the user orbits the Projector, halo phantoms rotate colour in lockstep with their 3D parents — visual identity persists across the dimensional collapse.

### §3.4 Autoregression (§8.2.2)
A phantom click commits a hard link (`concept-edge-create`), spawns a new focal `ConceptView`, and opens a new Halo around it — the user *walks the retrieval space* one click at a time. Finite in practice (user attention bounds it; the agent's actor-aware short-circuit prevents auto-loops, §7.4). Halos open on compiled-graph children identically (§8.2.3) — the apparition surface is uniform across all ConceptNode kinds.

---

## §4 — Composition

| Peer | Through |
|---|---|
| `Editor` (`editor.md`) | hosts the halo around the focal panel |
| `ConceptView` (`concept_view.md`) | each phantom is a `phantom`-mode view |
| `Projector` (`projector.md`) | supplies chunk world-positions + HSV for ray-projection |
| `LinkLayer` (`link_layer.md`) | the possibility ring (soft) vs commitment fan (hard) strokes |
| `WorkspaceStore` | `ui.halo_focus`, `index[focal].similar_to`, `layout` |
| `GestureGateway` | `ui-halo-focus`/`-clear`, `apparition-surface`, `concept-edge-create` |

---

## §5 — Activities & §6 Sequences

| Activity | Gesture | Effect |
|---|---|---|
| Open halo | `ui-halo-focus {focal_card_id}` | radiate candidates + ray-project neighbours |
| Hover phantom | (local) | slow-hover tooltip shows score |
| Click phantom | `concept-edge-create` + new `ui-halo-focus` | promote soft→hard; autoregress |
| Close halo | `ui-halo-clear` | phantoms dissolve |

```
ui-halo-focus {focal_card_id}
   → gateway apparition-surface → top-K candidates (multi-freq aggregated rank §8.1.1) [fetched, not computed]
   → ui_state_changed (halo_focus)
   → Halo: place soft-link phantoms at (angular=nomic-dir, radial=(1−norm_score)·r_extent)
   → if focal has data-3d-node-id: pick K projector-nearest from layout; ray-project onto cone; attach HSV/image
   → LinkLayer: commitment fan (existing hard links) + possibility ring (soft phantoms)
   → animate loop rotates HSV phantoms with camera azimuth (§3.3)
click phantom → concept-edge-create (soft→hard) → phantom fades from ring, hard edge materialises on fan
   → new focal ConceptView pins adjacent → new ui-halo-focus → new halo (autoregression §3.4)
   → if phantom was projector-backed, click also flies camera to c_i (§8.5)
```

---

## §7 — Data

**Reads:** `ui.halo_focus`, `index[focal].similar_to`, `layout` (neighbour positions + HSV), `edges`. **Sends:** `ui-halo-focus`/`-clear`, `apparition-surface` (GET), `concept-edge-create`. **Receives:** `ui_state_changed (halo)`, `concept_index_update` (refresh).

---

## §8 — Results

A concentric steel-ring halo of name-only phantoms around the focal, with projector-backed phantoms carrying HSV/imagery and rotating with the camera; clicking one wires a hard link and recursively opens the next halo. Telemetry: `halo_focus` (focal + candidate-name list) (§10.5).

---

## §9 — REPL Mirroring

`halo_focus` is a §10.5 mirror field with a dedicated viewer line (`focal + candidate-name list`). REPL actions `ui-halo-focus` / `apparition-surface` drive the same radiation; the `halo-focus-roundtrip` env-scenario exercises the single step, and chaining `ui-halo-focus` with successive `focal_card_id`s exercises the autoregression (§8.2.2). The phantom's HSV accent is read from the parent chunk's LayoutFrame 6-vector (§18.26); the *data* it consumes is locked by `6d-umap-format` (frame format) + `node cp/hsv_color.test.mjs` (pure conversion), while the continuous hue rotation of the rendered phantom is render-only and outside the REPL surface — no scenario asserts the rotation (the previously-referenced `halo-ray-projection-hsv-sync` scenario never existed; corrected per the no-over-claim rule).

---

## §10 — Theme

Ring guides: `--steel-700` 1px concentric arcs (faint, machined). Soft-link phantom chips: `--bg-panel` + `--steel-700` hairline, name in `--text-primary`; the connecting soft stroke is a `--steel-700` 1px undirected line (no arrowhead, §O.16) (`link_layer.md`). **Exception:** ray-projected phantoms inherit the parent chunk's **HSV fill or image texture** (`theme.md` §2.5) — the one place the exception leaks into the 2D plane, by inheritance from a billboard. Hover tooltip: monospace `--text-dim` on `--bg-recess` with a `--steel-700` hairline. No score chips, no colour badges; the only hue is the inherited HSV of projector-backed phantoms and (never here) the yellow arrow.

---

## §11 — References

- `DOMAIN_MODEL.md`: §8.2 (halo), §8.2.1 (concentric radiation), §8.2.1.1 (ray-projection), §8.2.1.2 (6D HSV), §8.2.2 (autoregression), §8.2.3 (child halos), §8.1.1 (multi-freq rank), §3.2.1 (hard/soft); anti-goals §18.21/§18.26.
- Object doc: [`../object_model/Halo.md`](../object_model/Halo.md) (reconcile to this).
- Peers: `editor.md`, `concept_view.md`, `projector.md`, `link_layer.md`.
