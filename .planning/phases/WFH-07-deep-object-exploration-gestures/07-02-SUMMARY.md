---
phase: WFH-07-deep-object-exploration-gestures
plan: 02
subsystem: frontend
tags: [magic-markdown, typed-rendering, rank-1-minimalism, vanilla-js]

# Dependency graph
requires: ["WFH-07-01: GET /api/concepts/{id}/next_rank rank-1 type-graph fetch endpoint"]
provides:
  - "renderTypedPanel(conceptNode, opts) — pure Line[]-shaped key:Type=value typed render for python-native/read-only nodes"
  - "isReadOnlyTypedNode(conceptNode) — single gate condition (python_ type_hint / fixture:: backing_pointer / read_only===true)"
  - "renderConceptPanel(conceptNode, opts) — dispatch seam selecting typed vs structural render"
affects: [WFH-07-03, WFH-07-04, WFH-07-05, WFH-07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Typed-rendering gated on isReadOnlyTypedNode ONLY — never a separate show-types flag; couples read-only-ness and typed presentation exactly as the legacy cp/concept_graph.js 🔒 check does"
    - "renderTypedPanel does its OWN JSON.parse of the ConceptNode's data/value (signature/ports.inputs/outputs/members shapes) rather than operating on the parsed magic_markdown {text,children} tree — the two render modes consume different input shapes by design"

key-files:
  created: []
  modified:
    - backend/static/js/fe/magic_markdown.mjs
    - backend/static/js/fe/magic_markdown.test.mjs

key-decisions:
  - "renderTypedPanel(conceptNode, opts) takes the backend ConceptNode shape (type_hint/read_only/backing_pointer/data/value), NOT a parsed magic_markdown tree node — confirmed via grep that no fe/*.mjs file currently passes ConceptNode-shaped fields (type_hint/read_only/backing_pointer) anywhere; this plan is the first wiring of that shape into fe/, exactly as RESEARCH/PATTERNS flagged (greenfield, no legacy literal-port target)"
  - "Added renderConceptPanel as the single dispatch seam (typed vs structural) rather than overloading renderPanel's existing signature — renderPanel(treeNode, opts) is called throughout magic_markdown_panel.mjs/integration.test.mjs/panel.test.mjs with a PARSED tree node, never a ConceptNode; changing its signature would have broken every existing caller. renderConceptPanel is purely additive and is the W4-flagged selection seam the plan asked for."
  - "magic_markdown_panel.mjs's panelVDom/mount were NOT modified — they consume renderPanel(treeNode, opts) directly and have zero ConceptNode-shaped input today (confirmed by grep). Wiring renderConceptPanel into panelVDom would require panelVDom to also accept/branch on a ConceptNode, which is a DOM-vdom-layer change outside this plan's stated files_modified (magic_markdown.mjs + .test.mjs only) and outside Task 1/2's explicit scope (a pure-function + Wave-0 test scaffold). This is the W4 confirmation: renderPanel lives solely in magic_markdown.mjs at the model level; the vdom-layer consumption of renderConceptPanel is left to whichever downstream 07-0x plan wires real ConceptNode data into the DOM (the next_rank endpoint consumer)."

patterns-established:
  - "Pattern: any future typed-rendering consumer (e.g. the next_rank-fetch hover preview) should call renderConceptPanel(conceptNode, opts), never call renderTypedPanel or renderPanel directly and branch on type_hint itself — the gate lives in ONE place (isReadOnlyTypedNode)."

requirements-completed: [EXPLORE-01]

# Metrics
duration: 18min
completed: 2026-06-24
---

# Phase WFH-07 Plan 02: Typed key:Type=value render mode + type-stripped rank-1 minimalism Summary

**Added `renderTypedPanel`/`isReadOnlyTypedNode`/`renderConceptPanel` to `magic_markdown.mjs`, re-implementing the legacy `_pythonNativeTypedView` algorithm as a pure `Line[]` function gated on the exact same read-only condition the legacy 🔒 check uses, with 5 new Wave-0 unit cases proving typed rendering, member rendering, the rank-1-minimalism type-stripping invariant, gate-selection, and a defensive malformed-data fallback.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-24T01:14:50Z
- **Completed:** 2026-06-24T01:24:33Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `renderTypedPanel(conceptNode, opts)` — parses the ConceptNode's `data`/`value` JSON (mirroring `_pythonNativeTypedView`'s `d.signature`/`d.ports.inputs`/`outputs`/`d.members` shapes), emits `Line[]` rows in the project's existing shape (`{depth,text,glyph,refTarget,path,source}`), with `"name : Type"` rows (value-included variant `"name : Type = value"` when a value is known), a trailing `"→ ReturnType"` row for functions, last-`::`-segment member rows for objects, and a defensive verbatim-row fallback on malformed/non-JSON data (T-07-03)
- `isReadOnlyTypedNode(conceptNode)` — the single gate (`/^fixture::/.test(backing_pointer) || /^python_/.test(type_hint) || read_only===true`), matching the legacy `cp/concept_graph.js` ~line 1687 check exactly
- `renderConceptPanel(conceptNode, opts)` — the dispatch seam: typed nodes route through `renderTypedPanel`; everything else parses `value`/`data` via the existing `parse()` and renders through the UNCHANGED structural `renderPanel`
- 5 new test cases in `magic_markdown.test.mjs`, all passing alongside all 18 pre-existing cases (23/23 total); sibling files `integration.test.mjs` (5/5), `magic_markdown_gestures.test.mjs` (11/11), `magic_markdown_panel.test.mjs` (7/7) all green — zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: renderTypedPanel pure function (key:Type=value mode, gated on read-only condition)** - `880a979` (feat)
2. **Task 2: Wave-0 unit-test scaffold for the typed-render mode** - `487e937` (test)

**Plan metadata:** (this commit) `docs(07-02): complete plan`

## Files Created/Modified
- `backend/static/js/fe/magic_markdown.mjs` - Added `isReadOnlyTypedNode`, `renderTypedPanel`, `renderConceptPanel`; exported all three from the module's named exports and default object
- `backend/static/js/fe/magic_markdown.test.mjs` - Added 5 test cases covering the four `<behavior>` requirements from Task 1 plus one extra defensive-fallback case (T-07-03)

## Decisions Made

- **`renderTypedPanel` takes the ConceptNode shape, not a parsed tree node** — confirmed (grep across `backend/static/js/fe/*.mjs`) that no existing fe/ module passes `type_hint`/`read_only`/`backing_pointer` fields anywhere; `renderPanel`'s existing signature operates exclusively on parsed `{text,children}` tree nodes. The two functions intentionally consume different input shapes; `renderConceptPanel` is the seam that reconciles them.
- **`renderConceptPanel` added as a new function rather than changing `renderPanel`'s signature** — `renderPanel(treeNode, opts)` is called directly by `magic_markdown_panel.mjs::panelVDom/graphVDom`, `integration.test.mjs`, `magic_markdown_panel.test.mjs`, and every existing case in `magic_markdown.test.mjs` itself, always with a parsed tree node. Overloading it to also accept a ConceptNode would require type-sniffing on every call site and risked breaking 18 passing pre-existing tests. `renderConceptPanel` is purely additive.
- **(W4 resolution) `magic_markdown_panel.mjs` was NOT modified.** `panelVDom`/`mount` consume `renderPanel(treeNode, opts)` directly today and have no ConceptNode-shaped input path at all (confirmed by grep — zero hits for `type_hint`/`read_only` outside the vendor bundle). Wiring `renderConceptPanel` into the DOM-vdom layer is a real, separate seam (panelVDom would need to accept a ConceptNode and branch), but it is outside this plan's `files_modified` list (`magic_markdown.mjs` + `.test.mjs` only) and outside Task 1/2's explicit scope (a pure model-level function + its Wave-0 test scaffold). No silent omission — documented here per the plan's explicit W4 instruction. The next consumer of `renderConceptPanel` (whichever 07-0x plan wires the `next_rank` endpoint's real data into a hover/click panel) should call `renderConceptPanel`, not duplicate the gate inline.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria were met without requiring any Rule 1-4 deviations. The one judgment call (ConceptNode-shaped input vs parsed-tree input, and the resulting `renderConceptPanel` seam rather than overloading `renderPanel`) was anticipated by RESEARCH/PATTERNS ("a pure function inside magic_markdown.mjs... not a literal port") and resolved without contradicting any plan instruction.

## Issues Encountered

None blocking. One test-authoring bug was caught and fixed during Task 2: `parse("plain\n\ta : 1")` makes `"plain"` the rendered root's own line (per `magic_markdown.mjs`'s "single top-level line becomes THE root" rule), so the gate-selection test's structural-path assertion needed to include that line in its expected output. Caught immediately by the test run itself (22/23 → fixed → 23/23); no Rule 1-4 deviation needed since this was a test-expectation bug, not a bug in the function under test.

## User Setup Required

None - no external service configuration required. Pure in-repo JS module change, verified via `node backend/static/js/fe/magic_markdown.test.mjs`.

## Next Phase Readiness
- `renderConceptPanel`/`renderTypedPanel`/`isReadOnlyTypedNode` are ready for whichever downstream 07-0x plan wires the `GET /api/concepts/{id}/next_rank` endpoint's real data into a hover-preview or panel-render consumer.
- The DOM-vdom-layer seam (`magic_markdown_panel.mjs::panelVDom` accepting a ConceptNode and dispatching to `renderConceptPanel`) is an explicit open item for that downstream plan — flagged above, not silently dropped.
- No blockers for downstream plans.

---
*Phase: WFH-07-deep-object-exploration-gestures*
*Completed: 2026-06-24*

## Self-Check: PASSED

- FOUND: backend/static/js/fe/magic_markdown.mjs
- FOUND: backend/static/js/fe/magic_markdown.test.mjs
- FOUND: .planning/phases/WFH-07-deep-object-exploration-gestures/07-02-SUMMARY.md
- FOUND: 880a979 (commit exists in git log)
- FOUND: 487e937 (commit exists in git log)
