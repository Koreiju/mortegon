# Code Architecture — Subsystems (the No-Mocks Contract)

> **Status: planned.** The four real subsystems, their wrappers, the harness-only fake gates, and the loud-failure contract. Distilled from `DOMAIN_MODEL.md` §13 and `CLAUDE.md` "No-Mocks Contract". Realises `code_constraints/no_mocks.md`. Cross-cuts the backend suite ([`backend/`](backend/)).

---

## §1 — The Contract (§13 / §8D.46)

**Production paths run real subsystems. Always.** Real-backend → stub fallback is **forbidden in production**. A failed load returns **503 + cascade halt**, never a silent stub substitution. The fake gates exist only for the REPL harness and CI's stub-mode pass.

| Subsystem | Real | Wrapper (module) | Fake gate (harness-only) |
|---|---|---|---|
| **SLM** | GPT4All `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA. **No Llama.** | `slm_client.py` ([`backend/agent.md`](backend/agent.md)) | `WFH_FAKE_SLM=1` |
| **Embedder** | GPT4All `Embed4All` `nomic-embed-text-v1.5.f16.gguf` on CUDA (CPU override allowed, still nomic) | `embedding_service.py` ([`backend/retrieval.md`](backend/retrieval.md)) | `WFH_FAKE_EMBEDDER=1` |
| **Selenium** | headful Firefox via `backend/drivers/geckodriver.exe` | `selenium_client.py` ([`backend/scanner.md`](backend/scanner.md)) | `NO_WEBDRIVER=1` |
| **LangGraph** | `langgraph.graph.StateGraph` | `conceptual_compute.py` ([`backend/compute.md`](backend/compute.md)) | **none** (missing import = hard error) |
| **Graph DB** | KuzuDB | persistence layer ([`backend/persistence.md`](backend/persistence.md)) | **none** |

---

## §2 — Load + Failure Semantics (§13.4)

- **Eager init on FastAPI lifespan** — SLM, embedder, Selenium load at boot; failures surface immediately, not on first request.
- **Failure = 503 + cascade halt.** The cascade scheduler ([`backend/lifecycle.md`](backend/lifecycle.md)) stops dispatching when a required subsystem is down; in-flight gestures get an `error` frame in the `--accent-error` envelope (`contracts.md` §3).
- **No quiet degradation.** There is no code path that, on a real-load failure, substitutes a stub and continues. The `_PlainChainApp` LangGraph surrogate exists for unit-shape probes only and is never reachable from a production route (§13.1).
- **CPU embedder is real-to-real**, not a fallback to a fake — `WFH_EMBEDDER_DEVICE=cpu` stays in the no-mocks lane (logs a WARNING; still nomic).

---

## §3 — `GET /api/subsystem_status` (the operator surface, §13.3)

```json
{ "ok": true, "all_real": true,
  "slm":       {"backend":"gpt4all","model":"Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf","loaded":true,"device":"cuda","fake_env":false},
  "embedder":  {"backend":"nomic","model":"nomic-embed-text-v1.5.f16.gguf","device":"cuda","fake_env":false},
  "selenium":  {"backend":"selenium","loaded":true,"driver_class":"WebDriver"},
  "langgraph": {"backend":"langgraph","loaded":true,"has_StateGraph":true},
  "apparition_mode": "single-frequency | multi-frequency" }
```
- `all_real` = `AND` over each subsystem's `loaded && !fake_env`. **CI asserts `all_real: true`** before any contract-bearing scenario runs.
- The Llama guard: `slm_client._resolve_model_name()` rejects any `*llama*` `WFH_SLM_MODEL` override loudly — a forbidden model never reports `loaded:true` (it raises) (§13.5).
- Surfaced in the REPL `watch-activity` seventh row ("subsystems") and the `frontend/repl_mirroring.md` dashboard.

---

## §4 — Env Knobs (the complete gate roster)

| Knob | Effect | Lane |
|---|---|---|
| `WFH_FAKE_SLM=1` | deterministic SLM stub | harness only |
| `WFH_FAKE_EMBEDDER=1` | hash-deterministic 768-dim fake | harness only |
| `NO_WEBDRIVER=1` | skip Selenium init at boot | harness only |
| `WFH_SLM_MODEL=…` | production GGUF (default Nous-Hermes-2-DPO; **Llama rejected**) | production |
| `WFH_SLM_DEVICE=cuda` / `WFH_EMBEDDER_DEVICE=cuda` | device (CPU override = real-to-real) | production |
| `WFH_DB_PATH=…` | Kuzu DB path | both |

**Production sets none of the fake gates.** The harness sets them per scenario; the full-smoke contract runs green in **both** modes.

---

## §5 — Excluded (per README §0)

- The register-level rationale for transparency (Symbolic). Only the wire status + load/failure behaviour is encoded.
- Per-subsystem internal algorithms — those live in the owning backend doc (`agent.md`, `retrieval.md`, `scanner.md`, `compute.md`).
