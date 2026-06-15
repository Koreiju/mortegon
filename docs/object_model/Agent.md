# Object: Agent (Foundational Fixture)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §1.2 (verbatim spec — *"Agent: slm with a meta-prompt, prompt, and output primitive functions"*), §9.5 (four foundational fixtures), §9.5.1 (Agent API), §12 (the agent body subgraph), §12.2.1 (recursion-over-iteration integration scheme), §12.6.1 (agent/editor entanglement).

**Status.** Realised — `fixture::agent::<wsid>` is a foundational fixture (four-fixtures-present); the three primitives are wired at `POST /api/agent/{meta_prompt,prompt,output}` (+ the `agent-{meta-prompt,prompt,output}` REPL actions) and exercised end-to-end by the `agent-three-primitives-chain` scenario (meta_prompt → prompt → output, real-or-stub SLM). The legacy single-call `Agent.invoke` survives as a convenience wrapper. Verified by `agent-three-primitives-chain` + full-smoke.

---

## §1 — What it is

The Agent fixture is the workspace's SLM (small language model) computational endpoint, surfaced as a foundational fixture (§9.5) alongside WebBrowser, Database, and Editor. It is not a black-box SLM call but three composable primitives — a meta-prompt setter, a prompt setter, and an `output` invoker — that the user (or the agent itself reaching into its own emitter) wires as a three-node chain. The chain's terminal `output` carries the live token stream (`agent_token` WS frames) and, when a Pydantic schema is provided, validates the structured result before returning it. Contextuality and continuity within recurrent conversations of agents also enable iterative procedural generative structures that aggregate the totality of the agent outputs for the initial input prompt, and a recurrent feedback prompt that can be wired in back to the same agent, in which context preservation between inputs to the same agent recurrently until stop. The Agent also carries a **`template` functional-object** (§O.21): a single template engine bound to the meta_prompt → prompt → output scheme that **parses the input prompts and the output simultaneously** — `{var}`-templating `meta_prompt`/`prompt` and applying the pydantic output schema of `output` (§7.2 / §O.20), authored in the minimalist field-tree pattern rather than raw JSON schema.

The §12.6.1 framing makes Agent's role symmetric to Editor's: the agent's reasoning *is* the imaginary register's expression of the same graph it operates on. The agent's emitter (one of its body cards, §12.1) calls Editor primitives identically to how the user calls them; Agent provides the SLM surface that the emitter routes its action JSON through.

The §12.2.1 integration scheme makes the agent a step in a recursion-over-iteration loop with world perceptions (the projector's chunks) as initial conditions and the perimeter-encompassing outputs (§6.6.1) as the locus of the loop's closing return.

---

## §2 — Shape

The Agent fixture is a `python_object` ConceptNode (`backing_pointer = fixture::agent::<wsid>`) with three `python_function` children plus a **`template` functional-object** (§O.21 — input-prompt templating + output parsing over the meta_prompt → prompt → output scheme). Each function carries a port schema (§9.8) the wiring uses.

### §2.1 `Agent.meta_prompt`

```
Signature: (text: str) -> str
Ports:
  inputs:  [{name: "text", type: "str", required: true}]
  outputs: [{name: "meta_prompt", type: "str"}]
Backing: agent::meta_prompt::<wsid>
```

Sets or returns the current meta-prompt for the next `output` invocation. Idempotent on identical text. State is per-agent-body (each spawned agent has its own meta_prompt slot; the fixture-level meta_prompt is the workspace default).

### §2.2 `Agent.prompt`

```
Signature: (text: str) -> str
Ports:
  inputs:  [{name: "text", type: "str", required: true}]
  outputs: [{name: "prompt", type: "str"}]
Backing: agent::prompt::<wsid>
```

Sets or returns the user-facing prompt for the next `output` invocation. The text accepts `{var}` references; they resolve at compile time (§7.2) using the same recursive substitution as any other field's text. Resolving a `{var}` reference into a multi-line value (e.g., a `Database.concept` result rendered as a tree-print) preserves indentation and newlines per §4.1.1's print-form contract.

### §2.3 `Agent.output`

```
Signature: (schema: PydanticType | None = None) -> AgentResult
Ports:
  inputs:  [{name: "schema", type: "PydanticType | None", required: false, default: null}]
  outputs: [{name: "result", type: "AgentResult"}]
Backing: agent::output::<wsid>
```

Fires the SLM call against the currently-set `meta_prompt` and `prompt`. Streams `agent_token` WS frames (§10.1) as tokens arrive. If a Pydantic schema is provided, the structured output is validated; validation failure surfaces as `{_validation_error, _raw}` envelope. The rendering settles when the SLM finishes; the rendering is written back to the ConceptNode via the lifecycle (§10.2) so downstream cascade re-fires.

### §2.4 `Agent.invoke` (legacy wrapper)

```
Signature: (meta_prompt: str, prompt: str, output_template: str | None = None) -> AgentResult
```

Convenience wrapper that calls `meta_prompt(meta_prompt) → prompt(prompt) → output(output_template)` in sequence as a single REST call. Retained for back-compat; new code should wire the three primitives explicitly to compose with cascade re-fires and partial-fire patterns.

### §2.5 Companion methods (Agent body subgraph spawn, §12.1)

| Method | Purpose |
|---|---|
| `Agent.spawn(goal, name?)` | Create a new agent body: parameter + perception + transformer + emitter quartet of ConceptNodes wired via `PERCEPTION_OF` / `TRANSFORMER_OF` / `EMITTER_OF` / `PERCEIVES` edges. Returns `parameter_card_id`. |
| `Agent.fork(source_pcid, name?)` | Clone an existing agent body subgraph. |
| `Agent.tick(parameter_card_id)` | Run one MetaCognitionTick: perceive → transform → emit. See [`AgentRuntime.md`](AgentRuntime.md). |
| `Agent.perceive(parameter_card_id)` | Fire only the perception step (apparition surface read against the parameter card's focal). |
| `Agent.emit(parameter_card_id, action_json)` | Apply an action JSON through the ActionResolver, equivalent to one emitter step. |

---

## §3 — Lifecycle

### §3.1 Fixture materialisation

`foundation_fixtures.ensure_foundation_fixtures(workspace_id)` produces the Agent fixture and its function-child tree on first workspace boot:

1. Create the root `python_object` ConceptNode with `name="Agent"`, `backing_pointer="fixture::agent::<wsid>"`, `provenance="committed-subgraph"`, `data={qualified_name, read_only: true, members: [<child ids>]}`.
2. Create the three primitive `python_function` children (`Agent.meta_prompt`, `Agent.prompt`, `Agent.output`) with `data={qualified_name, read_only: true, no_datablock: true, ports: {...}}` and `OBJECT_HAS_FUNCTION` edges from the parent.
3. Create the companion `python_function` children (`Agent.spawn`, `Agent.fork`, `Agent.tick`, `Agent.perceive`, `Agent.emit`) identically.
4. Materialise `FUNCTION_INPUT_TYPE` and `FUNCTION_OUTPUT_TYPE` edges for each function's port schema, resolving target types (e.g., `Agent.output`'s output type resolves to `AgentResult` — itself materialised as a `python_object` child of Agent).

Idempotent — re-running on an already-materialised workspace is a no-op (the existing tree is detected by `backing_pointer` match).

### §3.2 Agent body subgraph spawn

`Agent.spawn(goal, name?) -> parameter_card_id`:

1. Through the lifecycle dispatcher (§10.2):
   - Create parameter card (`type_hint="agent_parameter"`, `data={goal, step_index: 0, paused: false, cascade_enabled: true, zone_of_influence: []}`).
   - Create perception card (`backing_pointer="agent::perception::<pcid>"`).
   - Create transformer card (`backing_pointer="agent::transformer::<pcid>"`).
   - Create emitter card (`backing_pointer="agent::emitter::<pcid>"`).
2. Create the four typed edges (`PERCEPTION_OF`, `TRANSFORMER_OF`, `EMITTER_OF`, `PERCEIVES → parameter_card`).
3. Each ConceptNode emits `concept_changed`; each edge emits `concept_changed` × 2.
4. The frontend renders the four cards wired in the editor canvas.

### §3.3 Agent tick

See [`AgentRuntime.md`](AgentRuntime.md) §tick-loop for the full perceive → transform → emit sequence.

### §3.4 Pause / unpause / termination

| Gesture | Effect |
|---|---|
| `PATCH /api/concepts/<pcid>` with `data.paused=true` | Scheduler halts; next `tick` is a no-op until unpaused |
| `PATCH /api/concepts/<pcid>` with `data.paused=false` | Scheduler resumes; next `tick` runs from saved state |
| `DELETE /api/concepts/<pcid>` | Parameter card deletes; cascade removes perception/transformer/emitter via the body-subgraph cleanup; EvolutionLog captures the lineage |

---

## §4 — Persistence

The fixture node and its function-child tree are persisted as ConceptNodes in Kuzu like any other. The `backing_pointer` resolves to live Python at runtime via [`BackingRegistry.md`](BackingRegistry.md):

| Backing pointer | Resolves to |
|---|---|
| `fixture::agent::<wsid>` | The workspace's Agent fixture handle (composition of SLMClient + AgentRuntime + ActionResolver) |
| `agent::meta_prompt::<wsid>` | Function setting the workspace-level default meta_prompt |
| `agent::prompt::<wsid>` | Function setting the workspace-level default prompt |
| `agent::output::<wsid>` | Function firing the SLM call against the current meta_prompt/prompt |
| `agent::perception::<pcid>` | The PerceptionTick bound to a spawned agent body |
| `agent::transformer::<pcid>` | The SLM dispatch surface for a spawned agent body |
| `agent::emitter::<pcid>` | The ActionResolver gate for a spawned agent body |

A bumped backing pointer version (e.g., when the underlying SLMClient is rebuilt) invalidates compile-cache for any ConceptNode referencing the pointer (§15.6).

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`SLMClient.md`](SLMClient.md) | `Agent.output` calls SLMClient.async_stream_chat against real GPT4All Nous Hermes 2 DPO on CUDA |
| [`AgentRuntime.md`](AgentRuntime.md) | `Agent.tick` invokes `MetaCognitionTick.run_async`; the spawn lifecycle creates the four body cards |
| [`Editor.md`](Editor.md) | The agent's emitter card calls `Editor.create`/`link`/`overwrite`/`delete` via ActionResolver — Editor and Agent are entangled (§12.6.1) |
| [`ApparitionService.md`](ApparitionService.md) | The agent's perception card reads `apparition_service.surface_for(parameter_focal)` for its perception payload |
| [`Database.md`](Database.md) | The agent's transformer prompt commonly references `Database.search` or `Database.concept` results as `{var}` substitutions |
| [`WebBrowser.md`](WebBrowser.md) | The agent's emitter commonly issues `InvokeAction { method: WebBrowser.scan }` to drive new scans |
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | All emitter actions enter the lifecycle dispatcher identically to user gestures |
| [`UIStateService.md`](UIStateService.md) | Agent panel state (paused, current sample, perception focal) mirrored for the REPL viewer |
| [`EvolutionLog.md`](EvolutionLog.md) | Every emitter action records an `EditDiff` with `actor=agent:<pcid>` |

---

## §6 — Cross-references

- Feature touchpoints — [`features/four_fixture_api.md`](../features/four_fixture_api.md), [`features/agent_integration_scheme.md`](../features/agent_integration_scheme.md), [`features/perimeter_outputs.md`](../features/perimeter_outputs.md).
- Code constraints — [`api_routes.md`](../code_constraints/api_routes.md) `/api/agent/*` endpoints; [`backend_services.md`](../code_constraints/backend_services.md) SLM real-vs-fake rules; [`error_handling.md`](../code_constraints/error_handling.md) missing-GGUF returns 503.
- Sequence reference — DOMAIN_MODEL §17.5 (agent tick), §17.1.5 (halo ray-projection feeds perception).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Falling back to a stub SLM in production paths | Real-backend → stub fallback is forbidden in production (§13.4); only the harness gate `WFH_FAKE_SLM=1` may engage the stub | Missing GGUF returns 503; the `subsystem-status` row in the viewer flags non-real backends |
| Using Llama as the SLM target | Forbidden-concepts §3; production is Nous Hermes 2 DPO on CUDA | `slm_client._resolve_model_name` rejects any `WFH_SLM_MODEL=*llama*` loudly |
| Calling SLM directly without going through Agent.output | Bypasses the lifecycle's `concept_changed` emission and the EvolutionLog `EditDiff` record | Direct `SLMClient` calls outside the Agent fixture are confined to the harness path; production paths route through Agent.output |
| Wiring the agent's emitter to bypass Editor primitives | The emitter MUST go through Editor's four primitives via the lifecycle; bypassing ActionResolver breaks the §12.6.1 entanglement | The ActionResolver routes every emitter action through `apply_update_lifecycle`; no shortcut path exists |
| Treating `Agent.invoke` as the canonical surface | The three primitives are canonical per §1.2; invoke is a convenience wrapper | New code wires the three primitives; the four-fixture acceptance test asserts the primitives are present |
| Spawning an agent without recording the lineage in EvolutionLog | Rollback over agent activity becomes impossible | `Agent.spawn` enters the lifecycle; EvolutionLog records actor=`agent:spawn` |
| Letting an agent emitter re-trigger its own perception in the same tick | The cascade scheduler's actor-aware short-circuit (§2.7) prevents this; bypassing breaks the integration scheme convergence | The scheduler tags each re-fire with `actor=agent:<pcid>`; same-actor re-fire on the same parameter card short-circuits |
