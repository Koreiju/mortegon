# Feature: Halo Retrieval (Concentric Circles + Ray-Projection + Autoregression)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §8.2 (apparition halo), §8.2.1 (concentric circles), §8.2.1.1 (ray-projection to conic surface), §8.2.1.2 (6D UMAP HSV rotation), §8.2.2 (autoregressive feedback), §8.1.1 (multi-semantic-frequency-PageRank ranking), §1.1 ("distributional substance radiating from focal points"), §1.2.2 verbatim.

**Status.** Realised (core). The concentric layout, the ray-projection coupling, the HSV-state propagation, and the multi-frequency aggregation are all realised: `apparition_service.py` carries `_band_signals` + `_multi_freq_modulation` (the §8.1.1 5-band aggregation, mode-gated at K=32 → `apparition-mode-roundtrip`) + `manifold_nearest` + `apparitions_for_focal(..., transport, ray_project)`; the frontend `concept_graph.js::_renderApparitionHalo`/`_populateHalo` fetch `GET /api/apparitions/{focal_id}?transport=1&ray_project=1` and draw the cone-ray phantoms; HSV is the per-frame `colorMatrix` spectral rotation (`animation.js`). Verified by `halo-focus-roundtrip`, `halo-chain-roundtrip`, `apparition-mode-roundtrip` in `full-smoke`. *(Reconciled to §O: halo gating §O.3; connectors are undirected lines with no arrowheads §O.16; folding is knowledge-panel-only §O.1. Current spec: `frontend/halo.md`.)*

---

## §1 — What the user sees

The user hovers a panel and a concentric-circle radiation appears around it — candidates fan out angularly by the direction of their nomic embedding relative to the focal's, and radially by how strongly they retrieved. The inner ring carries the highest-similarity candidates; the outer ring carries the lower-similarity ones; candidates below the workspace's scale-space threshold fall off the visible halo entirely. Every phantom shows the candidate's name only — no scores, no description previews — because the *shape* of the distribution is what the user is reading at a glance. **Gating (§O.3):** the halo opens only from a field carrying rendered literal text (a blank / in-progress *text* field counts); a pure-`{ref}` field opens none (it is already bound); a mixed text+`{ref}` field queries the *whole resolved field*.

When the focal panel is anchored to a 3D chunk in the projector (via `data-3d-node-id`), the halo **transports** the retrieval-similar 3D chunks along a common cone whose apex is the 2D query element (§O.18): each node's normalized retrieval similarity sets its radial + along-ray distance along the cone, and its angular placement is the camera-view projection along the cone surface normal. Each lands as a collapsed-singular phantom whose cone position encodes its similarity to the 2D query (deleting a halo result transports in the next-most-similar from the retrieval queue, §O.14). Each collapsed phantom carries the chunk's original image billboard if one is attached, or its slowly-rotating UMAP HSV colour if not; the rotation phase tracks the camera azimuth so the phantom's hue rotates in lockstep with its parent chunk in the projector.

A click on any phantom promotes the soft link to a hard link, spawns a new focal at the phantom's screen position, and a new halo radiates around that new focal — the user walks the retrieval space one click at a time. The autoregression is bounded by the user's attention; the cascade scheduler prevents the agent from auto-firing the same loop.

The §1.1 framing makes this *distributional substance radiating from focal points* — every concept node is the centre of a continuous angular + radial neighbourhood the user reads density and direction simultaneously across.

---

## §2 — Cross-objects

| Object | Role in this feature |
|---|---|
| [`ApparitionService`](../object_model/ApparitionService.md) | Produces the ranked candidate list via multi-frequency aggregation; provides ray-projection annotations |
| [`Halo`](../object_model/Halo.md) | Frontend renderer; concentric layout + ray-projection + HSV rotation |
| [`LayoutService`](../object_model/LayoutService.md) | Provides `nearest_chunks` + LayoutFrame HSV state for ray-projection |
| [`ConceptIndexService`](../object_model/ConceptIndexService.md) | Sources per-concept nomic + TF-IDF + PageRank for ranking |
| [`ConceptEdge`](../object_model/ConceptEdge.md) | Soft links live in the apparition cache; promoted to hard links on click |
| [`UIStateService`](../object_model/UIStateService.md) | `halo_focus` + `halo_chain` mirror fields |
| [`Editor`](../object_model/Editor.md) | `Editor.link` is called on click promotion |
| [`KnowledgePanel`](../object_model/KnowledgePanel.md) | The focal whose halo radiates |

---

## §3 — Gestures

| Gesture | REPL action | Effect |
|---|---|---|
| Open halo | `ui-halo-focus { focal_card_id, candidates? }` | `apparition_service.surface_for(focal_card_id)`; halo renders; mirror updated |
| Re-target halo | `ui-halo-focus { focal_card_id }` with new id | New focal; new candidates; mirror updated |
| Close halo | `ui-halo-clear` | Halo overlay removed; mirror cleared |
| Click phantom (autoregressive promote) | (frontend gesture wraps as) `editor-link` + `ui-halo-chain-push` + open new halo | Soft → hard; new focal pinned; new halo radiates |
| Push halo chain step | `ui-halo-chain-push { focal_card_id }` | Records autoregressive walk in mirror |
| Clear halo chain | `ui-halo-chain-clear` | Resets the walk |

---

## §4 — State machine — halo open with ray-projection

```
gesture: ui-halo-focus { focal_card_id }
   │
   ▼
ApparitionService.surface_for(focal_card_id, k=8)
   │     ▼  for each candidate: triple_product evaluated per band (§8.1.1)
   │     ▼  per-band scores aggregated via PageRank-weighted combination
   │     ▼  candidates below min_score_threshold dropped
   │
   ▼
if focal has data-3d-node-id:
   ▼  surface_for_projector also runs:
   ▼  LayoutService.nearest_chunks(workspace, focal_chunk_id, k=4)
   ▼  for each: compute ray from focal-centre through screen-projected world position
   ▼  intersect with halo conic surface → ray_target screen point
   ▼  annotate candidate with ray_target + hsv + image_url from LayoutFrame
   │
   ▼
frontend Halo._renderApparitionHalo(focal_card, candidates):
   ▼  compute polar positions (angular = nomic_direction, radial = score)
   ▼  for ray-projected candidates: use ray_target instead
   ▼  draw collapsed-panel-form phantoms (name only, image billboard or HSV-fill)
   ▼  attach hover (slow tooltip with scores) + click handlers
   ▼  call _postHaloFocusMirror → POST /api/ui/halo_focus
   │
   ▼
WS ui_state_changed (kind=halo_focus) carries the candidate list to peer surfaces
   │
   ▼
animate loop (per frame): rotate each ray-projected phantom's fill on the SAME shared phase clock as its parent chunk (realised: the time-driven `colorMatrix`, `animation.js`; design intent is to drive that phase from camera azimuth instead — frontend_rendering §1.8) so phantom + parent never desync (§18.26)
   │
   ▼
on user click of phantom:
   ▼  Editor.link(focal_id, candidate_id, edge_type="DERIVED_FROM")
   ▼  ui-halo-chain-push { focal_card_id: candidate_id }
   ▼  spawn new pinned panel at phantom's screen rect
   ▼  open new halo around candidate_id → recurse
```

---

## §5 — WS frames + telemetry

| Frame | When | Carries |
|---|---|---|
| `ui_state_changed` (kind=halo_focus) | On halo open / re-target | `halo_focus = {focal_card_id, candidates, opened_at}` |
| `ui_state_changed` (kind=halo_clear) | On halo close | `halo_focus = null` |
| `ui_state_changed` (kind=halo_chain_push) | On phantom click promotion | `halo_chain` extended with new focal |
| `ui_state_changed` (kind=halo_chain_clear) | On explicit reset / purge | `halo_chain = []` |
| `concept_changed` (linked) | On soft→hard promotion | The new edge appears |
| `concept_index_update` | On settled cascade | The aggregated ranks are re-computable from the index |

The REPL viewer's `halo` row reads `halo_focus`; the `halochain` row reads `halo_chain`.

---

## §6 — Acceptance bar

The halo retrieval feature is realised when:

- `halo-focus-roundtrip` env-scenario passes — halo open / re-target / clear all mirror correctly + the candidate list is preserved.
- `halo-chain-roundtrip` env-scenario passes — autoregressive walk extends the chain on every click, consecutive-duplicate is no-op, clear resets.
- The §16.5 live-scan probe asserts a halo opens on at least one scanner-emitted chunk with multi-frequency ranking and at least one ray-projected projector-neighbour annotated with HSV state.
- The viewer's `halo` and `halochain` rows render correctly populated and cleared.
- A snapshot of the halo's DOM after open contains exactly the names of the top-K candidates (no score chips, no description previews per §USER D.1).
- The HSV phase on a ray-projected phantom matches its parent chunk's phase on the shared rotation clock (realised: time-driven `colorMatrix`; design intent camera-azimuth-driven, frontend_rendering §1.8) — they never desync (§18.26), per-frame inspection.

---

## §7 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| Concentric Fibonacci spheres as primary 3D layout (the halo is NOT this — it's a retrieval visualisation) | forbidden-concepts §1 |
| Compact-form regression (halo phantoms showing scores) | §18.21 |
| Ray-projection mismatched HSV | §18.26 |
| Single-frequency PageRank persisting after multi-freq activation | §18.25 |

---

## §8 — Code constraints

- [`frontend_rendering.md`](../code_constraints/frontend_rendering.md) — name-only halo phantoms; no dashes; HSV phase matched to camera azimuth.
- [`backend_services.md`](../code_constraints/backend_services.md) — ApparitionService multi-frequency mode + ray-projection annotation.
- [`api_routes.md`](../code_constraints/api_routes.md) — `/api/apparitions/<card_id>` + `/api/ui/halo_focus` + `/api/ui/halo_chain_push` shapes.

---

## §9 — Cross-features

- [`multi_frequency_pagerank.md`](multi_frequency_pagerank.md) — the ranking algorithm.
- [`autoregressive_halo.md`](autoregressive_halo.md) — the click-walk loop.
- [`6d_umap.md`](6d_umap.md) — the HSV-rotating colour the phantoms inherit.
- [`hard_soft_links.md`](hard_soft_links.md) — the soft → hard promotion.
- [`projective_inverse.md`](projective_inverse.md) — the closest-inverse reads the same apparition surface.
- [`three_register_model.md`](three_register_model.md) — the halo's coupling between Imaginary (concentric ring) and Real (ray-projected chunks).
