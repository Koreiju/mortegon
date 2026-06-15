# Spec — Backend / Agent (Runtime · Fixture · Template · SLM)

> Deepens [`code_architecture/backend/agent.md`](../../code_architecture/backend/agent.md). Files: `agent_runtime.py`, `slm_client.py`. Types: [`../types.md`](../types.md) §5. Constants: [`../constants.md`](../constants.md) §4. SLM = no-mocks boundary. Agent body lives in user parameter cards (§8D.37), not a special type.

---

## §1 — `SLMClient` (no-mocks boundary)

```python
# Realized (slm_client.py). `_resolve_model_name` is a MODULE function; the
# generate path is split by output kind (text / json / pydantic-structured);
# `async_stream_chat` is the streaming generator.
def _resolve_model_name() -> str                                   # module fn
class SLMClient:
    def generate_text(self, prompt: str, system_prompt: str = "") -> str
    def generate_json(self, prompt: str, system_prompt: str = "") -> dict
    def generate_structured(self, prompt: str, schema, ...) -> ...  # pydantic-constrained/-validated
    async def async_stream_chat(self, prompt: str, ...) -> AsyncIterator[str]
```
- **`_resolve_model_name`** — read `WFH_SLM_MODEL` (default `SLM_MODEL`); if it matches `*llama*` (case-insensitive) it **rejects loudly** (`slm_client.py:60` — logs "forbidden" + refuses; the §1.5 no-Llama guard, realized as an inline reject, not a named `ForbiddenModelError` class — errors.md §1). Returns the resolved GGUF name.
- **load** — GPT4All on `SLM_DEVICE` (cuda); a failed load surfaces as 503 on the SLM routes (errors.md). Fake gate `WFH_FAKE_SLM` → deterministic stub generator (harness only; `fake_env:true`).
- **`generate_structured`** — constrain/validate output to the pydantic model (retry once on parse fail). **`async_stream_chat`** — yields tokens; the caller buffers into the token ring (`TOKEN_RING_CAP`) and emits `agent_token` frames per token.

---

## §2 — `spawn_agent_body`

```python
# Realized name (agent_runtime.py:1627): spawn_agent_body_subgraph.
def spawn_agent_body_subgraph(goal: str, name: str | None = None, *, workspace_id: WorkspaceId) -> dict
```
- **Does** — create the `AGENT_BODY_CARDS` (=4) peer ConceptNodes and wire them.
- **Post** — four nodes (`parameter`, `perception`, `transformer`, `emitter`) exist with backings `agent::{perception,transformer,emitter}::<id>` (the parameter card is the control surface, no special backing); edges `PERCEPTION_OF`, `TRANSFORMER_OF`, `EMITTER_OF`; each create is an `apply_update_lifecycle(actor="agent:spawn")` diff.
- **Algorithm:** create parameter (provenance USER) → create perception/transformer/emitter (provenance AGENT) each via lifecycle.md → add the three edges via lifecycle.md (`change_kind=LINK`). Returns `AgentBody(ids...)`.

---

## §3 — `MetaCognitionTick.run_async`

```python
class MetaCognitionTick:
    async def run_async(self, parameter_card_id: ConceptId) -> TickResult
```
- **Pre** — the parameter card exists and is not paused (paused state read from the parameter card's `data`). **Post** — `TickResult(agent_id, tokens, actions_applied, rationale)`; each emitted action is a logged lifecycle mutation; the agent self-loop guard prevents immediate re-fire (lifecycle.md §3).
- **Algorithm (perceive → transform → emit):**
```
agent_id = owner_of(parameter_card_id)
1. PERCEIVE:  perceptions = ApparitionService.apparitions_for_focal(perception_focal(agent_id), workspace_id=ws)   # real nomic over workspace (realized name; spec earlier said surface_for)
2. TRANSFORM: prompt = template.render_input(meta_prompt, prompt_field, perceptions)        # §4
              buffer = ""
              async for tok in slm.async_stream_chat(prompt):
                  buffer += tok; broadcaster.emit(AgentTokenFrame(agent_id, tok, partial=True))
              broadcaster.emit(AgentTokenFrame(agent_id, "", partial=False))
3. EMIT:      actions = template.parse_output(buffer)            # pydantic schema → list[action] (§4)
              n = 0
              for a in actions:
                  ActionResolver.apply(a, actor=f"agent:{agent_id}")    # each = an Editor call (§12.6.1) → lifecycle.md
                  n += 1
return TickResult(agent_id, tokens=len(buffer.split()), actions_applied=n, rationale=buffer)
```

```python
class ActionResolver:
    def apply(self, action: dict, *, actor: str) -> EditDiff      # dispatch on action["op"]
```
Ops = `{create_card, link, write_field, invoke, delete}` → each maps to the matching lifecycle.md call. Deleting the **parameter card** terminates the agent (lifecycle.md guard does not apply — parameter cards are user nodes, deletable).

---

## §4 — Agent fixture + `template` functional-object (§O.21)

The Agent fixture (`fixture::agent::<wsid>`) carries `meta_prompt`, `prompt`, `output(schema?)`, legacy `invoke`, and the **`template`** functional-object (`agent::template::<wsid>`), authored as a minimalist pydantic field-tree (§O.20).
```python
class TemplateObject:
    def render_input(self, meta_prompt: str, prompt: str, perceptions: list[ApparitionCandidate]) -> str
    def parse_output(self, raw: str) -> list[dict]               # pydantic output schema → actions
```
- **`render_input`** — `{var}`-template the meta_prompt→prompt flow, splicing perception names/summaries. **`parse_output`** — apply the pydantic output schema (compute.md `build_pydantic_model_from_schema`) over `raw`; emit a list of action dicts. Input templating + output parsing in **one** object (§O.21). Downstream consumers read the parsed output as a normal field-tree (provenance `AGENT_OUT`, perimeter-projected by layout.md).

---

## §5 — Dependencies / Excluded
**Calls:** ApparitionService (retrieval.md), `SLMClient`, `ActionResolver`→lifecycle.md, `template`→compute.md (`STRUCTURED`). **Called by:** api.md `POST /api/agent/{spawn,tick}`; cascade when a parameter card is live. **Excluded:** fluid-sim §12.8 (deferred, migration.md); the meta-cognition register/telos framing.
