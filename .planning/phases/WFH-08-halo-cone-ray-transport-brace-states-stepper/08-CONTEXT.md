# Phase 8: Halo Cone-Ray Transport + Brace States + Stepper - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning
**Mode:** Smart-discuss (autonomous) — design is locked in the docs (§O.18 / §O.1a / §O.6,
`halo.md` / `projector.md`). This captures the build decisions. Brownfield realization
built on Phase 6 (projector) + Phase 7 (gestures + brace-state classification), NOT a
from-scratch design.

<domain>
## Phase Boundary

Realize the §O halo cone-ray transport, the three §O.1a `{ref}` render states, and the
§O.6 2D→3D per-sample stepper in the served `fe/` editor. Covers HALO-03, HALO-04, STEP-01.

In scope:
- **HALO-03 (§O.18)** — opening a halo TRANSPORTS retrieved 3D nodes onto a SHARED CONE
  whose apex is the 2D query element; normalized triple-product similarity
  (pagerank·tfidf·nomic) sets the radial+along-ray distance; camera view sets angular
  placement; deleting a result transports the next-most-similar in.
- **HALO-04 (§O.1/§O.1a/§O.2)** — the three `{ref}` render states made VISUAL with
  panel↔graph node-count parity: braced-hidden (▸ + literal braces), revealed-internal
  (▾ + inline rank-1 children), resolved-external (a SOLID cross-ref link to the
  already-visible node). This RENDERS Phase 7's already-correct `classifyBraceStates`
  classification (the Phase-7 self-flagged "computed but not rendered" gap, D-02 below).
- **STEP-01 (§O.6/§O.7/§O.11)** — the 2D `{chunk samples}` stepper drives 3D focus
  ONE-WAY: advancing a sample in 2D flies/highlights the corresponding chunk in 3D, while
  the 3D ALWAYS shows the full per-sample distribution.

Out of scope (later phases): the cascaded recurrent renderer / readout perimeter / bisector
projector node (§7.8/§P) — Phase 9; live mid-scan streaming refit — Phase 10; scroll-spine
reconciliation — Phase 11.
</domain>

<decisions>
## Implementation Decisions

### D-01 — HALO-03 verification: REAL-SUBSYSTEM INLINE (user choice)
The cone transport is verified against the REAL triple-product retrieval (real nomic + TF-IDF
indices over a real scan) IN THIS PHASE, driven from the MAIN context with a clean-GPU
preflight (consistent with Phase 7's D-01). The phase gate includes a live run: a real scan →
open a halo on a 2D query element → assert retrieved 3D nodes land on the cone with
radial+along-ray distance monotonic in the real normalized triple-product score, and that
deleting the top result transports the next-most-similar. Honor the env discipline: confirm
0 stray python/firefox + ~0 VRAM before the real boot; drive the real backend lifecycle from
the main context, never a verifier subagent (a wedged CUDA/Selenium boot hangs). Stub-backed
`halo.spec.js` cone-transport e2e + `apparition-mode`/`halo-chain-roundtrip` env-scenarios
stay green both modes as the fast gate; the real run is the acceptance proof on top.

### D-02 — HALO-04 brace render: WIRE Phase 7's classifyBraceStates INTO THE RENDERERS (user choice)
Consume Phase 7's existing `classifyBraceStates` output (in `magic_markdown.mjs`) in
`panelVDom`/`graphVDom` so the three states render VISUALLY:
- braced-hidden → ▸ glyph + literal `{braces}` retained, no children;
- revealed-internal → ▾ glyph + inline rank-1 children (braces drop);
- resolved-external → a SOLID cross-ref link to the already-visible target node (reusing the
  no-`stroke-dasharray` SVG solid-line idiom — Phase 6's 2D↔3D arrow / the `#link-layer`).
This CLOSES the Phase-7 self-flagged gap (07-03 SUMMARY: "classifyBraceStates computed but
panelVDom/graphVDom ignore l.braceState; resolved-external solid link has no graphVDom
drawing"). Node-count parity between panel and graph forms is asserted (revealing in one
reveals in both; the underlying graph link is identical across all three states).

### D-03 — STEP-01: NEW BACKEND ALLOWED AS NEEDED (user choice)
The 2D stepper → 3D focus wiring is frontend-first (reuse the existing `signal_stream` /
`signal_advance` backend from Phases 4/§R + the projector's fly-to/highlight from Phase 6),
but the planner may add NEW backend signal/focus plumbing where the existing surface does not
already expose what the one-way 2D→3D focus drive needs. D10 still holds: the 3D ALWAYS shows
the full per-sample distribution; the stepper only MOVES FOCUS (fly/highlight), it never
subsets the 3D distribution. New backend work is in-budget; it is NOT a license to move
layout/retrieval COMPUTATION into the frontend.

### D-04 — Port host: NEW DEDICATED fe/ MODULE(S) (user choice)
Author new dedicated `fe/` module(s) for the cone-transport geometry and the stepper (e.g.
`fe/halo_cone.mjs` and/or `fe/stepper.mjs`), wired into the existing `magic_markdown_halo.mjs`
(halo focus/chain) + `projector.mjs` (3D fly/highlight) + `magic_markdown.mjs`/panel (brace
render). New surface is preferred over cramming into the existing modules where a clean seam
exists; reuse the existing halo/projector/store plumbing rather than duplicating it.

### Locked-by-design (NOT re-decided — from halo.md / projector.md / DOMAIN_MODEL §O.18 / §O.1a / §O.6)
- **Cone geometry (§O.18):** apex = the 2D query element's screen position; retrieved nodes
  transported ONTO the cone surface; radial + along-ray distance encodes the NORMALIZED
  triple-product similarity (closer = more similar); camera azimuth/view sets the angular
  placement around the cone. Delete-a-result → the next-most-similar transports in.
- **Triple-product retrieval (§8.1):** ranking = pagerank · tfidf_cos · nomic_cos. The two
  embedding axes never mix; the frontend RENDERS the backend's ranked retrieval — it does not
  compute similarity (D10).
- **Three brace states over ONE invariant graph (§O.1a):** internal/external + folded/unfolded
  are RENDERING choices over one ConceptEdge; panel↔graph node-count parity holds.
- **Stepper one-way (§O.6/§O.7/§O.11):** 2D drives 3D focus; 3D never drives the 2D stepper
  back (one-way); the 3D distribution is always fully present (focus highlights a member).
- **Forbidden:** NO dotted/dashed lines (the resolved-external link + any cone rays are SOLID);
  no panel chrome; black-core+silver-outline theme; HSV color only in the projector exception
  zone. Verification idiom = env-scenario + probe + e2e, NEVER screenshots. No-mocks/all_real.
</decisions>

<code_context>
## Existing Code Insights

### Reusable assets (served fe/ — the port surface; extend per D-04)
- `backend/static/js/fe/magic_markdown_halo.mjs` (+ .test.mjs) — the existing halo (name-only
  phantoms, ray projections, `__mm_halo_*` hooks) from Phases 1–5/§V — the cone transport extends/wraps this
- `backend/static/js/fe/projector.mjs` — Phase 6's 3D projector (force-directed layout, billboards,
  2D↔3D solid arrow, `project()`→{x,y,inFront,ndcZ}) — the 3D fly/highlight + cone placement render here
- `backend/static/js/fe/magic_markdown.mjs` — Phase 7's `classifyBraceStates` (the classification HALO-04 renders); `renderPanel`/`panelVDom`/`graphVDom`
- `backend/static/js/fe/magic_markdown_panel.mjs` — `mount()` + the `#link-layer` SVG solid-line idiom (Phase 6/7)
- `backend/static/js/fe/store.mjs` — WorkspaceStore (concepts/edges/index/ui state incl. signal_stream)

### Backend (consume first; extend per D-03 only where a real gap exists)
- triple-product retrieval index (§8.1 — pagerank·tfidf·nomic); `/apparitions` / `/chunk_search`
- `signal_stream` / `signal_advance` UI-state + the `/ui/signal_*` routes (Phases 4/§R)
- `/ui/halo_chain_push` / `/ui/halo_chain_clear` (the halo-chain UI state)

### Verification surface
- `frontend_e2e/halo.spec.js` (exists, Phases 1–5/§V) — extend with cone-transport + the two-level brace-chain e2e
- REPL env-scenarios (exist): `apparition-mode`, `halo-chain-roundtrip`, `signal-stream-roundtrip`, `iterated-signal-rerender` — must stay green; add cone-transport telemetry
- probe — a `probe_live_*` for the D-01 real-retrieval cone-transport acceptance (real triple-product over a real scan)
</code_context>

<specifics>
## Specific Ideas

HALO-04 is the explicit Phase-7 follow-up: Phase 7's `classifyBraceStates` already computes
braced-hidden / revealed-internal / resolved-external correctly (proven at the model level by
07-03's e2e on `l.braceState`); the gap is purely that `panelVDom`/`graphVDom` ignore
`l.braceState` and `graphVDom` never draws the resolved-external solid cross-ref link. D-02
closes exactly that. The resolved-external link reuses Phase 6's solid `#link-layer` / 2D↔3D
arrow substrate (no dasharray). HALO-03's cone shares the same retrieval the in-editor halo
already fires; the new geometry is the transport-onto-a-cone placement keyed by the real
normalized triple-product score + camera azimuth.
</specifics>

<deferred>
## Deferred Ideas

- Cascaded recurrent renderer / readout perimeter / bisector projector node (§7.8/§P) — Phase 9.
- Live mid-scan incremental UMAP refit / streaming SLA (§V.1/§B.6) — Phase 10.
- Scroll-spine reconciliation (§G.1 vs §S.3) — Phase 11.
- The serif-vs-monospace design-doc conflict (object_exploration.md §13 vs DOMAIN_MODEL §4.1.2)
  flagged in Phase 7's UI audit — a doc reconciliation, NOT a Phase-8 implementation decision;
  HALO-04's brace render is font-agnostic (glyph/underline/link), so it does not block on this.
</deferred>
