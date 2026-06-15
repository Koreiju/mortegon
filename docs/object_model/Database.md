# Object: Database (Foundational Fixture)

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §1.2 (verbatim — *"Database: for retrieval that takes a natural language or cypher query as input and gives an unstructured chunk result output; also has a 'concept' function that returns the rank-1 knowledge graphs of a given input node in the db…"*), §4.6.1 (signal-stream constraint for iteration), §9.5, §9.5.1 Database, §8.1 / §8.1.1 (multi-frequency retrieval rank), §10.3 / §10.4 (the underlying indices), §15.7 (url-specific tokenisation).

**Status.** Realised — `search(query, cypher?)`, `cypher(query)`, and `concept(node_id [or list])` are wired at `POST /api/database/{cypher,concept}` (+ `web_browser/scan` for the scan surface) and the `database-cypher` / `database-concept` REPL actions. The signal-stream constraint for `concept`-over-iterable (§1.2 / §4.6.1) is realised: the multi-node `concept(ids)` form preserves request order in its `results`, verified by the `database-concept-signal-stream` scenario (single-node → 1 result; `ids="a,b"` → ordered `[a, b]`). The §8.1.1 multi-frequency band aggregation feeding the retrieval rank is now realised (core) — see [`ApparitionService.md`](ApparitionService.md): mode-gated band modulation, continuous at flat weights, with five real granularity bands (token=TF-IDF, phrase=bigram Jaccard, paragraph=unigram Jaccard, document=nomic, pattern=co-occurrence). Both prior refinements are now realised there too: the **pattern** band is literal `pattern_map` hash-bucket membership, and the §8.2.1.1 ray-projection coupling (`ray_project=1` augments the halo with manifold-nearest projector chunks) is wired.

---

## §1 — What it is

The Database fixture is the workspace's unified storage handle, surfaced as a foundational fixture (§9.5) alongside Agent, WebBrowser, and Editor. Its responsibilities span persistence (Kuzu ConceptNode + ConceptEdge), retrieval (TF-IDF + nomic + multi-frequency PageRank — §8.1.1), the web ontology (compiled-from-scans nodes — §15.5), and the meta-cognition substrate (the agent reads halo apparitions from the Database; the agent's emissions land in the Database).

The §1.5 framing places Database in a hybrid role: it owns the *substrate* both the Real register (the projector reads coords from the Database's LayoutFrame) and the Imaginary register (the editor reads concept-graph topology from Kuzu) build on. The four-fixture API exposes three primary functions for graph + retrieval interaction, plus an extensive set of companion methods for the projector and the UI mirror.

---

## §2 — Shape

The Database fixture is a `python_object` ConceptNode (`backing_pointer = fixture::database::<wsid>`) with `python_function` children.

### §2.1 `Database.search`

```
Signature: (query: str, *, cypher: bool = False) -> list[ChunkInstance]
Ports:
  inputs:  [{name: "query",  type: "str", required: true},
            {name: "cypher", type: "bool", required: false, default: false}]
  outputs: [{name: "chunks", type: "list[ChunkInstance]"}]
Backing: database::search::<wsid>
```

Auto-detects NL vs Cypher query. The flag forces Cypher when auto-detection would not. For NL queries, results are the unstructured chunk list ranked by the multi-frequency aggregation (§8.1.1) when active, falling back to the single-frequency triple product (§8.1) otherwise. For Cypher queries, results are ordered by the predicate.

### §2.2 `Database.cypher`

```
Signature: (query: str) -> KuzuResult
Ports:
  inputs:  [{name: "query",  type: "str", required: true}]
  outputs: [{name: "result", type: "KuzuResult"}]
Backing: database::cypher::<wsid>
```

Real Kuzu Cypher; the result decomposes recursively per §7.1 — top-level keys become child concept cards, leaves become literal values. Embedded cypher in a data block (§8D.2.1) detects and routes here automatically during Compile.

### §2.3 `Database.concept`

```
Signature: (node_id: str | list[str]) -> ConceptGraph
Ports:
  inputs:  [{name: "node_id", type: "str | list[str]", required: true}]
  outputs: [{name: "graph",   type: "ConceptGraph"}]
Backing: database::concept::<wsid>
```

Returns the rank-1 knowledge graph around the input — the focal plus every directly-edge-connected ConceptNode. Accepts a list for batch retrieval; under the **signal-stream constraint** (§4.6.1) the 2D panel renders only the currently-iterated node's rank-1 graph at any moment. The play/pause stepper (§7.5) advances the visible signal; the cascade re-fires per signal so the recursion-over-iteration tree composes correctly.

### §2.4 Companion utility methods

| Method | Purpose |
|---|---|
| `tfidf_retrieve(query, k)` | TF-IDF-only retrieval (no nomic mixing) |
| `walk(node_id, depth)` | BFS walk to a given depth; honours signal-stream when called over an iterable |
| `nearest_chunks(chunk_id, k)` | Projector-nearest chunks by 6D position (drives halo ray-projection per §8.2.1.1) |
| `by_provenance(class)` | Filter by provenance flag (e.g., `agent-output` perimeter chunks) |
| `by_url(url)` | All chunks scanned from a given URL |
| `iterate_pattern(pattern_hash, fn)` | Walk the sampled chunks of a `ChunkPatternSchema` |
| `fold(nodes, init, fn)` | Reduce over a node list |
| `select(node_id)` | UI mirror: set the workspace's selected node |
| `pop_chunk(chunk_id)` | UI mirror: extrude a chunk from its doc-hub |
| `collapse(url)` | UI mirror: collapse a URL's chunks back into the hub |
| `pin_panel(node_id)` | UI mirror: pin a panel via click-and-stick |
| `set_visibility(url, hidden)` | UI mirror: toggle per-URL visibility |
| `fly_to(node_id)` | UI mirror: tween camera to chunk |
| `frame_all()` | UI mirror: frame the entire scene |
| `focus_workspace(url)` | Switch the active workspace |
| `recompute_umap()` | Manual trigger for full 6D UMAP refit |

The UI mirror methods (`select`, `pop_chunk`, `collapse`, `pin_panel`, etc.) are wrappers that POST to UIStateService endpoints (§10.5) so the same gestures the user fires from the GUI can be fired programmatically from a compute graph or an agent emit.

---

## §3 — Lifecycle

### §3.1 Fixture materialisation

`foundation_fixtures.ensure_foundation_fixtures(workspace_id)` produces the Database fixture per [`FoundationFixtures.md`](FoundationFixtures.md). Idempotent on `backing_pointer` match.

### §3.2 Multi-frequency mode transition

The workspace starts in single-frequency mode (§8.1 triple product). After K observed-utility events (default K=32, configurable per workspace; an observed-utility event is a soft-to-hard link promotion, an apparition click, or a successful compile that uses an apparition-suggested wiring), the workspace transitions to multi-frequency mode (§8.1.1). The transition is automatic; `apparition_service.get_mode()` reports the current mode and the workspace's `subsystems` row in the in-place viewer surfaces it.

### §3.3 Signal-stream iteration

`Database.concept(node_id_list)` returns iterable results. The first call materialises all rank-1 graphs into the underlying ConceptNode's `data` field as a recursive tree; the panel displays signal index 0 (the first node's rank-1 graph) as the visible signal. Subsequent `ui-signal-advance` gestures (§17.1.2) advance the index; the panel re-renders the new signal in place; the cascade re-fires downstream cards consuming the value via `{var}` references.

### §3.4 Purge

Purging the workspace invokes `Database.<all>` cleanup through `apply_delete_lifecycle` for every ConceptNode (including the Database fixture's children, which then re-materialise on next workspace open). The Kuzu database file shrinks back to its pre-scan baseline; the persistent accessor table (§5.4) clears for the scanned domains; the TF-IDF and nomic indices return to empty. See [`features/live_scan_cleanup.md`](../features/live_scan_cleanup.md) for the §16.5 acceptance probe.

---

## §4 — Persistence

| Artefact | Storage |
|---|---|
| Fixture node + python_function children | Kuzu `ConceptNode` table |
| ConceptNode storage | Kuzu `ConceptNode` table |
| ConceptEdge storage | Kuzu `ConceptEdge` table |
| EditDiff append-only log | Kuzu `EditDiff` table |
| Per-chunk TF-IDF vectors (per band) | [`GlobalTfidfStore.md`](GlobalTfidfStore.md) — in-memory + persisted per workspace |
| Per-concept nomic vectors | [`ConceptIndexService.md`](ConceptIndexService.md) — in-memory + persisted per workspace |
| Per-workspace LayoutFrame (6D coords) | [`LayoutFrame.md`](LayoutFrame.md) — JSON file per workspace |
| Persistent accessor table (§5.4) | Kuzu, keyed by `(domain, pattern_hash)` |
| `ChunkPatternSchema` records | Inside `pattern_map` ConceptNode's `data` field |
| UI state mirror | [`UIStateService.md`](UIStateService.md) — in-memory + telemetry buffer |

The Kuzu database file is on-disk; `WFH_DB_PATH` overrides its location. Backup is opt-in via the standard Kuzu export path; the persistent accessor table re-exports as a JSON sidecar.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ConceptNode.md`](ConceptNode.md) | Database persists all ConceptNodes; `Database.concept` walks the edge graph rooted at the input |
| [`ConceptEdge.md`](ConceptEdge.md) | Database persists hard links; the `concept` walk traverses them |
| [`ConceptIndexService.md`](ConceptIndexService.md) | Database backs the index's persistence; the index drives the retrieval ranks |
| [`ApparitionService.md`](ApparitionService.md) | Apparition surface reads the multi-frequency-aggregated rank against the Database indices |
| [`LayoutService.md`](LayoutService.md) | Database stores chunk content; LayoutService stores chunk positions; the two compose at scan-end |
| [`GlobalTfidfStore.md`](GlobalTfidfStore.md) | The url-specific tokenisation and multi-frequency bands live in the TF-IDF store |
| [`Editor.md`](Editor.md) | Editor primitives mutate ConceptNode/ConceptEdge rows in Database |
| [`Agent.md`](Agent.md) | Agent.prompt commonly references `Database.search` or `Database.concept` results via `{var}` substitution |
| [`WebBrowser.md`](WebBrowser.md) | Scanner emits chunks into Database; `pattern_map` is a Database ConceptNode |

---

## §6 — Cross-references

- Feature touchpoints — [`features/four_fixture_api.md`](../features/four_fixture_api.md), [`features/multi_frequency_pagerank.md`](../features/multi_frequency_pagerank.md), [`features/signal_stream.md`](../features/signal_stream.md), [`features/halo_retrieval.md`](../features/halo_retrieval.md).
- Code constraints — [`persistence.md`](../code_constraints/persistence.md) (Kuzu storage rules), [`backend_services.md`](../code_constraints/backend_services.md) (Database singleton), [`concurrency.md`](../code_constraints/concurrency.md) (read/write semantics).
- Sequence reference — DOMAIN_MODEL §17.1.2 (signal-stream advance), §17.1.5 (halo ray-projection reads `nearest_chunks`).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Returning all rank-1 graphs for a `Database.concept(list)` call in a flat structure | §18.24 violates signal-stream | The panel renderer reads `signal_stream` mirror and shows only the current signal |
| Mixing the nomic and TF-IDF axes in a single rank | §8D.17.1 two-axis-separation rule | `search` keeps the axes distinct; nomic ranks description, TF-IDF ranks rendering, PageRank multiplies |
| Returning Cypher results that don't decompose through §7.1's recursive descent | Breaks the inline cypher detection (§8D.2.1) | `Database.cypher` always returns a recursive-tree-shaped result |
| Persisting soft links to Kuzu | Soft links are in-memory apparition cache only | The `ConceptEdge` table only holds hard links |
| Letting the Kuzu file grow unboundedly across scan rounds | §18.4 violates the cleanup contract | `purge_workspace` walks every ConceptNode through the lifecycle; the §16.5 probe asserts file-size returns to baseline |
| Caching multi-frequency aggregation results that don't invalidate on `concept_index_update` | Stale ranks would silently corrupt the apparition surface | The aggregation is computed on each `apparition_service.surface_for` call; cache invalidation is tied to the index's settled state |
| Falling back to a stub Kuzu in production | No stub fallback permitted for the storage layer | A missing Kuzu file returns 503; no in-memory fake survives the lifespan |
