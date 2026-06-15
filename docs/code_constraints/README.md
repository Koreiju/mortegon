# Code Constraints

> **Layer purpose.** This directory carries one document per programming surface in the codebase. Each constraint doc articulates the *must-hold* and *must-not* conditions that realise the upstream object and feature layers in actual code — concurrency rules, persistence invariants, REST and WebSocket shape contracts, frontend rendering rules, REPL gesture catalogues, test scenarios, error-handling conventions, and CI acceptance gates.
>
> Constraint docs are the layer where **what the codebase has to do** lives. They are derived from features and objects; when a constraint disagrees with a feature or object, the constraint is wrong and must be updated to match.
>
> See [`DOC_MAP.md`](../DOC_MAP.md) §4 for the place of this layer in the documentation chain.

---

## §0 — Reading Order

Constraints organise along programming surface, not along feature. Read by surface for *what the code has to do at that surface* across every feature touching it:

1. **Lifecycle invariants** — the central dispatcher and its fan-out; the most load-bearing constraint set.
2. **API routes** — REST contract, idempotency keys, error envelopes.
3. **WS frames** — frame schema, sequencing, backpressure, dual-routing.
4. **Backend services** — singleton rules, threading, fake-gate semantics.
5. **Frontend rendering** — what must render and what must never.
6. **REPL actions** — gesture catalogue contract (§14.2).
7. **Env scenarios** — what env-scenarios assert and what acceptance bar each carries.
8. **Streaming, persistence, concurrency, errors, testing, CI** — cross-cutting programming concerns.

---

## §1 — Constraint Catalogue

| Doc | Surface | Domain anchor | Owner role |
|---|---|---|---|
| [`lifecycle_invariants.md`](lifecycle_invariants.md) | `apply_update_lifecycle` / `apply_delete_lifecycle` | §2.2, §10.2 | The one-and-only-one mutation dispatcher; every actor enters through it |
| [`api_routes.md`](api_routes.md) | `backend/api/routes.py` REST endpoints | §2.5, §10 | URL shape, body schema, idempotency, error envelopes, four-fixture endpoints |
| [`ws_frames.md`](ws_frames.md) | `backend/api/ws_frames.py` WebSocket frames | §2.4, §10.1, §18.1 | Frame type schema, monotone `frame_seq`, lossy backpressure, workspace-WS dual-routing |
| [`backend_services.md`](backend_services.md) | `backend/services/*.py` | §2.1, §2.3, §13 | Service singletons, threading, real-vs-fake gates, no quiet degradation |
| [`frontend_rendering.md`](frontend_rendering.md) | `backend/static/js/cp/*.js` | §4, §6, §8, §forbidden-concepts | What renders / never renders; the unified-panel one-template rule; the no-dashed-lines rule |
| [`repl_actions.md`](repl_actions.md) | `scripts/sim_frontend.py` `_ACTIONS` | §14.2 | Every gesture's REPL action; the 5-tuple contract; the gesture catalogue is complete-by-design |
| [`env_scenarios.md`](env_scenarios.md) | `scripts/sim_frontend.py` env-scenarios | §14.4 | What each scenario asserts; the full-smoke chain; the acceptance bar |
| [`streaming.md`](streaming.md) | Workspace WS + LayoutService streaming | §6.1, §10.1, §10.3, §18.1 | Live-scan flow; UMAP refit cadence; chunk dual-routing; no severance |
| [`persistence.md`](persistence.md) | Kuzu + LayoutFrame + on-disk | §11, §11.1 | What lives in Kuzu vs in-memory vs on disk; cleanup contract |
| [`concurrency.md`](concurrency.md) | Lifecycle + cascade + agent + scanner | §2.6, §2.7, §7.4 | Optimistic concurrency; last-write-wins; actor-aware short-circuit; rollback as conflict-resolution tool |
| [`error_handling.md`](error_handling.md) | Across all backend services + frontend | §2.8, §13 | 503-or-loud; no quiet stub fallback; missing-load-equals-hard-error |
| [`testing.md`](testing.md) | env-scenarios + probes + full-smoke | §14.4, §16 | Real-stack mode AND stub mode; full-smoke green; lodestar probes |
| [`ci_acceptance.md`](ci_acceptance.md) | CI pipeline | §13.2, §16.5 | `all_real: true` gate; full-smoke per merge; live-scan probe per release |
| [`security.md`](security.md) | Routes + DB + storage | §11, §13 | On-device only; no cloud APIs; user data never leaves device |
| [`forbidden_patterns.md`](forbidden_patterns.md) | All surfaces | §forbidden-concepts; §18 | The anti-pattern catalogue reiterated per surface |

---

## §2 — Constraint Doc Anatomy

Every constraint doc follows the same anatomy:

1. **Surface scope** — exactly which files and which programming concern.
2. **Domain anchor** — which DOMAIN_MODEL section(s) the constraint derives from.
3. **Must-hold** — conditions the code must guarantee, with the design rationale for each.
4. **Must-not** — anti-patterns forbidden by the design.
5. **Test signal** — the env-scenario or probe that verifies the must-hold conditions; the regression signature each must-not condition would produce.
6. **Code anchor** — which file(s) implement the surface.
7. **Anti-goal anchor** — the §18 anti-goal each must-not entry guards against.
8. **Feature touchpoints** — which features depend on the constraint holding.

---

## §3 — Cross-Constraint Map

Some must-holds compose across surfaces. The map below names where one constraint depends on another.

| If this surface | Must hold | Then this surface | Must hold |
|---|---|---|---|
| Lifecycle invariants | Every mutation broadcasts `concept_changed` | WS frames | `concept_changed` schema is stable; sequencing is monotone |
| Lifecycle invariants | Every mutation records an EditDiff | Persistence | EditDiff appended atomically with the mutation |
| Backend services | LayoutService produces a 6-vector per chunk | WS frames | `umap_canonical` frame carries the 6-vector |
| Backend services | LayoutService rescales agent-output chunks to perimeter | Frontend rendering | Renderer reads provenance and applies HSV phase to perimeter chunks identically |
| WS frames | Dual-routes scan-emitted frames to workspace-WS | Streaming | Long-lived workspace WS receives chunk_added and umap_canonical without subscribing to per-snapshot WS |
| API routes | Every mutation endpoint accepts idempotency key | Lifecycle invariants | Re-application of identical key returns prior effect without re-dispatching |
| REPL actions | Every gesture in §14.2 catalogue has a REPL action | env scenarios | Every REPL action is referenced by at least one env-scenario assertion |
| env scenarios | Full-smoke chain runs every scenario | CI acceptance | Pipeline rejects merge if full-smoke is red in either real-stack or stub mode |
| Error handling | Missing GGUF or dead Selenium returns 503 | Frontend rendering | Frontend surfaces error gracefully; does not present stub data as success |
| Concurrency | Cascade scheduler's actor-aware short-circuit prevents agent self-loops | Lifecycle invariants | Emitter-emitted mutations do not re-trigger the same agent's perception in the same tick |

---

## §4 — Surface → Anti-Goal Cross-Reference

| Surface | Primary §18 anti-goal it guards |
|---|---|
| Lifecycle invariants | §18.16 Agent fixture missing — guard: foundation_fixtures runs four-fixture materialiser |
| Lifecycle invariants | §18.22 Foundation fixtures deletable — guard: `apply_delete_lifecycle` rejects fixture deletes |
| Lifecycle invariants | §18.27 Foundation fixture count drift — guard: foundation_fixtures emits exactly THREE python_object trees (§S removed Editor) |
| Lifecycle invariants | §18.28 Library middleware orphan trees — guard: re-import re-walks and bumps backing-pointer version |
| API routes | §18.5 Recompute UMAP doesn't fire twice — guard: `/recompute_umap` runs unconditionally |
| API routes | §18.13 Hover preview stops after first result — guard: hover endpoint always responds, no stateful gate |
| WS frames | §18.1 Scan ↔ streaming severance — guard: dual-route + workspace_id injection |
| WS frames | §18.29 pattern_map output not live-updating — guard: pattern_map mutation emitted on every detected pattern |
| Backend services | §18.3 3D spacing too close — guard: COLLIDER_SAFETY ≥ 2.0 on both backend and frontend |
| Backend services | §18.17 Misplaced nodes / outlier geometry — guard: joint UMAP fit over full TF-IDF index |
| Backend services | §18.20 Common origin for all scans — guard: per-URL `root_position` placement |
| Backend services | §18.23 Agent outputs lost to manifold interior — guard: perimeter-encompassing rescale per emission |
| Backend services | §18.25 Single-frequency PageRank persisting — guard: apparition_service reports active mode |
| Backend services | §18.30 URL-set panel iteration parallel-fire — guard: compile resolves urls_panel per signal-stream |
| Frontend rendering | §18.7 Stray dotted lines — guard: no stroke-dasharray in any cp/*.js SVG |
| Frontend rendering | §18.8 Click-pinned panel in wrong place — guard: freeze-at-hover-rect mechanic |
| Frontend rendering | §18.9 3D UI resize stuck — guard: ResizeObserver + setSize(_, _, false), no no-change guard |
| Frontend rendering | §18.10 Images stopped displaying — guard: single-fetch path with IDB cache |
| Frontend rendering | §18.11 Two different knowledge panels — guard: one _buildPanelDom for all surfaces |
| Frontend rendering | §18.12 URL click explodes all nodes — guard: IntersectionObserver spine scoping |
| Frontend rendering | §18.14 Eye button doesn't hide chunks — guard: per-URL `hidden_urls` set read by animate loop |
| Frontend rendering | §18.18 Camera zooms too far in — guard: per-frame minDistance/maxDistance recompute |
| Frontend rendering | §18.19 Two-panel split — guard: one panel anatomy enforced through single render template |
| Frontend rendering | §18.21 Compact-form regression — guard: halo phantom carries name only |
| Frontend rendering | §18.24 Signal-stream constraint violated — guard: panel renderer reads signal_index, hides other iterable elements |
| Frontend rendering | §18.26 Ray-projection mismatched HSV — guard: phantom reads parent chunk's HSV from LayoutFrame |
| Frontend rendering | §18.31 2D/3D coordinate cross-coupling — guard: pin captures screen rect not 3D coord |
| REPL actions | §14.4 Acceptance bar — guard: every new gesture extends §14.2 with all 5 fields |
| env scenarios | §14.4 Acceptance bar — guard: every new gesture has at least one env-scenario asserting round-trip |
| Error handling | §13 No-Mocks contract — guard: missing GGUF returns 503, no stub fallback |
| Persistence | §18.4 Old domains persist after purge — guard: purge handler walks every concept; LayoutFrame dropped; TF-IDF zeroed |
| Forbidden patterns | Forbidden-concepts §1 — guard: no fibSphereUnit / docShellRadius / clusterRadius as primary layout |
| Forbidden patterns | Forbidden-concepts §3 — guard: no Llama anywhere; slm_client rejects WFH_SLM_MODEL=*llama* |

---

## §5 — How To Read A Constraint Doc

A constraint doc tells you *what to check when changing the code* on the named surface. The recommended reading order when changing code:

1. Open the constraint doc for the surface you are editing.
2. Read the **must-hold** section to confirm your change preserves the invariants.
3. Read the **must-not** section to confirm your change does not introduce a forbidden pattern.
4. Run the env-scenario(s) listed in **test signal**.
5. If the change adds a new must-hold or surfaces a new must-not, update the constraint doc.
6. If the change resolves a §18 anti-goal, link the resolution from the constraint doc to the §18 entry; the anti-goal stays in DOMAIN_MODEL §18 as a guard against recurrence.

---

## §6 — How To Extend This Layer

When a new programming surface emerges:

1. Add a new `<surface>.md` constraint doc.
2. Update [`DOC_MAP.md`](../DOC_MAP.md) §4 catalogue.
3. Update [`README.md`](README.md) (this file) §1 catalogue.
4. Update the §3 cross-constraint map if the new surface depends on or is depended upon by existing ones.
5. Update the §4 surface → anti-goal table.
6. Link the relevant feature docs to the new constraint doc.

When the domain model adds a new anti-goal:

1. Identify which surface(s) the regression touches.
2. Add a guard entry to the relevant constraint doc(s) `must-not` section.
3. Update the §4 surface → anti-goal table.
4. Add or extend an env-scenario in [`env_scenarios.md`](env_scenarios.md) to verify the guard holds.

When a new feature lands:

1. The feature doc in [`../features/`](../features/) lists which constraint docs it touches.
2. Update each named constraint doc with a feature touchpoint entry.
3. Add the feature's REPL action to [`repl_actions.md`](repl_actions.md).
4. Add the feature's env-scenario to [`env_scenarios.md`](env_scenarios.md).
