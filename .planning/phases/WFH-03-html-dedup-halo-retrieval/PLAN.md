# Phase 3 — HTML Dedup + Halo Retrieval Render — PLAN

> Executable plan for HTML-01 / HALO-01 / HALO-02. Brownfield finish-and-verify:
> the §U content-tree is corpus-hardened and the §V halo model + live wiring exist
> (see CONTEXT). Every task's success criterion is a runnable command from
> [`.planning/TEST_MATRIX.md`](../../TEST_MATRIX.md) — never a screenshot (D1).
> Each task un-fixmes one acceptance spec or lands one scenario; the framework
> (`npm run test:all`) is the gate, green in both stub and real modes.

**Status legend:** ☑ done · ◑ partial · ☐ todo. **Depends on:** Phase 2 (complete).

## Tasks

### T1 — HTML-01 content-tree: VERIFY (not rebuild) ☑ DONE  (HTML-01)
- **Surface:** `backend/dom/content_tree.py` (built), `_try_parse_structured` (backend) + `_decomposeValue` (frontend), the §U golden fixtures, `scripts/breadth_content_tree_smoke.py`.
- **Steps:** confirm the HTML chunk slate body is built from `fields` (not `html_raw`); re-run the byte-exact §U golden; confirm `env-scenario --name syntax-agnostic-compile` exercises the HtmlStrategy arm. No new code (no golden regressed).
- **Done-when:** golden + `syntax-agnostic-compile` green; `breadth_content_tree_smoke.py` 0 violations re-confirmed. **(VERIFIED 2026-06-18 — `pytest backend/tests/test_content_tree*.py` 17/17; breadth smoke 61 sites · 120,226 instances · 0 violations; `syntax-agnostic-compile` green, HtmlStrategy arm = `entries ['h2','p'] + clean rendering`. Stub-verified; the detector is deterministic — no-SLM — so real mode is the same path. Live-data render is T6.)**

### T2 — Halo fires from a COLLAPSED CIRCULAR node, proximal (§S.5) ☐  (HALO-02)
- **Surface:** `editor.html` (collapse-to-node gesture → `openHalo` anchored at the node's live rect); reuse `magic_markdown_halo.mjs::haloVDom`.
- **Steps:** clicking a collapsed circular node (the §15.1 root-field-only form) fires the halo, **proximal to that node** (focal = the node's `getBoundingClientRect` centre), abstracting over the folded complexity; the halo already re-anchors on scroll/move.
- **Done-when:** the halo opens from a collapsed node in the served `/` editor (browser-verified, then codified in T3/T4).

### T3 — HALO-01 name-only phantoms + z-order + re-anchor ☐  (HALO-01/02)
- **Surface:** `frontend_e2e/halo.spec.js` (un-fixme); `magic_markdown_halo.mjs` (built) + `editor.html` (wiring).
- **Steps:** on a fixture scan, click a collapsed node → assert each `.mm-phantom` shows **only the candidate name** (no score chips; `data-sim` present for the tooltip); assert the `.mm-halo` z-index > the focal card's; scroll/move → phantoms track the focal-token rect.
- **Done-when:** un-fixme `halo.spec.js` "HALO-01 name-only phantoms" + "HALO-02 z-order + re-anchor".

### T4 — HALO-02 constant-similarity ray + camera-orbit slide ☐  (HALO-02)
- **Surface:** `frontend_e2e/halo.spec.js` (un-fixme); the projector camera-azimuth coupling already in `editor.html` (`projector.onFrame`).
- **Steps:** orbit the projector camera (azimuth) → phantoms **slide along their rays** (angle rotates, radius fixed = constant triple-product similarity); use `window.__mm_halo_rotate` / `__mm_halo_state` probes.
- **Done-when:** un-fixme `halo.spec.js` "HALO-02 constant-similarity ray + along-line slide".

### T5 — Triple-product ranking + autoregressive walk + DOM audit ☐  (HALO-01)
- **Surface:** `scripts/sim_frontend.py` (`apparition-mode` exists; add/extend a `halo-retrieval` scenario); `black_slate.spec.js` (extend the forbidden audit).
- **Steps:** assert candidates rank by `pagerank · tfidf_cos · nomic_cos` (no graph-analytics axes) and the autoregressive walk advances on click (`/api/ui/halo_chain_push`); DOM audit confirms the 2D↔3D arrow is solid and no dotted overlays exist.
- **Done-when:** `env-scenario --name apparition-mode` / `halo-retrieval` green both modes; the no-dotted-overlay audit green.

### T6 — Real-stack breadth (HTML-01 + halo on live data) ☐
- **Surface:** `scripts/probe_pattern_map.py` + live archive/tarot/yourchineseastrology/studycli scans.
- **Steps:** real scans render clean+deduped content-trees (0 invariant violations) and the halo retrieves real triple-product candidates against the live index.
- **Done-when:** `probe_pattern_map.py` passes and the four live sites render clean on the real stack (`all_real:true`).

## Coverage (req → task)

| Req | Tasks |
|---|---|
| HTML-01 | T1, T6 |
| HALO-01 | T3, T5 |
| HALO-02 | T2, T3, T4 |

## Phase gate
`npm run test:all` green in BOTH stub and real modes with every `halo.spec.js`
spec un-fixme'd + the `apparition-mode`/`halo-retrieval`/`syntax-agnostic-compile`
scenarios green; `probe_pattern_map.py` + live-site breadth pass on the real stack.

## Note on as-built leverage
HTML-01 is ~done (corpus-hardened) → T1 is verification. The halo MODEL + live
wiring exist → T2–T4 are the proximal-collapsed-node wire + the browser
acceptance (the e2e blind spot the REPL can't reach), mirroring Phase 2's
finish-and-verify idiom. The real build surface is small; the value is the
**verification** in the project's REPL/probe/e2e idiom.
