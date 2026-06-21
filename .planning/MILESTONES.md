# Milestones

## 1.0 Real-Stack Acceptance (Shipped: 2026-06-20)

**Phases completed:** 5 phases (1–5), direct execution

**Key accomplishments:**

- **Honest baseline** — no-mocks SLM 503 (no silent stub fallback), exactly three foundation fixtures, forbidden/legacy code deleted, dependencies pinned (kuzu 0.11, langgraph/selenium/webdriver-manager), `@mdxeditor/editor` removed.
- **Milkdown black-slate edit layer** (controlled view; store is sole truth) — recursive `{ref}` decoration, gestures over the Milkdown DOM, §3 syntax round-trip, live `?slate=milkdown` click-to-edit (caret-at-click, blur-commit), `{`-autocomplete; fixed the gateway `concept-update`→PATCH persistence path + `concept_id`→`id` store normalization.
- **HTML-dedup content-tree** corpus-clean (61 sites / 120,226 instances / 0 violations) + **apparition halo** from a collapsed circular node (name-only phantoms, scroll re-anchor, camera-orbit ray slide).
- **6D-UMAP/HSV projector** — renders the backend's `umap_canonical` HSV (not an invented sweep) with camera-azimuth recolour; live signal-stream + live `pattern_map`.
- **Real-stack acceptance MET** — `all_real: true`; `probe_no_mocks` + all four lodestar `probe_live_*.py` + `probe_live_scan_with_cleanup` PASS; **full-smoke 92/92 in BOTH stub and real modes**; e2e 26/0.

**Note:** v1 was **operator-executed** (not via the GSD autonomous loop); per-phase
`SUMMARY.md`/`RESEARCH.md` were therefore not produced. Outcomes are independently
verified by the test suite + the live probes above. v2 onward runs the canonical loop.

---
