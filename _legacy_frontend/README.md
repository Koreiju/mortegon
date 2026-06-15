# Legacy frontend artifacts (archived during frontend unification)

This directory holds the **superseded, non-active** frontend code that was
removed from the app's served tree on **2026-06-05** to unify the frontend
codebase on a single implementation.

## Why these were archived

The app had **two parallel frontend codebases**:

| Tree | Status before unification |
|---|---|
| `backend/static/js/cp/*.js` (17 modules, ~13,400 lines) | **THE realized frontend** — served at `/` via `backend/templates/index.html` (`main.py::read_root`), exercised by the `backend/static/js/tests/` harness (12 imports) and by the REPL contract (`scripts/sim_frontend.py`, 83 scenarios). Implements every subsystem: scanner, retrieval sidebar, instanced 3D, force-layout, telemetry, concept-graph editor, billboards, halo, links. |
| `backend/static/fe/*` (15 files, ~1,200 lines) | **Greenfield object-model skeleton** — the `spine/cell/real/imaginary/membranes/pulse` architecture from `FRONTEND_REDESIGN.md` made partly-real. Wired only into `index_fe.html`, **which no backend route ever served**. Untested (0 test imports). Missing the scanner, retrieval, force-layout, instancing, and telemetry subsystems (~8% the size of `cp/`). |

`CLAUDE.md` already designated the realized frontend: *"Frontend realized as
`backend/static/js/cp/*.js` mixins on ChunkProjector (NOT the greenfield
`fe/*.ts`)."* Keeping `fe/` in the active tree was the un-unified state — a
confusing second frontend that the app never loaded.

**The unification:** consolidate on the live, tested, complete `cp/` frontend;
move the dead parallel here. Nothing in the served app referenced any file in
this directory (verified: no python route serves `index_fe.html`; no
html/js/py outside `index_fe.html` itself imports `static/fe/*`; nothing
references `chunk_projector.monolith.js`).

The greenfield **architecture** is not lost — it is fully captured in the
design docs: `docs/code_architecture/frontend/` and `docs/code_specs/frontend/`
(spine · cell · real · imaginary · membranes · pulse), plus `FRONTEND_REDESIGN.md`.

## Contents

- `fe/` — the greenfield object-model frontend (was `backend/static/fe/`).
- `index_fe.html` — its entry template (was `backend/templates/index_fe.html`).
- `chunk_projector.monolith.js` — the pre-mixin monolith superseded by the
  `cp/*.js` split (was `backend/static/js/chunk_projector.monolith.js`).

## How to restore (this repo is not under git)

Move the pieces back to their original paths:

```
_legacy_frontend/fe/                          -> backend/static/fe/
_legacy_frontend/index_fe.html                -> backend/templates/index_fe.html
_legacy_frontend/chunk_projector.monolith.js  -> backend/static/js/chunk_projector.monolith.js
```

If instead you want `fe/` to *become* the app's frontend, that is a much larger
effort than a restore: `fe/` lacks the scanner/retrieval/force-layout/instancing/
telemetry subsystems and would need them reimplemented before it could replace
`cp/`. The realized contract lives in `cp/` + `scripts/sim_frontend.py`.
