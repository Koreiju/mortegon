# Synthesis Summary

Entry point for downstream consumers (gsd-roadmapper). Synthesized from classified planning
docs in net-new (bootstrap) mode. This is a RE-RUN after the source docs were reconciled to
the §S three-fixture re-baseline; prior intel + conflict report overwritten.

## Doc counts by type
- Total: 15 classified docs
- ADR: 1
- SPEC: 4
- PRD: 8
- DOC: 2

## Decisions locked
- Locked decisions: 0
- The sole ADR (docs/USER_REQUIREMENTS_VERBATIM.md, precedence 0) is authoritative and wins
  all content conflicts, but is classified locked=false (not a single Accepted-status ADR).
- 11 distinct decision statements extracted (D1–D11): process discipline, UMAP-linear-radial
  layout, triple-product retrieval, unified knowledge panel, strict scroll-spine, data-agnostic
  compile, three foundational fixtures (§S), one ConceptNode/one ConceptEdge schema, no-mocks
  contract, backend-computes/frontend-renders, forbidden concepts.
- See decisions.md.

## Requirements extracted (8)
- REQ-three-register-model       (docs/features/three_register_model.md)
- REQ-three-fixture-api          (docs/features/four_fixture_api.md)
- REQ-live-scan-cleanup          (docs/features/live_scan_cleanup.md)
- REQ-halo-retrieval             (docs/features/halo_retrieval.md)
- REQ-signal-stream              (docs/features/signal_stream.md)
- REQ-pattern-map                (docs/features/pattern_map.md)
- REQ-6d-umap                    (docs/features/6d_umap.md)
- REQ-click-to-edit              (docs/features/click_to_edit.md)
- See requirements.md.

## Constraints (4)
- precedence 1: CONSTRAINT-domain-model            (protocol / design contract)
- precedence 2: CONSTRAINT-frontend-redesign       (api-contract / object model)
- precedence 3: CONSTRAINT-black-slate-goal        (schema / rendering contract)
- precedence 3: CONSTRAINT-html-dedup-content-tree (api-contract / transform spec)
- See constraints.md.

## Context topics (2)
- Documentation chain / source-of-truth precedence (docs/DOC_MAP.md)
- Features layer index                             (docs/features/README.md)
- See context.md.

## Conflicts
- BLOCKERS: 0
- Competing variants (WARNINGS): 0
- Auto-resolved / INFO: 3
- The previous run's 2 WARNINGS (stale four-fixture vs. three-fixture contradiction) are
  verified RESOLVED — recorded as INFO.
- Detail: ../INGEST-CONFLICTS.md

## Pointers
- Decisions:    decisions.md
- Requirements: requirements.md
- Constraints:  constraints.md
- Context:      context.md
- Conflicts:    ../INGEST-CONFLICTS.md

## Status
READY — safe to route. No blockers, no unresolved competing variants.
