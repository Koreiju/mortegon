# Constraints (SPEC Intel)

Synthesized from 4 classified SPEC documents, ordered by precedence integer (1 = highest
SPEC authority). All SPECs are subordinate to ADR-user-requirements-verbatim (precedence 0).
Where a SPEC asserted a technical decision contradicting the ADR, the ADR wins and the SPEC
content is recorded as reconciled (see INGEST-CONFLICTS.md). No such contradictions were
found in this re-run — all SPECs are consistent with the §S three-fixture baseline and the
forbidden-concepts list.

---

## CONSTRAINT-domain-model  (precedence 1)
- source: docs/DOMAIN_MODEL.md
- type: protocol / design contract
- content: Full design elaboration of the single-user on-device workspace joining the 3D
  projector, 2D concept editor, and REPL into one Mortegon workflow. Defines the ConceptNode
  schema, the three foundational fixtures (Agent, WebBrowser, Database), halo retrieval, the
  UMAP-linear-radial layout, the no-mocks contract, and cascade compile. Must not contradict
  USER_REQUIREMENTS_VERBATIM. Black-slate panel/node design lives at §4.1.2 (thin silver
  border, black infill, serif white text, no chrome).

## CONSTRAINT-frontend-redesign  (precedence 2)
- source: docs/FRONTEND_REDESIGN.md
- type: api-contract / object model
- content: Frontend object model as a faithful projection of backend truth with ONE
  inbound/outbound seam (FrameBus + GestureGateway), one record renderer, a recursive field
  interpreter (FieldTree), two canvases (Projector 3D, Editor 2D), a WorkspaceStore, and a
  Liveness engine. Frontend renders only — no UMAP runtime, no embedding fitter. Themed
  dark-minimal stainless-steel-over-black. Canonical for all frontend specifics.

## CONSTRAINT-black-slate-goal  (precedence 3)
- source: docs/BLACK_SLATE_GOAL.md
- type: schema / rendering contract
- content: Binding spec to rebuild the 2D editor card as ONE black markdown text-tree slate
  (no chrome): parse-recovered structure, no widgets. Grammar + gesture set
  (internalize/externalize link gestures), anchoring/signal model, and strip/rebuild order
  over `cp/concept_graph.js` + `cp/billboard.js`. Backend preserved. Realises §S.4 black-slate
  and §T.

## CONSTRAINT-html-dedup-content-tree  (precedence 3)
- source: docs/HTML_DEDUP_CONTENT_TREE_GOAL.md
- type: api-contract / transform spec
- content: Binding spec defining an HTML chunk slate's body as DEDUPLICATED content printed
  as a pure-text tree (collapse wrappers, token-set dedup, surface href/src), realising the
  syntax-agnostic compile's HtmlStrategy as a backend `content_tree` transform. Rule-by-rule
  dedup grammar + binding golden I/O test. Built from the existing `fields` extraction, not
  `html_raw`. Backend `_try_parse_structured` is the single detector; frontend `_decomposeValue`
  mirrors the strategy order.

---

Consistency note: All four SPECs uphold the ADR's forbidden-concepts list (no concentric
spheres, no graph analytics, no Llama, no two-panel split, no chrome) and the three-fixture
baseline. No SPEC-vs-ADR contradiction detected.
