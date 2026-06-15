# Feature: The Three Register Model (Mortegon)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §1.1 (Real / Imaginary / Symbolic and the shape of death), §1.5 (operational cross-reference), §6.6.1 (perimeter outputs), §6.6.2 (2D/3D separation), §7.7 (projective inverse), §12.2.1 (agent as integration scheme), §12.6.1 (agent/editor entanglement), §14 (REPL as Symbolic register).

**Status.** Realised (structural). All three registers exist and are wired: the **Real** = the 3D Projector (`chunk_projector.js` + the `cp/` Three.js suite, 6D-UMAP chunk manifold); the **Imaginary** = the 2D concept-graph Editor (`cp/concept_graph.js`, ray-constrained card layout, panels/halos/links); the **Symbolic** = the REPL (`scripts/sim_frontend.py`) whose `watch-activity` dashboard + 79-scenario `full-smoke` mirror every §10.5 UIState field. The 2D↔3D separation (§6.6.2, screen-pixel vs metric coords; coupling only via the membranes) and the perimeter outputs (§6.6.1, agent-output → outer envelope) are realised. This feature is the structural frame the rest of the catalogue composes through; each composing feature carries its own realised/greenfield status.

---

## §1 — What the user sees

The workspace presents three surfaces — a 3D Projector, a 2D Concept Editor, and a REPL — that are not three independent UIs but three *registers* of the same workspace in a continuous alchemical loop. The user scans a URL and watches chunks land in the projector with their UMAP-fitted colours and positions (the Real). The user hovers a chunk and the unified panel previews; the user clicks and a panel pins at the same screen rect carrying the chunk's content as editable print-rendered fields (the Imaginary). The user opens a REPL terminal and watches the same activity stream through the in-place activity viewer (the Symbolic), drives the GUI by typing REPL actions, and reads the result both in the GUI and in the viewer's row updates.

When the user composes a compute graph in the editor — wiring `WebBrowser.scan` to feed `Database.concept` to feed `Agent.prompt` — the cascade re-fires per signal-stream advance, the agent's terminal outputs land at the projector's perimeter (the Imaginary returns to the Real), and the entire flow remains legible in the REPL. The three surfaces are bidirectionally coupled at every step: a 3D node hovered becomes the same panel that sticks on click, a `{var}` typed in the 2D editor resolves to a 3D actor through the projector's chunks, and a REPL action mutates state that the GUI re-renders the same frame.

---

## §2 — Cross-objects

| Object | Role |
|---|---|
| [`LayoutService`](../object_model/LayoutService.md) | Real register — builds the projector geometry; 6D UMAP + perimeter rescaling |
| [`Projector`](../object_model/Projector.md) | Real register — frontend rendering of the manifold + HSV phase loop |
| [`ConceptNode`](../object_model/ConceptNode.md) | Imaginary register's atomic unit — every concept node is an image of a perception |
| [`KnowledgePanel`](../object_model/KnowledgePanel.md) | Imaginary register's primary widget — the unified panel anatomy |
| [`Halo`](../object_model/Halo.md) | Imaginary register's retrieval surface; couples to Real via ray-projection (§8.2.1.1) |
| [`Editor`](../object_model/Editor.md) | Imaginary register's mutation surface |
| [`Agent`](../object_model/Agent.md) | Imaginary register's reasoning + Real register's measurement projection (agent outputs at perimeter) |
| [`UIStateService`](../object_model/UIStateService.md) | Symbolic register's bridge — the backend mirror that the REPL reads |
| [`ConceptLifecycle`](../object_model/ConceptLifecycle.md) | Symbolic register's source of truth — every mutation produces telemetry the REPL reads back |

---

## §3 — Gestures

Each register has its own gesture vocabulary, but every gesture composes with the other two registers:

| Register | Primary gesture | What the other two registers see |
|---|---|---|
| Real | Scan (`WebBrowser.scan`) | Imaginary: chunks materialise as ConceptNodes; halo opens around any focal. Symbolic: `chunk_added` × N + `umap_canonical` + `pattern_map` materialises. |
| Real | Camera rotate | Imaginary: HSV phase rotates on visible chunks + halo phantoms in lockstep. Symbolic: (camera state not mirrored — purely visual). |
| Imaginary | Click halo phantom | Real: corresponding 3D chunk (if ray-projected) flies into view. Symbolic: `concept_edge_create` + `ui_halo_chain_push`. |
| Imaginary | Type into a field, Enter | Real: cascade re-fires; downstream agent outputs may re-project to perimeter. Symbolic: `concept_changed` + `evolution_diff`. |
| Imaginary | Double-left-click compile/collapse (right-click = rank-1 reveal, §7.3.4/§O.1) | Real: graph-emitted outputs project to manifold (collapse path). Symbolic: `concept_changed` × N children + `ui_state_changed` (compile_expansions). |
| Symbolic | Any REPL action | Real + Imaginary: state mutates as if the user had performed the equivalent GUI gesture. |
| Symbolic | `watch-activity` viewer open | Reads Real + Imaginary mirrors in fixed-structure terminal display. |

---

## §4 — State machine — the alchemical loop

```
[scan] (Real) ─────────────────────────────────────────────────────────┐
   │                                                                    │
   ▼                                                                    │
chunks materialise in projector (Real interior)                         │
   │                                                                    │
   ▼                                                                    │
ConceptNodes index in nomic + TF-IDF + multi-freq bands (Imaginary primitives) │
   │                                                                    │
   ▼                                                                    │
user hovers, panel previews; user clicks, panel pins (Imaginary surface)│
   │                                                                    │
   ▼                                                                    │
halo opens — concentric ring of soft links + ray-projected projector neighbours (Imaginary)
   │                                                                    │
   ▼                                                                    │
user clicks phantom → soft promotes to hard → autoregressive walk      │
   │                                                                    │
   ▼                                                                    │
user composes compute graph: Editor.create / Editor.link wirings (Imaginary structure)
   │                                                                    │
   ▼                                                                    │
Compile fires: ConceptComputeNode chain (Imaginary computation) ───────►│
   │                                                                    │
   ▼                                                                    │
Agent.output renders SLM completion; perimeter projection (Imaginary → Real)
   │                                                                    │
   ▼                                                                    │
new chunks land at projector perimeter (Real synthesis)                 │
   │                                                                    │
   ▼                                                                    │
next scan / next tick / next user gesture re-enters loop ──────────────┘

At every step:
  WS frame fires → REPL viewer rows update → Symbolic legibility preserved
```

The loop runs both ways: a REPL action can enter at any node (drive a scan, drive an editor mutation, drive a halo open, drive a rollout play); the GUI sees the result identically.

---

## §5 — WS frames + telemetry

| Frame | Register touched | Emitted by |
|---|---|---|
| `chunk_added` | Real | Scanner via Layout Service |
| `umap_canonical` | Real | Layout Service (incremental + scan-end) |
| `concept_changed` | Imaginary | Lifecycle dispatcher (every mutation) |
| `concept_index_update` | Imaginary | ConceptIndexService (settled state) |
| `agent_token` | Imaginary (streaming) | Agent transformer |
| `evolution_diff` | Symbolic (mirror) | EvolutionLog (every mutation) |
| `ui_state_changed` | Symbolic | UIStateService (every mirror update) |
| `purge_workspace` | All three | Purge handler |

---

## §6 — Acceptance bar

The three-register model is realised when:

- **§16.5 live-scan + DB-cleanup probe** passes — scans complete with workspace-WS dual-routing intact, `pattern_map` materialises live, perimeter placement applies to agent outputs, purge returns the workspace to the three-fixture baseline (§S).
- **§14.5 in-place activity viewer** renders all four mirror rows accurately during a live scan + halo open + agent tick sequence.
- The hover→click→halo→click→compile→perimeter loop runs end-to-end in the `live-rag` env-scenario.
- §6.6.1's perimeter placement is geometrically verified by inspecting the LayoutFrame after an agent emission.

---

## §7 — Anti-goals

| Anti-goal | DOMAIN_MODEL §18 |
|---|---|
| Agent outputs lost to manifold interior | §18.23 |
| 2D / 3D coordinate cross-coupling | §18.31 |
| Two-panel split (Imaginary register fragmenting into two surfaces) | §18.11 |
| Scan ↔ streaming severance (Symbolic register desync from Real) | §18.1 |

---

## §8 — Code constraints

- [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) — the one-dispatcher rule that makes the Symbolic register's telemetry complete.
- [`ws_frames.md`](../code_constraints/ws_frames.md) — frame schema + dual-routing.
- [`frontend_rendering.md`](../code_constraints/frontend_rendering.md) — the unified-panel one-template rule.
- [`backend_services.md`](../code_constraints/backend_services.md) — LayoutService 6D fit + perimeter rescale; ApparitionService ray-projection coupling.

---

## §9 — Cross-features

- [`compile_collapse_dialectic.md`](compile_collapse_dialectic.md) — the dialectical inversion of synthesis ↔ analysis within the Imaginary.
- [`hard_soft_links.md`](hard_soft_links.md) — the commitment fan + possibility ring distinction within the Imaginary.
- [`projective_inverse.md`](projective_inverse.md) — the closest-inverse as the Imaginary's purely projective property.
- [`agent_integration_scheme.md`](agent_integration_scheme.md) — the agent's recursion-over-iteration loop with world perceptions as initial conditions.
- [`perimeter_outputs.md`](perimeter_outputs.md) — the geometric realisation of the Imaginary → Real return.
- [`2d_3d_separation.md`](2d_3d_separation.md) — the canvas separation that makes the loop legible.
- [`repl_two_way_feedback.md`](repl_two_way_feedback.md) — the Symbolic register's operationalisation.
