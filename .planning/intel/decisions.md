# Decisions (ADR Intel)

Synthesized from classified ADR-type documents. The sole ADR in this ingest set is the
verbatim user-requirements source-of-truth, which declares itself supreme over all other
documents (precedence 0). It is not a single Accepted-status ADR, so `locked=false`; it
nonetheless wins every content conflict per its manifest precedence.

---

## ADR-user-requirements-verbatim

- source: C:/Users/isaac/Documents/web_fiber_haptics/docs/USER_REQUIREMENTS_VERBATIM.md
- type: ADR
- status: authoritative (not locked; precedence 0 — supreme)
- scope: whole-project source-of-truth; wins all conflicts

Decision statements (each preserved separately):

### D1 — Process discipline: doc-first, correctness over comprehensiveness
- statement: Capture requirement verbatim → audit code against doc → record gap analysis →
  only then change code. A screenshot is not feature proof; verification runs in the REPL
  against the live full stack.
- scope: process / workflow
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D2 — 3D layout is UMAP-linear-radial force-directed hybrid
- statement: The 3D layout is the UMAP-linear-radial force-directed hybrid (UMAP places
  chunks, force-directed converges along root-URL rays, hard-collider repulsion). The 2D
  editor uses the ray-constrained 2D analogue around the focal card.
- scope: layout / 3D projector / 2D editor
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D3 — Retrieval ranks by triple product
- statement: Retrieval ranks by `pagerank · tfidf_cos · nomic_cos`. The two embedding axes
  (nomic over description, TF-IDF over rendering) never mix.
- scope: retrieval
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D4 — One unified knowledge-panel model
- statement: One knowledge-panel anatomy, one code path. The pinned panel materialises at
  the exact screen rect the hover billboard occupied at click time (freeze-at-hover-rect).
- scope: frontend / knowledge panel
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D5 — Strict retrieval scroll-spine
- statement: Retrieval chunks collapsed-hidden by default; only scroll-viewport-visible OR
  pinned-panel-referenced chunks are visible. No global show-all, no debug bulk-expand, no
  third path.
- scope: retrieval / 3D visibility
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D6 — Data-agnostic recursive compile
- statement: One syntax-agnostic recursive descent over all authored syntaxes. The data
  block dissolves into the field-tree; rows grow via horizontal `+→` (parent→child) and
  vertical `+↓` (sibling) plus-signs.
- scope: compile / field-tree
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D7 — Three foundational fixtures (§S re-baseline)
- statement: There are THREE foundational fixtures (Database, WebBrowser, Agent), all
  undeletable, all flat (no centrality hub). The former `Editor` fourth fixture is REMOVED
  (§S.1); its create/link/overwrite/delete gestures are intrinsic to the unified
  panel↔compute-graph scheme, routed through the same lifecycle (`/concepts` +
  `/concept_edges`) the agent emitter uses — never a Function-typed Editor object.
- scope: foundational fixtures
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D8 — One ConceptNode record, one ConceptEdge table
- statement: A single `ConceptNode` dataclass (§8D.44) carries all node kinds. One
  `ConceptEdge` table whose `edge_type` is the union enum; never two edge tables. `type_hint`
  is a naming convention, not a type discriminator.
- scope: schema / data model
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D9 — No-mocks contract
- statement: Production paths run real subsystems always (GPT4All SLM Nous-Hermes-2-DPO on
  CUDA, nomic Embed4All, headful Selenium Firefox, LangGraph StateGraph). `WFH_FAKE_*` gates
  are harness-only. `GET /api/subsystem_status` reports `all_real: true` in production.
  Real-backend → stub fallback is forbidden; failures are loud (503 + cascade halt).
- scope: subsystems / reliability
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D10 — Backend computes, frontend renders
- statement: Layout, embeddings, PageRank are backend services. Frontend has no UMAP runtime
  and no embedding fitter. One lifecycle dispatcher; append-only evolution log; idempotency
  keys on every mutation; optimistic concurrency (last-write-wins, rollback is the user's
  conflict tool).
- scope: architecture
- source: docs/USER_REQUIREMENTS_VERBATIM.md

### D11 — Forbidden concepts (hard deletions)
- statement: Removed and must not reappear: concentric Fibonacci spheres as 3D layout; graph
  analytics retrieval framework; Llama as SLM target; two-panel hover/click split; stray
  dotted UI lines; concentric concept-graph rings; the `Editor` fourth fixture (§S.1); the
  retrieval sidebar (§S.3); panel/node chrome (§S.4 — black-slate design only).
- scope: anti-goals
- source: docs/USER_REQUIREMENTS_VERBATIM.md

---

Note: SPEC and PRD documents in this ingest set elaborate these decisions; none contradict
them. Where lower-precedence docs carried stale four-fixture text, they have been reconciled
to D7 (§S three-fixture baseline); the residual contradiction is resolved (see
INGEST-CONFLICTS.md INFO bucket).
