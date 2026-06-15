"""
test_chunk_instance_pipeline.py — Covers the new per-instance render / embed
/ retrieve / signal-field stack built on top of the scan→trie→chunks pipeline.

Deterministic (no Selenium, no live GPU). The :class:`EmbeddingService` is
mocked where real GPT4All would normally run, and Kuzu tests spin up a
throwaway in-memory DB with the minimum schema each module needs.
"""

from __future__ import annotations

import hashlib
import os
import sys
from typing import List
from unittest.mock import MagicMock

import numpy as np
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

# --- Imports from the modules under test -----------------------------------
from backend.dom.shadow_html_parser import ShadowDOM
from backend.dom.chunk_query import InstanceResult, query_chunk
from backend.dom.pipeline import run_pipeline
from backend.mapper.chunk_render import (
    ChunkInstanceRender,
    extract_instance_html,
    html_to_rendered_text,
    render_all_chunks,
    render_chunk_instances,
    render_summary,
)
from backend.services.chunk_instance_embedder import (
    ChunkInstanceEmbedder,
    EmbeddingBatchResult,
)
from backend.services.chunk_instance_persistence import (
    ChunkInstanceRow,
    PageEmbeddingRow,
    build_instance_rows,
    build_page_embedding_row,
    load_all_instances,
    load_all_page_embeddings,
    load_instance_by_id,
    load_instances_by_url,
    load_instances_by_urls,
    load_page_embedding,
    persist_chunk_instances,
    persist_page_embedding,
)
from backend.services.chunk_retrieval import (
    retrieve_instances_by_urls,
    retrieve_pages_by_query,
    retrieve_with_drilldown,
)
from backend.services.embedding_service import (
    EmbeddingService,
    cosine_similarity,
    mean_pool,
)
from backend.services.signal_fields import (
    SignalFieldRow,
    collect_signal_fields,
    load_pagination_fields,
    load_search_fields,
    persist_signal_fields,
)


# ===========================================================================
# Fixtures
# ===========================================================================


HTML_TAROT_LIKE = """
<!doctype html>
<html><head>
  <title>Daily Tarot</title>
</head><body>
  <nav>
    <a href="/horoscopes">Horoscopes</a>
    <a href="/tarot">Tarot</a>
  </nav>
  <main>
    <section class="card-grid">
      <article class="card">
        <img src="/img/fool.png" alt="The Fool"/>
        <h2>The Fool</h2>
        <p>New beginnings, spontaneity, a free spirit.</p>
        <a href="/tarot/fool">Read more</a>
      </article>
      <article class="card">
        <img src="/img/magician.png" alt="The Magician"/>
        <h2>The Magician</h2>
        <p>Manifestation, resourcefulness, power, inspired action.</p>
        <a href="/tarot/magician">Read more</a>
      </article>
      <article class="card">
        <img src="/img/priestess.png" alt="The High Priestess"/>
        <h2>The High Priestess</h2>
        <p>Intuition, sacred knowledge, divine feminine.</p>
        <a href="/tarot/priestess">Read more</a>
      </article>
    </section>
    <section class="filters">
      <form>
        <label for="q">Search readings</label>
        <input id="q" name="q" type="search"
               placeholder="love, career, health..." />
        <button type="submit">Search</button>
      </form>
    </section>
    <nav class="pager">
      <a href="?page=2" rel="next">Next</a>
      <a href="?page=0" rel="prev">Previous</a>
    </nav>
  </main>
</body></html>
""".strip()


class _DeterministicEmbedder:
    """Drop-in replacement for :class:`EmbeddingService` in tests.

    ``embed_texts`` returns a stable vector per text — derived from the
    SHA-1 of the string so repeated calls for the same string give the
    same row. This lets us assert dedup semantics end-to-end without
    needing GPT4All.
    """

    def __init__(self, dim: int = 16):
        self.dim = dim
        self.calls_texts: List[List[str]] = []
        self.calls_query: List[str] = []

    def _vec_for(self, text: str) -> np.ndarray:
        h = hashlib.sha1(text.encode("utf-8")).digest()
        # Spread bytes across dim dims as floats in [-1, 1].
        vec = np.zeros(self.dim, dtype=np.float32)
        for i in range(self.dim):
            vec[i] = ((h[i % len(h)] / 255.0) - 0.5) * 2.0
        # L2-normalize so cosine works sensibly.
        n = np.linalg.norm(vec)
        if n > 0:
            vec = vec / n
        return vec

    def embed_texts(self, texts, *, prefix: str = "search_document") -> np.ndarray:
        self.calls_texts.append(list(texts))
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self._vec_for(t) for t in texts], axis=0)

    def embed_query(self, query: str) -> np.ndarray:
        self.calls_query.append(query)
        return self._vec_for(query)


@pytest.fixture()
def tarot_result():
    """Full :class:`PipelineResult` over the tarot fixture (no persist).

    ``char_budget=400`` forces the top-down chunker to recurse past the
    `<section class="card-grid">` level and emit one chunk per
    `<article>` card. The default production budget (HARD_CHAR_LIMIT)
    would happily swallow this tiny fixture as a single `/html` chunk
    — realistic for a 1.4 KB page, useless as a unit test of card-
    level granularity.
    """
    return run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
        char_budget=400,
    )


@pytest.fixture()
def tarot_dom():
    return ShadowDOM(HTML_TAROT_LIKE)


@pytest.fixture()
def mock_embedder():
    return _DeterministicEmbedder()


# ===========================================================================
# 1. chunk_query regression — empty instances must be dropped
# ===========================================================================


def test_query_chunk_drops_empty_instances(tarot_result, tarot_dom):
    """
    Before the fix, shape-varying members surfaced as blank ``{}`` dicts
    between populated instances. Iterating the card chunk on the tarot
    fixture should yield exactly 3 non-empty results — no blanks.
    """
    card_chunk = next(
        c for c in tarot_result.chunks
        if c.pattern.rstrip("/").endswith("/article")
    )
    results: List[InstanceResult] = query_chunk(
        tarot_dom, card_chunk.pattern, card_chunk.extraction_trie,
    )
    assert len(results) == 3
    for inst in results:
        assert bool(inst)
        assert not inst.is_empty()
        assert inst.fields, "populated InstanceResult should have fields"


# ===========================================================================
# 2. chunk_render — HTML serialization + markdown-lite + summary
# ===========================================================================


def test_html_to_rendered_text_inlines_anchor_text():
    html = (
        '<article><h2>The Fool</h2>'
        '<p>New beginnings, <a href="/x">read more</a>.</p></article>'
    )
    text = html_to_rendered_text(html)
    # Anchor collapsed to its text only.
    assert "read more" in text
    assert "/x" not in text
    # Block structure — headline + paragraph should survive on separate lines.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert any("The Fool" in ln for ln in lines)
    assert any("New beginnings" in ln for ln in lines)


def test_html_to_rendered_text_drops_scripts_and_styles():
    html = (
        '<div>Hello'
        '<script>alert(1)</script>'
        '<style>.x{color:red}</style>'
        '<p>World</p></div>'
    )
    text = html_to_rendered_text(html)
    assert "alert" not in text
    assert "color:red" not in text
    assert "Hello" in text and "World" in text


def test_html_to_rendered_text_list_bullets():
    text = html_to_rendered_text("<ul><li>One</li><li>Two</li></ul>")
    # Every <li> gets a "- " prefix.
    assert "- One" in text
    assert "- Two" in text


def test_html_to_rendered_text_alt_fallback_for_void_elements():
    text = html_to_rendered_text('<p><img src="/x.png" alt="A cat"/></p>')
    assert "A cat" in text


def test_extract_instance_html_strips_event_handlers():
    html = '<div onclick="pwn()"><a href="/x" onmouseover="bad()">hi</a></div>'
    dom = ShadowDOM(html)
    # ShadowDOM parses the bare fragment as /div (no implicit html/body wrap).
    serialized = extract_instance_html(dom, "/div")
    assert serialized, "failed to resolve injected div by xpath"
    assert "onclick" not in serialized
    assert "onmouseover" not in serialized
    assert 'href="/x"' in serialized  # non-event attrs preserved


def test_render_chunk_instances_populates_html_and_text(tarot_result, tarot_dom):
    card_chunk = next(
        c for c in tarot_result.chunks
        if c.pattern.rstrip("/").endswith("/article")
    )
    rendered = render_chunk_instances(card_chunk, tarot_dom)
    assert len(rendered) == 3
    # Each card should have distinct HTML and text.
    htmls = {r.html_raw for r in rendered}
    texts = {r.rendered_text for r in rendered}
    assert len(htmls) == 3
    assert len(texts) == 3
    # The Fool should only appear in one card's text.
    fool_matches = [r for r in rendered if "The Fool" in r.rendered_text]
    assert len(fool_matches) == 1
    # html_raw preserves resource URLs.
    assert "/img/fool.png" in fool_matches[0].html_raw
    # rendered_text drops the href but keeps the anchor label.
    assert "/tarot/fool" not in fool_matches[0].rendered_text
    assert "Read more" in fool_matches[0].rendered_text


def test_render_summary_matches_original_presentation(tarot_result, tarot_dom):
    card_chunk = next(
        c for c in tarot_result.chunks
        if c.pattern.rstrip("/").endswith("/article")
    )
    rendered = render_chunk_instances(card_chunk, tarot_dom)
    summary = render_summary(card_chunk, instances=rendered)
    # Header
    assert summary.startswith("[Chunk] Pattern: ")
    assert "Found 3 non-empty instance" in summary
    # Three instance rows, all numbered 1-based.
    assert "  Instance 1 @" in summary
    assert "  Instance 2 @" in summary
    assert "  Instance 3 @" in summary


def test_render_all_chunks_flattens_across_chunks(tarot_result, tarot_dom):
    rendered = render_all_chunks(tarot_result.chunks, tarot_dom)
    # At least the 3 cards should survive.
    assert len(rendered) >= 3
    # Every survivor has a non-empty rendered_text (no blank rows).
    assert all(r.rendered_text.strip() for r in rendered)


def test_instance_id_is_deterministic():
    r = ChunkInstanceRender(
        chunk_id="c1", instance_idx=0, pattern="/a/b",
        absolute_xpath="/html/body/div[2]", html_raw="<div/>",
        rendered_text="hi",
    )
    a = r.instance_id("v1")
    b = r.instance_id("v1")
    c = r.instance_id("v2")
    assert a == b and a != c and len(a) == 20


# ===========================================================================
# 3. EmbeddingService helpers — cosine + mean_pool
# ===========================================================================


def test_cosine_similarity_basic():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0], dtype=np.float32)
    assert cosine_similarity(a, b) == pytest.approx(1.0)
    c = np.array([0.0, 1.0], dtype=np.float32)
    assert cosine_similarity(a, c) == pytest.approx(0.0, abs=1e-6)
    d = np.array([-1.0, 0.0], dtype=np.float32)
    assert cosine_similarity(a, d) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_returns_zero():
    a = np.array([1.0, 0.0], dtype=np.float32)
    z = np.array([0.0, 0.0], dtype=np.float32)
    assert cosine_similarity(a, z) == 0.0


def test_mean_pool_normalizes_output():
    vecs = [
        np.array([1.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0, 0.0], dtype=np.float32),
    ]
    out = mean_pool(vecs)
    assert out is not None
    assert np.linalg.norm(out) == pytest.approx(1.0, abs=1e-5)


def test_mean_pool_empty_returns_none():
    assert mean_pool([]) is None
    assert mean_pool([None]) is None


# ===========================================================================
# 4. ChunkInstanceEmbedder — dedupe + page-level mean
# ===========================================================================


def _fake_render(text: str, xpath: str) -> ChunkInstanceRender:
    return ChunkInstanceRender(
        chunk_id="c", instance_idx=0, pattern="/a",
        absolute_xpath=xpath, html_raw=f"<div>{text}</div>",
        rendered_text=text,
    )


def test_chunk_instance_embedder_dedupes_repeat_text(mock_embedder):
    instances = [
        _fake_render("alpha", "/a[1]"),
        _fake_render("alpha", "/a[2]"),  # repeat
        _fake_render("beta", "/a[3]"),
    ]
    embedder = ChunkInstanceEmbedder(embedder=mock_embedder)
    result = embedder.embed_instances(instances)

    # Only the 2 unique texts should have been passed to the model.
    assert len(mock_embedder.calls_texts) == 1
    unique_batch = mock_embedder.calls_texts[0]
    assert set(unique_batch) == {"alpha", "beta"}
    assert result.unique_text_count == 2
    assert result.embedded_count == 3

    # Both alpha instances share the same vector.
    assert instances[0].embedding == instances[1].embedding
    # Beta is different.
    assert instances[0].embedding != instances[2].embedding
    # Page vec is populated + normalized.
    assert result.page_embedding is not None
    assert np.linalg.norm(result.page_embedding) == pytest.approx(1.0, abs=1e-5)


def test_chunk_instance_embedder_empty_input():
    embedder = ChunkInstanceEmbedder(embedder=_DeterministicEmbedder())
    out = embedder.embed_instances([])
    assert out.embedded_count == 0
    assert out.page_embedding is None


# ===========================================================================
# 5. chunk_instance_persistence — Kuzu round-trip
# ===========================================================================


@pytest.fixture()
def instance_kuzu_conn():
    """Minimal schema covering ChunkInstance + PageEmbedding + Page."""
    import kuzu

    # §R.9 — janitor-managed throwaway dir (canonical prefix + atexit net).
    from backend.services.db_janitor import temp_db_dir

    with temp_db_dir("chunk_inst") as tmp:
        db_path = os.path.join(tmp, "db")
        db = kuzu.Database(db_path)
        conn = kuzu.Connection(db)
        stmts = [
            "CREATE NODE TABLE Page(url STRING, PRIMARY KEY(url))",
            "CREATE NODE TABLE ChunkInstance("
            "instance_id STRING, chunk_id STRING, pattern_id STRING, "
            "version_id STRING, url STRING, snapshot_id STRING, "
            "absolute_xpath STRING, html_raw STRING, rendered_text STRING, "
            "fields_json STRING, embedding FLOAT[16], created_at STRING, "
            "PRIMARY KEY(instance_id))",
            "CREATE NODE TABLE PageEmbedding("
            "page_embedding_id STRING, url STRING, version_id STRING, "
            "snapshot_id STRING, instance_count INT64, embedding FLOAT[16], "
            "created_at STRING, PRIMARY KEY(page_embedding_id))",
            "CREATE REL TABLE HAS_INSTANCE(FROM Page TO ChunkInstance)",
            "CREATE REL TABLE HAS_PAGE_EMBEDDING(FROM Page TO PageEmbedding)",
        ]
        for s in stmts:
            conn.execute(s)
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass
            try:
                db.close()
            except Exception:
                pass


def _make_rows(url: str, n: int = 2, dim: int = 16) -> List[ChunkInstanceRow]:
    rows = []
    for i in range(n):
        rows.append(
            ChunkInstanceRow(
                instance_id=f"iid_{i}",
                chunk_id="c1",
                pattern_id="p1",
                version_id="v1",
                url=url,
                snapshot_id="s1",
                absolute_xpath=f"/html/body/div[{i+1}]",
                html_raw=f"<div>hi{i}</div>",
                rendered_text=f"hi{i}",
                fields_json="{}",
                embedding=[float((i + 1) / dim)] * dim,
                created_at="2026-04-20T00:00:00Z",
            )
        )
    return rows


def test_persist_and_load_instances_roundtrip(instance_kuzu_conn):
    url = "https://x/_inst"
    # Pre-insert Page rows so HAS_INSTANCE can MERGE.
    instance_kuzu_conn.execute(
        "CREATE (p:Page {url: $u})", parameters={"u": url},
    )

    rows = _make_rows(url)
    n = persist_chunk_instances(instance_kuzu_conn, rows)
    assert n == 2

    all_rows = load_all_instances(instance_kuzu_conn)
    assert len(all_rows) == 2
    got_by_url = load_instances_by_url(instance_kuzu_conn, url)
    assert len(got_by_url) == 2
    got_by_id = load_instance_by_id(instance_kuzu_conn, "iid_0")
    assert got_by_id is not None
    assert got_by_id.rendered_text == "hi0"
    assert len(got_by_id.embedding) == 16

    # Multi-URL loader.
    got_multi = load_instances_by_urls(instance_kuzu_conn, [url, "https://other"])
    assert len(got_multi) == 2


def test_instance_upsert_is_idempotent(instance_kuzu_conn):
    url = "https://x/_dup"
    instance_kuzu_conn.execute(
        "CREATE (p:Page {url: $u})", parameters={"u": url},
    )
    rows = _make_rows(url, n=1)
    persist_chunk_instances(instance_kuzu_conn, rows)
    # Change the text and persist again.
    rows[0].rendered_text = "hi_updated"
    persist_chunk_instances(instance_kuzu_conn, rows)

    got = load_all_instances(instance_kuzu_conn)
    assert len(got) == 1  # no duplicate
    assert got[0].rendered_text == "hi_updated"


def test_page_embedding_persist_and_load(instance_kuzu_conn):
    url = "https://x/_pe"
    instance_kuzu_conn.execute(
        "CREATE (p:Page {url: $u})", parameters={"u": url},
    )
    page_row = build_page_embedding_row(
        version_id="v1", url=url, snapshot_id="s1",
        page_vector=np.asarray([0.1] * 16, dtype=np.float32),
        instance_count=3,
    )
    persist_page_embedding(instance_kuzu_conn, page_row)
    loaded = load_page_embedding(instance_kuzu_conn, url)
    assert loaded is not None
    assert loaded.instance_count == 3
    assert len(loaded.embedding) == 16

    # load_all returns exactly one.
    all_pe = load_all_page_embeddings(instance_kuzu_conn)
    assert len(all_pe) == 1 and all_pe[0].url == url


def test_build_instance_rows_lazy_embedding_placeholder(tarot_result, tarot_dom):
    rendered = render_all_chunks(tarot_result.chunks, tarot_dom)
    # Embeddings are LAZY (chunk_instance_persistence.build_instance_rows):
    # unembedded instances still materialise as rows, carrying the
    # canonical-size zero-vector placeholder so the FLOAT[1024] binder
    # never sees an empty list. Downstream semantic consumers gate on the
    # placeholder; sparse TF-IDF retrieval proceeds without the vector.
    rows = build_instance_rows(
        rendered,
        version_id=tarot_result.trie.version.version_id,
        url=tarot_result.url,
        snapshot_id=tarot_result.snapshot_id,
        pattern_id_by_key={
            k: v.pattern_id for k, v in tarot_result.trie.by_pattern_key.items()
        },
    )
    assert len(rows) == len(rendered)
    assert all(len(r.embedding) == 1024 for r in rows)
    assert all(not any(r.embedding) for r in rows)  # all-zero placeholder

    # Now fake-embed and try again.
    for r in rendered:
        r.embedding = [0.01] * 16
    rows = build_instance_rows(
        rendered,
        version_id=tarot_result.trie.version.version_id,
        url=tarot_result.url,
        snapshot_id=tarot_result.snapshot_id,
        pattern_id_by_key={
            k: v.pattern_id for k, v in tarot_result.trie.by_pattern_key.items()
        },
    )
    assert len(rows) == len(rendered)
    # At least the three article patterns should resolve to a real pattern_id.
    article_rows = [
        r for r in rows if r.absolute_xpath.rsplit("/", 1)[-1].startswith("article")
    ]
    assert article_rows
    assert all(r.pattern_id for r in article_rows)


# ===========================================================================
# 6. signal_fields — coalesce on (domain, generalized_xpath)
# ===========================================================================


@pytest.fixture()
def signal_kuzu_conn():
    import kuzu

    # §R.9 — janitor-managed throwaway dir.
    from backend.services.db_janitor import temp_db_dir

    with temp_db_dir("signal_fields") as tmp:
        yield from _signal_kuzu_conn_impl(tmp)


def _signal_kuzu_conn_impl(tmp):
    import kuzu

    db_path = os.path.join(tmp, "db")
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    stmts = [
        "CREATE NODE TABLE Domain(domain STRING, PRIMARY KEY(domain))",
        "CREATE NODE TABLE SearchInputField("
        "field_id STRING, domain STRING, generalized_xpath STRING, "
        "last_seen_url STRING, last_seen_absolute_xpath STRING, "
        "tag STRING, text_hint STRING, attributes_json STRING, "
        "score INT64, first_seen STRING, last_seen STRING, "
        "PRIMARY KEY(field_id))",
        "CREATE NODE TABLE PaginationField("
        "field_id STRING, domain STRING, generalized_xpath STRING, "
        "last_seen_url STRING, last_seen_absolute_xpath STRING, "
        "tag STRING, text_hint STRING, attributes_json STRING, "
        "score INT64, first_seen STRING, last_seen STRING, "
        "PRIMARY KEY(field_id))",
        "CREATE REL TABLE HAS_SEARCH_FIELD(FROM Domain TO SearchInputField)",
        "CREATE REL TABLE HAS_PAGINATION_FIELD(FROM Domain TO PaginationField)",
    ]
    for s in stmts:
        conn.execute(s)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass


def test_collect_signal_fields_finds_search_and_pagination(tarot_dom):
    url = "https://www.tarot.com/_test_fixture"
    search, paginate = collect_signal_fields(tarot_dom, url)
    assert search, "search input not detected — fixture has input[type=search]"
    # At least one pagination candidate (Next/Previous links).
    assert paginate, "pagination links not detected"
    # Domain must coalesce correctly.
    for row in search + paginate:
        assert row.domain == "www.tarot.com"


def test_persist_signal_fields_preserves_first_seen(signal_kuzu_conn):
    url = "https://www.tarot.com/a"
    dom = ShadowDOM(HTML_TAROT_LIKE)
    search_v1, paginate_v1 = collect_signal_fields(dom, url)
    sc1, pc1 = persist_signal_fields(signal_kuzu_conn, search_v1, paginate_v1)
    assert sc1 == len(search_v1)
    assert pc1 == len(paginate_v1)

    loaded_v1 = load_search_fields(signal_kuzu_conn, domain="www.tarot.com")
    assert loaded_v1
    first_seen_v1 = {r.field_id: r.first_seen for r in loaded_v1}

    # Second scan with a new last_seen stamp. first_seen should stick.
    search_v2, paginate_v2 = collect_signal_fields(
        dom, "https://www.tarot.com/b",
    )
    # Mutate last_seen timestamps so the upsert must differentiate them.
    for row in search_v2:
        row.last_seen = "2099-01-01T00:00:00Z"
    persist_signal_fields(signal_kuzu_conn, search_v2, paginate_v2)

    loaded_v2 = load_search_fields(signal_kuzu_conn, domain="www.tarot.com")
    for r in loaded_v2:
        if r.field_id in first_seen_v1:
            assert r.first_seen == first_seen_v1[r.field_id]
            assert r.last_seen == "2099-01-01T00:00:00Z"


# ===========================================================================
# 7. chunk_retrieval — URL scoping + query ranking with mock embedder
# ===========================================================================


def _insert_seed_instances(conn, url: str, count: int = 3, dim: int = 16):
    """Insert ``count`` ChunkInstance rows with distinguishable embeddings.

    Embedding dim[i] gets 1.0 for the i-th row, others 0 — so cosine
    similarity against a query vector with dim[0]=1 picks row 0.
    """
    conn.execute("CREATE (p:Page {url: $u})", parameters={"u": url})
    for i in range(count):
        emb = [0.0] * dim
        emb[i % dim] = 1.0
        conn.execute(
            "CREATE (i:ChunkInstance {"
            "instance_id: $iid, chunk_id: 'c', pattern_id: 'p', "
            "version_id: 'v', url: $url, snapshot_id: 's', "
            "absolute_xpath: $xp, html_raw: $hr, rendered_text: $rt, "
            "fields_json: '{}', embedding: $emb, created_at: $ca})",
            parameters={
                "iid": f"iid_{i}",
                "url": url,
                "xp": f"/html/body/div[{i+1}]",
                "hr": f"<div>hi{i}</div>",
                "rt": f"hi{i}",
                "emb": emb,
                "ca": f"2026-04-0{i+1}T00:00:00Z",
            },
        )


def test_retrieve_instances_by_urls_no_query(instance_kuzu_conn):
    url = "https://x/_retr"
    _insert_seed_instances(instance_kuzu_conn, url, count=3)

    hits = retrieve_instances_by_urls(
        instance_kuzu_conn, [url], query=None, limit=0,
    )
    assert len(hits) == 3
    # Newest first (iid_2 has the latest created_at).
    assert hits[0].instance_id == "iid_2"
    # HTML is surfaced with each hit.
    assert hits[0].html_raw


def test_retrieve_instances_by_urls_empty_input_returns_empty():
    assert retrieve_instances_by_urls(MagicMock(), []) == []
    assert retrieve_instances_by_urls(MagicMock(), [None, ""]) == []


def test_retrieve_instances_by_urls_with_query(instance_kuzu_conn, mock_embedder):
    """Query path: picks the row whose embedding aligns with the query vec."""
    url = "https://x/_retr2"
    _insert_seed_instances(instance_kuzu_conn, url, count=3)

    # Build a query vec that strongly matches iid_0 (dim[0] = 1).
    query_text = "_fake_query_that_we_will_patch_"
    target_vec = np.zeros(16, dtype=np.float32)
    target_vec[0] = 1.0
    mock_embedder.embed_query = MagicMock(return_value=target_vec)  # type: ignore[method-assign]

    hits = retrieve_instances_by_urls(
        instance_kuzu_conn, [url], query=query_text, limit=3,
        embedder=mock_embedder,
    )
    assert hits, "query path returned no hits"
    # iid_0 should rank first (cos=1.0 vs ~0 for the others).
    assert hits[0].instance_id == "iid_0"
    assert hits[0].score >= hits[-1].score


def test_retrieve_pages_by_query_ranks_by_cosine(instance_kuzu_conn, mock_embedder):
    """PageEmbedding URL-level retrieval uses the same Kuzu cosine UDF."""
    # Two URLs with opposing page vectors.
    url_a = "https://x/_pa"
    url_b = "https://x/_pb"
    instance_kuzu_conn.execute("CREATE (p:Page {url: $u})", parameters={"u": url_a})
    instance_kuzu_conn.execute("CREATE (p:Page {url: $u})", parameters={"u": url_b})
    vec_a = [0.0] * 16
    vec_a[0] = 1.0
    vec_b = [0.0] * 16
    vec_b[1] = 1.0
    for peid, url, vec in (("pe_a", url_a, vec_a), ("pe_b", url_b, vec_b)):
        instance_kuzu_conn.execute(
            "CREATE (e:PageEmbedding {page_embedding_id: $pid, url: $url, "
            "version_id: 'v', snapshot_id: 's', instance_count: 2, "
            "embedding: $emb, created_at: '2026'})",
            parameters={"pid": peid, "url": url, "emb": vec},
        )

    query_vec = np.array([1.0] + [0.0] * 15, dtype=np.float32)
    mock_embedder.embed_query = MagicMock(return_value=query_vec)  # type: ignore[method-assign]
    hits = retrieve_pages_by_query(
        instance_kuzu_conn, "anything", limit=2, embedder=mock_embedder,
    )
    assert hits[0].url == url_a
    assert hits[0].score > hits[1].score


# ===========================================================================
# 8. Pipeline wiring — flags off == no-op, flags on == populated
# ===========================================================================


def test_pipeline_flags_default_off_keeps_legacy_behavior():
    """Existing callers must not see the new artifacts unless they opt in."""
    result = run_pipeline(HTML_TAROT_LIKE, url="https://x/_p1", persist=False)
    assert result.instances == []
    assert result.embedding_batch is None
    assert result.page_embedding is None
    assert result.search_fields == []
    assert result.pagination_fields == []


def test_pipeline_render_instances_flag_populates_renders():
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://x/_p2",
        persist=False,
        render_instances=True,
    )
    assert result.instances, "render_instances=True must yield renders"
    assert all(r.html_raw and r.rendered_text for r in result.instances)
    # Embedding path still off.
    assert result.embedding_batch is None
    assert result.page_embedding is None


def test_pipeline_embed_instances_flag_populates_vectors(mock_embedder):
    """Pass a mock embedder via the ChunkInstanceEmbedder shim."""
    inner = ChunkInstanceEmbedder(embedder=mock_embedder)
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://x/_p3",
        persist=False,
        embed_instances=True,
        embedder=inner,
    )
    assert result.instances
    assert result.embedding_batch is not None
    assert result.embedding_batch.embedded_count == len(result.instances)
    assert result.page_embedding is not None
    assert np.linalg.norm(result.page_embedding) == pytest.approx(1.0, abs=1e-5)
    # Every instance got a vector list.
    for r in result.instances:
        assert r.embedding is not None
        assert len(r.embedding) == mock_embedder.dim


def test_pipeline_detect_signal_fields_flag_populates_fields():
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_p4",
        persist=False,
        detect_signal_fields=True,
    )
    assert result.search_fields, "search fields should have been detected"
    assert result.pagination_fields, "pagination fields should have been detected"
    # Summary propagates the counts.
    summ = result.as_summary()
    assert summ["search_fields"] == len(result.search_fields)
    assert summ["pagination_fields"] == len(result.pagination_fields)
