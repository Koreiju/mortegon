# Requirements (PRD Intel)

Synthesized from 8 classified PRD documents (all precedence 6), all under the authority of
ADR-user-requirements-verbatim (precedence 0). Each requirement traces to its source PRD;
acceptance criteria are lifted from each doc's §6 / acceptance-bar section. One PRD yields
multiple requirements where the feature decomposes.

No competing acceptance variants were found across PRDs: the feature docs cover disjoint
scopes, and the only prior overlap (fixture count) is now uniformly reconciled to the §S
three-fixture baseline.

---

## REQ-three-register-model
- source: docs/features/three_register_model.md
- description: Three coupled workspace registers — Real (3D Projector), Imaginary (2D
  Concept-Graph Editor), Symbolic (REPL) — bound by an alchemical compose-compile-perimeter
  loop. The loop runs both ways: a REPL action can enter at any node and the GUI sees the
  result identically.
- acceptance:
  - 2D/3D separation maintained (perimeter outputs §6.6.1; 2D/3D separation §6.6.2).
  - WS frame telemetry mirrors register state.
  - §16.5 live-scan + DB-cleanup probe passes; purge returns the workspace to the
    three-fixture baseline (§S).
- scope: registers / Mortegon loop

## REQ-three-fixture-api
- source: docs/features/four_fixture_api.md  (title: "The Three-Fixture API (§S re-baselined; was four)")
- description: Three foundational fixtures (Agent, WebBrowser, Database) with their
  primitives, gestures, and acceptance bar. Identical invocation surface for user and agent.
  Concept-graph mutation gestures (create/link/overwrite/delete) are panel-scheme intrinsics
  routed via `/concepts` + `/concept_edges`; the former Editor fixture is demoted to those
  gestures (§S.1).
- acceptance:
  - `foundation_fixtures.ensure_foundation_fixtures` produces exactly THREE root
    python_object ConceptNodes with backing pointers `fixture::agent::<wsid>`,
    `fixture::web_browser::<wsid>`, `fixture::database::<wsid>`.
  - No `fixture::editor::<wsid>` card materialises (§S.1).
  - `three-fixtures-present` scenario green (the old `four-fixtures-present` survives only as
    an alias).
- scope: foundational fixtures / API surface
- note: Historical four-fixture acceptance criteria (incl. an Editor card) are superseded by
  the §S banner at the top of the source doc.

## REQ-live-scan-cleanup
- source: docs/features/live_scan_cleanup.md
- description: Mandatory acceptance probe verifying a real archive.org scan, real retrieval,
  and the workspace purge cleanup contract round-trip against the live full stack.
- acceptance:
  - `live-scan-real-with-cleanup` probe passes (all_real-gated; skips in stub).
  - Real Selenium scan completes; TF-IDF + nomic indices alive; real-UMAP 6D fit over the
    scanned space.
  - Purge cleanup contract: `layout_dropped` + `tfidf_rows_dropped`; Kuzu ConceptNode count
    returns to the three-fixture baseline (§S).
  - `GET /api/concepts` count == foundation-fixture baseline (three fixtures + materialised
    member trees).
  - Re-scan rebuilds to a comparable pool.
- scope: scanning / persistence / CI acceptance

## REQ-halo-retrieval
- source: docs/features/halo_retrieval.md
- description: Apparition halo — concentric-ring retrieval visualisation with ray-projection
  coupling, 6D-UMAP HSV state, multi-frequency PageRank ranking, and autoregressive
  click-walk; soft/hard link promotion.
- acceptance:
  - Halo phantoms show candidate name only; scores in slow-hover tooltips.
  - Ranking by triple product (pagerank · tfidf_cos · nomic_cos); no graph-analytics axes.
  - Halo stays proximal to the central node, abstracting over folded semantic complexity
    (§S.5).
  - Autoregressive walk advances via click; ApparitionService + Halo renderer wired.
- scope: retrieval / halo

## REQ-signal-stream
- source: docs/features/signal_stream.md
- description: Signal-stream display constraint — panels render only ONE iterable signal at a
  time, advanced via play/pause/step rollout; the cascade re-fires per visible signal.
- acceptance:
  - `signal_stream` UIStateService mirror field holds the current signal index.
  - `RolloutCoordinator` advances iteration; `/api/ui/signal_advance` recompiles the
    `{ref}`-consumers per sample (§R.7 / §4.6.1).
  - Applies across pattern_map iteration, url_set panel iteration, Database.concept iterables.
- scope: iteration / rollout / 2D panel rendering

## REQ-pattern-map
- source: docs/features/pattern_map.md
- description: `pattern_map` ConceptNode output panel that materialises and updates live
  during a WebBrowser scan, rendering one chunk-pattern schema at a time under signal-stream.
- acceptance:
  - Live `pattern_map` ConceptNode materialises during scan and updates in place.
  - Golden-trio joint-presence gate (§15.8.1); a second scan accretes into the same peer node.
  - PageRank traverses the same Kuzu ConceptEdge graph.
  - One pattern schema rendered at a time under signal-stream.
- scope: scanner / live output

## REQ-6d-umap
- source: docs/features/6d_umap.md
- description: A 6D UMAP fit giving each chunk a manifold position (3D) plus camera-azimuth-
  rotated HSV colour (3D) across projector, halo, and readout nodes.
- acceptance:
  - LayoutService emits a 6-vector `umap_canonical` WS frame on scan-end joint fit (§11.5).
  - HSV rotates with camera azimuth across Projector, Halo phantoms, and type-only readout
    nodes.
  - Frontend renders only; no UMAP runtime client-side.
- scope: layout / colour / projector

## REQ-click-to-edit
- source: docs/features/click_to_edit.md
- description: Click-to-edit field interaction — pure-print panels with hidden hover overlays
  that swap to textareas on click; Shift-Enter multiline; plus-sign row growth; commit-on-
  Enter through the lifecycle.
- acceptance:
  - Pure-print panel; hidden overlay buttons appear on hover; click swaps row to textarea.
  - Shift-Enter inserts a newline (multiline); Enter commits through ConceptLifecycle.
  - Plus-sign field-tree growth (`+→` parent→child, `+↓` sibling); empty rows hide.
  - Edit-cycle state machine routed via the single lifecycle dispatcher.
- scope: frontend / field-tree editing
