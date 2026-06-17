# Verification Matrix — requirement → runnable check

The contract `gsd-verifier` (and `/gsd-autonomous`) executes per phase. Every
`REQ-*` maps to a **runnable** command in the unified framework
(`scripts/run_full_stack_tests.py` / `npm run test:all`), so there are no
manual/"screenshot" gates (D1). This is the nyquist-coverage ledger: no
requirement is unsampled.

## Run policy — fast inner loop vs. acceptance gate

| Tier | When | Command | Cost |
|---|---|---|---|
| **fast** (stub) | every execute/verify iteration | `python scripts/run_full_stack_tests.py --no-pytest --only repl --only e2e` (+ `--only` the phase's scenarios) | seconds |
| **full stub** | end of a plan | `npm run test:all` (pytest + repl `all` + e2e, isolated temp DB) | ~1–2 min |
| **acceptance** (real) | phase ship gate | `npm run test:all:real` (adds the 4 lodestar probes + `probe_no_mocks`; live scans real) | ~5–10 min |
| **acceptance, deterministic** | CI / unattended | `python scripts/run_full_stack_tests.py --real --fixture-scan` | ~3–5 min, no archive.org throttle |

Rules: iterate on **stub**; gate phase completion on **full stub** green; gate
phase **ship** on **acceptance** (`all_real: true`). Use `--fixture-scan` for
unattended/autonomous acceptance so a flaky archive.org never reds the loop; the
real-archive lodestar (§8D.45) is the human-run / milestone acceptance.

Every framework run is **isolated** (db_janitor temp DB) by default — never
touches `kuzu_db/_default`.

## Per-phase verification

### Phase 1 — Honest Baseline
| Req | Check (runnable) |
|---|---|
| REL-01/02 (no-mocks 503) | `--real`: `scripts/probe_no_mocks.py` (SLM not `[stub-slm]`); stub: SLM unit tests in pytest |
| FIX-01/02 (3 fixtures, no forbidden code) | `env-scenario --name three-fixtures-present`; `rg -i 'fibonacci|concentric|hyperbolic|llama|graph.analytics' backend` finds only deprecation banners |
| HYG-01/02 (deps, launch, MDXEditor) | `pip check` against `backend/requirements.txt`; `grep -L mdxeditor package.json` |
| gate | `npm run test:all` green (both modes) |

### Phase 2 — Black-Slate Field Editing (frontend)
| Req | Check (runnable) |
|---|---|
| EDIT-01 (click-to-edit, caret, Shift-Enter) | `frontend_e2e/edit.spec.js` (Playwright) **+** `env-scenario --name click-to-edit` / `edit-field-roundtrip` |
| EDIT-02 (`+→`/`+↓`, `{`-autocomplete, lifecycle) | `frontend_e2e/edit.spec.js` **+** `env-scenario --name editor-primitives-roundtrip` / `autocomplete-state-roundtrip` |
| EDIT-03 (CM6-vs-custom decision; no frontend state) | `frontend_e2e/edit.spec.js` reconnect-re-render assertion; `docs/EDITOR_INTEGRATION_ASSESSMENT.md` |
| gate | `npm run test:all` green; e2e covers render, REPL covers the API/WS seam |

### Phase 3 — HTML Dedup + Halo Retrieval Render
| Req | Check (runnable) |
|---|---|
| HTML-01 (dedup content tree) | `pytest backend/tests/test_content_tree.py` + `test_content_tree_breadth.py`; `python scripts/breadth_content_tree_smoke.py` (61-site corpus); `env-scenario --name syntax-agnostic-compile` |
| HALO-01/02 (name-only phantoms, triple-product, circular node, ray) | `frontend_e2e/halo.spec.js` (Playwright: z-order, token-anchor) **+** `env-scenario --name apparition-mode-roundtrip` / `halo-focus-roundtrip` / `halo-chain-roundtrip`; `--real`: `scripts/probe_pattern_map.py` |
| gate | `npm run test:all` green + the breadth smoke |

### Phase 4 — Live Layout, Signal & Pattern
| Req | Check (runnable) |
|---|---|
| UMAP-01 (6D fit + camera HSV) | `env-scenario --name 6d-umap-format` / `perimeter-rescale` |
| SIG-01 (one-signal rollout, per-sample cascade) | `env-scenario --name iterated-signal-rerender` / `signal-stream-roundtrip` / `urls-panel-iteration` |
| PAT-01 (live pattern_map) | `env-scenario --name pattern-map-live-update`; `--real`: `scripts/probe_pattern_map.py` |
| gate | `npm run test:all` green |

### Phase 5 — Three-Register Synthesis & Live Acceptance
| Req | Check (runnable) |
|---|---|
| REG-01 (compose-compile-perimeter both ways) | `env-scenario --name complex-interaction-walkthrough` / `cascade-reflow-roundtrip` |
| ACC-01/02 (lodestars + cleanup, all_real) | `--real`: `scripts/probe_live_scan_with_cleanup.py` + the 4 `probe_live_*` lodestars + `probe_no_mocks`; `GET /api/subsystem_status` `all_real: true` |
| gate | `npm run test:all:real` ALL GREEN (the project's success metric) |

## Coverage status (2026-06-15)

- Built + green: every Phase 1/4/5 + the Phase 3 HTML-dedup checks; the full
  REPL `all` (95) + pytest + e2e (5 specs) in both modes.
- **Outstanding e2e specs** (the only nyquist gaps): `frontend_e2e/edit.spec.js`
  (Phase 2 caret/IME/`+→`/`+↓`/`{`-autocomplete) and `frontend_e2e/halo.spec.js`
  (Phase 3 halo z-order + token-anchored re-anchor, circular collapsed node).
  These are written as the FIRST deliverable of their phases (the criteria are
  also their build targets).
