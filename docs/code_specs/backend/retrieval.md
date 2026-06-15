# Spec — Backend / Retrieval (Index · Apparitions · TF-IDF · Nomic)

> Deepens [`code_architecture/backend/retrieval.md`](../../code_architecture/backend/retrieval.md). Files: `concept_index_service.py`, `apparition_service.py`, `global_tfidf_store.py`, `embedding_service.py`. Types: [`../types.md`](../types.md) §5. Constants: [`../constants.md`](../constants.md) §2/§5. Axes never mix for chunks; panels deviate (§O.22).

---

## §1 — ConceptIndexService

```python
def upsert(self, node: ConceptNode) -> None
def remove(self, concept_id: ConceptId) -> None
def settle(self) -> None
def slot(self, concept_id: ConceptId) -> IndexSlot
```
- **`upsert`** — re-embed `node.description` → nomic `Vec768` (`EmbeddingService.embed`) and `node.rendering` → TF-IDF sparse vec (`GlobalTfidfStore`); mark the workspace PageRank dirty. **Raises** `SubsystemDownError` if embedder dead. Idempotent on `concept_id`.
- **`settle`** — debounced `PAGERANK_DEBOUNCE_MS`: run PageRank (`PAGERANK_DAMPING`) over the **concept-edge** graph; recompute `similar_to` top-`SIMILAR_TO_TOPK` by the triple product (§3.1); emit `ConceptIndexUpdate`. Complexity O(E) power-iteration.
- **`slot`** — return the cached `IndexSlot`; if multi-frequency active (`band_scores` non-null after `MULTI_FREQ_K` utility events), include per-band scores.
- **Invariant** — descriptions only to nomic, renderings only to TF-IDF (assertion, errors.md §3) — except the panel path (§3.1).

---

## §2 — EmbeddingService / GlobalTfidfStore

```python
def embed(self, text: str) -> Vec768                 # nomic; CUDA default, CPU-ok (WARNING)
def add(self, chunk_or_node) -> None                 # tfidf incremental
def cos(self, a, b) -> float                          # cosine in [-1,1]
def matrix(self, workspace_id) -> SparseMatrix        # full index (layout.md consumes)
def vectorize(self, text: str) -> SparseVec
```
- **`embed`** — real GPT4All `Embed4All(EMBED_MODEL)`; fake gate `WFH_FAKE_EMBEDDER` → hash-deterministic `Vec768`. Batch where possible.
- **TF-IDF tokenisation** — **url-specific**: split on `TFIDF_SPLIT` (`/?&=.`) so URLs vectorize; **URLs go to TF-IDF only, never nomic** (§15.7). Incremental: each `add` updates the sparse matrix without a full refit; document-frequency updated lazily.

---

## §3 — ApparitionService

```python
# Realized names (apparition_service.py): surface_for → apparitions_for_focal,
# surface_for_projector → manifold_nearest (the ray-projection augment appended
# when apparitions_for_focal is called with ray_project=True).
def apparitions_for_focal(self, focal_id: ConceptId, *, workspace_id: WorkspaceId,
                          k: int = APPARITION_K, transport: bool = False,
                          ray_project: bool = False) -> list[ApparitionCandidate]
def manifold_nearest(self, focal_id: ConceptId, *, workspace_id: WorkspaceId,
                     k: int = 6) -> list[ApparitionCandidate]   # + RayTransport
def closest_inverse(self, input_type_desc: str, k: int = INVERSE_K) -> list[ApparitionCandidate]
```

### §3.1 Scoring (the load-bearing algorithm)
```
is_panel = focal is an aggregate (singular-primitive aspect false, §O.19)
search_set = all chunks ⊕ all panels/functional-objects/subgraphs    # one BLENDED space (§O.22)

if not is_panel:   # chunk focal — axes SEPARATED (§8D.17.1)
    for c in search_set:
        score = c.pagerank * tfidf_cos(focal.rendering, c.rendering) * nomic_cos(focal.description, c.description)

else:              # panel focal — DEVIATION (§O.22)
    q = render_panel_chunk(focal, iterable_recursion_sampled=True)   # §O.14/§O.19 sampling
    raw = [(c, nomic_cos(q, c.text), tfidf_cos(q, c.text)) for c in search_set]
    N = minmax([n for _,n,_ in raw]); T = minmax([t for _,_,t in raw])   # min-max each to [0,1] over its OWN space FIRST
    for i,(c,_,_) in enumerate(raw):
        score = c.pagerank * max(N[i], T[i])                            # THEN max (independent-scale bias removed)

return top-k by score as ApparitionCandidate(concept_id, name, score, nomic_cos, tfidf_cos, transport=None)
```
- **`closest_inverse`** — embed `input_type_desc` (nomic), rank type-compatible nodes by nomic_cos; return top-`k` or `[]` (not an error, errors.md §2). Used at compile output ports (compute.md §3.3).

### §3.2 ray-projection transport (`manifold_nearest` / `ray_project=True`) — cone-ray (§O.18; coords only)
```
cands = apparitions_for_focal(focal_id, workspace_id=ws, k=k)   # + manifold_nearest augment
smax = max(c.score for c in cands) or 1.0
for c in cands:
    s = c.score / smax                                  # normalized similarity
    c.transport = RayTransport(
        radial    = (1 - s) * TARGET_RADIUS,            # closer-on-cone == more similar
        along_ray = f_along(s),
        angular   = camera_view_projection(c, cone_surface_normal),   # supplied to client; recomputed per camera
        hsv       = index.slot(c.concept_id).hsv_of_nearest_chunk())
return cands     # frontend membranes/halo RENDERS; backend computes no geometry beyond these scalars
```
Delete-a-result is a frontend pop from this ranked list (membranes.md); the next candidate is already ranked.

---

## §4 — Dependencies / Excluded
**Calls:** `EmbeddingService`, `GlobalTfidfStore`, Kuzu edge graph (PageRank), `BackingRegistry` (panel render). **Called by:** lifecycle.md (`upsert`/`remove`/`settle`), api.md (`surface`/halo), compute.md (`closest_inverse`), agent.md (perception). **Sibling** of LayoutService (shared `GlobalTfidfStore`, never nested). **Excluded:** forbidden graph-analytics features (migration.md); the halo *render* (membranes.md); the "apparition" register meaning.
