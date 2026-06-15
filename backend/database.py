import os
import kuzu
import shutil
import sys
import time

DB_PATH = os.environ.get(
    "WFH_DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kuzu_db")),
)

db = None
conn = None


def _find_lock_holders(db_path: str) -> list[dict]:
    """Best-effort identification of processes that may be holding the
    kuzu lock at ``db_path``.

    Returns a list of ``{pid, name, cmdline}`` dicts. Uses ``psutil`` if
    available; otherwise returns ``[]`` and the caller falls back to a
    generic message.

    Heuristic: match python/uvicorn processes whose cmdline contains
    the project root AND one of our entry-point markers
    (``backend.main``, ``uvicorn``, ``scripts``, ``kuzu_db``). A pure
    cwd match would catch VS Code's Python language server, which is
    not what we want — only processes actually running our code.
    """
    try:
        import psutil  # type: ignore
    except Exception:
        return []
    db_real = os.path.realpath(db_path).lower()
    project_root = os.path.dirname(db_real)
    markers = ("backend.main", "backend/main", "backend\\main",
               "uvicorn", "scripts", "kuzu_db", "wfh_db_path")
    holders: list[dict] = []
    me = os.getpid()
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["pid"] == me:
                continue
            name = (p.info.get("name") or "").lower()
            if "python" not in name and "uvicorn" not in name:
                continue
            cmd = " ".join(p.info.get("cmdline") or []).lower()
            if project_root not in cmd and db_real not in cmd:
                continue
            if not any(m in cmd for m in markers):
                continue
            holders.append({
                "pid": p.info["pid"],
                "name": p.info.get("name") or "?",
                "cmdline": " ".join(p.info.get("cmdline") or []),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return holders


def _explain_lock_error(db_path: str, original: Exception) -> RuntimeError:
    """Wrap the raw kuzu lock RuntimeError with actionable guidance."""
    holders = _find_lock_holders(db_path)
    lines = [
        "",
        "=" * 70,
        "[Database] Could not acquire the kuzu DB lock.",
        f"  path: {db_path}",
        "",
        "  Kuzu is single-writer. Another process (most commonly a stale",
        "  uvicorn / preview server / earlier scan) is still holding this DB.",
    ]
    if holders:
        lines.append("")
        lines.append("  Likely holders (matched by project path in cmdline):")
        for h in holders:
            cmd = h["cmdline"]
            if len(cmd) > 120:
                cmd = cmd[:117] + "..."
            lines.append(f"    PID={h['pid']:<6} {h['name']:<14} {cmd}")
        lines.append("")
        pids = " ".join(str(h["pid"]) for h in holders)
        if sys.platform.startswith("win"):
            lines.append(f"  Kill them:  powershell -c \"Stop-Process -Id {pids} -Force\"")
        else:
            lines.append(f"  Kill them:  kill -9 {pids}")
    else:
        lines.append("")
        lines.append("  (Could not auto-identify the holder — install `psutil`")
        lines.append("  for automatic detection: `pip install psutil`.)")
    lines.append("")
    lines.append("  One-shot reset (kill holders + nuke DB/snapshots/logs):")
    lines.append("    python scripts/reset_state.py --kill")
    lines.append("=" * 70)
    lines.append("")
    msg = "\n".join(lines)
    print(msg, file=sys.stderr)
    return RuntimeError(f"Kuzu lock conflict at {db_path}. See stderr for details. "
                        f"Original: {original}")


def _effective_db_path() -> str:
    """Resolve where the kuzu data file actually lives.

    kuzu ≥ 0.11 is FILE-based — ``kuzu.Database(path)`` refuses a directory.
    The legacy layout used ``<repo>/kuzu_db/`` as a directory-based DB, and
    the per-workspace side files (``concept_index_*`` / ``evolution_log_*`` /
    ``layout_frame_*`` / ``ontology_frame_*``) still default their storage
    into that same directory. When ``DB_PATH`` is an existing NON-empty
    directory (the artifact layout), nest the kuzu data file inside it as
    ``data.kuzu`` so the store and the side files coexist; otherwise use
    ``DB_PATH`` directly (the file-mode path every test/probe temp DB uses).
    Computed at call time because tests rebind ``database.DB_PATH``.
    """
    if os.path.isdir(DB_PATH) and os.listdir(DB_PATH):
        return os.path.join(DB_PATH, "data.kuzu")
    return DB_PATH


def get_connection():
    global db, conn
    if conn is None:
        if os.path.exists(DB_PATH) and os.path.isdir(DB_PATH) and not os.listdir(DB_PATH):
            shutil.rmtree(DB_PATH)
        path = _effective_db_path()

        retries = 5
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                db = kuzu.Database(path)
                conn = kuzu.Connection(db)
                break
            except RuntimeError as e:
                last_err = e
                if "Could not set lock" in str(e) and attempt < retries - 1:
                    print(f"[Database] Lock detected, retrying in 1s... (Attempt {attempt + 1}/{retries})")
                    time.sleep(1)
                elif "Could not set lock" in str(e):
                    raise _explain_lock_error(path, e) from e
                else:
                    raise
        if conn is None and last_err is not None:
            raise last_err
    return conn

def get_database():
    global db
    if db is None:
        get_connection()
    return db

def close_db():
    global db, conn
    if conn is not None and hasattr(conn, "close"):
        conn.close()
    if db is not None and hasattr(db, "close"):
        db.close()
    conn = None
    db = None

def init_db():
    conn = get_connection()
    # Was 768 (nomic v1 / v1.5 GGUF). Bumped to 1024 to match the
    # TF-IDF random-projection dim — the user asked for ``dense_dim``
    # in the 1k range, and aligning the schema means we don't need a
    # parallel storage path for legacy nomic vs. new TF-IDF rows.
    # Existing pre-1024 databases should be deleted to re-init at the
    # new width (the kuzu lock dance the user has already been
    # running through repeatedly does this automatically — there's no
    # production data here that needs migrating).
    NOMIC_EMBED_DIM = 1024

    tables = [
        # --- Core domain / page / snapshot tables ---
        ("Domain", "domain STRING, first_seen STRING, PRIMARY KEY (domain)"),
        ("Page", "url STRING, domain STRING, timestamp STRING, PRIMARY KEY (url)"),
        ("DomSnapshot", "snapshot_id STRING, url STRING, file_path STRING, content_hash STRING, captured_at STRING, node_count INT64, PRIMARY KEY (snapshot_id)"),
        ("ContentTree", "tree_id STRING, url STRING, xpath_json STRING, PRIMARY KEY (tree_id)"),

        # --- Label system (separate from content tree) ---
        # DEPRECATED layout: NodeLabel carries both `xpath` (instance) and
        # `pattern` (generalized). New labels should be keyed on
        # TriePattern.pattern_id (one label per generalized pattern, not per
        # instance). Phase 3 adds a PatternLabel table that supersedes this.
        ("NodeLabel", "label_id STRING, url STRING, xpath STRING, label STRING, pattern STRING, is_instance BOOLEAN, snapshot_id STRING, created_at STRING, PRIMARY KEY (label_id)"),
        ("StructureTag", "tag_id STRING, url STRING, tag_name STRING, label_group STRING, pattern STRING, lca_xpath STRING, description STRING, created_at STRING, PRIMARY KEY (tag_id)"),

        # --- Existing RAG tables ---
        ("Chunk", "chunk_id_str STRING, stem_selector STRING, subtree_root STRING, frequency INT64, is_input BOOL, is_button BOOL, is_text BOOL, is_link BOOL, has_url_pattern BOOL, has_structure BOOL, PRIMARY KEY (chunk_id_str)"),
        ("Sample", f"sample_id STRING, content STRING, is_text BOOL, has_alt BOOL, content_hash STRING, embedding FLOAT[{NOMIC_EMBED_DIM}], PRIMARY KEY (sample_id)"),
        ("UrlPattern", "pattern STRING, PRIMARY KEY (pattern)"),
        ("UrlPath", "segment STRING, full_path STRING, PRIMARY KEY (full_path)"),
        ("Prompt", "prompt_id STRING, prompt_text STRING, timestamp STRING, PRIMARY KEY (prompt_id)"),
        ("DetectedField", "field_id STRING, field_type STRING, selector STRING, url STRING, PRIMARY KEY (field_id)"),
        ("Action", "action_id STRING, action_type STRING, success BOOL, timestamp STRING, PRIMARY KEY (action_id)"),

        # --- Phase 0A (Snapshot Segmentation / Typing / Core) ---
        ("MediaAsset", "asset_id STRING, source_url STRING, local_path STRING, content_hash STRING, mime_type STRING, file_size INT64, width INT64, height INT64, duration DOUBLE, phash STRING, thumbnail_path STRING, source_xpath STRING, snapshot_id STRING, created_at STRING, PRIMARY KEY (asset_id)"),
        ("SegmentEmbedding", f"embedding_id STRING, snapshot_id STRING, cluster_id INT64, label STRING, text_content STRING, embedding FLOAT[{NOMIC_EMBED_DIM}], token_count INT64, patricia_pattern STRING, url STRING, created_at STRING, PRIMARY KEY (embedding_id)"),
        ("SnapshotPatriciaIndex", "index_id STRING, url STRING, snapshot_id STRING, PRIMARY KEY (index_id)"),
        ("ChatSession", "session_id STRING, title STRING, created_at STRING, message_count INT64, PRIMARY KEY (session_id)"),
        ("ChatMessage", f"message_id STRING, session_id STRING, role STRING, content STRING, tool_name STRING, tool_input STRING, tool_output STRING, token_count INT64, embedding FLOAT[{NOMIC_EMBED_DIM}], created_at STRING, PRIMARY KEY (message_id)"),
        ("OntologyFieldEmbedding", f"embedding_id STRING, node_id STRING, node_type STRING, field_name STRING, field_value STRING, embedding FLOAT[{NOMIC_EMBED_DIM}], updated_at STRING, PRIMARY KEY (embedding_id)"),
        ("RetrievalStreamEntryDB", "entry_id STRING, actor STRING, trigger STRING, query_text STRING, cypher_query STRING, legs_used STRING, results_json STRING, focal_node_id STRING, pinned_node_ids STRING, created_at STRING, PRIMARY KEY (entry_id)"),

        # --- Phase 0D: Activity system ---
        ("ActivityEntry", "entry_id STRING, timestamp STRING, actor STRING, actor_type STRING, action_verb STRING, target_type STRING, target_id STRING, summary STRING, diff_json STRING, context_json STRING, parent_entry_id STRING, PRIMARY KEY (entry_id)"),

        # --- Phase 4A: Knowledge graph editor ---
        ("UserNote", f"note_id STRING, content STRING, tags STRING, source_url STRING, embedding FLOAT[{NOMIC_EMBED_DIM}], created_at STRING, PRIMARY KEY (note_id)"),
        ("OntologyNode", f"ontology_node_id STRING, label_name STRING, label_type STRING, description STRING, properties_json STRING, embedding FLOAT[{NOMIC_EMBED_DIM}], created_at STRING, PRIMARY KEY (ontology_node_id)"),
        ("PinnedComponent", "pin_id STRING, source_snapshot STRING, lca_xpath STRING, label_summary STRING, patricia_hash STRING, created_at STRING, PRIMARY KEY (pin_id)"),
        ("ContextAssembly", "assembly_id STRING, name STRING, fragments_json STRING, priority INT64, created_at STRING, PRIMARY KEY (assembly_id)"),

        # --- W4 / §8D.44: Unified ConceptNode model ---
        # One uniform record type for every concept-graph artefact: chunk
        # cards, user notes, ontology nodes, function-pattern nodes,
        # committed subgraphs, fixtures (Database / WebBrowser), and the
        # compiled-in-from-scans peers (SearchableURL, XPathPattern,
        # DetectedAccessor, PinnedComponent). Per §8D.44, ConceptNodes
        # differ only by ``name``, ``linked_nodes`` (denormalised view of
        # the ConceptEdge rel table), and ``backing_pointer`` (opaque
        # runtime handle). ``embedding_nomic`` is the description-only
        # vector (§8D.40); ``embedding_tfidf`` is the rendered-value
        # vector (§8D.17 + §8D.43's external frequency vector). Both
        # contribute to the triple-product apparition scoring (§8D.43).
        # ``pagerank`` is refreshed on the Concept Index Service's batch
        # cadence (§11.6). ``provenance`` tags the record's origin per
        # §9.12 (user-authored | agent-authored | derived-from-chunk |
        # committed-subgraph). ``layout_xy`` and ``ui_state`` are JSON
        # blobs holding the editor's per-card position and minimised/
        # pinned state respectively. The §8A "entity types" (UserNote,
        # OntologyNode, PinnedComponent, ContextAssembly) coexist for
        # now as separate tables for backward compatibility; new code
        # writes ConceptNode rows. §8D.34 / §8A.12 explain the
        # subsumption.
        (
            "ConceptNode",
            f"concept_id STRING, "
            f"name STRING, "
            f"description STRING, "
            f"data STRING, "
            f"rendering STRING, "
            f"linked_nodes_json STRING, "
            f"backing_pointer STRING, "
            f"embedding_nomic FLOAT[{NOMIC_EMBED_DIM}], "
            f"embedding_tfidf FLOAT[{NOMIC_EMBED_DIM}], "
            f"pagerank DOUBLE, "
            f"provenance STRING, "
            f"workspace_id STRING, "
            f"layout_xy STRING, "
            f"ui_state STRING, "
            f"type_hint STRING, "
            f"created_at STRING, "
            f"updated_at STRING, "
            f"PRIMARY KEY (concept_id)"
        ),

        # --- Post-scan content chunks (SLM-sized partitions of the distilled DOM) ---
        ("ContentChunk", "chunk_id STRING, snapshot_id STRING, url STRING, pattern STRING, representative_xpath STRING, member_xpaths_json STRING, char_count INT64, commutation_count INT64, content_fields_json STRING, text_preview STRING, label STRING, extraction_trie_json STRING, created_at STRING, PRIMARY KEY (chunk_id)"),

        # --- Persistent Patricia trie (the single authoritative structural record) ---
        # TrieVersion: one row per scan of a URL. parent_version links prior version for diff lineage.
        ("TrieVersion", "version_id STRING, url STRING, snapshot_id STRING, parent_version_id STRING, pattern_count INT64, content_pattern_count INT64, total_char_count INT64, root_hash STRING, created_at STRING, PRIMARY KEY (version_id)"),
        # TriePattern: one row per unique generalized-xpath pattern in a version.
        # tag_set is a JSON list of content categories; subtree_hash is a Merkle-style hash of (self + sorted(child_subtree_hashes)) so unchanged subtrees can be collapsed by diff.
        ("TriePattern", "pattern_id STRING, version_id STRING, pattern STRING, representative_xpath STRING, parent_pattern_id STRING, tag_set STRING, commutation_count INT64, depth INT64, has_shadow_boundary BOOLEAN, char_count INT64, self_hash STRING, subtree_hash STRING, member_xpaths STRING, PRIMARY KEY (pattern_id)"),
        # Phase 3: SLM-generated semantic label for a TriePattern. One label per
        # generalized pattern, not per instance. raw_json preserves the SLM's
        # full response for auditability.
        ("PatternLabel", "label_id STRING, pattern_id STRING, version_id STRING, role STRING, category STRING, summary STRING, confidence DOUBLE, raw_json STRING, model STRING, created_at STRING, PRIMARY KEY (label_id)"),
        # Phase 4: 768-dim nomic embedding of a labeled pattern's knowledge panel.
        # text_source is the canonical serialization that was fed to the encoder.
        ("PatternEmbedding", f"embedding_id STRING, pattern_id STRING, version_id STRING, text_source STRING, embedding FLOAT[{NOMIC_EMBED_DIM}], created_at STRING, PRIMARY KEY (embedding_id)"),

        # --- Phase 5: Per-instance chunk render + embedding ---
        # One row per populated instance of a ChunkBuilder pattern. Stores
        # the full HTML of the instance subtree (resources preserved, event
        # handlers stripped), the markdown-lite rendered text fed to the
        # embedder, and the 768-dim nomic vector.  Keyed on a deterministic
        # hash of (version_id, absolute_xpath) so re-scans upsert.
        ("ChunkInstance", f"instance_id STRING, chunk_id STRING, pattern_id STRING, version_id STRING, url STRING, snapshot_id STRING, absolute_xpath STRING, html_raw STRING, rendered_text STRING, fields_json STRING, embedding FLOAT[{NOMIC_EMBED_DIM}], created_at STRING, PRIMARY KEY (instance_id)"),
        # One row per page-level embedding (mean of that page's instance
        # embeddings). Enables URL-level semantic search that returns
        # URLs-as-anchors the caller can drill down into.
        ("PageEmbedding", f"page_embedding_id STRING, url STRING, version_id STRING, snapshot_id STRING, instance_count INT64, embedding FLOAT[{NOMIC_EMBED_DIM}], created_at STRING, PRIMARY KEY (page_embedding_id)"),
        # Signal-field tables: search inputs and pagination controls tracked
        # across scans of the same domain. field_id = sha1(domain | generalized_xpath | text_hint_hash)
        # so the same xpath coalesces across URLs.
        ("SearchInputField", "field_id STRING, domain STRING, generalized_xpath STRING, last_seen_url STRING, last_seen_absolute_xpath STRING, tag STRING, text_hint STRING, attributes_json STRING, score INT64, first_seen STRING, last_seen STRING, PRIMARY KEY (field_id)"),
        ("PaginationField", "field_id STRING, domain STRING, generalized_xpath STRING, last_seen_url STRING, last_seen_absolute_xpath STRING, tag STRING, text_hint STRING, attributes_json STRING, score INT64, first_seen STRING, last_seen STRING, PRIMARY KEY (field_id)"),

        # --- Phase 9: Agentic fluid ---
        ("FluidSession", "session_id STRING, state STRING, agent_count INT64, propagation_steps INT64, created_at STRING, PRIMARY KEY (session_id)"),
        ("FluidStep", "step_id STRING, session_id STRING, step_idx INT64, coagulated_substance STRING, centroidal_recommendation STRING, PRIMARY KEY (step_id)"),
        ("AgentRecord", "record_id STRING, step_id STRING, name STRING, domain STRING, action STRING, output STRING, PRIMARY KEY (record_id)"),

        # --- DEPRECATED: DomNode (legacy per-node rows, superseded by TriePattern) ---
        # Retained for backward compat with the 3D viewer. New code should use
        # TrieVersion/TriePattern (see backend/dom/trie_persistence.py). Do not
        # add new callers — remove once the 3D pipeline is rewritten on top of
        # the trie. html_raw in particular duplicates what the ground-truth
        # HTML store (local_html_root in pipeline.py) now owns.
        ("DomNode", "node_id STRING, xpath STRING, tag STRING, label STRING, is_user_labeled BOOLEAN, depth INT, html_raw STRING, layout_x FLOAT, layout_y FLOAT, layout_z FLOAT, node_type INT64, tag_name STRING, node_name STRING, id_attr STRING, class_name STRING, attributes STRING, text_content STRING, signature STRING, page_url STRING, content_hash STRING, PRIMARY KEY (node_id)")
    ]

    for name, schema in tables:
        try:
            conn.execute(f"CREATE NODE TABLE {name}({schema})")
            print(f"Created {name} table.")
        except Exception:
            # Table already exists (RuntimeError) or schema mismatch — ignore.
            # Kuzu raises RuntimeError for duplicate names but may use other
            # exception types on version upgrades; catching Exception ensures
            # newly-added tables (e.g. ContentChunk) are created in existing
            # databases without requiring a full wipe.
            pass

    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_domnode_url ON DomNode (page_url);")
    except Exception:
        pass

    rels = [
        # --- New mapper relationships ---
        ("HAS_PAGE", "Domain", "Page"),
        ("HAS_SNAPSHOT", "Page", "DomSnapshot"),
        ("HAS_CONTENT_TREE", "DomSnapshot", "ContentTree"),

        # --- Existing RAG relationships ---
        ("CONTAINS", "Page", "Chunk"),
        ("HAS_SAMPLE", "Chunk", "Sample"),
        ("HAS_PATTERN", "Page", "UrlPattern"),
        ("HAS_PATH_ROOT", "Page", "UrlPath"),
        ("NEXT_SEGMENT", "UrlPath", "UrlPath"),
        ("LINKED_TO_PROMPT", "Page", "Prompt"),
        ("HAS_DETECTED_FIELD", "Page", "DetectedField"),
        ("WAS_USED_FOR", "Chunk", "Action"),
        ("HAS_ACTION", "Page", "Action"),

        # --- Phase 0A Relationships ---
        ("HAS_MEDIA", "DomSnapshot", "MediaAsset"),
        ("DERIVED_FROM", "SegmentEmbedding", "DomSnapshot"),
        ("MATCHES_PATTERN", "SegmentEmbedding", "SnapshotPatriciaIndex"),
        ("HAS_LABEL", "SegmentEmbedding", "NodeLabel"),
        ("HAS_MESSAGE", "ChatSession", "ChatMessage"),
        ("MSG_REFS_SNAPSHOT", "ChatMessage", "DomSnapshot"),
        ("MSG_REFS_SEGMENT", "ChatMessage", "SegmentEmbedding"),
        ("DESCRIBES", "OntologyFieldEmbedding", "DomNode"),
        ("FOCUSED_ON", "RetrievalStreamEntryDB", "DomNode"),
        ("PINNED", "RetrievalStreamEntryDB", "DomNode"),
        ("EMBEDS", "SegmentEmbedding", "Chunk"),

        # --- Phase 0D: Activity relationships ---
        ("CAUSED", "ActivityEntry", "ActivityEntry"),
        ("AFFECTED_NODE", "ActivityEntry", "DomNode"),

        # --- Phase 4A: Knowledge graph relationships ---
        ("ANNOTATES", "UserNote", "DomNode"),
        ("IS_A", "OntologyNode", "OntologyNode"),
        ("HAS_A", "OntologyNode", "OntologyNode"),
        ("PART_OF", "OntologyNode", "OntologyNode"),
        ("RELATES_TO_ONTOLOGY", "OntologyNode", "OntologyNode"),
        ("INCLUDES", "ContextAssembly", "UserNote"),
        ("INCLUDES_ONTOLOGY", "ContextAssembly", "OntologyNode"),
        ("INCLUDES_PIN", "ContextAssembly", "PinnedComponent"),

        # --- W4 / §8D.44: ConceptEdge ---
        # ConceptEdge carries rel-properties (edge_type, weight, ports,
        # etc.) and is created via the extended ``CREATE REL TABLE``
        # syntax in the dedicated block below the simple-rels loop.
        # See ``concept_edge_ddl`` further down in init_db.

        # --- Phase 9: Agentic relationships ---
        ("HAS_STEP", "FluidSession", "FluidStep"),
        ("HAS_AGENT", "FluidStep", "AgentRecord"),

        # --- Post-scan chunking ---
        ("HAS_CHUNK", "DomSnapshot", "ContentChunk"),

        # --- Persistent Patricia trie relationships ---
        ("HAS_TRIE_VERSION", "Page", "TrieVersion"),
        ("SNAPSHOT_OF", "TrieVersion", "DomSnapshot"),
        ("NEXT_VERSION", "TrieVersion", "TrieVersion"),
        # Trie-side version→pattern edge. Named HAS_TRIE_PATTERN to avoid
        # colliding with the legacy Page→UrlPattern HAS_PATTERN (Kuzu keys
        # rel tables by name alone, so two different (FROM,TO) pairs under
        # the same name are unsupported and the second CREATE silently
        # loses the race, which in turn caused persist_trie to raise
        # ``Binder exception: Query node v violates schema`` and Stage 10
        # ChunkInstance persistence to be skipped — the UMAP zero-samples
        # symptom).
        ("HAS_TRIE_PATTERN", "TrieVersion", "TriePattern"),
        ("PARENT_PATTERN", "TriePattern", "TriePattern"),
        ("CHUNK_PATTERN", "ContentChunk", "TriePattern"),
        ("LABELS_PATTERN", "PatternLabel", "TriePattern"),
        ("EMBEDDING_OF", "PatternEmbedding", "TriePattern"),

        # --- Phase 5 relationships ---
        ("INSTANCE_OF", "ChunkInstance", "TriePattern"),
        ("HAS_INSTANCE", "Page", "ChunkInstance"),
        ("HAS_PAGE_EMBEDDING", "Page", "PageEmbedding"),
        ("HAS_SEARCH_FIELD", "Domain", "SearchInputField"),
        ("HAS_PAGINATION_FIELD", "Domain", "PaginationField"),

        # --- Legacy DomNode relationships ---
        ("PARENT_OF", "DomNode", "DomNode"),
        ("HAS_SHADOW_ROOT", "DomNode", "DomNode"),
        ("ChildOf", "DomNode", "DomNode"),
        ("LcaLinkTo", "DomNode", "DomNode"),
        ("SequenceLink", "DomNode", "DomNode"),
    ]

    for name, src, dst in rels:
        try:
            conn.execute(f"CREATE REL TABLE {name}(FROM {src} TO {dst})")
            print(f"Created {name} table.")
        except Exception:
            pass  # Already exists or node tables for this rel not yet created

    # --- W4 / §8D.44: REL tables with properties ---
    # The generic (name, src, dst) loop above creates property-less rel
    # tables. ConceptEdge needs typed metadata on each edge — edge_id,
    # edge_type (one of §8A.2's typed labels OR §8D's port-binding
    # labels), source_port / target_port for port-binding wires,
    # weight for SIMILAR_TO cosine, and variable_name for the mid-edge
    # chip label (§8C.3). Kuzu supports rel-table properties via the
    # extended ``CREATE REL TABLE`` syntax. We create this separately
    # so the simple-loop above stays minimal.
    concept_edge_ddl = (
        "CREATE REL TABLE ConceptEdge("
        "FROM ConceptNode TO ConceptNode, "
        "edge_id STRING, "
        "edge_type STRING, "
        "source_port STRING, "
        "target_port STRING, "
        "weight DOUBLE, "
        "variable_name STRING, "
        "workspace_id STRING, "
        "created_at STRING"
        ")"
    )
    try:
        conn.execute(concept_edge_ddl)
        print("Created ConceptEdge table.")
    except Exception:
        pass  # Already exists; ignore.
