# Backend — Retrieval (Index · Apparitions · TF-IDF · Nomic)

> **Owns:** the concept-side vectorization pipeline + the apparition scoring + the two embedding stores. Files: `concept_index_service.py`, `apparition_service.py`, `global_tfidf_store.py`, `embedding_service.py`. Design: §8.1 / §8.1.1 / §8.2 / §7.7 / §8D.17.1 / §O.18 / §O.22 / §15.7. Realises `code_constraints/retrieval.md`, `embeddings.md`.

---

## §1 — Responsibility

Rank candidates around any focal by the **triple product** and feed the halo + side panel. Hold the two **strictly separated** embedding axes (for scan chunks): `description → nomic` (functional similarity), `rendering → TF-IDF` (content similarity). **The two axes never mix for chunks** (§8D.17.1); **knowledge panels deviate** (§O.22). The forbidden graph-analytics retrieval framework is **not** here (`migration.md` §2).

---

## §2 — Public Surface

```python
# concept_index_service.py — the concept-side pipeline
def upsert(node) -> None                  # incremental: re-embed description(nomic) + rendering(tfidf); mark dirty
def settle() -> None                      # debounced joint PageRank refit; emit concept_index_update
def slot(concept_id) -> IndexSlot         # {nomic, tfidf, pagerank, similar_to, band_scores}

# apparition_service.py — retrieval + halo coupling
def surface_for(card_id, k=8) -> list[ApparitionCandidate]            # halo soft links
def surface_for_projector(focal_id) -> list[ApparitionCandidate]      # + ray-transport coords/HSV (§O.18)
def closest_inverse(input_type_desc, k=1) -> list[ApparitionCandidate]# §7.7

# global_tfidf_store.py — chunk-side TF-IDF (shared with layout.md)
def add(chunk) -> None; def matrix() -> SparseMatrix; def cos(a, b) -> float

# embedding_service.py — nomic (no-mocks boundary, subsystems.md)
def embed(text: str) -> Vector768           # GPT4All Embed4All nomic-v1.5; CUDA default, CPU-ok
```

---

## §3 — Internal Logic

### §3.1 Scoring (§8.1 / §O.22)
```
chunk focal:   score = pagerank · tfidf_cos(focal.rendering, c.rendering) · nomic_cos(focal.description, c.description)
                       # axes SEPARATED: descriptions never to tf-idf, renderings never to nomic (§8D.17.1)
panel focal:   chunk_text = render the same panel chunk (iterable-recursion sampled, §O.14/§O.19)
               n = nomic_cos(query, chunk_text);  t = tfidf_cos(query, chunk_text)     # BOTH models, same render
               score = pagerank · max( minmax(n over nomic space), minmax(t over tfidf space) )
                       # min-max each cosine to [0,1] over ITS OWN space FIRST (independent scales are biased), THEN max (§O.22)
search set = data chunks  ⊕  ALL panels / functional-objects / computation subgraphs   # one blended space (§O.22)
```
So a halo search blends **data retrieval** with **computational-task retrieval** in a single space.

### §3.2 Halo cone-ray-similarity transport (§O.18 — coords only; `frontend/membranes.md` renders)
```
the 2D query element = cone APEX
for each retrieved 3D node:
    s = normalized retrieval similarity
    radial distance + along-ray distance ← f(s)            # closer-on-cone == more similar
    angular placement ← camera-view projection along the cone surface normal
    HSV carried from the node (rotates with parent)
delete a halo result → pop next-most-similar from the ranked queue
```

### §3.3 Multi-frequency bands (§8.1.1 / §18.25)
After ≥K observed-utility events (default 32), aggregation switches single→multi-semantic-frequency; `apparition_mode` reported in `subsystem_status`. PageRank refit in `settle()` runs over the **concept-edge** graph; top-K `similar_to` recomputed by the triple product.

### §3.4 TF-IDF tokenisation (§15.7)
`GlobalTfidfStore` uses **url-specific tokenisation** (split on `/ ? & = .`) so URLs vectorize meaningfully; **URLs go to TF-IDF only, never nomic.** Incremental: each chunk add updates the sparse matrix without a full refit; the joint UMAP refit (layout.md) consumes the current matrix.

---

## §4 — Dependencies

- **Calls:** `embedding_service` (nomic), `global_tfidf_store` (tfidf), Kuzu edge graph (PageRank), `BackingRegistry` (panel render sampling).
- **Called by:** ConceptLifecycle (`upsert` on every mutation, lifecycle.md §3.1 step 5), the halo route + projector apparitions (`contracts.md` §2.3), `closest_inverse` from the compile output port (compute.md §3.3).
- **Sibling, never nested:** LayoutService (the chunk side) — `GlobalTfidfStore` is shared input to both, but the index and layout services do not nest (§2.3).

---

## §5 — Excluded

- The register meaning of "apparition"; the visual halo radiation (frontend). The forbidden analytics features (depth/cluster_id/wl_hash) are not implemented (`migration.md`).
