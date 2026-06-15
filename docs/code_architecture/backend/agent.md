# Backend — Agent (Runtime · Fixture · Template · SLM)

> **Owns:** the meta-cognition tick, the Agent fixture's prompt/template structure, and the SLM client. Files: `agent_runtime.py`, `slm_client.py`, the Agent fixture in `foundation_fixtures.py`. Design: §12 / §9.5.1 / §9.6 / §7.2 / §O.21 / §13.5. Realises `code_constraints/agent.md`. SLM is a no-mocks boundary (`subsystems.md`).

---

## §1 — Responsibility

Run the autonomous agent loop — perceive the workspace, transform via the SLM, emit mutations — where the **agent body lives in user-designated parameter cards** (§8D.37), not a special card type. Hold the Agent fixture's `meta_prompt → prompt → output` scheme plus the **`template` functional-object** that does input-prompt templating AND output parsing simultaneously (§O.21). Run the real SLM (`Nous-Hermes-2-Mistral-7B-DPO`, no Llama).

---

## §2 — Public Surface

```python
# agent_runtime.py
class MetaCognitionTick:
    async def run_async(self, parameter_card_id: str) -> TickResult   # POST /api/agent/tick
def spawn_agent_body(goal: str, name: str | None) -> AgentBody         # POST /api/agent/spawn → 4 cards + edges

class ActionResolver:                       # parses structured action JSON → lifecycle calls
    def apply(self, action: dict, *, actor: str) -> EditDiff           # actor = "agent:<id>"

# slm_client.py (no-mocks boundary)
class SLMClient:
    def generate(self, prompt: str, *, schema: PydanticModel | None = None) -> str
    async def async_stream_chat(self, prompt: str) -> AsyncIterator[str]   # yields agent_token frames
    def _resolve_model_name(self) -> str    # REJECTS any *llama* override loudly (§13.5)
```

---

## §3 — Internal Logic

### §3.1 The agent body subgraph (§12.1)
`spawn_agent_body` creates four peer ConceptNodes — **parameter · perception · transformer · emitter** — wired by `PERCEPTION_OF / TRANSFORMER_OF / EMITTER_OF` edges, with backing pointers `agent::{perception,transformer,emitter}::<pcid>` (`data_schemas.md` §3). The **parameter card** is the control surface: editing it pauses/resumes; deleting it terminates the agent (§12). Spawn records `actor="agent:spawn"` diffs.

### §3.2 The tick (§12 — perceive → transform → emit)
```
run_async(parameter_card_id):
  PERCEIVE:   ApparitionService.surface_for(perception_focal)        # real nomic apparitions over the workspace (retrieval.md)
  TRANSFORM:  async_stream_chat(template.render_input(meta_prompt, prompt, perceptions))
              → stream agent_token frames into the token ring buffer; accumulate rationale
  EMIT:       template.parse_output(buffer)  → list[action]          # pydantic output schema (§O.21)
              for action in actions: ActionResolver.apply(action, actor=f"agent:{id}")   # each = an Editor call (§12.6.1)
```
- **Emitter actions ARE Editor calls** (§12.6.1): `ActionResolver` = `{CreateCardAction, LinkAction, WriteFieldAction, InvokeAction, …}`, each routed through `apply_update_lifecycle` (lifecycle.md) → so agent edits are logged, cascaded, and rollback-able like any user edit.
- The cascade's **actor-aware short-circuit** (`agent:<id>`) prevents the agent re-triggering itself (lifecycle.md §3.2).

### §3.3 The `template` functional-object (§O.21)
A functional-object on the Agent fixture (backing `agent::template::<wsid>`) authored as a **field-tree** (the minimalist pydantic pattern, §O.20). It `{var}`-templates the input prompts AND applies the pydantic output schema — input templating and output parsing in one object — over the `meta_prompt → prompt → output` flow. Downstream consumers read the parsed output as a normal field-tree (provenance `agent-output`, perimeter-projected, layout.md §3 step 6).

### §3.4 SLM client (§13.5)
GPT4All `Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf` on CUDA. `_resolve_model_name` raises on any `*llama*` override (forbidden). Fake gate `WFH_FAKE_SLM=1` (harness only) returns deterministic tokens; production never sets it.

---

## §4 — Dependencies

- **Calls:** ApparitionService (retrieval.md), `SLMClient`, `ActionResolver` → ConceptLifecycle (lifecycle.md), the `template` functional-object → compile (compute.md §3.1 `structured`).
- **Called by:** `POST /api/agent/{spawn,tick}`, `GET /api/agent/cascade_status`, and the cascade when an agent parameter card is live.

---

## §5 — Excluded

- The fluid-agent simulation (§12.8 — deferred, `migration.md`). The register/telos framing of meta-cognition. Only the tick loop + body subgraph + template + SLM boundary are encoded.
