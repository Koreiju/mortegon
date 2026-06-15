# Code Specs Suite — Line-Level Implementation Contracts

> **Status: planned (line-level spec).** The layer **below** [`code_architecture/`](../code_architecture/) and immediately above CODE. Where `code_architecture/` gives the module decomposition + indicative signatures + pseudocode, this suite gives the **implementable contract**: every public function fully typed, with pre/postconditions, raised errors, step-precise algorithm, complexity, idempotency, and concrete I/O examples. A developer implements directly against these; a reviewer checks code against them line-for-line.
>
> **Precedence.** Design (`DOMAIN_MODEL.md` + `USER_REQUIREMENTS_VERBATIM.md` §M/§N/§O/§Q) wins on intent; `code_architecture/` wins on structure; this suite is authoritative on **exact contract** (signature, type, error, constant, step). When a spec and the blueprint disagree on structure, the blueprint wins and the spec is corrected; when a spec and the design disagree on intent, the design wins.
>
> **⚠ All-Real Tests For Everything (DOMAIN_MODEL §0 / §13, verbatim §Q.1).** Every contract in this suite is verified against the **real** stack — real SLM (Nous-Hermes-2-Mistral-7B-DPO/CUDA) + real embedder (nomic/CUDA) + real WebBrowser (live Selenium) + real LangGraph — with `all_real: true`. The fake gates (`WFH_FAKE_SLM`/`WFH_FAKE_EMBEDDER`/`NO_WEBDRIVER`) are harness-only; no production path sets them. `repl.md` carries the verification-surface assertions; `backend/scanner.md` the live-Selenium boundary; a capability without an all-real probe/scenario is not integrated (§14.4).

---

## §0 — Place In The Chain

```
DOMAIN_MODEL → object_model/ → features/ → code_constraints/ → code_architecture/ → code_specs/ → CODE
(intent)        (object shape)  (UX)        (must-hold)         (how it's built)     (THIS: exact contract)
```
Each spec names the `code_architecture/` doc it deepens and cross-refs the design `§`.

---

## §1 — The Suite

**Cross-cutting foundation** (every per-area spec references these — declared once, never re-declared):
| Doc | Holds |
|---|---|
| [`types.md`](types.md) | Every type: id aliases, enums, records, DTOs, WS frame payloads, REST request/response bodies — fully field-typed |
| [`constants.md`](constants.md) | Every tunable / magic number — value · meaning · source § · env override |
| [`errors.md`](errors.md) | Every error mode → exception class → HTTP status / WS frame / cascade effect; the edge-case catalogue |

**Backend** ([`backend/`](backend/)):
`api` · `lifecycle` · `layout` · `retrieval` · `compute` · `agent` · `materialiser` · `scanner` · `persistence`

**Frontend** ([`frontend/`](frontend/)):
`spine` · `cell` · `real` · `imaginary` · `membranes` · `pulse`

**REPL:** [`repl.md`](repl.md) — the `sim_frontend.py` action catalogue (arg/return per action), the `watch-activity` 7-row dashboard layout, the `env-scenario` contract, the live probes.

---

## §2 — Per-Function Spec Template

Every public function/method is specified as:

```python
def name(pos: T1, *, kw: T2 = default) -> Ret        # signature with exact types (types.md)
```
- **Does** — one sentence.
- **Params** — each param's meaning + constraints (only where non-obvious).
- **Returns** — the exact value + shape.
- **Raises** — error classes (errors.md) + the condition.
- **Pre** / **Post** — pre/postconditions (invariants true before/after).
- **Idempotent?** — yes/no + the key, if a mutation.
- **Algorithm** — numbered steps, precise enough to implement; constants by name (constants.md).
- **Complexity** — where it matters (per-frame, per-mutation, joint refit).
- **Example** — concrete I/O for the load-bearing path.

Specs are **terse**: signatures, tables, numbered steps. No design rationale (that's upstream); the **Excluded** line at the foot of each doc names what is deliberately left to the design layer.

---

## §3 — Conventions

- **Types** — Python: `@dataclass` / `TypedDict` / `Enum` / `NewType` aliases (`types.md`). Frontend: TS-ish interfaces (same field names as the backend DTOs they mirror).
- **Idempotency** — every mutation function takes `idempotency_key: IdemKey | None`; the dedup window is `IDEMPOTENCY_WINDOW` (`constants.md`). Replays return the prior result; they are **not** errors.
- **Errors** — functions raise typed exceptions (`errors.md`); the API layer (`backend/api.md`) maps them to HTTP status + WS `error` frame. Services never return error sentinels.
- **No-mocks** — any function touching SLM / embedder / Selenium / LangGraph / Kuzu documents its real dependency + the harness-only fake gate (`code_architecture/subsystems.md`); a failed real load raises `SubsystemDownError` (→503 + cascade halt), never a stub fallback.
- **Time / ids** — timestamps ISO-8601 UTC strings; ids are opaque `NewType` aliases; `chunk_id` is the one **integer** id (stable instance key).
- **Async** — SLM streaming + WS handlers are `async`; services are sync unless they await a subsystem.
- Signatures are **near-final** but still indicative where the design leaves a free choice; the spec marks such points `(impl-choice)`.

---

## §4 — Excluded (per `code_architecture/README.md` §0)

The same selectivity filter applies, one level deeper: philosophy / registers, aspirational (fluid-sim), theme micro-detail (→ `frontend/theme.md`), historical analysis-plan, and forbidden/legacy code (→ `code_architecture/migration.md`) are **not** specified here. This suite specifies only code that is planned to exist.
