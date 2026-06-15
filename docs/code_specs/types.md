# Code Specs — Types

> **Status: planned.** The single source for every type. Per-area specs reference these by name and never re-declare them. Python `@dataclass` / `Enum` / `NewType`; the frontend mirrors the same field names (TS interfaces). Deepens [`code_architecture/data_schemas.md`](../code_architecture/data_schemas.md).

---

## §1 — Id Aliases & Scalars

```python
ConceptId   = NewType("ConceptId", str)      # opaque uuid
EdgeId      = NewType("EdgeId", str)
EditId      = NewType("EditId", str)          # monotone-orderable by created_at
WorkspaceId = NewType("WorkspaceId", str)
ChunkId     = NewType("ChunkId", int)         # the ONE integer id (stable instance key)
IdemKey     = NewType("IdemKey", str)
Backing     = NewType("Backing", str)         # opaque pointer; see §3 prefixes
Slug        = NewType("Slug", str)            # from name; rename propagates {old}→{new}
Ts          = NewType("Ts", str)              # ISO-8601 UTC
Vec768      = list[float]                      # len == NOMIC_DIM
Vec6        = tuple[float,float,float,float,float,float]   # (x,y,z,h,s,v)
XY          = tuple[float,float]               # screen px (editor) — NEVER world coords
Rect        = TypedDict("Rect", {"top": float, "left": float, "w": float, "h": float})  # viewport px
```

---

## §2 — Enums

```python
# ConceptNode.provenance — the concept-graph NODE's origin. In the realized
# code (graph_editor.py) this is a plain `str` field; these are its 4 canonical
# values. DISJOINT from the projector chunk flags below.
class Provenance(str, Enum):
    USER="user-authored"; AGENT="agent-authored"; CHUNK="derived-from-chunk"
    SUBGRAPH="committed-subgraph"

# Projector chunk provenance — a SEPARATE concept (backend/api/ws_frames.py
# `Provenance`): the 3D-CHUNK origin flag that drives the §9.12 perimeter
# rescale. Default is scanner-emitted; output_projection maps agent-authored
# nodes → agent-output and other peripherals → graph-output. NEVER written to
# ConceptNode.provenance (the two value sets do not overlap).
class ChunkProvenance(str, Enum):
    SCANNER="scanner-emitted"; GRAPH_OUTPUT="graph-output"; AGENT_OUT="agent-output"

class ChangeKind(str, Enum):
    CREATE="create"; MODIFY="modify"; DELETE="delete"; LINK="link"; UNLINK="unlink"
    COMPILE="compile"; RENAME="rename"; PIN="pin"; FOLD="fold"

class Actor(str, Enum):                         # EditDiff.actor (agent uses "agent:<id>")
    USER="user"; CASCADE="cascade"; SCANNER="scanner"; EDITOR="editor"
    MATERIALISER="materialiser"; ROLLBACK="rollback"   # AGENT is dynamic: f"agent:{id}"

class EdgeType(str, Enum):
    IS_A="IS_A"; HAS_A="HAS_A"; PART_OF="PART_OF"; RELATES_TO="RELATES_TO"; SIMILAR_TO="SIMILAR_TO"
    CLASSIFIES="CLASSIFIES"; DERIVED_FROM="DERIVED_FROM"; INCLUDES="INCLUDES"; ANNOTATES="ANNOTATES"
    OBJECT_HAS_PROPERTY="OBJECT_HAS_PROPERTY"; OBJECT_HAS_FUNCTION="OBJECT_HAS_FUNCTION"
    FUNCTION_INPUT_TYPE="FUNCTION_INPUT_TYPE"; FUNCTION_OUTPUT_TYPE="FUNCTION_OUTPUT_TYPE"
    PERCEPTION_OF="PERCEPTION_OF"; TRANSFORMER_OF="TRANSFORMER_OF"; EMITTER_OF="EMITTER_OF"; PERCEIVES="PERCEIVES"
    URL_HAS_ACCESSOR="URL_HAS_ACCESSOR"; ACCESSOR_OF_PATTERN="ACCESSOR_OF_PATTERN"   # §8D.39

class DispatchKind(str, Enum):  PLAIN="plain"; PROMPT="prompt"; STRUCTURED="structured"; PYTHON="python"
class SampleSource(str, Enum):  CHUNK_3D="chunk_3d"; HALO="halo"; SCALAR="scalar"; CONCEPT_IDS="concept_ids"
class ApparitionMode(str, Enum): SINGLE="single-frequency"; MULTI="multi-frequency"
class UiMode(str, Enum):        PANEL="panel"; COLLAPSED="collapsed"; PHANTOM="phantom"; CHILD="child"
class BraceState(str, Enum):    HIDDEN="braced-hidden"; INTERNAL="revealed-internal"; EXTERNAL="resolved-external"  # §O.1a
```

---

## §3 — Core Records (Kuzu-persisted)

```python
@dataclass
class ConceptNode:
    concept_id: ConceptId; name: str; description: str; data: str          # data = JSON field-tree (user never sees JSON)
    rendering: str; linked_nodes_json: str; backing_pointer: Backing
    pagerank: float; provenance: Provenance; workspace_id: WorkspaceId
    layout_xy: str                 # JSON XY (editor px) | ""
    ui_state: str                  # "collapsed"|"expanded"|"pinned"|"latched"
    type_hint: str                 # naming convention ONLY — never a runtime discriminator
    created_at: Ts; updated_at: Ts
    # flags carried in ui_state/type_hint convention: read_only, no_datablock (python-native, §8D.4.2)

@dataclass
class ConceptEdge:
    edge_id: EdgeId; source_id: ConceptId; target_id: ConceptId; edge_type: EdgeType
    source_port: str; target_port: str            # "" = default port
    workspace_id: WorkspaceId; created_at: Ts
    # hard = persisted row; soft = apparition-cache only (NOT a row); promote writes a row

@dataclass
class EditDiff:
    edit_id: EditId; workspace_id: WorkspaceId; actor: str                  # Actor | f"agent:{id}"
    target: str                    # ConceptId | EdgeId | "workspace"
    action: str                    # ChangeKind | "rollback" | "rejected"
    before: str; after: str        # JSON snapshots
    idempotency_key: IdemKey | None; created_at: Ts
```

`Backing` prefixes (resolved by `BackingRegistry`, `backend/persistence.md`):
`python_object::<q>` · `python_property::<q>` · `python_function::<q>` · `fixture::{agent,web_browser,database,editor}::<wsid>` · `agent::{perception,transformer,emitter,template}::<id>` · `xpath_pattern::<h>` · `searchable_url::<h>` · `detected_accessor::<h>` · `chunk::<id>`.

---

## §4 — Layout / Chunk / Pattern

```python
@dataclass
class UrlRoot:
    url: str; root_position: tuple[float,float,float]; bounding_radius: float
    umap_locked: set[ChunkId]; hidden: bool; accessor_dict: dict[str,str]

@dataclass
class LayoutFrame:
    workspace_id: WorkspaceId; per_chunk: dict[ChunkId, Vec6]; per_url: dict[str, UrlRoot]; updated_at: Ts

@dataclass
class Chunk:
    chunk_id: ChunkId; url: str; image_url: str | None; summary: str
    rendering: str; provenance: Provenance; pattern_hash: str | None

@dataclass
class ChunkPatternSchema:
    pattern_hash: str; url_root: str; generalized_xpath: str
    accessor_map: dict[Slug,str]; golden_trio: tuple[str,str,str]
    sampled_chunks: list[ChunkId]; pagerank: float
    sub_patterns: dict[str,"ChunkPatternSchema"]
```

---

## §5 — Retrieval / Compute DTOs

```python
@dataclass
class IndexSlot:
    concept_id: ConceptId; nomic: Vec768; tfidf: "SparseVec"; pagerank: float
    similar_to: list[tuple[ConceptId,float]]; band_scores: dict[int,float] | None   # multi-frequency

@dataclass
class ApparitionCandidate:
    concept_id: ConceptId; name: str; score: float
    nomic_cos: float; tfidf_cos: float                  # raw, pre-blend (for tooltips)
    transport: "RayTransport | None"                    # set by surface_for_projector (§O.18)

@dataclass
class RayTransport:                                     # halo cone coords (frontend renders)
    radial: float; along_ray: float; angular: float; hsv: tuple[float,float,float]

@dataclass
class Rendering: text: str; dispatch: DispatchKind; children: list[ConceptId]; cached: bool

@dataclass
class SampleResult: sample_idx: int; content: str; source: SampleSource; concept_id: ConceptId | None

@dataclass
class TickResult: agent_id: ConceptId; tokens: int; actions_applied: int; rationale: str
```

---

## §6 — UIState (the mirror; `backend/persistence.md` owns; one setter per field)

```python
PinChrome      = TypedDict("PinChrome", {"top":float,"left":float,"width":float,"height":float,"minimised":bool})
ExpansionState = TypedDict("ExpansionState", {"children":list[ConceptId],"expanded_at":Ts})
FoldState      = TypedDict("FoldState", {"expanded_paths":list[str]})
HaloFocus      = TypedDict("HaloFocus", {"focal_card_id":ConceptId,"candidates":list[ConceptId],"opened_at":Ts})
VisibleRows    = TypedDict("VisibleRows", {"ordered":list[ChunkId],"total":int})
Autocomplete   = TypedDict("Autocomplete", {"row_id":str,"query":str,"candidates":list[ConceptId]})
SignalSlot     = TypedDict("SignalSlot", {"signal_index":int,"total":int})
RolloutMirror  = TypedDict("RolloutMirror", {"node_id":ConceptId,"paused":bool,"sample_idx":int})
DominanceCollapse = TypedDict("DominanceCollapse", {"collapsed":bool,"hidden_set":list[ConceptId],"folded_set":list[ConceptId],"expanded_at":Ts})  # §6.6.5/§7.3.5 rank-dominance collapse (Q.3–Q.5); membership = dominator's dominated-set over the ConceptEdge graph (§8.1.2)

@dataclass
class UIState:
    workspace_id: WorkspaceId
    selected_id: ConceptId | None; hovered_id: ConceptId | None
    pinned_billboards: list[ConceptId]; pinned_collapsed: dict[ConceptId,bool]
    last_hover_rect: Rect | None; last_stick_rect: Rect | None
    pin_chrome: dict[ConceptId,PinChrome]; latch_state: dict[ConceptId,str]
    url_collapsed: dict[str,bool]; hidden_urls: set[str]
    compile_expansions: dict[ConceptId,ExpansionState]
    node_fold_state: dict[ConceptId,FoldState]
    dominance_collapse: dict[ConceptId,DominanceCollapse]    # §6.6.5/§7.3.5 — keyed by dominator node id (root-URL hub or bisector compute node)
    halo_focus: HaloFocus | None
    viewport_visible_rows: VisibleRows
    autocomplete_state: Autocomplete | None
    signal_stream: dict[str,SignalSlot]        # key = f"{card_id}::{field_path}"
    rollout_state: RolloutMirror | None
    last_changed_at: Ts; last_change_kind: str
```

---

## §7 — Wire DTOs (deepen `code_architecture/contracts.md`)

### WS frame union (every frame: `{frame_seq:int, type:str, workspace_id:WorkspaceId, ...}`)
```python
ChunkAddedFrame      = {..., "type":"chunk_added", "chunk": Chunk}
UmapCanonicalFrame   = {..., "type":"umap_canonical", "per_chunk": dict[ChunkId,Vec6], "per_url": dict[str,UrlRoot]}
ConceptChangedFrame  = {..., "type":"concept_changed", "concept_id": ConceptId, "change_kind": ChangeKind, "node": ConceptNode|None}
ConceptIndexUpdate   = {..., "type":"concept_index_update", "updated": list[{"id":ConceptId,"pagerank":float,"similar_to":list}]}
AgentTokenFrame      = {..., "type":"agent_token", "agent_id": ConceptId, "token": str, "partial": bool}
EvolutionDiffFrame   = {..., "type":"evolution_diff", "diff": EditDiff}
UiStateChangedFrame  = {..., "type":"ui_state_changed", "ui": UIState, "last_change_kind": str}
RolloutFrame         = {..., "type":"rollout_paused"|"rollout_resumed", "rollout_id":str, "sample_idx":int, "current_node_id":ConceptId}
PurgeFrame           = {..., "type":"purge_workspace"}
DoneFrame / ErrorFrame = {..., "type":"done"|"error", "ref": str|None, "message": str|None}   # error → --accent-error envelope
```

### REST bodies (representative; full route table in `backend/api.md`)
```python
PinReq        = {"chunk_id": ChunkId, "rect": Rect}
PatchReq      = {"name?": str, "description?": str, "data?": str}                 # field-merge
EdgeReq       = {"source_id": ConceptId, "target_id": ConceptId, "edge_type?": EdgeType, "source_port?": str, "target_port?": str}
CompileReq    = {"concept_id": ConceptId, "use_slm": bool, "persist_rendering": bool}
ScanReq       = {"url": str, "query?": str, "samples?": int, "duration_s?": int}   # duration_s = time-box (§15.10, Q.2); 0 ⇒ sample-bounded
DominanceCollapseReq = {"node_id": ConceptId, "collapsed": bool}                   # §6.6.5/§7.3.5 rank-dominance collapse (Q.3–Q.5)
AgentTickReq  = {"parameter_card_id": ConceptId}
RolloutReq    = {"node_id": ConceptId}
PurgeReq      = {"workspace_id": WorkspaceId, "confirm": "erase"}                  # or url-scoped
SubsystemStatus = {"ok":bool,"all_real":bool,"slm":{...},"embedder":{...},"selenium":{...},"langgraph":{...},"apparition_mode":ApparitionMode}
```

---

## §8 — Excluded

The register meaning of fields; the JSON-DDL of the Kuzu tables (below the spec line). Frontend TS mirrors these names 1:1 — only divergences are noted in `frontend/*`.
