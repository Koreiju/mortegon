"""
pipeline.py — End-to-end scan → trie → chunks pipeline, Selenium-optional.

Given raw HTML (or a live Selenium driver), this module walks the full
content-tagging pipeline in one shot and returns a :class:`PipelineResult`
bundling every intermediate artifact so tests and the API can inspect or
persist them independently.

Flow:
    html_source  ──>  ShadowDOM
                 └─>  ContentTagger   ──>  TaggedContent
                 └─>  XPathTreeBuilder ──>  content_tree (nested dict)
                 └─>  build_trie_from_tree ──>  BuiltTrie
                 └─>  ChunkBuilder   ──>  List[Chunk]

Optional downstream stages (off by default, enable by flag):
    (render_instances)   └─>  render_all_chunks ──> [ChunkInstanceRender]
    (embed_instances)    └─>  ChunkInstanceEmbedder  — fills .embedding +
                                                       page-level vector
    (detect_signal_fields) └─> collect_signal_fields ──> search + pagination

For live scans, pass a driver and a URL — we invoke ShadowDOMScanner to
produce the HTML string, then run the same pipeline. The only side-effect
is optional persistence to Kuzu when ``persist=True`` (and a connection
is reachable via ``get_connection()``).
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from backend.dom.shadow_html_parser import ShadowDOM
from backend.dom.content_tagger import ContentTagger, TaggedContent
from backend.dom.xpath_tree_builder import XPathTreeBuilder
from backend.dom.trie_persistence import (
    BuiltTrie,
    build_trie_from_tree,
    persist_trie,
    get_latest_version_id,
    load_trie,
)
from backend.dom.trie_diff import TrieDiff, diff_tries
from backend.mapper.chunk_builder import (
    Chunk,
    ChunkBuilder,
    DEFAULT_CHAR_BUDGET,
    build_xpath_node_map,
    build_text_provider_from_dom,
    build_structure_provider_from_dom,
)
from backend.mapper.chunk_render import ChunkInstanceRender, render_all_chunks
from backend.services.chunk_instance_embedder import (
    ChunkInstanceEmbedder,
    EmbeddingBatchResult,
)
from backend.services.chunk_instance_persistence import (
    build_instance_rows,
    build_page_embedding_row,
    persist_chunk_instances,
    persist_page_embedding,
)
from backend.services.signal_fields import (
    SignalFieldRow,
    collect_signal_fields,
    persist_signal_fields,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Everything produced by one end-to-end pipeline run.

    The embed/render/signal-field fields are populated only when the
    corresponding ``run_pipeline`` flag is True — they default to empty
    so existing callers keep working without modification.
    """

    url: str
    snapshot_id: str
    html_source_len: int
    dom: ShadowDOM
    tagged: TaggedContent
    content_tree: Dict[str, Any]
    trie: BuiltTrie
    chunks: List[Chunk]
    previous_version_id: str = ""
    diff: Optional[TrieDiff] = None
    saved_to_kuzu: bool = False
    elapsed_ms: float = 0.0

    # Stage 9+ artifacts (render / embed / signal detection).
    instances: List[ChunkInstanceRender] = field(default_factory=list)
    embedding_batch: Optional[EmbeddingBatchResult] = None
    page_embedding: Optional[np.ndarray] = None
    search_fields: List[SignalFieldRow] = field(default_factory=list)
    pagination_fields: List[SignalFieldRow] = field(default_factory=list)

    def as_summary(self) -> Dict[str, Any]:
        """A compact dict suitable for logging or an API response."""
        return {
            "url": self.url,
            "snapshot_id": self.snapshot_id,
            "html_bytes": self.html_source_len,
            "content_xpaths": len(self.tagged.all_content_xpaths()),
            "tree_version_id": self.trie.version.version_id,
            "tree_pattern_count": self.trie.version.pattern_count,
            "content_pattern_count": self.trie.version.content_pattern_count,
            "chunks": len(self.chunks),
            "billboard_chunks": sum(1 for c in self.chunks if c.image_urls),
            "instances": len(self.instances),
            "unique_instance_texts": (
                self.embedding_batch.unique_text_count
                if self.embedding_batch else 0
            ),
            "has_page_embedding": self.page_embedding is not None,
            "search_fields": len(self.search_fields),
            "pagination_fields": len(self.pagination_fields),
            "elapsed_ms": round(self.elapsed_ms, 2),
            "diff": self.diff.summary() if self.diff else None,
            "saved_to_kuzu": self.saved_to_kuzu,
        }


def _default_snapshot_id(url: str) -> str:
    salt = uuid.uuid4().hex[:8]
    return hashlib.sha1(f"{url}|{salt}".encode("utf-8")).hexdigest()[:16]


def run_pipeline(
    html_source: str,
    url: str,
    *,
    snapshot_id: Optional[str] = None,
    char_budget: int = DEFAULT_CHAR_BUDGET,
    persist: bool = False,
    conn=None,
    parent_version_id: Optional[str] = None,
    local_html_root: Optional[str] = None,
    render_instances: bool = False,
    embed_instances: bool = False,
    detect_signal_fields: bool = False,
    embedder: Optional[ChunkInstanceEmbedder] = None,
) -> PipelineResult:
    """
    Run the full scan → trie → chunks pipeline on a pre-captured HTML source.

    Parameters
    ----------
    html_source:
        Raw HTML string. For live scans, obtain via
        ``ShadowDOMScanner(driver).scan(url)``.
    url:
        The source URL. Used as a key in Kuzu and for the snapshot label.
    snapshot_id:
        Optional deterministic snapshot id. Auto-generated if omitted.
    char_budget:
        Text-character budget per chunk (see ``ChunkBuilder``).
    persist:
        If True, write TrieVersion + TriePattern rows to Kuzu via
        ``persist_trie``. Requires a valid ``conn`` (falls back to
        ``backend.database.get_connection``).
    parent_version_id:
        Optional explicit parent version for the NEXT_VERSION lineage.
        If None and ``persist`` is True, the latest persisted version for
        the same URL is looked up automatically.
    local_html_root:
        If provided, the raw HTML source is saved on disk under this root
        keyed by snapshot_id. This is the "ground truth" store the plan
        mandates so the DB stays lean.
    render_instances:
        If True, produce :class:`ChunkInstanceRender` objects for every
        populated instance under every chunk (HTML + markdown-lite text).
        Required for ``embed_instances``.
    embed_instances:
        If True (implies ``render_instances``), run the nomic-v1
        :class:`ChunkInstanceEmbedder` over the rendered instances,
        populate ``.embedding`` in place, and compute the L2-normalized
        mean page-level embedding. When ``persist=True`` the instances
        and page embedding are upserted into Kuzu.
    detect_signal_fields:
        If True, run the search-input + pagination collectors and emit
        cross-URL signal fields coalesced on (domain, generalized_xpath).
    embedder:
        Optional pre-built :class:`ChunkInstanceEmbedder` to reuse a
        loaded GPU model across calls. Ignored unless ``embed_instances``.
    """
    started = time.perf_counter()
    snapshot_id = snapshot_id or _default_snapshot_id(url)

    # Per-stage wall-clock. Emitted at INFO when FIBER_PIPELINE_PROFILE is
    # truthy so the user can see where chunking/render time goes without
    # wiring up cProfile for every run.
    _profile = bool(os.environ.get("FIBER_PIPELINE_PROFILE"))
    _stage_times: Dict[str, float] = {}
    def _mark(stage: str, since: float) -> float:
        now = time.perf_counter()
        if _profile:
            _stage_times[stage] = (now - since) * 1000.0
        return now
    _t = started

    # Stage 1: parse HTML -> ShadowDOM.
    dom = ShadowDOM(html_source)
    _t = _mark("parse_shadow_dom", _t)

    # Stage 2: content tagging.
    tagger = ContentTagger(dom)
    tagged = tagger.tag()
    _t = _mark("content_tag", _t)

    # Stage 3: xpath tree (collapsed Patricia).
    tree_builder = XPathTreeBuilder()
    tree_builder.add_tagged_content(tagged)
    content_tree = tree_builder.build()
    _t = _mark("xpath_tree", _t)

    # Stage 4: flatten into persistent trie rows.
    resolved_parent = parent_version_id
    if persist and resolved_parent is None:
        try:
            _c = conn
            if _c is None:
                from backend.database import get_connection

                _c = get_connection()
            resolved_parent = get_latest_version_id(_c, url) or ""
        except Exception as exc:  # best-effort
            logger.debug("Pipeline: could not look up latest version (%s)", exc)
            resolved_parent = ""

    built = build_trie_from_tree(
        tree=content_tree,
        url=url,
        snapshot_id=snapshot_id,
        parent_version_id=resolved_parent or "",
    )
    _t = _mark("build_trie", _t)

    # Stage 5: chunking.
    # One O(N) DOM walk shared by all three consumers (text provider,
    # structure provider, render_all_chunks) — avoids the legacy triple traversal.
    _xpath_map = build_xpath_node_map(dom)
    text_provider = build_text_provider_from_dom(dom, xpath_map=_xpath_map)
    structure_provider = build_structure_provider_from_dom(dom, xpath_map=_xpath_map)
    _t = _mark("build_xpath_map", _t)
    # ``all_tags`` is what lets ChunkBuilder populate per-chunk
    # ``extraction_trie`` (the per-instance data-address schema).
    # Without it the trie is silently empty and downstream consumers
    # like ``chunk_query.query_chunk`` find matching instances but no
    # fields to extract, so every instance is returned as ``{}``.
    # ``mapper.DomMapper.chunk`` already threads this; the headless
    # pipeline needs to match.
    chunks = ChunkBuilder(
        content_tree,
        text_provider,
        char_budget=char_budget,
        all_tags=tagged.all_tags,
        structure_provider=structure_provider,
    ).build(snapshot_id=snapshot_id)
    _t = _mark("chunk_build", _t)

    # Stage 5b: cross-fill per-pattern char_count from chunks so the DB
    # carries live text measurements (not just zeros).
    for ch in chunks:
        row = built.by_pattern_key.get(ch.pattern)
        if row is not None:
            row.char_count = int(ch.char_count)
    built.version.total_char_count = sum(r.char_count for r in built.patterns)

    # Stage 6: optional persistence.
    saved = False
    diff: Optional[TrieDiff] = None
    if persist:
        try:
            _c = conn
            if _c is None:
                from backend.database import get_connection

                _c = get_connection()

            prior: Optional[BuiltTrie] = None
            if resolved_parent:
                prior = load_trie(_c, resolved_parent)
            diff = diff_tries(prior, built)

            persist_trie(_c, built)
            saved = True
        except Exception:
            logger.exception("Pipeline: persist_trie failed")

    # Stage 7: optional ground-truth HTML save.
    if local_html_root:
        try:
            os.makedirs(local_html_root, exist_ok=True)
            html_path = os.path.join(local_html_root, f"{snapshot_id}.html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(html_source)
        except Exception:
            logger.exception("Pipeline: local HTML save failed")

    # Stage 8: optional per-instance render + embed.
    instances: List[ChunkInstanceRender] = []
    embedding_batch: Optional[EmbeddingBatchResult] = None
    page_vec: Optional[np.ndarray] = None

    if render_instances or embed_instances:
        try:
            instances = render_all_chunks(chunks, dom, xpath_map=_xpath_map)
            logger.info(
                "Pipeline: rendered %d non-empty instance(s) across %d chunk(s)",
                len(instances), len(chunks),
            )
        except Exception:
            logger.exception("Pipeline: render_all_chunks failed")
            instances = []
        _t = _mark("render_instances", _t)

    if embed_instances and instances:
        try:
            active_embedder = embedder or ChunkInstanceEmbedder()
            embedding_batch = active_embedder.embed_instances(instances)
            page_vec = embedding_batch.page_embedding
            logger.info(
                "Pipeline: embedded %d instance(s) via %d unique text(s)",
                embedding_batch.embedded_count,
                embedding_batch.unique_text_count,
            )
        except Exception:
            logger.exception("Pipeline: ChunkInstanceEmbedder failed")
            embedding_batch = None
            page_vec = None
        _t = _mark("embed_instances", _t)

    # Stage 9: optional signal-field detection (search + pagination).
    search_fields: List[SignalFieldRow] = []
    pagination_fields: List[SignalFieldRow] = []
    if detect_signal_fields:
        try:
            search_fields, pagination_fields = collect_signal_fields(dom, url)
        except Exception:
            logger.exception("Pipeline: collect_signal_fields failed")
            search_fields, pagination_fields = [], []

    # Stage 10: optional persistence of new artifacts (gated on ``persist``).
    if persist and saved:
        try:
            _c = conn
            if _c is None:
                from backend.database import get_connection

                _c = get_connection()
            if instances:
                pattern_id_by_key = {
                    key: row.pattern_id
                    for key, row in built.by_pattern_key.items()
                }
                # Only persist rows that actually have embeddings — the
                # schema requires a 768-dim FLOAT array.
                if embed_instances and embedding_batch is not None:
                    inst_rows = build_instance_rows(
                        instances,
                        version_id=built.version.version_id,
                        url=url,
                        snapshot_id=snapshot_id,
                        pattern_id_by_key=pattern_id_by_key,
                    )
                    if inst_rows:
                        n = persist_chunk_instances(_c, inst_rows)
                        logger.info("Pipeline: persisted %d ChunkInstance row(s)", n)

                    if page_vec is not None:
                        page_row = build_page_embedding_row(
                            version_id=built.version.version_id,
                            url=url,
                            snapshot_id=snapshot_id,
                            page_vector=page_vec,
                            instance_count=len(inst_rows),
                        )
                        persist_page_embedding(_c, page_row)
                        logger.info("Pipeline: persisted PageEmbedding for %s", url)

            if detect_signal_fields and (search_fields or pagination_fields):
                sc, pc = persist_signal_fields(
                    _c, search_fields, pagination_fields,
                )
                logger.info(
                    "Pipeline: persisted %d search / %d pagination field(s)",
                    sc, pc,
                )
        except Exception:
            logger.exception("Pipeline: downstream-artifact persist failed")

    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if _profile and _stage_times:
        breakdown = " | ".join(
            f"{k}={v:.1f}ms" for k, v in _stage_times.items()
        )
        logger.info("Pipeline profile: total=%.1fms | %s", elapsed_ms, breakdown)

    return PipelineResult(
        url=url,
        snapshot_id=snapshot_id,
        html_source_len=len(html_source),
        dom=dom,
        tagged=tagged,
        content_tree=content_tree,
        trie=built,
        chunks=chunks,
        previous_version_id=resolved_parent or "",
        diff=diff,
        saved_to_kuzu=saved,
        elapsed_ms=elapsed_ms,
        instances=instances,
        embedding_batch=embedding_batch,
        page_embedding=page_vec,
        search_fields=search_fields,
        pagination_fields=pagination_fields,
    )


def run_pipeline_live(
    driver,
    url: str,
    *,
    max_duration: int = 60,
    pause: float = 4.0,
    persist: bool = True,
    conn=None,
    char_budget: int = DEFAULT_CHAR_BUDGET,
    local_html_root: Optional[str] = None,
    single_pass: bool = False,
    render_instances: bool = False,
    embed_instances: bool = False,
    detect_signal_fields: bool = False,
    embedder: Optional[ChunkInstanceEmbedder] = None,
) -> PipelineResult:
    """Live-scan a URL via Selenium, then run the shared pipeline.

    ``single_pass=True`` uses ``ShadowDOMScanner.scan_single`` (no scroll
    loop) which is faster and sufficient for pages that fit above the
    fold. The default drives the full scroll+merge loop via ``scan``.

    All render/embed/signal-field flags are forwarded verbatim to
    :func:`run_pipeline` — see that function's docstring for details.
    """
    from backend.dom.scanner import ShadowDOMScanner, serialize_to_html

    scanner = ShadowDOMScanner(driver)

    if single_pass:
        html_source, _tree = scanner.scan_single(url)
    else:
        # scan() is a generator yielding (master_tree, added_nodes) — we
        # drain it so the master_tree is fully merged, then serialize once.
        last_tree: Any = None
        for master_tree, _added in scanner.scan(url, max_duration=max_duration, pause=pause):
            last_tree = master_tree
        html_source = serialize_to_html(last_tree) if last_tree else ""

    return run_pipeline(
        html_source=html_source,
        url=url,
        char_budget=char_budget,
        persist=persist,
        conn=conn,
        local_html_root=local_html_root,
        render_instances=render_instances,
        embed_instances=embed_instances,
        detect_signal_fields=detect_signal_fields,
        embedder=embedder,
    )
