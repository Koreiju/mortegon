# Object: ConceptNode

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §3.1 (the schema), §3.3 (backing pointer), §4 (the unified panel anatomy), §10.2 (lifecycle dispatcher).

**Status.** Realised — the one `ConceptNode` record (§8D.44) is the production path for every card. The §1.2-update fields are realised too: the **four-fixture distinction** via `type_hint` (`fixture_database` / `fixture_web_browser` / `fixture_agent` / `fixture_editor`, all undeletable — `four-fixtures-present` / `fixtures-undeletable` scenarios) + the read-only python-native / `pattern_map` / `url_set` type tags; and the **signal-stream display contract** (a `meta.iterable` field renders one signal at a time via the `signal_stream` mirror + `RolloutCoordinator`, exercised by `pattern_map` / `url_set` panels + `rollout-roundtrip`).

---

## §1 — What it is

The universal record every workspace surface is an instance of. A scan-spawned chunk is a ConceptNode. A user-authored card is a ConceptNode. A materialised Python class / property / function is a ConceptNode. A halo phantom is a ConceptNode rendered in its compact form. A compiled-graph child is a ConceptNode rendered as single `name : value`. An agent's perception, transformer, emitter cards are ConceptNodes. There is one record table; differences between record kinds are encoded in `type_hint`, `backing_pointer`, `data`, and `provenance`.

The §1.5 framing places the ConceptNode squarely in the Imaginary register — the editor's images of perceptions. The Real register (the projector) renders chunks whose ConceptNode form holds their identity, position, and HSV state; the Symbolic register (the REPL) mirrors every ConceptNode mutation through `concept_changed` frames.

---

## §2 — Shape

```python
@dataclass
class ConceptNode:
    concept_id:        str       # opaque UUID
    name:              str       # slug source
    description:       str       # nomic-indexed (functional declaration)
    data:              str       # constructor template (JSON-serialised field-tree)
    rendering:         str       # tf-idf-indexed; compile output
    linked_nodes_json: str       # cached neighbour list
    backing_pointer:   str       # opaque registry handle
    pagerank:          float     # multi-frequency aggregation per §8.1.1
    provenance:        str       # user-authored | agent-authored | derived-from-chunk | committed-subgraph (the 4 canonical ConceptNode values; see §2.2)
    workspace_id:      str
    layout_xy:         str       # last-known editor position
    ui_state:          str       # collapsed/expanded/pinned/latched
    type_hint:         str       # naming convention; NOT a discriminator
    created_at:        str
    updated_at:        str
```

### §2.1 Field invariants

| Field | Invariant |
|---|---|
| `concept_id` | Permanent; assigned at creation; never mutated; never reused |
| `name` | Slug-derived; rename propagates `{old} → {new}` across descriptions and data of every other card in the workspace via the lifecycle's rename cascade |
| `description` | Nomic-indexed; resides on the nomic axis only; tube TF-IDF or quantised-transformer mixing is forbidden (DOMAIN_MODEL §8D.17.1) |
| `data` | Serialised field-tree (JSON in storage; the UI surface dissolves it into the recursive `name : value` tree of §4.6) |
| `rendering` | Read-only at the UI; produced by Compile (§7.1); TF-IDF-indexed for retrieval |
| `linked_nodes_json` | Cache only; the canonical neighbour list is `ConceptEdge`. Re-derivable on demand |
| `backing_pointer` | Opaque string; the runtime registry (§3.3) maps it to live Python; bumped versions invalidate compile-cache (§15.6) |
| `pagerank` | Multi-frequency aggregation (§8.1.1) when the workspace has accumulated K observed-utility events; single-frequency triple product otherwise (§8.1) |
| `provenance` | One of the four canonical values in §2.2; the projector's perimeter-vs-interior rendering depends on the projection-meta value derived from it (§6.6.1) |
| `workspace_id` | Scopes every operation; `""` resolves to `"_default"` |
| `layout_xy` | Persisted 2D editor position; restored on workspace re-open |
| `ui_state` | UI-mirror hint; not authoritative for live rendering (UIStateService is) |
| `type_hint` | Naming convention used by the materialiser and the panel renderer; NOT a discriminator — code must not branch on `type_hint` value |

### §2.2 Provenance enum

The **four canonical `ConceptNode.provenance` values** (as realized in `graph_editor.py` + `output_projection.py`):

| Value | Meaning | Projector placement |
|---|---|---|
| `user-authored` | Created via Editor.create from the GUI or REPL | Interior — joint UMAP fit |
| `agent-authored` | Created via Editor.create from the agent's emitter | Interior; projected as `agent-output` → **perimeter** (§6.6.1) |
| `derived-from-chunk` | Click-and-stick from a 3D chunk hover, scanner-derived nodes, compile var-auto-create from a chunk, **and python-API materialised nodes** | Interior — inherits chunk position |
| `committed-subgraph` | Agent subgraph-commit / pinned subgraph compiled-from-scans (§8D.39.4) | Interior |

> **Not ConceptNode field values:** `agent-output` and `graph-output` are **projection-meta** tags that `output_projection` *derives* (`agent-authored → agent-output`, everything else → `graph-output`) purely to drive the layout perimeter rescale — they are never written to `ConceptNode.provenance`. There is **no** `scanner-emitted` ConceptNode value: scanner chunks are not concept nodes (they project natively from the scanner pathway and, when promoted to nodes, carry `derived-from-chunk`). The apparition surface also tags in-memory candidates `ray-projected` (§8.2.1.1), which is likewise not a persisted ConceptNode value.

---

## §3 — Lifecycle

Every mutation of a ConceptNode goes through `apply_update_lifecycle` or `apply_delete_lifecycle` in [`ConceptLifecycle.md`](ConceptLifecycle.md). The dispatcher fans out to:

1. **Kuzu write** — the persistent storage update.
2. **WS broadcast** — `concept_changed` carrying the new state.
3. **ConceptIndex upsert** — nomic re-embedding (description) + TF-IDF refresh (rendering) + PageRank re-fit notification.
4. **Output-projection schedule** — if `provenance == agent-output`, schedule the perimeter-encompassing projection (§6.6.1).
5. **Evolution-log diff** — append an `EditDiff` record with actor, target, before, after.
6. **Cascade** — downstream cards referencing this node via `{var}` get a **synchronous**, cycle-safe BFS re-compile (visited-set + depth cap; the storm guard is the visited-set + the `conceptual_compute`/`cascade*` actor-exclusion, not a timer). Additionally, if this node is an agent body card, the **debounced** agent-tick `CascadeScheduler` is nudged (§7.4).

### §3.1 Create

`Editor.create(name, description?, data?) -> concept_id`:
- Assigns a fresh `concept_id`.
- Sets `provenance` per the actor:
  - User via GUI/REPL → `user-authored`.
  - Agent emitter → `agent-authored`.
  - Editor.create from a click-and-stick → `derived-from-chunk` with the chunk's id stored in the data block.
  - Materialiser → `committed-subgraph` for python_object/property/function nodes.
  - Scanner → `scanner-emitted`.
- Enters lifecycle dispatch.

### §3.2 Modify

`Editor.overwrite(node_id, name?, description?, data?) -> concept_id`:
- Field-merge: only the kwargs explicitly passed mutate; unset kwargs preserve prior value.
- If `description` mutates → ConceptIndex re-embed.
- If `data` mutates → cascade scheduler re-fires downstream cards.
- If `name` mutates → the rename cascade propagates `{old} → {new}` across every other card's description and data via a workspace-wide find-and-replace, recorded as a single multi-target `EditDiff`.

### §3.3 Delete

`Editor.delete(node_id) -> bool`:
- Foundation fixtures (§9.5) are rejected.
- Referencing `{var}` slugs in dependents mark broken via `reference_invalidated` event (§9.11); dependents do not auto-delete.
- Edges connected to the node are removed atomically with the node.
- Layout position freed; no perimeter rescale required (no further projections).

### §3.4 The four fixtures' special-case

The four foundational fixtures (Agent, WebBrowser, Database, Editor — §9.5) are ConceptNodes with `backing_pointer = fixture::<kind>::<workspace_id>` and `provenance = committed-subgraph`. Their python_function / python_property children carry `data` blocks with `read_only: true` and (for non-class nodes) `no_datablock: true`. The lifecycle dispatcher rejects deletion attempts via the `fixture_delete_guard` env-scenario.

---

## §4 — Persistence

| Field | Storage |
|---|---|
| `concept_id`, `name`, `description`, `data`, `rendering`, `linked_nodes_json`, `backing_pointer`, `pagerank`, `provenance`, `workspace_id`, `layout_xy`, `ui_state`, `type_hint`, `created_at`, `updated_at` | Kuzu `ConceptNode` table; one row per node |
| `concept_id` index | Primary key; integer-id alias in `_chunk_ids` for fast lookup |
| `description` embeddings | ConceptIndexService in-memory + persisted per-workspace file |
| `rendering` TF-IDF vectors | GlobalTfidfStore (per-band; §8.1.1) |
| Edges | Separate `ConceptEdge` table; see [`ConceptEdge.md`](ConceptEdge.md) |

Purge (`POST /api/purge_workspace`) walks every ConceptNode through `apply_delete_lifecycle` per [`ConceptLifecycle.md`](ConceptLifecycle.md), drops the persisted LayoutFrame, resets `frame_seq`, and emits a single consolidated `purge_workspace` WS frame.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ConceptEdge.md`](ConceptEdge.md) | A ConceptNode is the source/target of hard `ConceptEdge` rows; soft links are not persisted, live only in the apparition cache |
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | Every mutation enters this dispatcher |
| [`ConceptIndexService.md`](ConceptIndexService.md) | Nomic + TF-IDF + multi-frequency band indices per node |
| [`LayoutService.md`](LayoutService.md) | Layout coords (6-vector) for `provenance == scanner-emitted` or `agent-output` |
| [`ApparitionService.md`](ApparitionService.md) | Reads node's indices to surface halo candidates |
| [`EvolutionLog.md`](EvolutionLog.md) | Every mutation appends an EditDiff record |
| [`UIStateService.md`](UIStateService.md) | Pinned-panel state, halo focus, edit-field-open state all key by `concept_id` |
| [`KnowledgePanel.md`](KnowledgePanel.md) | The frontend renders one ConceptNode per panel using the single `_buildPanelDom` template |
| [`AgentRuntime.md`](AgentRuntime.md) | Agent body cards are ConceptNodes; emitter creates new ConceptNodes via Editor.create |

---

## §6 — Cross-references

- Feature touchpoints — virtually every feature in [`features/`](../features/) operates on ConceptNodes.
- Code constraints — [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) carries the one-dispatcher rule; [`persistence.md`](../code_constraints/persistence.md) carries the Kuzu storage rules.
- Sequence reference — DOMAIN_MODEL §17.1.1 Editor Mutation Sequence carries the create / link / overwrite / delete state machine.

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Branching on `type_hint` to gate behaviour | `type_hint` is a naming convention, not a discriminator (§3.1 invariant) | Code review; `type_hint` reads are confined to renderers |
| Creating a second ConceptNode table or denormalising scan-spawned nodes into a separate type | One record, one path (§3 invariant) | Foundation fixtures + scanner emit through the same `Editor.create` lifecycle |
| Mutating fields without going through `apply_update_lifecycle` | Breaks the WS broadcast and the evolution-log invariants | All mutations route through the dispatcher; direct Kuzu writes are forbidden |
| Letting two writes race without conflict resolution | Last-write-wins is the policy (§2.7); the cascade scheduler's actor-aware short-circuit prevents agent self-loops but is not a lock | Conflict resolution is rollback (§2.6); user/agent compose; the actor field in `EditDiff` disambiguates |
| Storing `data` as anything other than the serialised field-tree | The UI surface dissolves it into rows; non-tree shapes break the §4.6 progressive build | The compile pipeline rejects malformed data on first read |
| Hardcoding fixture `concept_id`s elsewhere in the code | `concept_id` is opaque; only `backing_pointer` is the stable identifier for foundation fixtures | Use `BackingRegistry.resolve(backing_pointer)`; never write the UUID literal |
