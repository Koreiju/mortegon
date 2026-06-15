# Object: ApparitionService

**Domain anchor.** [`DOMAIN_MODEL.md`](../DOMAIN_MODEL.md) §8 (retrieval and apparitions), §8.1 (triple-product), §8.1.1 (multi-semantic-frequency-PageRank), §8.2 (halo), §8.2.1 / §8.2.1.1 / §8.2.1.2 (concentric ring + ray-projection + 6D UMAP HSV), §8.2.2 (autoregressive feedback), §7.7 (closest-inverse), §1.5 (perceptions are retrieval patterns).

**Status.** Realised (core) — the single-frequency triple product (`pagerank · tfidf_cos · nomic_cos`, §8.1; §O.22 `max(minmax)` panel deviation) is the baseline, and **multi-frequency aggregation (§8.1.1) is now wired**: once K=32 observed-utility events accrue (`get_mode()` → `multi_frequency`), `apparitions_for_focal` modulates each score by a band-weighted factor `M = weighted_avg(band_signals; band_weights) / flat_avg` that **reduces to 1.0 at flat weights** (single-frequency stays bit-for-bit, so §18.25 — single-frequency persisting past the threshold — is closed) and tilts toward bands with more user-confirmed utility. Per-band `band_scores` attach to each `ApparitionCandidate` (token/phrase/paragraph/document/pattern; `ConceptEdge.md` SoftLink §2.2). The five bands are each a **distinct, real granularity view** of the card's content: **token** = TF-IDF content cosine, **phrase** = bigram-set Jaccard, **paragraph** = unigram-token-set Jaccard (both computed from the `ConceptIndexSlot.token_set` / `bigram_set` lexical fingerprints built at upsert — parameter-free IR, no fitted model, no mock), **document** = nomic semantic cosine, **pattern** = literal `pattern_map` hash-bucket membership (1.0 same structural family / 0.0 different, from `ConceptIndexSlot.pattern_hash`; co-occurrence fallback only for non-structural cards). The **§8.2.1.1 ray-projection coupling with LayoutService is wired**: `manifold_nearest(focal)` finds the focal's nearest cards in the 6D-UMAP `LayoutFrame` (Euclidean over the 3 position dims) and `apparitions_for_focal(..., ray_project=True)` (route `?ray_project=1`) appends them as ray-projected soft-links carrying manifold-derived §O.18 cone transport (nearest ⇒ apex). Verified: continuity unit (M=1 at flat weights), the offline lexical-band unit (phrase/paragraph Jaccard distinct from blend), live pattern-bucket (`pattern==1.0` for shared bucket), offline manifold-nearest (correct order + apex-near transport), full-smoke crossing into `multi_frequency` (`band_scores (6/6)`; linked candidates still surface), live `band_scores` over the API, offline manifold-nearest (correct order + apex-near transport). All five bands are real fitted/parameter-free signals — the **token** band's TF-IDF runs on the `ngram_range=(1,2)` vectorizer (`tfidf_service.py` / `global_tfidf_store.py`), so the fitted phrase-n-gram TF-IDF projection the §8.1.1 prose calls for is already present; the **phrase/paragraph** Jaccard bands are now **IDF-weighted** (`ConceptIndexService.band_idf` computes smoothed corpus IDF over the slot token/bigram fingerprints; `_jaccard(a, b, idf)` weights a rare shared term above a ubiquitous one). No open refinement remains for the band set.

---

## §1 — What it is

The apparition service produces ranked candidates around any focal ConceptNode. It evaluates the triple product `pagerank · tfidf_cos · nomic_cos` at multiple semantic frequencies (token / phrase / paragraph / document / pattern bands per §8.1.1) and aggregates the per-band scores via PageRank-weighted combination across the band graph, producing a single ordered list of soft-link candidates for the halo. It is also the source for the closest-inverse lookup (§7.7) when a function-card has its output wired but input unwired.

The §1.5 framing places ApparitionService in a dual role: it is the **Imaginary register's retrieval engine** (every concept node's halo is a distributional substance radiating around it), and it is the bridge between the Imaginary's soft links and the Real's manifold (the ray-projection in §8.2.1.1 takes projector-resident chunks and lands them on the halo's conic surface, so the halo simultaneously shows retrieval rank AND manifold neighbourhood at the same focal).

The user's framing in §1.1: *"every focal node is the centre of a distributional substance radiating from it"* — the apparition service is what produces that distribution.

**Knowledge-panel scoring + the blended search space (§O.22).** For dynamically-structured **knowledge panels**, the service deviates from the strict two-axis separation: it embeds the **same rendered panel chunk** (iterable-recursion sampled, §4.6.1) with **both** nomic and TF-IDF, and scores `pagerank · max(minmax(nomic_cos), minmax(tfidf_cos))` — the max of the two cosines, **each min-max normalized to [0, 1] over its own space** (removing the independent-scale bias between the two cosine distributions), linked to PageRank. All panels — functional-objects, whole computation **subgraphs**, iterable chunks — are embedded into the **same** search set as data chunks, so a halo retrieves *computational tasks* (e.g. a research-agent subgraph, panel rendered + vectorized) as readily as data: search over data blends with search over computational tasks. (Scan chunks keep the separated axes, §8.1; the panel embedding reflects the panel's internal memory of external-`{ref}` vs rank-1-inline fields, §O.19, and the graph stays isomorphic to panel containment bounds.)

---

## §2 — Shape

### §2.1 ApparitionCandidate

```python
@dataclass
class ApparitionCandidate:
    focal_id:        str         # the halo's focal ConceptNode.concept_id
    candidate_id:    str         # the proposed soft-link target ConceptNode.concept_id
    score:           float       # aggregated multi-frequency rank
    pagerank:        float       # per-band pagerank (when band-specific) or aggregated pagerank
    tfidf_cos:       float       # per-band tfidf cosine
    nomic_cos:       float       # per-band nomic cosine
    band_scores:     dict[str, float]   # per-band aggregated score when multi-freq active
    name:            str         # the candidate's display name (halo phantom shows name only — §4.5)
    is_projector_neighbour: bool # true if the candidate is also one of focal's manifold-nearest chunks
    ray_target:      tuple[float, float, float] | None  # screen-space conic-surface intersection point if ray-projected
    hsv:             tuple[float, float, float] | None  # if ray-projected, the chunk's HSV state from LayoutFrame
    image_url:       str | None  # if ray-projected and an image billboard is attached
```

### §2.2 Key methods

| Method | Purpose |
|---|---|
| `surface_for(card_id, k=8)` | Return top-K ApparitionCandidates ranked by aggregated multi-frequency score |
| `surface_for_projector(card_id, k=8, projector_neighbours=4)` | Same but additionally annotate the K projector-nearest chunks with ray_target + hsv + image_url for the halo's conic-surface placement (§8.2.1.1) |
| `closest_inverse(target_concept, input_type, k=1)` | Return the candidate whose predicted output best matches the observed `target_concept`; used by §7.7 |
| `completions(prefix, *, parent_card_id=None, k=8)` | Autocomplete-scoped ranking (§4.7); when `parent_card_id` is a python-bound object, restrict to its members |
| `get_mode()` | Return `"single_frequency"` or `"multi_frequency"` based on accumulated observed-utility events |
| `record_utility_event(focal_id, candidate_id, kind)` | Increment the workspace's observed-utility counter; the K-threshold transition into multi-frequency mode is automatic |

---

## §3 — Ranking algorithm

### §3.1 Single-frequency triple product (§8.1)

For each candidate `c` relative to focal `f`:

```
score(c, f) = pagerank(c) · tfidf_cos(f.rendering, c.rendering) · nomic_cos(f.description, c.description)
```

The two embedding axes never mix: descriptions go through nomic, renderings go through TF-IDF, PageRank operates on the concept graph. When the focal's `description` is populated and `rendering` is empty (a freshly-typed empty primitive), the triple collapses to `pagerank · nomic_cos`. When only `rendering` is populated, it collapses to `pagerank · tfidf_cos`.

### §3.2 Multi-frequency aggregation (§8.1.1)

When the workspace has accumulated K observed-utility events (default K=32), the service transitions to multi-frequency mode. The triple product is evaluated at five semantic frequencies:

| Band | TF-IDF granularity | Nomic granularity | PageRank source |
|---|---|---|---|
| Token | per-token IDF | n/a | per-token co-occurrence graph |
| Phrase | 2-5 gram TF-IDF | nomic over phrase chunks | phrase-level neighbour graph |
| Paragraph | per-paragraph TF-IDF (single-freq default) | nomic over paragraph descriptions (single-freq default) | concept-edge PageRank |
| Document | per-doc TF-IDF | nomic over doc-aggregated rendering | URL-level co-citation graph |
| Pattern | per-chunk-pattern TF-IDF | nomic over pattern descriptions | golden-trio + accessor-table neighbour graph |

The per-band scores are combined as `aggregated_score = Σ_f w_f · triple_product_at_band(f)`, where the weights `w_f` are themselves PageRank scores over the **semantic-frequency band graph** (the bands that historically produced soft links the user promoted get higher weight). The weights are auto-tuned per workspace from the EvolutionLog's record of observed-utility events.

### §3.3 Ray-projection augmentation (§8.2.1.1)

When `surface_for_projector` is called (i.e., the halo's focal panel has a `data-3d-node-id`):

1. Read the focal's 3D position from the LayoutFrame.
2. Call `LayoutService.nearest_chunks(workspace_id, focal_chunk_id, k=projector_neighbours)`.
3. For each projector-neighbour, compute the ray from the focal-panel screen centre through the screen-projected world position; intersect with the halo's conic surface (cone apex at focal centre, lateral surface at halo outer ring radius); the intersection becomes the candidate's `ray_target`.
4. Read the projector-neighbour's HSV state from the LayoutFrame; if an image billboard is attached, read the `image_url`; populate the ApparitionCandidate.
5. Merge the projector-neighbours into the ranked candidate list (de-duplicating by candidate_id; the projector-neighbour version wins for HSV + ray_target annotations).

The resulting list now carries dual semantics — every visible phantom is *both* a soft-link candidate by retrieval rank *and* (for projector-backed phantoms) a manifold-nearest chunk by 3D geometry. The user sees retrieval space and manifold space superimposed at the focal.

### §3.4 Closest-inverse (§7.7)

For a function-card with output wired to `target_concept` but input unwired:

1. Search the persistent store for candidate ConceptNodes whose type matches the function's input parameter annotation.
2. For each candidate `c`, project `(c, function_metadata)` into the same space the output `target_concept` embeds in.
3. Rank by `cos_sim(predicted_output_for_c, target_concept)`.
4. Return the top match (or top-K).

The Imaginary's projective property (§7.7): the same projection that runs forward (input → output) is read backward (output → closest input). The inverse uses the same multi-frequency triple product when multi-freq mode is active.

---

## §4 — Persistence

| Artefact | Storage |
|---|---|
| Per-workspace mode (`single_frequency` / `multi_frequency`) | In-memory; recomputed from EvolutionLog observed-utility events on workspace reload |
| Per-band weight cache (`w_f` for each band) | In-memory per workspace; refit on `concept_index_update` settle |
| Observed-utility event count | Tracked in EvolutionLog; counted on workspace boot |
| ApparitionCandidate list per focal | In-memory cache only; vanishes on halo close or focal description change |

The service is stateful but its state is fully derivable from upstream (Kuzu + ConceptIndex). A backend restart rebuilds state from those sources.

---

## §5 — Peer interactions

| Peer | Interaction |
|---|---|
| [`ConceptIndexService.md`](ConceptIndexService.md) | Reads per-concept nomic + TF-IDF + PageRank from the index |
| [`GlobalTfidfStore.md`](GlobalTfidfStore.md) | Reads per-band TF-IDF vectors for multi-frequency evaluation |
| [`LayoutService.md`](LayoutService.md) | Reads `nearest_chunks` + LayoutFrame HSV state for ray-projection annotation |
| [`Halo.md`](Halo.md) | Frontend halo renderer reads the candidate list and the ray-projection annotations |
| [`UIStateService.md`](UIStateService.md) | `halo_focus` mirror tracks the active focal; `halo_chain` tracks the autoregressive walk |
| [`EvolutionLog.md`](EvolutionLog.md) | Observed-utility events read from here for K-threshold + per-band weight tuning |
| [`Editor.md`](Editor.md) | Soft-to-hard promotion (click on phantom) calls Editor.link |
| [`AgentRuntime.md`](AgentRuntime.md) | Agent perception card reads `surface_for(parameter_focal)` for its perception payload |

---

## §6 — Cross-references

- Feature touchpoints — [`features/halo_retrieval.md`](../features/halo_retrieval.md), [`features/multi_frequency_pagerank.md`](../features/multi_frequency_pagerank.md), [`features/autoregressive_halo.md`](../features/autoregressive_halo.md), [`features/projective_inverse.md`](../features/projective_inverse.md), [`features/empty_primitive_radiation.md`](../features/empty_primitive_radiation.md), [`features/autocomplete.md`](../features/autocomplete.md).
- Code constraints — [`backend_services.md`](../code_constraints/backend_services.md) (apparition service singleton), [`api_routes.md`](../code_constraints/api_routes.md) (`/api/apparitions/<card_id>` shape), [`error_handling.md`](../code_constraints/error_handling.md) (graceful empty halos when index is empty).
- Sequence reference — DOMAIN_MODEL §17.7 (apparition resolve), §17.1.5 (halo ray-projection), §17.9 (closest-inverse).

---

## §7 — Anti-patterns (must-not)

| Anti-pattern | Why forbidden | Guard |
|---|---|---|
| Mixing the nomic and TF-IDF axes in a single embedding | §8D.17.1 — two-axis-separation rule | The triple product evaluates the axes independently at each band; the aggregation only multiplies the per-axis cosines, never adds across axes |
| Persisting soft-link candidates to Kuzu | Soft links are in-memory only; persisting pollutes the deterministic edge table | The service stores no candidate list to disk |
| Falling back to single-frequency aggregation when multi-frequency mode is active | §18.25 — stale rank quality | The service's `get_mode()` is the source of truth; clients must check before reading |
| Halo phantoms showing score chips or score numbers | §18.21 / §USER D.1 — compact form regression | Frontend renderer ignores the score field; scores live in slow-hover tooltip only |
| Ray-projection annotations carrying mismatched HSV | §18.26 — the phantom's hue must match its parent chunk's | The annotation reads HSV from the LayoutFrame on every `surface_for_projector` call; no caching |
| Returning candidates with score below `min_score_threshold` | §8.2.1 — scale-space periphery preservation | Candidates below threshold fall off the visible halo entirely |
| Computing the multi-frequency aggregation without all five bands | Incomplete bands produce a misleadingly low aggregated score | The service errors loudly if a band's index is unavailable; no silent fallback |
| Letting the per-band weights `w_f` drift outside [0, 1] | Aggregation invariants depend on the weights being a probability distribution | The PageRank refit normalises the weights; bounds are enforced |
