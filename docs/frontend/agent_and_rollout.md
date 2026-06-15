# Agent & Rollout — Body Subgraph, Token Stream, Play/Pause Iteration

> **Status: realised (cp/*.js core).** The §7.5 **play/pause iterated rollout** is wired: `concept_graph.js::_attachPatternMapStepper`/`_attachUrlSetStepper` carry a ▶/⏸ toggle driving the per-interval advance cadence and firing `/api/rollout/{play,pause}` + `/api/ui/signal_advance` into the backend `RolloutCoordinator` ([`../object_model/RolloutCoordinator.md`](../object_model/RolloutCoordinator.md); `rollout-roundtrip` scenario; mirrored in the `watch-activity` `rollout` row). The **agent body subgraph (§12.1)** renders as four normal `concept_view` cards (parameter + perception + transformer + emitter, `agent-spawn`/`agent-three-primitives-chain`), and the **live token-stream** renders via `concept_graph.js::_appendAgentToken` / `_ensureAgentTokenPanel` / `_renderAgentTokenTabs` (per-pcid tabbed token buffer over the `agent_token` WS frames). Remaining refinement: the general play/pause control as a top-right editor affordance (M.11) over *any* iterable card (the per-panel stepper covers pattern_map + url_set today).

---

## §1 — Identity

The agent has **no separate frontend runtime** — it is a *visible recursive computation graph* in the same Editor the user composes in (§12). This surface renders: the four-card agent body subgraph (parameter / perception / transformer / emitter), the live `agent_token` stream into the transformer card's body, and the play/pause stepper that drives iterated rollout under the signal-stream constraint. The agent's emissions are *Editor calls* (§12.6.1) and render identically to the user's own edits — attribution is the `evolution_diff` actor, never a separate widget.

---

## §2 — Structure

**Agent body** — four `panel`-mode `ConceptView`s wired by edges (§12.1):
| Card | type_hint | Renders |
|---|---|---|
| Parameter | `agent_parameter` | `goal`, `step_index`, `zone_of_influence`, `cascade_enabled`, `paused` (editable field-tree) |
| Perception | `agent_perception` | composed payload from the apparition surface around the parameter focal |
| Transformer | `agent_transformer` | the SLM prompt template + the **live token stream** body |
| Emitter | `agent_emitter` | the structured action + applied-emission summary |

**Rollout** — a play/pause/step control bound to `ui.rollout_state` and the per-field `ui.signal_stream` (`field_tree.md` §7).

**Owns (transient):** the token ring-buffer cursor for the transformer body. **Reads:** `concepts` (the four cards), `edges` (the wiring), `tokens[agent_id]`, `ui.rollout_state`, `ui.signal_stream`, `cascade`.

---

## §3 — Behaviours

1. **Token stream is live (§12.1).** Each `agent_token` frame appends to `tokens[agent_id]` (a bounded ring buffer in the store); the transformer card's body renders the stream in real time, settling when the SLM finishes. No polling; pure frame-driven append (`liveness.md` §1).
2. **Emissions render as ordinary edits (§12.6.1).** The emitter's `Editor.create/link/overwrite/delete` actions flow through the lifecycle (§10.2) and arrive as `concept_changed` frames; the Editor renders the new cards/edges identically to user edits. Agent-output chunks land on the **projector perimeter** (`projector.md` §5, §6.6.1).
3. **Pause/resume via parameter-card edit (§12.4).** Editing the parameter card's `paused` field halts/resumes the scheduler; the frontend just edits a field (`field_tree.md`) — no special control needed, though the rollout control is a convenience binding to it.
4. **Signal-stream rollout (§7.5, §4.6.1).** Play iterates samples; the visible field shows one signal at a time; pause reveals edit affordances (plus-signs) on the paused node; an edit changes the next iteration's input; resume uses the edited content. The cascade re-fires per signal (§7.4).
5. **Termination via parameter-card delete (§12.4).** Deleting the parameter card dissolves the body subgraph; the evolution log records the lineage (§11.4).
6. **Actor-aware short-circuit is observable (§7.4).** The `cascade` slice shows per-actor fire counts + last-skip reasons; the agent's own emissions don't re-trigger its perception in the same tick.
7. **Pause freezes at the walk frontier (§O.10).** Because compile lazily reveals nodes as it walks (§O.9), Pause keeps the nodes revealed so far visible at rank-1, shows the current per-sample signal, and lets the user edit any revealed node; Resume continues the walk + iteration from there.
8. **Per-sample iteration uses one cycling readout node, not fan-out (§O.11).** A function iterating over `{chunk samples}` shows the current sample's output in a *single* readout node (signal-stream §4.6.1); per-sample outputs accumulate as the full distribution in 3D (§O.7); the 2D stays rank-1.
9. **The generative readout is a 2D rank-1 node + a 3D distribution (§O.12).** A type-stripped readout node holds the current output; per-sample / agent outputs land in 3D (agent outputs on the perimeter, §6.6.1); the 2D `{output}` is a reference into the 3D set. A **full rollout** settles to the **readout perimeter** (§7.8.2) and streams to the projector as **async per-node deltas** (§7.8.3, P.6/P.7); on the projector the collapsed graph appears as the **bisector node + UMAP-independent link network** (§6.6.4).
10. **Agent outputs are shaped downstream by pydantic templates in the minimalist text pattern (§O.20).** The *consuming* node's input panel carries a pydantic template authored as a field-tree (inferred names, `{var}` content, Tab/Shift-Enter handlers); `Agent.output(schema=…)` is validated/shaped by it, and structured chunk samples (§15.8) flow into the same templated fields (§7.2). The template engine is the Agent's **`template` functional-object** (§O.21), which templates the input prompts (`meta_prompt`/`prompt`) and parses the output simultaneously over the meta_prompt → prompt → output scheme.

---

## §4 — Composition

| Peer | Through |
|---|---|
| `ConceptView` / `FieldTree` | the four cards + token-stream body + editable parameters |
| `Editor` (`editor.md`) | lays out the wired subgraph; renders emissions |
| `Projector` (`projector.md`) | agent-output chunks at the perimeter |
| `Halo` (`halo.md`) | perception reads the apparition surface around the parameter focal |
| `pattern_map_and_url_set.md` | the rollout stepper advances pattern/URL signals too |
| `WorkspaceStore` | `tokens`, `ui.rollout_state`, `ui.signal_stream`, `cascade` |
| `GestureGateway` | `agent-spawn`, `agent-tick`, `rollout-play/-pause/-step`, `ui-signal-advance` |

---

## §5 — Activities

| Activity | Gesture | Effect |
|---|---|---|
| Spawn agent | `agent-spawn {goal, name?}` | four wired cards appear |
| Tick | `agent-tick {parameter_card_id}` | token stream + emissions render |
| Pause / Resume | `rollout-pause {node_id}` / `rollout-play` | halt/advance iteration; reveal/hide edit affordances |
| Step | `rollout-step {sample_idx}` | one iteration forward |
| Advance signal | `ui-signal-advance {card_id, field_path}` | swap visible signal in place |
| Pause-edit | `field-tree-*` / `concept-edit-*` | edit the paused node for the next iteration |
| Terminate | `editor-delete {parameter_card_id}` | dissolve the subgraph |

---

## §6 — Sequences

### §6.1 Agent tick (§17.5)
```
agent-tick {parameter_card_id}
   → MetaCognitionTick.run_async (backend §12.2)
      perceive: apparition_service.surface_for(parameter_card_id) (real nomic + PageRank)
      transform: real GPT4All → agent_token {agent_id, token, partial} streamed
      emit: ActionResolver → Editor.create/link/overwrite/delete → lifecycle (§10.2)
   → FrameBus: agent_token×M (into tokens ring) + concept_changed×emissions
   → transformer card body appends tokens live; Editor renders new cards/edges; perimeter chunks land
   → REPL viewer agent row: "agent:X perceive=N apparitions | tokens=M | emit: creates=3 links=2"
```
### §6.2 Play/pause rollout (§17.6)
```
rollout-play → coordinator iterates samples 1..N → rollout_resumed / rollout_progress
rollout-pause {node_id} → rollout_paused {sample_idx, current_node_id}
   → frontend reveals plus-signs / editable fields on the paused node
edit paused node (field-tree, does NOT advance) → rollout-play → next sample uses edited content
   → signal-stream swaps the visible signal; cascade re-fires (§7.4)
```

---

## §7 — Data

**Reads:** the four `concepts` cards + `edges`; `tokens[agent_id]`; `ui.rollout_state` (`{node_id, paused, sample_idx}`); `ui.signal_stream`; `cascade`. **Sends:** `agent-spawn`, `agent-tick`, `rollout-*`, `ui-signal-advance`, edit gestures. **Receives:** `concept_changed`×4 (spawn), `agent_token` stream, `concept_changed`×emissions, `rollout_paused`/`rollout_resumed`, `cascade_status`.

---

## §8 — Results

A live agent subgraph: tokens streaming into the transformer card, emissions appearing as new steel-framed cards/edges, agent outputs fanning onto the 3D perimeter, and a stepper that pauses mid-rollout for edits. Telemetry: `rollout_state`, `signal_stream`, `cascade` (§10.5); the agent row + perimeter via the projector.

---

## §9 — REPL Mirroring

`rollout_state` and `signal_stream` are §10.5 mirror fields; `cascade` feeds `GET /api/agent/cascade_status`. The viewer's optional `agent` row shows `perceive=N | tokens=M | emit: creates/links` and the `subsystems` row confirms real GPT4All (§13). REPL `agent-spawn`/`agent-tick`/`rollout-*` drive the same subgraph and stream; `probe_live_agent.py` (§16.3) asserts the token buffer holds real streamed tokens and emissions flow through the same lifecycle as user gestures (§12.6.1 entanglement).

---

## §10 — Theme

All four cards are steel-on-black `ConceptView` panels. The transformer's **token stream** renders in monospace `--text-primary` over `--bg-recess`, appending live — the only "motion" is text arriving (no colour pulse). Play/pause/step controls: `--steel-300` glyphs, `--steel-100` on active; the paused state brightens the paused card's border to `--steel-100` 2px to signal "editable now" (`theme.md` §4). Emitted cards appear with the standard steel frame; **agent-output chunks on the 3D perimeter carry HSV** (the exception zone, `projector.md`) so the user reads the perimeter as syntheses by colour-in-3D while the 2D agent chrome stays monochrome.

---

## §11 — References

- `DOMAIN_MODEL.md`: §12 (agent), §12.1 (body subgraph), §12.2/§12.2.1 (tick + integration scheme), §12.4 (pause/terminate), §12.6.1 (editor entanglement), §7.5 (play/pause), §4.6.1 (signal-stream), §6.6.1 (perimeter), §6.6.4 (bisector node + projector link network), §7.8.2/§7.8.3 (rollout to the readout perimeter + async delta-stream), §17.5/§17.6 (sequences).
- Object docs: [`../object_model/Agent.md`](../object_model/Agent.md), [`../object_model/AgentRuntime.md`](../object_model/AgentRuntime.md), [`../object_model/RolloutCoordinator.md`](../object_model/RolloutCoordinator.md).
- Peers: `concept_view.md`, `field_tree.md`, `editor.md`, `projector.md`, `pattern_map_and_url_set.md`.
