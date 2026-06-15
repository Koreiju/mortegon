# Code Specs — Constants Registry

> **Status: planned.** Every tunable / magic number in one place. A spec that uses a number names it **by symbol**, never inlines the literal — drift is caught here. Value · meaning · source § · env override.

---

## §1 — Layout (`backend/layout.md`, §6.1 / §O.17)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `TARGET_RADIUS` | `40.0` | farthest chunk sits at this radius after sphere-fit (raised from the nominal 25 per **B.3** — "3D spacing too close together") | §O.17 / B.3 |
| `COLLIDER_SAFETY` | `2.2` | min pair separation = `2·R·COLLIDER_SAFETY`; hard, no soft tail (≥2.0 required; bumped 1.15→2.2 per **B.3**) | §O.17 / B.3 |
| `COLLIDER_ITERS` | `8` *(impl-choice)* | Lagrange collider passes per refit | §6.1 |
| `URL_SAFETY_GAP` | `3.0` *(impl-choice)* | gap when placing a new URL root beyond `existing_max_radius` | §18.20 |
| `CAMERA_MIN_FACTOR` | `0.6` | near bound = `0.6 · cluster_radius` | §5.5 |
| `CAMERA_MAX_FACTOR` | `3.0` | far bound = `3.0 · max(\|pos\|)` | §5.5 |
| `UMAP_DIM` | `6` | the joint fit = 3 position + 3 HSV | §8.2.1.2 |
| `REFIT_DEBOUNCE_MS` | `250` *(impl-choice)* | coalesce incremental chunk arrivals before a mid-scan refit | §16.5 |

## §2 — Embeddings & Retrieval (`backend/retrieval.md`, §8 / §15.7)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `NOMIC_DIM` | `768` | nomic embedding dimension | §10.4 |
| `APPARITION_K` | `8` | default halo candidate count | §8.2 |
| `INVERSE_K` | `1` | default closest-inverse count | §7.7 |
| `MULTI_FREQ_K` | `32` | observed-utility events before single→multi-frequency | §18.25 |
| `TFIDF_SPLIT` | `r"[/?&=.]"` | url-specific tokenisation split set | §15.7 |
| `SIMILAR_TO_TOPK` | `16` *(impl-choice)* | neighbours cached per concept | §8.1 |
| `PAGERANK_DAMPING` | `0.85` *(impl-choice)* | standard PageRank damping | §8.1 |
| `PAGERANK_DEBOUNCE_MS` | `800` | settle delay before a joint PageRank refit | §10.6 |

## §3 — Compile / Cascade / Rollout (`backend/compute.md`, §7)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `COMPILE_MAX_DEPTH` | `4` | `compile_subgraph_to_langgraph` / `compile_chain` default depth | §7.1 |
| `CASCADE_DEBOUNCE_MS` | `800` | debounce before cascade re-fires dirty nodes | §7.4 |
| `CASCADE_MAX_DEPTH` | `16` *(impl-choice)* | recursion guard for cascade fan-out | §7.4 |
| `REF_RESOLVE_MAX` | `64` *(impl-choice)* | max `{ref}` resolutions per compile (cycle guard ceiling) | §7.1 |
| `READOUT_DELTA_MAX_INFLIGHT` | `64` *(impl-choice)* | max un-acked async readout-perimeter deltas per workspace before per-node coalescing (keep-latest) | §7.8.3 |

## §4 — Agent / SLM (`backend/agent.md`, §12 / §13.5)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `SLM_MODEL` | `"Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"` | the only production SLM; **Llama rejected** | §13.5 |
| `SLM_DEVICE` | `"cuda"` | default device (`WFH_SLM_DEVICE`) | §13.5 |
| `SLM_MAX_TOKENS` | `512` *(impl-choice)* | per-tick generation cap | §12 |
| `TOKEN_RING_CAP` | `2048` *(impl-choice)* | streamed-token buffer size per agent | §12 |
| `AGENT_BODY_CARDS` | `4` | parameter + perception + transformer + emitter | §12.1 |

## §5 — Embedder model (`backend/retrieval.md`)

| Symbol | Value | Source |
|---|---|---|
| `EMBED_MODEL` | `"nomic-embed-text-v1.5.f16.gguf"` | §10.4 |
| `EMBED_DEVICE` | `"cuda"` (CPU override = real-to-real) | §10.4 |

## §6 — Scanner (`backend/scanner.md`, §15)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `PATTERN_MIN_MEMBERS` | `2` | min homogeneous siblings to emit a chunk pattern | §15.4 |
| `GECKODRIVER_PATH` | `backend/drivers/geckodriver.exe` | headful Firefox driver | §15.1 |
| `GOLDEN_TRIO` | `(title, link, content)` | joint-presence-gated accessor triple | §15.8.1 |
| `DOM_SNAPSHOT_DEDUP` | `sha256` | DOM snapshot disk dedup key | §11.1 |

## §7 — Lifecycle / Persistence / WS (`backend/{lifecycle,persistence,api}.md`, §10 / §2)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `IDEMPOTENCY_WINDOW` | `300s` (5 min) | per-workspace mutation dedup window | §2.5 |
| `WS_RESUME_WINDOW` | `300s` (5 min) | `?resume=<seq>` replay horizon | §2.4 |
| `WS_BACKPRESSURE_HIGHWATER` | `256` *(impl-choice)* | queued frames before shedding sheddable types | §2.4 |
| `BACKEND_PORT` | `8080` | `backend/main.py` default | env knobs |
| `DEFAULT_WORKSPACE` | `"default"` *(impl-choice)* | single-user default workspace id | §1 |

## §8 — Frontend (`frontend/*`, §5 / §11.2)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `IDB_TEXTURE_STORE` | `wfh_texture_cache` / `textures` | IndexedDB db/store | §11.2 |
| `TWEEN_MS` | `400` *(impl-choice)* | default interruptible-tween duration | §5.4 |
| `TELEMETRY_BATCH_MS` | `120` *(impl-choice)* | gateway telemetry flush interval | §10.5 |
| `HARD_COLLIDER_SAFETY_FE` | `2.0` | client collider matches `COLLIDER_SAFETY` so frames agree | §5.5 |
| `LINK_HARD_PX` / `LINK_SOFT_PX` | `2` / `1` | hard / soft link stroke width | §O.16 |
| `CONNECTOR_HEX` | `#ffd700` | the only-hue 2D↔3D headless connector | theme |

## §9 — REPL (`repl.md`, §11.7 / §11.8)

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| `WATCH_ROWS` | `7` base (scan / retrieval / visible-3D / hidden-3D / pinned / compile / subsystems) + realised extension rows (halo / chrome / latch / spine / autocomp / editing / halochain / signal / rollout / apparition / nodefold) — one per §10.5.1 mirror field | §11.8 |
| `SIM_ACTIONS` | `157` across `19` categories (asserted by `action-registry-coverage`) | `sim_frontend.py` action surface | §11.7 |
| `FULL_SMOKE_SCENARIOS` | `83` (chain); `86` registered in `_ENV_SCENARIOS` | `env-scenario --name full-smoke` | §11.7 |
| `REPL_BACKEND_DEFAULT` | `http://localhost:8000` | pass `--backend http://127.0.0.1:8080` to align | env knobs |

> Values marked `(impl-choice)` are not fixed by the design — the spec picks a sane default; changing one is a local decision, not a design change. All others are design-binding.
