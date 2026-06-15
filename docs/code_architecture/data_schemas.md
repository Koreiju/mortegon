# Code Architecture — Data Schemas

> **Status: planned.** The record shapes the workspace stores and moves. Distilled from `DOMAIN_MODEL.md` §3 / §11 / §6.1 / §15.8 / §10.5. Realises `code_constraints/persistence.md`.

---

## §1 — The One Record: `ConceptNode` (§3.1)

Everything the workspace manipulates — panel, halo phantom, compiled child, agent body card, materialised `python_object`, scan chunk-derived node, URL-set panel, `pattern_map` — is one of these. **One table, one edge table.**

```python
@dataclass
class ConceptNode:
    concept_id:        str    # opaque UUID
    name:              str    # slug source; renames propagate {old}→{new} across all cards
    description:       str    # nomic-indexed (functional declaration, §8D.40)
    data:              str    # constructor template (§8D.30); JSON-serialised field-tree (the user never sees JSON)
    rendering:         str    # tf-idf-indexed; compile output (§8D.20)
    linked_nodes_json: str    # cached neighbour list
    backing_pointer:   str    # opaque handle; resolved by BackingRegistry (§3 below)
    pagerank:          float
    provenance:        str    # user-authored | agent-authored | derived-from-chunk | committed-subgraph (4 canonical; the projector chunk flags scanner-emitted/graph-output/agent-output are a SEPARATE ws_frames.Provenance, never written to this field)
    workspace_id:      str
    layout_xy:         str    # last-known 2D editor position (screen-pixel; §6.6.2)
    ui_state:          str    # collapsed | expanded | pinned | latched
    type_hint:         str    # naming convention, NOT a discriminator
    created_at:        str
    updated_at:        str
```

**Invariants** (realise `code_constraints/lifecycle_invariants.md`):
- `type_hint` is a **naming convention**, never a runtime discriminator — no `if type_hint == ...` branching in the dispatcher.
- `data` persists as JSON; the editor renders it as a pure-print field-tree (`frontend/field_tree.md`); JSON syntax never surfaces to the user.
- The two embedding axes: `description` → nomic, `rendering` → TF-IDF — **separated for scan chunks** (§8D.17.1); **knowledge panels deviate** — both models over the same rendered panel chunk, scored `pagerank · max(minmax(nomic_cos), minmax(tfidf_cos))` (§O.22).

---

## §2 — `ConceptEdge` (§3.2 / §3.2.1)

One edge dataclass; `edge_type` is the union enum. **One edge table; never two.**

```python
@dataclass
class ConceptEdge:
    edge_id:      str
    source_id:    str
    target_id:    str
    edge_type:    str    # IS_A|HAS_A|PART_OF|RELATES_TO|SIMILAR_TO|CLASSIFIES|DERIVED_FROM|INCLUDES|ANNOTATES
                         #  | OBJECT_HAS_PROPERTY|OBJECT_HAS_FUNCTION|FUNCTION_INPUT_TYPE|FUNCTION_OUTPUT_TYPE
                         #  | SearchableURL→DetectedAccessor etc. (§8D.39) | PERCEPTION_OF|TRANSFORMER_OF|EMITTER_OF|PERCEIVES
    source_port:  str    # port name on source function node (§9.8); "" = default
    target_port:  str
    workspace_id: str
    created_at:   str
```

- **Hard links** are committed `ConceptEdge` rows in Kuzu (persistent, drive PageRank + cascade). **Soft links** are *not* persisted — they live only in the apparition cache (§3.2.1); promoting a soft→hard writes a row through the lifecycle.
- Rendering is **undirected lines, no arrowheads** (§O.16); hard/soft by stroke brightness + weight only. `source_port`/`target_port` carry directionality semantically, not visually.

---

## §3 — Backing Pointer Registry (§3.3)

`backing_pointer` is opaque to the editor; `BackingRegistry` maps it to live Python.

| Prefix | Resolves to |
|---|---|
| `python_object::<qual>` / `python_property::<qual>` / `python_function::<qual>` | imported class / descriptor / bound callable (§9.6) |
| `fixture::{agent,web_browser,database,editor}::<wsid>` | the four foundation-fixture handles (§9.5) |
| `agent::{perception,transformer,emitter}::<pcid>` | the agent body card backings (§12.1) |
| `agent::template::<wsid>` | the Agent's `template` functional-object (§O.21) |
| `xpath_pattern::<hash>` / `searchable_url::<hash>` / `detected_accessor::<hash>` | compiled-from-scans accessors (§8D.39) |
| `chunk::<id>` | the canonical unit chunk (§15.5) |

A **version-bumped pointer** (§15.6) invalidates the compile-cache of every node referencing it.

---

## §4 — Supporting Records

### §4.1 `EditDiff` — the evolution log (§11.4)

```python
@dataclass
class EditDiff:
    edit_id:     str    # UUID, monotone-orderable by created_at
    workspace_id:str
    actor:       str    # user | agent:<id> | cascade | scanner | editor | materialiser | rollback
    target:      str    # concept_id | edge_id | "workspace"
    action:      str    # create | modify | delete | link | unlink | rollback | rejected
    before:      str    # JSON snapshot
    after:       str
    idempotency_key: str | None
    created_at:  str
```
Append-only. Rollback applies the inverse **and records the rollback itself as a new diff** (§2.6). Three scopes: single edit / edit range / actor scope. RolloutCoordinator records **sample boundaries** here for diff-consistent rollback (§7.6 / `object_model/RolloutCoordinator.md`).

### §4.2 `LayoutFrame` — canonical 3D coords (§6.1 / §11.1)

```python
@dataclass
class LayoutFrame:
    workspace_id: str
    per_chunk:    dict[int, tuple[float,float,float,float,float,float]]  # chunk_id → 6-vector (x,y,z,h,s,v)
    per_url:      dict[str, UrlRoot]    # url → {root_position, bounding_radius, umap_locked:set[int], hidden:bool, accessor_dict}
    updated_at:   str
```
The **6-vector** (3 position + 3 HSV) is the single UMAP fit (§8.2.1.2). Legacy 3-vector frames are migrated on first load by re-fitting HSV from TF-IDF. Persisted per-workspace (file) + in-memory frontend cache. **The only authority for 3D placement** (no Fibonacci/hash as final, §18.2).

### §4.3 `ChunkPatternSchema` — `pattern_map` entry (§15.8)

```python
@dataclass
class ChunkPatternSchema:
    pattern_hash:      str
    url_root:          str               # first URL the pattern was seen at (schema root)
    generalized_xpath: str
    accessor_map:      dict[str, str]     # field slug → relative xpath (§8.7)
    golden_trio:       tuple[str,str,str] # (title, link, content) accessor names (§15.8.1)
    sampled_chunks:    list[int]          # chunk_ids; the iterable (3D-resident, §O.14)
    pagerank:          float
    sub_patterns:      dict[str, "ChunkPatternSchema"]
```
Lives in the `pattern_map` ConceptNode's `data` (a recursive tree). Updates **live during scan** (§18.29). Under the signal-stream constraint the panel shows one `pattern_hash` at a time (§4.6.1).

### §4.4 `UIState` — the frontend mirror (§10.5)

The backend's authoritative copy of frontend UI state; the source for the REPL viewer and peer-tab sync. Fields (the §10.5.1 roster + §O additions):

```python
@dataclass
class UIState:
    workspace_id:          str
    selected_id:           str | None
    hovered_id:            str | None
    pinned_billboards:     list[str]                 # ordered
    pinned_collapsed:      dict[str, bool]
    last_hover_rect:       Rect | None               # {top,left,w,h} viewport px
    last_stick_rect:       Rect | None               # freeze-at-rect parity (§18.8)
    pin_chrome:            dict[str, PinChrome]       # {top,left,width,height,minimised}; field-merge (§17.12)
    latch_state:           dict[str, str]            # "latched" | "unlatched"
    url_collapsed:         dict[str, bool]
    hidden_urls:           set[str]                   # visibility flag (§6.3)
    compile_expansions:    dict[str, ExpansionState]  # central_id → {children, expanded_at}
    node_fold_state:       dict[str, FoldState]       # card_id → {expanded_paths} (§7.3.4 inline fold)
    halo_focus:            HaloFocus | None           # {focal_card_id, candidates, opened_at}
    viewport_visible_rows: VisibleRows                # {ordered:[chunk_id], total}
    autocomplete_state:    Autocomplete | None
    signal_stream:         dict[str, SignalSlot]      # "card_id::field_path" → {signal_index, total}
    rollout_state:         RolloutMirror | None       # {node_id, paused, sample_idx}
    last_changed_at:       str
    last_change_kind:      str
```
Every field has **exactly one setter**; setters are idempotent and **broadcast on every call** (`ui_state_changed`, full snapshot) so peer surfaces re-sync (§10.5).

### §4.5 `ProjectorLink` + `ComputeGraphPlacement` — the compute-graph projector overlay (§6.6.4)

```python
@dataclass(frozen=True)
class ProjectorLink:                       # UMAP-INDEPENDENT — carries NO coordinates (§18.34)
    src_id:   str                          # root_url | input root | click-sticked node | readout chunk
    dst_id:   str                          # the chunk_sample node, or the compute-graph node
    kind:     str                          # "url_to_sample" | "input_to_graph" | "readout_to_graph"
    graph_id: str

@dataclass(frozen=True)
class ComputeGraphPlacement:               # the single collapsed compute-graph node (§6.6.4, P.10)
    graph_id:   str
    pos:        tuple[float, float, float] # midpoint of bisector(input-centroid xyz, output-centroid xyz)
    hsv:        tuple[float, float, float] # carried from the input centroid (passive rotation §7.8.3)
    settle_seq: int                        # monotone per graph; lets out-of-order readout deltas re-order
```

Both are **transient / projector-overlay**, **not** Kuzu-persisted: they are derived each rollout from the live edge set + the readout-perimeter coords (`layout.md` §3.1) and ride the `compute_graph_layout` WS frame (`contracts.md` §3). The two **hidden centroids** are never emitted — only `ComputeGraphPlacement.pos` (§18.34). `ProjectorLink` deliberately holds **no coordinates**, so the link network can never couple to the UMAP fit.

---

## §5 — Persistence Map (§11.1)

| Artefact | Store |
|---|---|
| ConceptNode + ConceptEdge + EditDiff + chunk content + accessor table | **KuzuDB** (`WFH_DB_PATH`) |
| LayoutFrame (canonical 6-vectors) | per-workspace file + in-memory frontend cache |
| ConceptIndex (per-card nomic + PageRank + similar_to) | per-workspace file + in-memory cache |
| Image textures | in-memory `Map<url,Texture>` + IndexedDB `wfh_texture_cache.textures` (§11.2) |
| Full DOM HTML snapshots | disk (`snapshots/`), referenced from `DomSnapshot` records (dedup by SHA256) |
| Media assets | disk (`media/<domain>/<hash>.<ext>`) + `MediaAsset` records |
| `signal_stream` / `node_fold_state` / pin chrome (UIState) | per-workspace mirror snapshot (for `?resume`) |

**Purge** (§6.5) clears every store + resets `frame_seq` in one transaction; the frontend store resets in one paint (§18.4).

---

## §6 — Excluded (per README §0)

- The *meaning* of provenance bands (Real/Imaginary register framing) — only the enum values are encoded.
- The philosophical rationale for the field-tree dissolution — only the `data:str`-as-JSON shape is encoded.
- Theme tokens / rendering of any field — see `frontend/theme.md`.
