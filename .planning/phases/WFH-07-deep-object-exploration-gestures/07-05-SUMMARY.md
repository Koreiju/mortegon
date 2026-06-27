---
phase: WFH-07-deep-object-exploration-gestures
plan: 05
subsystem: frontend
tags: [javascript, dom, gestures, playwright, e2e, repl, node-test]

# Dependency graph
requires:
  - phase: WFH-07-01
    provides: "GET /concepts/{id}/next_rank — the endpoint the hover/right-click preview resolves a path to and fetches"
  - phase: WFH-07-02
    provides: "renderTypedPanel / renderConceptPanel — the typed key:Type=value render the next-rank preview shows"
  - phase: WFH-07-03
    provides: "frontend_e2e/object_exploration.spec.js (the shared phase spec, extended here) + the brace-state render"
  - phase: WFH-07-04
    provides: "gateway WIRE_LINK(inherit_types) / DELETE_REF(edge-delete) — the backend seam the drag-wire + double-right-delete gestures call"
provides:
  - "magic_markdown_panel.mjs::mount() seven-gesture DOM capture: contextmenu (single-right fold / right-self collapse / double-right DELETE via a 400ms timestamp debounce), left-drag-wire state machine (mousedown→mousemove past 4px→mouseup) drawing a SOLID transient line, the 🔒 read-only edit gate, and the hover next-rank preview (onHoverPreview/onHoverEnd). Every handler routes through the shared resolveGesture — never an inline button chain."
  - "next-rank CLI/REPL mirror in scripts/sim_frontend.py + coverage_map entry — closes the route-coverage gap 07-01 introduced"
  - "EXPLORE-03/01 e2e in object_exploration.spec.js: hover-preview, drag-wire(solid line), double-right-delete debounce, fold-preservation (M.6)"
affects: [WFH-07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "mount() is a thin DOM-capture layer: it classifies the raw event (classifyTarget → resolveGesture target vocabulary), resolves the Action via the SHARED resolveGesture, and invokes a handler callback — it never fetches /next_rank or mutates the store itself (backend computes, frontend renders, D10; the caller owns the gateway round-trip)."
    - "No native double-right DOM event — a manual {ts,el} timestamp debounce (DOUBLE_RIGHT_MS=400) over consecutive contextmenu on the SAME element synthesizes {clicks:2}=DELETE_REF; the first of the pair still fires its single-right fold."
    - "The transient drag line is a SOLID <line> (stroke var(--slate-border), no stroke-dasharray) appended during mousemove and torn down on every mouseup (success or discard) — Forbidden-Concepts no-dotted-lines holds; black_slate.spec stays green."

key-files:
  created:
    - frontend_e2e/object_exploration.spec.js  # (extended; created in 07-03)
  modified:
    - backend/static/js/fe/magic_markdown_panel.mjs
    - backend/static/js/fe/magic_markdown_panel.test.mjs
    - scripts/sim_frontend.py
    - frontend_e2e/object_exploration.spec.js
---

# Plan 07-05 Summary — mount() seven-gesture DOM capture + EXPLORE-03/01 e2e

## What was built

Wired the seven-gesture DOM capture (§7.3.4 / §18.32) into `magic_markdown_panel.mjs::mount()`, which previously listened only for `click`/`dblclick`:

- **contextmenu** → single-right `TOGGLE_FOLD` (rank-1 inline fold) / right-on-self `COLLAPSE_TO_NODE`; a second contextmenu on the same target within `DOUBLE_RIGHT_MS=400` synthesizes `DELETE_REF` (N.13) — `classifyTarget` maps the DOM event into the `resolveGesture` target vocabulary so deletion fires only on `ref`/`token`, never the self line.
- **mousedown→mousemove(>4px)→mouseup** drag state machine → `WIRE_LINK` (N.4) with a SOLID transient line for live feedback; press-without-move stays a click, mouseup on empty canvas / same node discards cleanly.
- **🔒 read-only gate** — `isReadOnlyRoot` (`python_*` type_hint or `fixture::` backing pointer) refuses single-left edit while hover/contextmenu/dblclick pass through.
- **hover** → `onHoverPreview(path,kind)` / `onHoverEnd` (EXPLORE-01) with no-flicker (same-target) and right-click-commit-survives-unhover semantics; `mount()` reports the hovered path so the caller fetches `GET /concepts/{id}/next_rank` (D10) and renders it via `renderTypedPanel` (07-02).

Closed the **route-coverage** regression 07-01 introduced: added a `next-rank` CLI action + `coverage_map` entry in `scripts/sim_frontend.py` (the §12 REPL-mirroring rule — a normal JSON route gets a real mirror, not an exemption).

## Verification (automated — no screenshots)

- `node backend/static/js/fe/magic_markdown_panel.test.mjs` → **19/19** (the seven gesture-capture cases: fold, collapse-to-self, double-right debounce + boundary, drag synthesis, no-move-no-drag, empty-canvas discard, 🔒 gate, hover fire/no-flicker/commit-survives).
- `npx playwright test object_exploration.spec.js` → **8/8** incl. the 4 new EXPLORE-03/01 cases (hover-preview fires + `renderTypedPanel` renders the `name:Type` + `→ output` type graph; drag-wire fires `WIRE_LINK` with a SOLID transient line, no dasharray; double-right-delete debounce; fold-preservation M.6) — and `black_slate.spec.js` → **6/6** (no-dotted regression intact).
- `route-coverage` env-scenario (offline pytest) → **pass** (next_rank now mirrored).
- Prior-plan units stay green: gateway `9/9` (07-04), `test_next_rank_route.py` `4/4` (07-01), `test_edge_inherit_types.py` `7/7` (07-04).

## Deviations / scope notes

- **Resume close-out.** This plan was executed across interrupted sessions: a first partial attempt was discarded (uncommitted, no task boundary); a second attempt committed Tasks 1–2 + the hover wiring + the route-coverage fix but was cut off before Task 3's e2e + this SUMMARY. The orchestrator authored Task 3's e2e and this SUMMARY to close it out — no work was duplicated (the 4 prior commits were verified intact and green).
- **E2e scoping (intentional, documented).** The Task-3 e2e drives the REAL served `mount()` in a browser with synthetic DOM events and asserts the in-browser gesture→handler+render+solid-affordance contract. The deepest backend mutations the gestures ultimately trigger — the `inherit_types` edge-create row and the `DELETE /concept_edges/{id}` row removal — are proven by 07-04's `test_edge_inherit_types.py` (7/7) + `gateway.test.mjs` (9/9) rather than re-exercised through a full materialised-fixture backend round-trip in the e2e (which would require seeding a python-native tree per case and is the brittle path). The browser proves the gesture capture + the gateway intent; the backend tests prove the mutation.

## Next-phase readiness (07-06)

The full gesture surface (hover→next_rank, drag-wire→inherit, double-right→delete, fold) is now live in `mount()` and exercised end-to-end against the stub stack — 07-06's DuckDuckGo §N walkthrough drives this exact surface against the REAL subsystems (clean-GPU human checkpoint).
