# Object: Halo (Frontend Component)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §8.2 (apparition halo), §8.2.1 (concentric-circle radiation), §8.2.1.1 (ray-projection to conic surface), §8.2.1.2 (6D UMAP HSV rotation on collapsed singular phantoms), §8.2.2 (autoregressive halo feedback), §1.1 ("distributional substance radiating from the focal points"), §1.2.2 verbatim.

**Status.** Realised (core) — the halo renders soft-link phantoms (name-only §8D.1.3, undirected silver connectors §O.16) on a **§O.18 cone-ray projection**: `concept_graph.js::_populateHalo` consumes the backend `transport` scalars — `radial=(1-s)·R` drives the perpendicular offset (`_rEff`, most-similar nearest the apex), **`along_ray=s·R` drives the depth cue** (apex-near phantoms render larger + on top, wired this pass), `angular` is the camera-relative arc, and `yScale` is the camera foreshortening — so the ring reads as a true projected cone. The backend half (`apparition_service` `transport` coords + `/api/apparitions?transport=1`) is REPL-verified (`radial+along_ray = R = 40`). §O.18 specifies **`angular = camera-client`** — i.e. the angular axis is computed client-side in screen space — so the camera-projected screen-space cone IS the §O.18 realisation (not a stopgap for a world-space mesh); all three transport axes + camera foreshortening are consumed. The **autoregressive walk (§8.2.2 / ConceptEdge.md §3.4)** is wired: clicking a phantom commits the link, pushes the `halo_chain` mirror (`/api/ui/halo_chain_push`, REPL-traceable — verified to record a multi-step chain), and **opens a new halo around the clicked candidate** so the walk continues. **HSV-state propagation (§8.2.2 / §10 theme / §709)** is wired: when a candidate is a ray-projected 3D chunk, the phantom inherits that node's UMAP content-HSV (`initialNodeData[id].umapHsl`, coords[3:6]) with the SAME live camera-azimuth hue phase the projector mesh uses (`ChunkProjector._currentHuePhase`, applied via the pure `applyHuePhase`/`hslToRgb`) as a left-edge accent — the one permitted halo colour; the connector lines stay silver (§O.16). The animate loop's `_updateHaloPhantomHues` keeps it rotating in lockstep with the parent chunk across the 3D→2D collapse (§18.26 shared-phase invariant). This fixed a prior bug where the code read `.r/.g/.b` off a `THREE.Vector3` (`umapColor`, which only exposes `.x/.y/.z`) so every phantom accent resolved to `rgb(0,0,0)`. Reconciled to §O: gating §O.3; undirected lines, no arrowheads §O.16. Current frontend spec: `frontend/halo.md`.

---

## §1 — What it is

The frontend renderer for the apparition halo. When the user (or agent) opens a halo around a focal panel, the renderer draws a polar-coordinate radiation around the focal — each soft-link candidate (§3.2.1) becomes a collapsed-panel-form phantom (name only per §4.5) positioned by its retrieval rank. The renderer is responsible for the visual realisation of §1.1's *distributional substance radiating from the focal points* — the user reads density, direction, and (for projector-backed phantoms) manifold neighbourhood at a single glance. **Gating (§O.3):** a halo opens only from a field carrying rendered literal text input (a blank / in-progress text field counts); a pure-`{ref}` field opens none; a mixed text+`{ref}` field queries the whole resolved field.

The §1.5 framing places the Halo squarely in the **Imaginary register's rendering surface**, with a structural coupling to the Real register: ray-projected phantoms carry their parent chunk's HSV state (§8.2.1.2) so the halo simultaneously expresses retrieval space (concentric rings) and manifold space (collapsed singular nodes from the projector).

---

## §2 — Rendering responsibilities

### §2.1 Polar-coordinate layout

For each candidate returned by `apparition_service.surface_for(focal_id)`:

- **Angular position** = `nomic_direction_relative_to_focal(candidate)`, recentred so the strongest two candidates anchor the arc and the rest fan around them.
- **Radial position** = `r_focal + r_inner + (1 − normalized_score) · r_extent`, where `normalized_score` is the candidate's aggregated multi-frequency rank divided by the top candidate's rank.
- **Visibility cutoff** = candidates below `min_score_threshold` (default 0.3) fall off the visible halo entirely (scale-space periphery preservation).

The result is a concentric ring of phantoms around the focal, sparser at the periphery, denser near the focal.

### §2.2 Cone-ray-similarity transport (§8.2.1.1 / §O.18)

> **Superseded by §O.18 transport (2026-05-30):** rather than projecting only the focal's *manifold-nearest* chunks, the renderer **transports any retrieval-similar 3D node** along the common cone (apex = the 2D query element) — normalized retrieval similarity sets both radial and along-ray distance; angular placement is the camera-view projection along the cone surface normal; deleting a halo result transports in the next-most-similar from the retrieval queue (§O.14). The `surface_for_projector` mechanics below are retained for the cone / billboard / HSV detail, but the *selection* is similarity-driven, not 3D-nearest.

When the halo's focal has a `data-3d-node-id` resolving to a chunk in the projector, the renderer also calls `apparition_service.surface_for_projector(focal_id)` which returns the ApparitionCandidates annotated with `ray_target`, `hsv`, and `image_url` for the K projector-nearest chunks. The renderer:

- Computes the conic surface (apex at focal-panel screen centre; lateral surface coincides with the halo's outer ring).
- For each ray-projected candidate, places the phantom at the `ray_target` (the cone-surface intersection of the ray from focal centre through the screen-projected world position).
- The phantom carries the chunk's image billboard (if `image_url` is set) or its HSV-rotating fill (if not).
- The HSV rotation phase is the same camera-azimuth-phase the projector applies to the parent chunk, so the phantom's hue tracks the chunk's hue in lockstep as the camera orbits.

The result: every visible phantom is *both* a soft-link candidate by retrieval rank *and* (for projector-backed phantoms) a manifold-nearest chunk by 3D geometry — superimposed at the focal.

### §2.3 Phantom compact form

Every phantom shows the candidate's **name only** per §4.5 / §USER D.1. No score chips, no description preview, no rendering excerpt. Scores live in a slow-hover tooltip (`title` attribute or equivalent). The phantom shares the collapsed-panel form of §4.3 — name, optional 🔒 indicator for read-only candidates.

### §2.4 Click → autoregressive promotion (§8.2.2)

A click on a phantom:

1. Calls `Editor.link(focal_id, candidate_id, edge_type="DERIVED_FROM")` via REST — the soft link promotes to a hard link.
2. Spawns a new pinned panel adjacent to the original focal (per §4.2 freeze-at-rect, anchored to the phantom's screen position).
3. Fires `apparition_service.surface_for(new_focal_id)` — a new concentric-ring halo radiates around the new focal.
4. `UIStateService.push_halo_chain(new_focal_id)` records the autoregressive step.
5. Visual: the phantom fades from the possibility ring; a new edge materialises on the commitment fan between the original focal and the new focal; the new focal's halo opens.

---

## §3 — Render lifecycle

### §3.1 Open

`_renderApparitionHalo(focal_card, candidates)` in `concept_graph.js`:

1. Compute the focal's screen rect.
2. Lay out the candidates per §2.1.
3. If the focal has a `data-3d-node-id`, augment with ray-projection per §2.2.
4. Draw each phantom; attach hover + click handlers.
5. Call `_postHaloFocusMirror(focal_id, candidates)` — POST to `/api/ui/halo_focus` so the backend mirror updates.

### §3.2 Refresh

If the workspace's apparition surface changes (cascade settle, edge add/remove, ConceptIndex refit), the halo re-renders in place with the new candidates. The renderer reuses the overlay DOM element rather than tearing down + rebuilding.

### §3.3 Close

`_clearApparitionHalo()`:

1. Remove the halo overlay from the DOM.
2. Hide the candidate-list panel (if open).
3. POST `/api/ui/halo_clear` — backend mirror clears.

### §3.4 HSV phase animation

Per animate frame (in `animation.js`):

- Read current camera azimuth.
- For each visible phantom with an `hsv` field, apply the `(camera_azimuth_phase + chunk_hsv_phase)` rotation to the fill colour.
- The rotation period defaults to 60 seconds (matched to a slow projector orbit cadence).

---

## §4 — Persistence

The Halo is render-state-only. The halo overlay is a DOM element created per open; no client-side storage. The backend mirror lives in [`UIStateService.md`](UIStateService.md) (`halo_focus` + `halo_chain`).

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ApparitionService.md`](ApparitionService.md) | Source of the candidate list; provides ray-projection annotations |
| [`LayoutService.md`](LayoutService.md) | Indirectly (via apparition service) — supplies `nearest_chunks` + LayoutFrame HSV state |
| [`UIStateService.md`](UIStateService.md) | `halo_focus` + `halo_chain` mirror updated on every open / re-target / clear |
| [`KnowledgePanel.md`](KnowledgePanel.md) | The focal panel; the halo's screen rect is computed relative to it |
| [`Projector.md`](Projector.md) | For projector-backed phantoms, the projector's camera azimuth drives the HSV phase |
| [`Editor.md`](Editor.md) | Click promotion calls Editor.link via REST |
| [`ConceptEdge.md`](ConceptEdge.md) | Soft links are the candidates; the click creates a hard link |

---

## §6 — Cross-references

- Feature touchpoints — [`features/halo_retrieval.md`](../features/halo_retrieval.md), [`features/multi_frequency_pagerank.md`](../features/multi_frequency_pagerank.md), [`features/autoregressive_halo.md`](../features/autoregressive_halo.md), [`features/6d_umap.md`](../features/6d_umap.md), [`features/hard_soft_links.md`](../features/hard_soft_links.md).
- Code constraints — [`frontend_rendering.md`](../code_constraints/frontend_rendering.md) (name-only compact, no dashes, hidden-overlay buttons not on halo phantoms).
- Sequence reference — DOMAIN_MODEL §17.7 (apparition resolve), §17.1.5 (ray-projection sequence).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Halo phantoms showing scores or extra text | §18.21 — compact-form regression | Phantom DOM contains the name only; scores in tooltip |
| Drawing phantoms with dashed lines | Forbidden-concepts §5 | All halo strokes are solid |
| Caching the candidate list across focal changes | Stale candidates would mislead the user | Renderer re-fetches on every focal change |
| Ignoring ray-projection annotations for projector-backed focals | Loses the §8.2.1.1 dual-semantics rule | The renderer always calls `surface_for_projector` when the focal has a 3D node id |
| HSV phase mismatch between phantom and parent chunk | §18.26 | The phantom reads HSV from LayoutFrame on every render; rotation phase matches the projector's |
| Clicking a phantom without calling `push_halo_chain` | Breaks the autoregressive mirror | The click handler always calls Editor.link + push_halo_chain |
| Leaving the halo overlay attached to the DOM after focal close | Memory leak; phantom click handlers stale | `_clearApparitionHalo` removes the overlay element fully |
| Mixing halo phantoms with hard-link edges on the same SVG layer | The commitment fan and the possibility ring are separate layers (§3.2.1) | The halo overlay is its own layer; hard-link edges are on the concept_graph SVG layer |
