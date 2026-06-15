# Features

> **Layer purpose.** This directory carries one document per cross-cutting user-visible feature in the workspace. Each feature doc elaborates [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) into the *feature-level realisation* — the UX contract in prose, the full gesture-to-effect state machine, the REPL action / WebSocket frame / frontend render / telemetry quadruple, the acceptance bar — and cross-references the relevant objects in [`object_model/`](../object_model/) and code constraints in [`code_constraints/`](../code_constraints/).
>
> Feature docs are the layer where **what the user does** lives. Object docs decompose objects; feature docs cross-compose them along user-visible axes.
>
> See [`DOC_MAP.md`](../DOC_MAP.md) §3 for the place of this layer in the documentation chain.

---

## §0 — Reading Order

Features cluster naturally by the register they primarily belong to (per the Mortegon §1.1). Read by register:

1. **Framing features** — the philosophical anchors that govern multiple registers.
2. **API features** — the three-fixture surface (§S; was four) and the library middleware.
3. **Retrieval features** — halo, ranking, autoregression.
4. **3D / projector features** — manifold, UMAP, visibility, click-and-stick.
5. **Panel / editor features** — click-to-edit, plus-signs, signal-stream, autocomplete, play/pause.
6. **Scanner features** — pattern_map, URL-set, golden trio, type inheritance.
7. **Observability + verification features** — REPL, in-place viewer, live-scan probe, evolution log.

> **Reconciliation note (2026-05-30).** Existing feature docs are reconciled to §M/§N/§O (gestures, halo gating, chunk-storage, no-arrowheads). Some catalogued docs were never created (`compile_collapse_dialectic`, `plus_sign_field_tree`, `autoregressive_halo`, and others below) — their behaviour is now canonical in `DOMAIN_MODEL.md` (§7.3.4 / §7.3 / §8.2.2 / §4.6) + the [`../frontend/`](../frontend/) suite; treat those as the source and disregard dangling links here. **Files that exist:** `three_register_model`, `four_fixture_api`, `halo_retrieval`, `6d_umap`, `signal_stream`, `click_to_edit`, `pattern_map`, `live_scan_cleanup` — every other catalogued row is planned (no file yet).

---

## §1 — Framing Features

Cross-register features that shape how every other feature behaves.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`three_register_model.md`](three_register_model.md) | §1.1, §1.5 | The Real / Imaginary / Symbolic Mortegon alchemy; the bidirectional flow between projector / editor / REPL |
| [`compile_collapse_dialectic.md`](compile_collapse_dialectic.md) | §7.3 | Double-left-click panel ↔ subgraph as the synthesis/analysis dialectical inversion (right-click = rank-1 reveal, §7.3.4) |
| [`hard_soft_links.md`](hard_soft_links.md) | §3.2.1 | Committed `ConceptEdge` vs halo-suggested apparition; commitment fan vs possibility ring |
| [`projective_inverse.md`](projective_inverse.md) | §7.7 | Closest-inverse as the Imaginary's purely projective property; automatic per-Compile |
| [`agent_integration_scheme.md`](agent_integration_scheme.md) | §12.2.1 | The agent tick as recursion-over-iteration integration with world perceptions as initial conditions |
| [`perimeter_outputs.md`](perimeter_outputs.md) | §6.6.1 | Agent-output chunks at the projector's outer envelope (geometric Imaginary → Real return) |
| [`2d_3d_separation.md`](2d_3d_separation.md) | §6.6.2 | The 2D and 3D canvases share no coordinate system; coupling only through click-and-stick and live output projection |

---

## §2 — API Features

The three-fixture surface (§S; was four) and its generalisation.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`four_fixture_api.md`](four_fixture_api.md) | §9.5, §9.5.1, §12.6.1 | Agent / WebBrowser / Database as foundational fixtures (Editor demoted to mutation-gestures, §S); identical surface for user and agent |
| [`library_imports_middleware.md`](library_imports_middleware.md) | §9.7 | Generalised materialiser walking arbitrary Python module hierarchies; idempotent on qualified names |

---

## §3 — Retrieval Features

The halo and the multi-frequency rank.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`halo_retrieval.md`](halo_retrieval.md) | §8.2, §8.2.1, §8.2.1.1, §8.2.1.2 | Concentric-circle radiation + ray-projection to conic surface + HSV-rotating collapsed phantoms |
| [`multi_frequency_pagerank.md`](multi_frequency_pagerank.md) | §8.1.1 | Token / phrase / paragraph / document / pattern bands; PageRank-weighted aggregation |
| [`autoregressive_halo.md`](autoregressive_halo.md) | §8.2.2 | Click promotes soft to hard, spawns new focal, new halo radiates; walking the retrieval space |

---

## §4 — 3D / Projector Features

The manifold and its UMAP-driven structure.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`6d_umap.md`](6d_umap.md) | §6.1, §8.2.1.2 | UMAP fits 3 position + 3 HSV jointly; HSV rotates with camera azimuth |
| [`visibility_spine.md`](visibility_spine.md) | §6.4, §8.3 | IntersectionObserver-driven viewport spine; only visible result rows have visible 3D chunks |
| [`click_and_stick.md`](click_and_stick.md) | §4.2 | Freeze-at-hover-rect: pinned panel materialises at the exact screen rect the hover billboard occupied |
| [`multi_scan_layout.md`](multi_scan_layout.md) | §9.5 | Per-URL `root_position`, `bounding_radius`, no-mutation-of-existing-URLs-on-new-scan |

---

## §5 — Panel / Editor Features

The 2D editor's surfaces.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`click_to_edit.md`](click_to_edit.md) | §4.1.1 | Hidden-overlay buttons over print tokens; Shift-Enter for newline; Enter for commit |
| [`plus_sign_field_tree.md`](plus_sign_field_tree.md) | §4.6 | Right (`+→`) and bottom (`+↓`) plus-signs progressively grow a singular compute node into a full panel |
| [`signal_stream.md`](signal_stream.md) | §4.6.1 | Iterables in panels render one signal at a time; advance by play/pause stepper |
| [`play_pause_rollout.md`](play_pause_rollout.md) | §7.5 | Edit between iterations of a compiled compute graph; cascade re-fires per signal |
| [`autocomplete.md`](autocomplete.md) | §4.7 | Multi-frequency ranking over linked structures; scoped to python-object trees when applicable |
| [`empty_primitive_radiation.md`](empty_primitive_radiation.md) | §5.1 | Typing in a fresh empty node radiates apparitions ranked by multi-frequency aggregation |
| [`variable_auto_creation.md`](variable_auto_creation.md) | §17.8 | Typed `{slug}` references auto-create the empty primitive when no matching node exists |

---

## §6 — Scanner Features

The DOM scanning + chunk-pattern pipeline.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`pattern_map.md`](pattern_map.md) | §15.8.2 | Live-streaming output panel for chunk-pattern schemas; signal-stream over `pattern_hash` keys |
| [`url_set_panel.md`](url_set_panel.md) | §15.7 | User-created URL aggregator referenced as `{urls_panel}`; url-specific TF-IDF tokenisation |
| [`golden_trio.md`](golden_trio.md) | §15.8.1 | Title / link / content joint-presence rule for content-precise extraction |
| [`type_inheritance.md`](type_inheritance.md) | §15.9 | Passthrough composition of content patterns through `{var}` references and typed-edge chains |
| [`live_scan_streaming.md`](live_scan_streaming.md) | §17.1, §18.1 | Workspace-WS dual-routing; chunks reach the long-lived frontend WS without severance |

---

## §7 — Observability + Verification Features

The Symbolic register's surfaces and the acceptance probes.

| Doc | Domain anchor | What it captures |
|---|---|---|
| [`repl_two_way_feedback.md`](repl_two_way_feedback.md) | §14, §14.1 | REPL action → backend mutation → WS frame → frontend renders → telemetry → REPL reads back |
| [`in_place_activity_viewer.md`](in_place_activity_viewer.md) | §14.5, §11.8 | Fixed-structure terminal dashboard refreshed via ANSI cursor codes |
| [`live_scan_cleanup.md`](live_scan_cleanup.md) | §16.5 | Mandatory real-site scan + DB-cleanup probe; verifies repeatability of the Real-Imaginary loop |
| [`evolution_log_rollback.md`](evolution_log_rollback.md) | §11.4 | Append-only diff log; single / range / actor rollback scopes |
| [`no_mocks_contract.md`](no_mocks_contract.md) | §13 | Real GPT4All + nomic + Selenium + LangGraph in production paths; fake gates harness-only |

---

## §8 — Feature → Anti-Goal Cross-Reference

Each feature has a primary §18 anti-goal that guards against its most likely regression. The table below maps each feature to its guardian anti-goal; the code constraint docs in [`code_constraints/`](../code_constraints/) reiterate these per programming surface.

| Feature | Primary anti-goal | DOMAIN_MODEL §18 |
|---|---|---|
| three_register_model | Two-panel hover/click split | §18.11 |
| four_fixture_api | Foundation fixture count drift | §18.27 |
| library_imports_middleware | Library middleware orphan trees | §18.28 |
| halo_retrieval | Concentric sphere as primary layout | §18.2 / forbidden-concepts §1 |
| halo_retrieval | Compact-form regression (halo showing scores) | §18.21 |
| halo_retrieval | Ray-projection mismatched HSV | §18.26 |
| multi_frequency_pagerank | Single-frequency PageRank persisting | §18.25 |
| autoregressive_halo | (covered by halo_retrieval) | — |
| 6d_umap | (covered by halo_retrieval HSV mismatch) | §18.26 |
| visibility_spine | URL click explodes all nodes | §18.12 |
| visibility_spine | Eye button doesn't hide chunks | §18.14 |
| click_and_stick | Click-pinned panel materialises in wrong place | §18.8 |
| click_to_edit | (no specific anti-goal yet — flag for §18 add if regressions seen) | — |
| plus_sign_field_tree | (no specific anti-goal yet) | — |
| signal_stream | Signal-stream constraint violated by full-iterable rendering | §18.24 |
| play_pause_rollout | (no specific anti-goal yet) | — |
| autocomplete | (no specific anti-goal yet) | — |
| pattern_map | `pattern_map` output not live-updating during scan | §18.29 |
| url_set_panel | URL-set panel iteration fired all-at-once | §18.30 |
| live_scan_streaming | Scan ↔ streaming severance | §18.1 |
| live_scan_cleanup | (own scenario; doubles as anti-goal #18.1 verification) | §18.1 |
| repl_two_way_feedback | Scan ↔ streaming severance | §18.1 |
| in_place_activity_viewer | (no specific anti-goal — viewer is the operator's truth) | — |
| evolution_log_rollback | (no specific anti-goal yet) | — |
| no_mocks_contract | Llama as SLM target | forbidden-concepts §3 |
| perimeter_outputs | Agent outputs lost to manifold interior | §18.23 |
| 2d_3d_separation | 2D / 3D coordinate cross-coupling | §18.31 |
| compile_collapse_dialectic | (covered by §18.11 two-panel split) | §18.11 |

---

## §9 — Feature Doc Anatomy

Every feature doc follows the same anatomy so cross-doc reading is predictable:

1. **Domain anchor** — link to DOMAIN_MODEL §X.Y(.Z) section(s) the feature elaborates.
2. **Status** — realised / specified / planned / deprecated.
3. **What the user sees** — prose UX contract; no implementation.
4. **Cross-objects** — list of object_model docs the feature touches; each link carries the role the object plays in this feature.
5. **Gestures** — REPL action(s), GUI gesture(s), agent emit-path(s).
6. **State machine** — gesture-to-settled-state sequence; mirrors the §17 functional-sequence diagrams in DOMAIN_MODEL where applicable.
7. **WS frames + telemetry** — what crosses the wire; what UI state mirror fields are updated.
8. **Acceptance bar** — which env-scenario asserts the round-trip; what the assertion checks.
9. **Anti-goal** — the primary §18 regression the feature is at risk of; what guards against it.
10. **Code constraints** — pointer to code_constraints/`<surface>`.md entries that articulate the programming-side conditions for this feature.

---

## §10 — How To Extend This Layer

When the domain model adds or refines a feature:

1. Add or update the relevant `<feature>.md` in this directory.
2. Update [`DOC_MAP.md`](../DOC_MAP.md) §3 catalogue with the new doc.
3. Update [`README.md`](README.md) (this file) §1 – §7 with the new doc, grouped by register.
4. Update the §8 feature → anti-goal map with the primary regression the feature is at risk of.
5. Cross-link the relevant `object_model/<O>.md` doc(s) with the new feature.
6. Add or update the relevant `code_constraints/<surface>.md` entries.
7. Add a REPL action to `code_constraints/repl_actions.md` and an env-scenario to `code_constraints/env_scenarios.md`.
8. Where the feature implies a new §18 anti-goal, add it to DOMAIN_MODEL §18 first, then cross-reference.
