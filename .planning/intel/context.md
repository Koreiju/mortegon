# Context (DOC Intel)

Running notes from 2 classified DOC-type sources, keyed by topic with source attribution.
DOCs are navigational / overview material (precedence 4 and 6); they carry no decisions,
requirements, or contracts of their own — they index the layers above.

---

## Topic: Documentation chain / source-of-truth precedence
- source: docs/DOC_MAP.md  (precedence 4)
- notes: Navigation index for the layered documentation chain: design ideation → object/
  feature elaboration → code constraints → code architecture → code specs. Establishes the
  source-of-truth precedence order (USER_REQUIREMENTS_VERBATIM supreme, then DOMAIN_MODEL,
  then FRONTEND_REDESIGN + frontend/ suite, then DOC_MAP itself, with
  MORTEGON_INTEGRATION_SCHEME + CODEBASE_GAP_ANALYSIS marked historical/superseded). Read
  this to navigate between documentation layers (object_model/, features/, code_constraints/,
  code_architecture/, code_specs/, code_specs/repl.md, code_specs/backend/scanner.md).

## Topic: Features layer index
- source: docs/features/README.md  (precedence 6)
- notes: Index for the per-feature documentation layer, cataloguing cross-cutting
  user-visible features by Mortegon register and mapping each to its guardian anti-goal.
  Registers covered: API features (the three-fixture surface §S — "was four" — plus library
  middleware), retrieval halo + multi-frequency PageRank, 3D/projector UMAP features,
  panel/editor features (click-to-edit, plus-signs, signal-stream, autocomplete, play/pause),
  scanner pattern-map features, observability/verification features. The four_fixture_api doc
  is catalogued with "Editor demoted to mutation-gestures, §S". Carries a feature-to-anti-goal
  cross-reference and the feature-doc anatomy / extension process.

---

Both DOCs are internally consistent with the §S three-fixture re-baseline and add no claims
that conflict with the ADR, SPECs, or PRDs.
