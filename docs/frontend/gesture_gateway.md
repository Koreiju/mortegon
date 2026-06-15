# GestureGateway — The Single Outbound Seam

> **Status: realised (cp/*.js).** The `GestureGateway` role is carried in the realised frontend by `cp/interaction.js::_mirrorUi(path, body)` (the single outbound seam — every gesture POSTs through it) + the per-view gesture handlers in `cp/concept_graph.js` / `cp/billboard.js` / `cp/search.js`. **The §5 gesture catalogue is complete**: every `kind` maps to a live `/api/*` route + a `sim_frontend.py` REPL action + an env-scenario asserting the round-trip (route-coverage + action-registry-coverage gate this), and the once-missing `ui-node-expand/-collapse` (`/api/ui/node_fold`, §7.3.4 inline fold) is now wired (mirror `node_fold_state`, `ui-node-fold` action, `node-fold-roundtrip` scenario). The greenfield object form is `FRONTEND_REDESIGN.md` §3.3.

---

## §1 — Identity

`GestureGateway` turns every user (or in-frontend agent-driven) gesture into a backend mutation, carries an idempotency key (§2.5), optionally renders a zero-latency optimistic echo into the store's overlay (`workspace_store.md` §5), and posts the telemetry that keeps the Symbolic register's mirror faithful (§10.5, `repl_mirroring.md`). It is the outbound mirror of `FrameBus`: all intent leaves here, all truth returns there.

---

## §2 — Structure

**Owns (transient):** an in-flight request table keyed by idempotency key; a telemetry batch buffer (debounced); the REST base URL + the workspace id. **Reads:** nothing it must own — it snapshots view state at call time. **Writes:** the store's `overlay` slice only (echoes); never canonical slices.

**The gesture envelope:**
```
Gesture { kind, args, idempotency_key, echo? }
```
`kind` maps 1:1 to a §14.2 catalogue row. **A gesture with no catalogue row cannot be sent** — it would have no REPL action and no env-scenario (§14.4), so it is not a real gesture. The gateway *is* the frontend's enumeration of §14.2.

---

## §3 — Composition

| Peer | Relationship |
|---|---|
| Every view | Calls `gateway.send(gesture)` and `gateway.telemetry(kind, snapshot)` |
| `WorkspaceStore` (`workspace_store.md`) | Gateway writes the overlay; reads merged state for snapshots |
| Backend lifecycle (§10.2) | The gateway's REST lands here; it is the single mutation authority |
| `FrameBus` (`frame_bus.md`) | The effect returns as a frame; the gateway awaits `done`/`error` to settle/roll-back the echo |

---

## §4 — Behaviours

1. **One outbound seam.** No view issues its own `fetch`; all REST goes through the gateway.
2. **Idempotency on every mutation (§2.5).** Every POST/PATCH/DELETE carries a key; replays return the original effect without re-applying. This makes the REPL ↔ frontend round-trip retry-safe (§14.3).
3. **Optimistic echo + reconcile.** For latency-sensitive gestures, write the echo to `overlay`, fire REST, and on the authoritative frame let canonical supersede the echo; on error, roll the echo back. Canonical slices are never touched by an echo (`workspace_store.md` §5).
4. **The loop always closes through the backend.** The gateway never short-circuits to a view; even the user's own edit round-trips (§1.1-FR) — the echo only hides latency.
5. **Telemetry completeness (§10.5, §8).** After a render settles, the responsible view calls `gateway.telemetry(kind, snapshot)`; the gateway batches and POSTs `/api/ui/telemetry`. *What rendered is reported.*
6. **Cascade discipline (§4.1.1).** Edit gestures do not fire per keystroke; the commit gesture (Enter/blur) is the single cascade trigger.

---

## §5 — Activities: the complete gesture catalogue (§14.2)

Every `kind` the gateway sends, its REST target, the frame it expects back, and the mirror field it touches. (Grouped by surface; each surface doc restates its own subset.)

### §5.1 Pin / panel chrome
| kind | REST | returns | mirror |
|---|---|---|---|
| `ui-hover` | POST /api/ui/hover | `ui_state_changed` | `hovered_id`, `last_hover_rect` |
| `ui-pin` | POST /api/ui/pin | `ui_state_changed` | `pinned_billboards`, `last_stick_rect` |
| `ui-pin-move` / `-resize` / `-minimise` | POST /api/ui/pin_chrome | `ui_state_changed (pin_chrome)` | `pin_chrome[panel_id]` (field-merge) |
| `ui-pin-close` | POST /api/ui/unpin | `ui_state_changed (unpin)` | `pinned_billboards`, `pin_chrome` cleared |
| `ui-collapse` | POST /api/ui/collapse | `ui_state_changed` | `pinned_collapsed` |
| `ui-latch-toggle` | POST /api/ui/latch | `ui_state_changed (latch)` | `latch_state[card_id]` |

### §5.2 Editing & field-tree
| kind | REST | returns | mirror |
|---|---|---|---|
| `concept-rename` | PATCH /api/concepts/{id} | `concept_changed` | — |
| `concept-edit-description` | PATCH /api/concepts/{id} | `concept_changed` + `concept_index_update` | — |
| `concept-edit-data-row` | PATCH /api/concepts/{id} | `concept_changed` | — |
| `field-tree-add-child` / `-add-sibling` | PATCH /api/concepts/{id} | `concept_changed` | — |
| `ui-autocomplete-open` / `-close` | POST /api/ui/autocomplete[_clear] | `ui_state_changed (autocomplete)` | `autocomplete_state` |
| `concept-completions` | GET /api/concept_completions | (REST only) | feeds autocomplete |

### §5.3 Compile / cascade / inline fold
(Gesture note: `ui-compile-expand`/`-collapse` are fired by **double-left-click** on the panel; `ui-node-expand`/`-collapse` by **right-click** on a token — §7.3.4 / `object_exploration.md`.)
| kind | REST | returns | mirror |
|---|---|---|---|
| `ui-compile-expand` | POST /api/ui/compile_expand | `concept_changed`×N + `ui_state_changed` | `compile_expansions[card_id]` |
| `ui-compile-collapse` | POST /api/ui/compile_collapse | `concept_changed`×N + `ui_state_changed` | `compile_expansions` cleared |
| `ui-node-expand` / `-collapse` | POST /api/ui/node_fold | `ui_state_changed (node_fold)` | `node_fold_state[card_id].expanded_paths` |
| `conceptual-compile` | POST /api/conceptual/compile | `concept_changed` | — |
| `conceptual-compile-chain` | POST /api/conceptual/compile_chain | `concept_changed`×N | — |

### §5.4 Retrieval / sidebar / spine
| kind | REST | returns | mirror |
|---|---|---|---|
| `ui-viewport-spine` | POST /api/ui/viewport_spine | `ui_state_changed (viewport_spine)` | `viewport_visible_rows` |
| `ui-row-click` | composed — no dedicated route: POST /api/ui/pin (+ /api/ui/viewport_spine) | `ui_state_changed` | `pinned_billboards`, `viewport_visible_rows` |
| `ui-hover-row` | composed — POST /api/ui/hover (+ /api/ui/halo_focus for the preview) | `ui_state_changed` | `hovered_id`, `halo_focus?` |
| `ui-url-visibility` / `ui-domain-toggle` | POST /api/ui/url_visibility (per-URL `set_url_collapsed`; kind `url_collapse`/`url_expand`) | `ui_state_changed (url_collapse)` | `url_collapsed` (the frontend-only `hidden_urls` Set drives the animate-loop scale=0 per frontend_rendering §1.9) |
| `ui-dominance-collapse` / `-expand` | POST /api/ui/dominance_collapse | `ui_state_changed (dominance_collapse)` | `dominance_collapse[node_id]` — the **generalized rank-dominance collapse** (§6.6.5 3D / §7.3.5 2D, Q.3–Q.5): **right-click** a dominator (root-URL hub or bisector compute node) → fold its dominated set + (in 3D) hide all else; right-click again → re-expand. Membership = dominator's dominated-set over the `ConceptEdge` graph (DOMAIN §8.1.2). **Distinct from `ui-url-visibility`** (different button + surface + mirror, DOMAIN §18.12/§18.35). |
| `ui-url-purge` | POST /api/purge_workspace (scoped) | `purge_workspace` (scoped) | clears affected |

### §5.5 Halo / wiring
(Firing gesture: **left-click-drag node→node** in graph form fires `concept-edge-create`; the target inherits the source's I/O types + object model — §7.3.4 / N.4 / `object_exploration.md` §5.1.)
| kind | REST | returns | mirror |
|---|---|---|---|
| `ui-halo-focus` / `-clear` | POST /api/ui/halo_focus · POST /api/ui/halo_clear | `ui_state_changed (halo)` | `halo_focus` |
| `ui-halo-chain-push` / `-clear` | POST /api/ui/halo_chain_push · POST /api/ui/halo_chain_clear | `ui_state_changed (halo_chain_*)` | `halo_chain` |
| `apparition-surface` | GET /api/apparitions/{focal_id} (+ GET /api/apparitions/mode) | (REST only) | feeds `halo_focus` |
| `concept-edge-create` | POST /api/concept_edges | `concept_changed`×2 | — |

### §5.6 Scan / fixtures / agent / rollout
(Firing gesture: **double-right-click** on a token reference/instance fires `editor-delete` on that node — §7.3.4 / N.13.)
| kind | REST | returns | mirror |
|---|---|---|---|
| `web-scan` | POST /api/web_browser/scan `{url, query?, samples?, duration_s?}` (legacy: GET /api/snapshot, 202) | `chunk_added`×N → `umap_canonical` → `done` | viewer `scan` row |  ⟵ `duration_s` = timed-scan time-box (§15.10, Q.2; 0 ⇒ sample-bounded) |
| `recompute-umap` | POST /api/recompute_umap | `umap_canonical` | — |
| `editor-create` / `-link` / `-overwrite` / `-delete` | POST /api/editor/{primitive} | `concept_changed` | `evolution_diff` actor=editor |
| `library-import` | POST /api/python_api/materialise_module (refresh: /rematerialise_module) | `concept_changed`×N | — |
| `agent-spawn` | POST /api/agent/spawn | `concept_changed`×4 | — |
| `agent-tick` | POST /api/agent/tick | `agent_token` stream + `concept_changed`×emit | — |
| `rollout-play` / `-pause` / `-step` | POST /api/rollout/{verb} | `rollout_resumed`/`rollout_paused` | `rollout_state` |
| `ui-signal-advance` | POST /api/ui/signal_advance | `ui_state_changed (signal_advance)` | `signal_stream` |
| `purge-workspace` | POST /api/purge_workspace | `purge_workspace` | all cleared |
| `evolution-rollback` | POST /api/evolution_log/rollback | `evolution_diff` + `concept_changed` | — |
| `subsystem-status` | GET /api/subsystem_status | (REST only) | viewer `subsystems` row |

This table is **complete-by-design** (§14.2): code that introduces a gesture must add its row here, with REST, frame, and mirror — or it is not integrated (§14.4).

---

## §6 — Sequences

```
send(gesture):
   key = gesture.idempotency_key ?? uuid()
   if echo: store.overlay.write(echo)
   inflight[key] = REST(gesture.kind → url, args, body: idempotency_key=key)
   await frame(done|error for this action) via FrameBus
      done  → overlay entry cleared (canonical frame already superseded it)
      error → overlay rollback + surface --accent-error envelope
telemetry(kind, snapshot):
   batch.push({kind, snapshot, t})
   debounced flush → POST /api/ui/telemetry
```

---

## §7 — Data

**Out:** REST per §5; `/api/ui/telemetry` batches. **In (indirectly):** the effect returns as frames to `FrameBus`; the gateway only awaits `done`/`error` to settle echoes. **Echo writes:** the store `overlay` slice only.

---

## §8 — Results

A gesture's result is always a frame (the backend's authoritative effect), rendered by a view reading the store. The gateway's own visible result is the optimistic echo (instant feedback) and, on error, the `--accent-error` surfacing. Its invisible result is faithful telemetry.

---

## §9 — REPL Mirroring

The gateway is the frontend half of the REPL round-trip (§14.1): a frontend gesture here is the exact analogue of a REPL action in `sim_frontend.py` — both hit the same REST route with an idempotency key, both produce the same frames, both update the same §10.5 mirror. The telemetry POST is what lets a *frontend* gesture show up in the REPL viewer; the REST route is what lets a *REPL* action show up in the frontend. The two directions are symmetric by construction (`repl_mirroring.md`).

---

## §10 — Theme

The gateway has no surface. Its one themed artefact is the error surfacing: a `done`/`error` failure renders the offending control's border in `--accent-error` (`theme.md` §4) with a monospace tooltip — the single non-steel state in the chrome.

---

## §11 — References

- `DOMAIN_MODEL.md`: §14.2 (gesture catalogue), §2.5 (idempotency), §14.3 (REPL idempotency), §10.2 (lifecycle), §10.5 (mirror).
- `code_constraints/api_routes.md`, `code_constraints/repl_actions.md`.
- Peers: `frame_bus.md`, `workspace_store.md`, `repl_mirroring.md`.
