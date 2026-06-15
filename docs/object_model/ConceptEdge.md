# Object: ConceptEdge

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §3.2 (the edge), §3.2.1 (hard vs soft links), §8.2 (halo as soft-link surface), §7.7 (closest-inverse over the bidirectional link), §1.5 (commitment fan / possibility ring spatial separation).

**Status.** Realised for hard links; soft links realised (core) — they live in the in-memory apparition cache as `ApparitionCandidate`s, which now carry the §2.2 SoftLink shape: `card_id`, `score`, `pagerank`, `tfidf_cos`, `nomic_cos`, `name`, `transport` (§O.18 cone-ray), and **`band_scores`** (the per-frequency-band scores when the service is in multi-frequency mode, §8.1.1 — wired this pass). Promotion to a hard link goes through `Editor.link` → `create_concept_edge` + `apply_edge_create_lifecycle` (realised this pass; §3.4). Open: the explicit `focal_id`/`opened_at` cache-eviction bookkeeping as named fields (currently the focal is the query arg + the cache is rebuilt per halo open).

---

## §1 — What it is

The edge between concept nodes, modelled in two modes that share a focal anchor but separate their spatial layouts. **Hard links** are committed `ConceptEdge` rows in Kuzu — survive reloads, participate in PageRank, drive the cascade (§7.4), draw as solid full-colour lines on the commitment fan between focal and target. **Soft links** are halo-suggested candidates surfaced by triple-product retrieval (§8.1 / §8.1.1) — live only in the in-memory apparition cache, vanish when the halo closes, draw as solid lighter-stroke lines on the concentric possibility ring around the focal at halo radius. A click on a soft link promotes it to a hard link through `Editor.link`, and the spatial promotion echoes the data promotion: the phantom fades from the ring while the new hard edge materialises on the fan.

The §1.5 framing places both kinds in the Imaginary register but distinguishes them by their *persistence* — hard links are the imaginary's *commitment* to structure; soft links are the imaginary's *possibility* before commitment. The autoregressive halo (§8.2.2) is the imaginary's mechanism for walking the possibility space without polluting the commitment table.

---

## §2 — Shape

### §2.1 Hard link (`ConceptEdge` row)

```python
@dataclass
class ConceptEdge:
    edge_id:      str         # opaque UUID
    source_id:    str         # ConceptNode.concept_id (source)
    target_id:    str         # ConceptNode.concept_id (target)
    edge_type:    str         # one of the typed-edge family enum
    source_port:  str         # function-node port binding (§8D.4.1); "" for default
    target_port:  str         # function-node port binding; "" for default
    weight:       float       # edge weight; PageRank uses this
    workspace_id: str
    created_at:   str
    metadata:     str         # JSON for edge-class-specific extras (commutation source, etc.)
```

### §2.2 Soft link (in-memory only)

```python
# Not a persisted record; lives inside ApparitionCandidate (apparition_service.py)
@dataclass
class SoftLink:
    focal_id:        str         # the halo's focal ConceptNode.concept_id
    candidate_id:    str         # the proposed target ConceptNode.concept_id
    score:           float       # aggregated multi-frequency rank (§8.1.1)
    pagerank:        float
    tfidf_cos:       float
    nomic_cos:       float
    band_scores:     dict[str, float]  # per-frequency-band scores when multi-freq active
    name:            str         # the candidate's name, for the halo phantom (§4.5 compact)
    opened_at:       float       # epoch; cache eviction key
```

### §2.3 Edge-type enum (the union of §3.2)

| Family | Members |
|---|---|
| User-ontology (§8A.2) | `IS_A`, `HAS_A`, `PART_OF`, `RELATES_TO`, `SIMILAR_TO`, `CLASSIFIES`, `DERIVED_FROM`, `INCLUDES`, `ANNOTATES` |
| Port-binding (§8D.4.1) | `SOURCE_PORT`, `TARGET_PORT` (via the `source_port`/`target_port` fields rather than as a discrete edge_type — port edges piggyback on a typed edge) |
| Web ontology (§8D.39) | `SearchableURL → DetectedAccessor`, `XPathPattern → DomSnapshot`, `PinnedComponent → DomSnapshot`, etc. |
| Python-native (§9.6) | `OBJECT_HAS_PROPERTY`, `OBJECT_HAS_FUNCTION`, `FUNCTION_INPUT_TYPE`, `FUNCTION_OUTPUT_TYPE` |
| Agent body (§12.1) | `PERCEPTION_OF`, `TRANSFORMER_OF`, `EMITTER_OF`, `PERCEIVES` |

**One edge table; never two.** Forward query applies the map; inverse query is closest-match by triple product (§8.1 / §8.1.1). The closest-inverse (§7.7) reads the same hard-link graph for forward execution and the soft-link space (the ranked apparition surface) for the inverse closest-match suggestion.

### §2.4 Spatial layout

| Mode | Visual treatment | Spatial region around focal |
|---|---|---|
| Hard | Solid undirected line; full brightness; ~2px stroke; **no arrowhead** (§O.16; `edge_type` shown by weight + brightness, not glyph) | **Commitment fan** — between focal and its committed targets at the angular position the typed-edge family canonicalises |
| Soft | Solid undirected line (no dashes — forbidden-concepts §5); ~40% brightness; ~1px stroke; **no arrowhead** (§O.16) | **Possibility ring** — concentric at the halo radius, angular by nomic-embedding direction, radial by triple-product score |

The two layouts never interfere: the fan reaches outward from the focal toward its hard targets; the ring sits concentric at a larger radius. A soft→hard promotion is therefore both a data promotion (Editor.link commits the row) and a spatial promotion (the phantom fades from the ring, the new edge materialises on the fan).

---

## §3 — Lifecycle

### §3.1 Hard-link create

`Editor.link(source_id, target_id, edge_type?, source_port?, target_port?) -> edge_id`:

1. Validate both `source_id` and `target_id` resolve to live ConceptNodes.
2. Determine `edge_type` (defaults to `RELATES_TO` if not specified).
3. Assign a fresh `edge_id`.
4. Enter the lifecycle dispatcher:
   - Kuzu `ConceptEdge` table insert.
   - `concept_changed` WS frame for both source and target (their `linked_nodes_json` cache is now stale; downstream renders update).
   - ConceptIndexService incremental PageRank update.
   - EvolutionLog appends an `EditDiff` with `action="link"`, `actor=user|agent:<id>|cascade|editor`.
   - Cascade scheduler nudges downstream cards if the new edge implies a `{var}` resolution previously unresolved.
5. Frontend renders the new edge on the commitment fan.

### §3.2 Hard-link delete

`Editor.unlink(edge_id)` (or `Editor.delete(node_id)` for cascade-removal):

1. Kuzu `ConceptEdge` table delete.
2. `concept_changed` for both source and target.
3. ConceptIndexService PageRank refit notification.
4. EvolutionLog appends `action="unlink"`.
5. Cascade scheduler re-fires affected downstream cards (the removed edge may have been carrying a `{var}` resolution).

### §3.3 Soft-link materialisation

Soft links are *not* mutated through the lifecycle — they live only in the in-memory apparition cache and have no persisted identity. They are materialised on `apparition_service.surface_for(focal_id, k)` and stay valid for the duration of the open halo. The cache evicts soft links when:

- The halo closes (explicit `ui_halo_clear` or implicit on focal panel close).
- The focal's `description` or `rendering` changes (the candidate set is recomputed).
- The workspace-wide multi-frequency aggregation refits (`concept_index_update` settles).

### §3.4 Soft-to-hard promotion (`autoregressive halo`)

Click on a halo phantom (§17.7, §8.2.2):

1. Read the soft link's `focal_id` and `candidate_id`.
2. Call `Editor.link(focal_id, candidate_id, edge_type="DERIVED_FROM")` — this enters the lifecycle per §3.1.
3. The frontend fades the phantom from the possibility ring while the new edge materialises on the commitment fan.
4. UIStateService.push_halo_chain records the autoregressive step.
5. A new halo opens around `candidate_id` automatically (the user is walking the retrieval space).

---

## §4 — Persistence

| Mode | Storage |
|---|---|
| Hard link | Kuzu `ConceptEdge` table; one row per edge; primary key `edge_id`; secondary indexes on `(source_id)`, `(target_id)`, `(edge_type)` |
| Soft link | In-memory apparition cache only (`apparition_service.py`); no persistence; rebuilt on halo open from indices |
| Halo chain | UIStateService.halo_chain — ordered list of focal_card_ids the user has walked; in-memory mirror; cleared on `ui_halo_chain_clear` or `purge_workspace` |
| EvolutionLog records of links | Kuzu `EditDiff` table; `target = edge:<edge_id>`; `action = "link" | "unlink"` |

Purge clears the `ConceptEdge` table for the workspace and resets the apparition cache; the rebuild on the next halo open is from-scratch and respects the new (empty) workspace state.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ConceptNode.md`](ConceptNode.md) | Hard links connect ConceptNode rows; the source/target ids index into the node table |
| [`ConceptLifecycle.md`](ConceptLifecycle.md) | Edge create/delete enters via the dispatcher |
| [`ConceptIndexService.md`](ConceptIndexService.md) | PageRank refit on every hard-link add/remove; soft-link surface fed by the index |
| [`ApparitionService.md`](ApparitionService.md) | Generates soft links via multi-frequency aggregation; ray-projection augments them with manifold-nearest projector chunks (§8.2.1.1) |
| [`Halo.md`](Halo.md) | Frontend renderer draws the concentric possibility ring; reads HSV state per phantom |
| [`Editor.md`](Editor.md) | Editor.link is the canonical hard-link create; called from GUI gestures and from the agent's emitter via ActionResolver |
| [`UIStateService.md`](UIStateService.md) | halo_focus / halo_chain mirror fields track which focal's soft links are currently visible |

---

## §6 — Cross-references

- Feature touchpoints — [`features/hard_soft_links.md`](../features/hard_soft_links.md), [`features/halo_retrieval.md`](../features/halo_retrieval.md), [`features/autoregressive_halo.md`](../features/autoregressive_halo.md), [`features/projective_inverse.md`](../features/projective_inverse.md).
- Code constraints — [`api_routes.md`](../code_constraints/api_routes.md) `/api/concept_edges` shape; [`lifecycle_invariants.md`](../code_constraints/lifecycle_invariants.md) link-create fan-out.
- Sequence reference — DOMAIN_MODEL §17.1.1 (Editor mutation), §17.7 (apparition resolve), §17.1.5 (halo ray-projection).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Persisting soft links to Kuzu | Pollutes the deterministic edge table; cascade would re-fire on speculative candidates | Soft links live exclusively in the apparition cache; persisting them is a design break |
| Drawing edges with dashed strokes or arrowheads | Forbidden-concepts §5 / §O.16; hard/soft distinction is via stroke brightness + weight (undirected lines), not dashes or arrowheads | Frontend SVG audit; `stroke-dasharray` and arrowhead markers are grep-rejected |
| Mixing hard and soft links spatially | The commitment fan and the possibility ring are separate regions (§3.2.1) | Halo renderer places soft links at halo radius; concept_graph renderer places hard links between focal and target |
| Branching cascade behaviour on `edge_type` value | Cascade reads `{var}` references in `data`/`description`, not the edge type; edge_type is for visual + semantic, not control flow | The cascade scheduler reads dependency from `{var}` references, not edges |
| Allowing duplicate hard links between the same `(source, target, edge_type, source_port, target_port)` | The five-tuple is the natural key; duplicates inflate PageRank and break the cascade | Editor.link checks for duplicates and short-circuits if the edge exists |
| Promoting a soft link without firing the lifecycle | The promotion IS a hard-link create; bypassing the dispatcher breaks WS broadcast + EvolutionLog | Soft-to-hard always calls Editor.link |
