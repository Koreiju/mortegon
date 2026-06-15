# Code Architecture — Migration (Keep / Remove / Replace Ledger)

> **Status: planned.** The per-file disposition of the **existing** tree against the design. Backend is **aligned** (keep the real subsystems, remove the forbidden frameworks); the frontend is **greenfield** (the legacy `cp/*.js` is replaced wholesale, not adapted). Distilled from the top-of-`CLAUDE.md` Forbidden Concepts + the codebase glob audit. Realises `code_constraints/` (the anti-goal anchors).

---

## §1 — Verdict Legend

- **Keep & align** — design-current; align signatures to the relevant `backend/` doc.
- **Remove** — design-**forbidden**; delete, do not adapt.
- **Audit → fold/remove** — keep only the slice the design needs; drop framework dependents.
- **Replace** — superseded; build the greenfield target instead.
- **Defer** — aspirational / out of current blueprint scope.

---

## §2 — Backend Ledger

| Existing code | Verdict | Target / reason |
|---|---|---|
| `backend/services/` (lifecycle, layout, ui-state, scanner glue), `backend/mapper/` (Selenium scan), Kuzu/cypher, SLM + embedding wrappers | **Keep & align** | The real subsystems — align to [`backend/`](backend/) signatures |
| `backend/ontology/{knowledge_graph,cypher_engine,field_types,models}.py` | **Keep & align** | Concept graph / Kuzu / typed fields are design-current |
| `backend/dom/` internals (WL hashing, Zhang-Shasha, PQ-trees, trie distillation) | **Keep** (scanner-internal) | Chunk-roster algorithms; **not** a retrieval framework, never surface in the editor (§19) — see [`backend/scanner.md`](backend/scanner.md) |
| `scripts/sim_frontend.py` + `scripts/probe_live_*.py` + `probe_*.py` | **Keep** | The REPL verification surface (§14) |
| **`backend/analytics/algorithms/*`** (topology, spectral, curvature, centrality, tree-kernels, graphlets, wavelets, hyperbolic-embeddings, graph-invariants, hashing) | **Remove** | The **forbidden graph-analytics retrieval framework**. Retrieval is the triple product (`pagerank · tfidf_cos · nomic_cos`), not graph analytics — see [`backend/retrieval.md`](backend/retrieval.md) |
| `backend/analytics/{scoring,clustering,evolution,auto_fit,auto_labeler,ontologizer,…}` | **Audit → fold/remove** | Keep only what the triple-product index / evolution log needs; drop everything keyed to the analytics framework |
| **`backend/ontology/hyperbolic_layout.py`, `gyrovector.py`** | **Remove** | **Forbidden layout** — replaced by UMAP-linear-radial-force ([`backend/layout.md`](backend/layout.md)) |
| any **Llama** SLM path / `_FAST_HARNESS_MODEL` | **Remove** | **Forbidden** — Nous-Hermes-2-Mistral-7B-DPO only ([`subsystems.md`](subsystems.md)) |
| `backend/agentic/fluid_engine.py` | **Defer** | Realises the aspirational fluid-sim (§12.8) — out of current blueprint scope |

**Forbidden concepts to never re-introduce** (doc or code): concentric Fibonacci spheres; the graph-analytics retrieval framework (depth/subtree_size/cluster_id/wl_hash as retrieval features); Llama; the two-panel hover/click split; dotted/dashed UI lines; arrowheads; concentric concept-graph rings.

---

## §3 — Frontend Dissolution (`cp/*.js` → greenfield `fe/`)

The frontend is rebuilt from `FRONTEND_REDESIGN.md` §11; the legacy is a **replacement map**, not a porting guide. ~16 cross-cutting modules collapse to the tiered seam set.

| Legacy `cp/*.js` (+ `chunk_projector*.js`) | Replaced by |
|---|---|
| `billboard.js` | `cell/concept_view.ts` (anatomy) + `membranes/billboard.ts` (hover/pin) — [`frontend/cell.md`](frontend/cell.md), [`frontend/membranes.md`](frontend/membranes.md) |
| `concept_graph.js` | `cell/field_tree.ts` (tree) + `imaginary/editor.ts` (canvas) — [`frontend/cell.md`](frontend/cell.md), [`frontend/imaginary.md`](frontend/imaginary.md) |
| `scanner.js` | `real/chunk_field.ts` + store `chunks` slice + `spine/frame_bus.ts` — [`frontend/real.md`](frontend/real.md), [`frontend/spine.md`](frontend/spine.md) |
| `animation.js` | `real/projector.ts` animate + `pulse/raf.ts` + `membranes/link_layer.ts` |
| `instance_manager.js` | `real/chunk_field.ts` |
| `force_layout.js` / `layout.js` | **backend** LayoutService — the frontend computes **no** layout ([`backend/layout.md`](backend/layout.md)) |
| `search.js` | `imaginary/editor.ts` result list + `ui-viewport-spine` (store-driven) |
| `workspace.js` | `imaginary/editor.ts` sidebar + store `ui.url_*` + `projector.ts` visibility |
| `sprite_manager.js` / `media.js` | `real/texture_cache.ts` |
| `interaction.js` | `real/projector.ts` raycast + `membranes/billboard.ts` |
| `telemetry.js` | `spine/gateway.ts` (telemetry batch) |
| `edge_manager.js` / `node_loader.js` / `ui_utils.js` | `membranes/link_layer.ts` / `real/chunk_field.ts` / shared util |
| `chunk_projector.js` / `chunk_projector.monolith.js` | the whole `fe/` tree — **no monolith** |

The collapse from ~16 modules to **6 tiers** (spine / cell / real / imaginary / membranes / pulse) is the structural claim (`FRONTEND_REDESIGN.md` §0/§11).

---

## §4 — Sequencing (suggested)

1. **Backend removals first** (`analytics/algorithms`, `hyperbolic_layout`/`gyrovector`, Llama paths) — they have no design-current dependents; removing them unblocks clean alignment.
2. **Align backend services** to the `backend/` signatures (the real subsystems stay; the seams get enforced).
3. **Greenfield `fe/`** — build Spine → Cell → Organs → Membranes → Pulse; keep the legacy served until the `fe/` tree passes the acceptance bar, then delete `cp/`.
4. **Verify continuously** against `env-scenario --name full-smoke` (both real + stub modes) and the live probes (§14).

---

## §5 — Excluded (per README §0)

- The *rationale* behind each forbidden concept (it lives in `DOMAIN_MODEL.md` forbidden-concepts + the §O clarifications). This doc records only the disposition + target.
