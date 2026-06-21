## Conflict Detection Report

Mode: new (net-new bootstrap; no existing .planning context to check against).
Sources: 15 classified docs (1 ADR, 4 SPEC, 8 PRD, 2 DOC).
Precedence: ADR(0) > SPEC(1-3) > PRD(6) > DOC(4,6); per-doc manifest integer honored.
Cycle detection: ran (DFS three-color, depth cap 50). The sibling feature PRDs cross-link
mutually (e.g. four_fixture_api ↔ signal_stream ↔ three_register_model), but these are
peer navigation references, not supersession chains — no traversal blowup, no synthesis cycle.
UNKNOWN/low-confidence docs: none (all 15 classified high-confidence).

Re-run note: This re-run follows reconciliation of the source docs to the §S three-fixture
re-baseline. The previous run's 2 WARNINGS (stale four-fixture vs. three-fixture contradiction
across four_fixture_api.md, live_scan_cleanup.md, three_register_model.md, features/README.md)
have been verified RESOLVED — see INFO bucket.

### BLOCKERS (0)

None.

Only ADR-vs-ADR locked contradictions gate the workflow, and there is exactly one ADR in the
ingest set (USER_REQUIREMENTS_VERBATIM, precedence 0). With a single ADR, no LOCKED-vs-LOCKED
contradiction is possible. No dependency cycles, no UNKNOWN-confidence-low docs.

### WARNINGS (0)

None.

The previous run's 2 competing-fixture-count warnings are resolved (now INFO). No PRD defines
a requirement on the same scope with divergent acceptance criteria — the 8 feature PRDs cover
disjoint scopes, so no competing acceptance variants exist.

### INFO (3)

[INFO] Resolved: four-fixture vs. three-fixture contradiction cleared across 4 docs
  Found: docs/features/four_fixture_api.md now leads with a §S deprecation banner declaring
    THREE fixtures (Agent/WebBrowser/Database) authoritative; the Editor "fourth fixture" is
    removed (§S.1) and its create/link/overwrite/delete gestures are demoted to panel-scheme
    intrinsics routed via /concepts + /concept_edges. The §6 acceptance bar asserts exactly
    three root python_object ConceptNodes and "No fixture::editor::<wsid> card materialises";
    four-fixture prose is explicitly marked "(historical)" and "superseded".
  Found: docs/features/live_scan_cleanup.md asserts "Three fixtures (Agent/WebBrowser/Database)
    remain present + reachable after purge (§S)" and "Kuzu ConceptNode count == three-fixture-
    baseline (§S)".
  Found: docs/features/three_register_model.md asserts "purge returns the workspace to the
    three-fixture baseline (§S)"; residual Editor mentions are the §S-sanctioned Imaginary-
    register mutation surface, not a fixture-count claim.
  Found: docs/features/README.md catalogues "the three-fixture surface (§S; was four)" and
    "Editor demoted to mutation-gestures, §S".
  Note: All four lower-precedence docs now agree with ADR decision D7 (three foundational
    fixtures). The contradiction the previous run flagged as WARNING is fully reconciled. No
    user action required.

[INFO] Auto-resolved (transparency): ADR > SPEC > PRD > DOC precedence, no overrides triggered
  Found: All non-ADR docs (4 SPEC, 8 PRD, 2 DOC) elaborate ADR decisions without contradiction.
  Note: Because no lower-precedence doc asserts a technical decision contradicting a higher-
    precedence source, precedence ordering did not have to override any content. The §S
    fixture-count reconciliation already landed at the doc level, so synthesis adopts the
    three-fixture baseline directly rather than auto-resolving a live conflict.

[INFO] ADR self-declared supreme but locked=false
  Found: docs/USER_REQUIREMENTS_VERBATIM.md (type ADR, precedence 0) declares itself the
    source-of-truth that wins all conflicts, but is not a single Accepted-status ADR, so the
    classifier set locked=false.
  Note: With precedence 0 it still wins every content conflict in synthesis. Because it is the
    only ADR, the LOCKED distinction has no bearing here — there is no second ADR to contend
    with. Recorded for downstream transparency.
