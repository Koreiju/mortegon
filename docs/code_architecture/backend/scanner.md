# Backend — Scanner (Selenium · Chunk Build · pattern_map · Web Ontology)

> **Owns:** the live web scan, chunk construction, the live pattern map, and the compiled-from-scans web ontology. Files: `selenium_client.py`, `chunk_builder.py`, `compiled_from_scans.py`, `backend/dom/`. Design: §15.1 / §15.4 / §15.5 / §15.8 / §15.8.1 / §15.8.2 / §8.7 / §8D.39 / §18.29 / §18.1. Realises `code_constraints/scanner.md`, `streaming.md`. Selenium is a no-mocks boundary (`subsystems.md`).

---

## §1 — Responsibility

Drive a real headful Firefox, recursively scan the DOM (shadow-aware), and stream **chunks** into the workspace; build one chunk per homogeneous repeating pattern with golden-trio extraction; materialise the `pattern_map` live during the scan; compile reusable accessors into the web-ontology peer nodes. The `dom/` distillation algorithms (WL hashing, Zhang-Shasha, PQ-trees) are **scanner-internal** — never a retrieval framework, never surfaced in the editor (`migration.md` §2).

---

## §2 — Public Surface

```python
# selenium_client.py  (WebBrowserManager fixture backing)
def scan(self, url: str, query: str | None = None) -> Iterator[Chunk]            # unbounded
def web_query(self, url: str, query: str | None, samples: int) -> Iterator[Chunk]# bounded (POST /api/web_query)

# chunk_builder.py
def build_chunks(dom_tree) -> Iterator[Chunk]            # _recurse_absolute_trie → homogeneous patterns
def extract_golden_trio(pattern) -> tuple[str,str,str]   # (title, link, content), joint-presence gated

# compiled_from_scans.py — the web-ontology peers (§8D.39)
def compile_accessors(scan_result) -> list[ConceptNode]  # SearchableURL / DetectedAccessor / XPathPattern / ...
```

---

## §3 — Internal Logic

### §3.1 Scan (§15.1)
`WebBrowserManager` (the `WebBrowser` fixture's backing) inits eagerly on lifespan (fake gate `NO_WEBDRIVER=1`). `scan` does a recursive, **shadow-DOM-aware** walk; discovers the search input; applies the query; handles implicit pagination. Each chunk is **streamed** (`chunk_added`) to the **workspace** WS — **dual-routed**, not only the per-snapshot socket (§18.1). On arrival a chunk gets a transient hash-direction placeholder position; LayoutService refits it mid-scan and at scan-end (layout.md §3).

### §3.2 Chunk build (§15.4 / §15.8.1)
```
_recurse_absolute_trie(dom):
   find repeating homogeneous sibling patterns (≥2 members, homogeneous structure)
   emit ONE chunk per pattern member
   extract_golden_trio: title + link + content via the joint-presence gate
        (a pattern qualifies only if all three accessors resolve together, §15.8.1)
```

### §3.3 `pattern_map` — live (§15.8.2 / §18.29)
Materialises as a ConceptNode whose `data` is a recursive `ChunkPatternSchema` tree (`data_schemas.md` §4.3): `{pattern_hash, url_root, generalized_xpath, accessor_map, golden_trio, sampled_chunks, sub_patterns}`. **Updates incrementally during the scan** — the user watches patterns accrete. Under the signal-stream constraint the panel shows one `pattern_hash` at a time (§4.6.1; `frontend/cell.md`).

### §3.4 Compiled-from-scans peers (§8D.39 / §15.5)
`SearchableURL`, `DetectedAccessor`, `XPathPattern`, `PinnedComponent`, `ChunkInstance` are compiled into ConceptNodes that are **peers of the fixtures**, not children of Database. Their edges (`SearchableURL → DetectedAccessor`, etc.) compose the web ontology. Backings: `searchable_url::<hash>`, `detected_accessor::<hash>`, `xpath_pattern::<hash>` (persistence.md). A re-scan upserts by hash (idempotent); backing-version bump invalidates dependents (§15.6).

---

## §4 — Dependencies

- **Calls:** Selenium WebDriver, `dom/` distillation, ConceptLifecycle (emit chunks/peers, lifecycle.md), LayoutService (`index_chunk_incremental`, layout.md), GlobalTfidfStore (retrieval.md).
- **Called by:** `POST /api/web_query` / scan routes, the `WebBrowser` fixture, the §8D.49 iterated-compile flow (re-uses recent scan chunks).

---

## §5 — Excluded

- The `dom/` algorithm derivations (WL / Zhang-Shasha / PQ-tree internals) — they stay as scanner-internal implementation, not architecture-level surface. The Real-register meaning of "chunk."
