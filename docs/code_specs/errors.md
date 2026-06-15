# Code Specs — Error Catalogue

> **Status: planned.** Every error mode → exception class → HTTP status / WS frame / cascade effect, plus the edge-case dispositions (the things that are **not** errors). Services raise typed exceptions; the API layer (`backend/api.md`) maps them. Realises `code_constraints/error_handling.md`.

---

## §1 — Exception Classes → Status / Frame

> **Realized state.** The **status-code + WS-frame + cascade columns are the binding, realized contract** — they hold in code today via FastAPI `HTTPException(status_code=...)` raised inline at the route/service boundary plus the in-dispatcher / in-client guards: fixture-delete → **409** (DELETE route + the §1.6 dispatcher guard), subsystem failure → **503** (e.g. `routes.py` SLM path `raise HTTPException(503, "SLM error: …")`), the `*llama*` reject at SLM load (`slm_client.py`), `all_real` on `GET /api/subsystem_status`. The **named exception classes** in the first column (`FixtureGuardError`, `SubsystemDownError`, …) are the *design intent* — a single typed-exception taxonomy with one central API-layer mapper (cleaner OOP than scattered inline `HTTPException`s) — and are NOT yet realized as distinct classes. Code to the status/disposition contract; treat the class names as the target refactor.

| Exception (planned class) | Raised when | HTTP | WS | Cascade |
|---|---|---|---|---|
| `FixtureGuardError` | delete of a `fixture::*` node (lifecycle.md §guard) | **409** | `error` (`--accent-error`) | unaffected; the delete is `EditDiff(action="rejected")` |
| `ReadOnlyEditError` | edit/patch of a `read_only` python-native node (§8D.4.2) | **409** | `error` | unaffected |
| `SubsystemDownError` | required real subsystem failed to load / died (SLM, embedder, Selenium, LangGraph, Kuzu) | **503** | `error` | **HALTS** (subsystems.md §2) — no stub fallback |
| `ForbiddenModelError` | `WFH_SLM_MODEL` resolves to a `*llama*` variant (§13.5) | **500** at boot | — | process refuses to serve |
| `ValidationError` | malformed body / missing required field | **422** | `error` | unaffected |
| `NotFoundError` | unknown `concept_id` / `edge_id` / `workspace_id` | **404** | `error` | unaffected |
| `BackingResolveError` | `backing_pointer` resolves to nothing (stale registry) | **500** | `error` | the dependent compile is skipped + logged |
| `CompileError` | dispatch raised (SLM bad output, python_entry threw, cypher invalid) | **200** + `error` frame | `error` | node's `rendering` keeps prior value; cascade continues for siblings |
| `ScanError` | Selenium navigation / driver failure mid-scan | **200** + `error` | `error` + partial `done` | unaffected; chunks already streamed persist |

`error` frame shape (`types.md` §7): `{type:"error", ref:<gesture_ref>|None, message:str}`. The frontend renders it in the desaturated `--accent-error` envelope (`frontend/spine.md`); a pending gesture echo is rolled back.

---

## §2 — NOT Errors (explicit dispositions)

| Situation | Disposition |
|---|---|
| **Idempotency replay** — same `idempotency_key` within `IDEMPOTENCY_WINDOW` | return the **prior** `EditDiff` unchanged; no re-apply; **200** (lifecycle.md §3.1 step 2) |
| **Concurrent edit conflict** (two actors, same node) | **last-write-wins**; no lock, no error — rollback is the user's tool (§2.7) |
| **Backpressure** — WS queue past `WS_BACKPRESSURE_HIGHWATER` | **shed** oldest sheddable frames (`chunks_partial`, progress); keep `done`/`error`/latest `umap_canonical`/all `concept_changed`+`evolution_diff` (spine.md §3.2). Not surfaced |
| **Compile `{ref}` cycle** | cycle-safe: a visited-set breaks the loop at `REF_RESOLVE_MAX`; the ref renders as its braced marker, no error (compute.md §3.2) |
| **Closest-inverse no match** | return `[]`; the output port shows no suggestion (not an error) |
| **Halo empty** (no candidates) | open with zero phantoms; not an error |
| **CPU embedder** (`WFH_EMBEDDER_DEVICE=cpu`) | real-to-real; logs **WARNING**, `fake_env:false`; stays no-mocks |
| **Texture fetch fail** | use the transparent-PNG fallback but **never cache it** (real.md §3.3) — re-resolves next frame |
| **WS reconnect gap > `WS_RESUME_WINDOW`** | server can't replay; client does a full re-sync (fresh snapshot), not an error |

---

## §3 — Invariant Violations (must-never; assertion-level)

These are programmer errors — they must be impossible by construction, asserted in dev:

- A mutation that does **not** pass through `apply_*_lifecycle` (the one-dispatcher invariant, lifecycle.md).
- A second mutation path / a second edge table (§3.2).
- A `type_hint`-based runtime branch in the dispatcher (`type_hint` is naming-only, types.md §3).
- A description routed to TF-IDF or a rendering routed to nomic **for a scan chunk** (axes-never-mix, retrieval.md §3.1) — the panel deviation (§O.22) is the *only* both-models path.
- A frontend module computing UMAP / embeddings / PageRank / compile (backend-computes invariant, frontend/README).
- A `stroke-dasharray` or an arrowhead in any link render (§O.16 / §18.7).
- A real→stub fallback on a production path (subsystems.md §2).

A violated invariant is a **build/test failure**, not a runtime 5xx — caught by `env-scenario` + the no-mocks CI gate (`repl.md`).

---

## §4 — Excluded

Retry/backoff policy for transient subsystem blips (impl-choice, below the spec line) and the register framing of "loud failure."
