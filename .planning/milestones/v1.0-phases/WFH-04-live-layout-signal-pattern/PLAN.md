# Phase 4 — Live Layout, Signal & Pattern — PLAN

> Executable plan for UMAP-01 / SIG-01 / PAT-01. The backend is built +
> scenario-green (see CONTEXT); SIG-01/PAT-01 are verify, UMAP-01 has a focused
> projector render build. Every task's criterion is a runnable framework command.

**Status legend:** ☑ done · ◑ partial · ☐ todo. **Depends on:** Phase 3 (complete).

## Tasks

### T1 — `buildPointArrays` renders the backend 6D HSV (UMAP-01) ☑ DONE
- **Surface:** `projector.mjs::buildPointArrays` + `projector.test.mjs`.
- **Steps:** a 6-vector colours from HSV(`p[3..5]`); a 3-vector keeps the positional sweep (backward compatible); the `azimuth` opt rotates the hue. The legacy positional `hslToRgb` arg still works.
- **Done-when:** `projector.test.mjs` green with new cases. **(7/7 — 6D→frame HSV; azimuth rotates hue; 3D→sweep unchanged.)**

### T2 — `createProjector` recolours on camera azimuth (UMAP-01) ☑ DONE
- **Surface:** `projector.mjs::createProjector` (`setNodes` stores `_coords`; `recolor()`; the animate loop recolours when azimuth moves > 0.05) + `nodeColor` probe.
- **Steps:** orbiting the scene rotates the HSV field (hue += azimuth offset); `nodeColor(i)` exposes the rendered colour.
- **Done-when:** the projector recolours on azimuth. **(codified in T4 — green.)**

### T3 — Editor consumes the `umap_canonical` 6D frame (UMAP-01) ☑ DONE
- **Surface:** `editor.html::connectWS` — a `umap_canonical` frame → `projector.setNodes(frame.coords)`; `/api/recompute_umap` stays the 3D bootstrap; `__mm_proj_set`/`__mm_proj_color`/`__mm_proj_orbit` probes.
- **Steps:** the 6D HSV the backend broadcasts reaches the projector; the frontend renders only (no client UMAP).
- **Done-when:** an injected `umap_canonical` frame colours the projector from its HSV. **(codified in T4 — green.)**

### T4 — Projector render e2e (UMAP-01) ☑ DONE
- **Surface:** `frontend_e2e/projector.spec.js` (new).
- **Steps:** boot `/`, inject a 6D frame (`__mm_proj_set`), assert the node colour reflects the frame hue (green for 0.33 — NOT the n=1 red sweep); orbit (`__mm_proj_orbit`) → colour rotates. Skips deterministically if THREE/WebGL is unavailable.
- **Done-when:** `projector.spec.js` green; full e2e stays green. **(green — full e2e 26 passed / 0 failed.)**

### T5 — SIG-01 / PAT-01 verification (no new build) ☑ VERIFIED
- **Surface:** existing scenarios + probe.
- **Steps:** confirm `iterated-signal-rerender`, `signal-stream-roundtrip`,
  `database-concept-signal-stream`, `urls-panel-iteration`, `pattern-map-live-update`
  green + `probe_pattern_map.py` PASS.
- **Done-when:** all green. **(VERIFIED 2026-06-18 against the stub — all exit 0; `probe_pattern_map` ALL CHECKS PASS.)**

### T6 — UMAP-01 scenario verification ◑
- **Surface:** `6d-umap-format` + `perimeter-rescale`.
- **Steps:** confirm green (the 6-vector contract + HSV-in-[0,1] + perimeter rescale).
- **Done-when:** both green. **(VERIFIED 2026-06-18 — exit 0.)** The frontend render of that HSV is T1–T4.

## Coverage (req → task)

| Req | Tasks |
|---|---|
| UMAP-01 | T1, T2, T3, T4, T6 |
| SIG-01 | T5 |
| PAT-01 | T5 |

## Phase gate
`npm run test:all` green both modes with `projector.spec.js` added + the
UMAP/signal/pattern scenarios green; `probe_pattern_map.py` PASS; `full-smoke`
stays green. Real-stack: the live-scan `umap_canonical` 6D fit is exercised by
`probe_live_scan_with_cleanup.py` (Phase 5 / real backend).
