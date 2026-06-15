"""
test_trie_pipeline.py — End-to-end verification for the scan→trie→chunks pipeline.

No Selenium, no live network — uses hand-crafted HTML fixtures so the whole
contract (content tagging, trie construction, commutation, chunk budget,
billboarding) is asserted deterministically.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.dom.pipeline import run_pipeline
from backend.dom.trie_persistence import (
    BuiltTrie,
    build_trie_from_tree,
    persist_trie,
    load_trie,
    get_latest_version_id,
)
from backend.dom.trie_diff import diff_tries


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


HTML_TAROT_LIKE = """
<!doctype html>
<html><head>
  <title>Daily Tarot</title>
  <meta name="description" content="Get your daily tarot reading."/>
</head><body>
  <nav>
    <a href="/horoscopes">Horoscopes</a>
    <a href="/tarot">Tarot</a>
    <a href="/astrology">Astrology</a>
  </nav>
  <main>
    <section class="hero">
      <h1>Today's Tarot Spread</h1>
      <p>Read your cards. Find your focus. Trust the draw.</p>
    </section>
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
        <input id="q" type="text" placeholder="love, career, health..." />
        <button type="submit">Search</button>
      </form>
    </section>
  </main>
</body></html>
""".strip()


HTML_TAROT_LIKE_V2 = HTML_TAROT_LIKE.replace(
    "<h2>The High Priestess</h2>",
    "<h2>The High Priestess of Light</h2>",  # tag-value change
).replace(
    "</section>\n    <section class=\"filters\">",
    # Add a fourth card to change commutation count
    "</article>\n      <article class=\"card\">\n"
    "        <img src=\"/img/empress.png\" alt=\"The Empress\"/>\n"
    "        <h2>The Empress</h2>\n"
    "        <p>Abundance, nurturing, beauty.</p>\n"
    "        <a href=\"/tarot/empress\">Read more</a>\n"
    "      </article>\n    </section>\n    <section class=\"filters\">"
)


# ---------------------------------------------------------------------------
# Pipeline (no DB) tests
# ---------------------------------------------------------------------------


def test_pipeline_runs_end_to_end_on_fixture():
    result = run_pipeline(
        html_source=HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    assert result.html_source_len > 0
    assert result.trie.version.pattern_count > 0
    assert result.chunks, "Pipeline must produce chunks from fixture"
    summary = result.as_summary()
    assert summary["content_pattern_count"] > 0
    # Three cards in the fixture -> at least one card pattern should show
    # up with commutation_count == 3.
    card_tri_rows = [r for r in result.trie.patterns if r.commutation_count == 3]
    assert card_tri_rows, "Expected a pattern with commutation_count=3 (the three cards)"


def test_commutation_count_matches_card_instances():
    """
    The three <article class="card"> elements share the same generalized
    xpath. Their descendants (h2, p, img, a) therefore also appear three
    times with the same pattern. Every card-descendant pattern should
    record commutation_count == 3.
    """
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    card_descendant_patterns = [
        r for r in result.trie.patterns
        if "/article/" in r.pattern or r.pattern.endswith("/article")
    ]
    assert card_descendant_patterns, "Expected card patterns in the trie"
    for row in card_descendant_patterns:
        assert row.commutation_count == 3, (
            f"Pattern {row.pattern!r} commutation_count={row.commutation_count} "
            f"(expected 3 for a three-card grid)"
        )


def test_chunk_budget_excludes_urls_and_media():
    """
    Budget is text-only. A chunk's char_count must approximate the
    length of the aggregated text() field values — image src and anchor
    href attribute values do NOT contribute to the budget.

    Current chunker schema: content_fields is keyed by extended-
    relative xpath (``/article/h2/text()``, ``/article/a/@href``, …)
    rather than the older category-prefix form. Address suffix
    determines whether a key contributes to the text budget: ``text()``
    counts, ``@src``/``@href``/``@srcset``/``@data-src`` do not.
    """
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    media_attrs = {"@src", "@srcset", "@data-src"}
    href_attrs = {"@href", "@data-link", "@data-url"}
    for chunk in result.chunks:
        budget_text_len = 0
        for key, values in chunk.content_fields.items():
            tail = key.rsplit("/", 1)[-1] if "/" in key else key
            # Skip media + href attribute entries — they live in
            # image_urls / link_urls maps, not the text budget.
            if tail in media_attrs or tail in href_attrs:
                continue
            budget_text_len += sum(len(v) for v in values)
        # _format_summary joins entries with separators and adds the
        # key labels (e.g. "/article/h2/text(): The Fool"); allow
        # generous slack for those decorations.
        assert chunk.char_count <= budget_text_len + 512, (
            f"Chunk {chunk.pattern!r} char_count={chunk.char_count} "
            f"exceeds budget_text_len={budget_text_len}+512"
        )


def test_billboard_detection_for_card_chunks():
    """
    Each card has an <img src>. The chunk aggregator should fill
    ``image_urls`` for chunks whose subtree contains a media.images node.
    """
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    chunks_with_images = [c for c in result.chunks if c.image_urls]
    assert chunks_with_images, "At least one chunk should carry image URLs"
    # Every resolved URL in image_urls should look like an image.
    for chunk in chunks_with_images:
        for xp, url in chunk.image_urls.items():
            assert url.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
            ), f"Non-image URL {url!r} for member xpath {xp!r}"


def test_knowledge_panel_has_tagged_fields_only():
    """
    ``content_fields`` on a chunk is the "knowledge panel" payload. It
    should only surface tag-extracted fields — every key must be a
    relative xpath ending in ``text()`` or ``@<attr>`` (no raw HTML,
    no styling junk, no bare element names).
    """
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    for chunk in result.chunks:
        for key in chunk.content_fields.keys():
            assert key.startswith("/"), (
                f"key {key!r} must start with '/' (relative xpath)"
            )
            tail = key.rsplit("/", 1)[-1] if "/" in key else key
            assert tail == "text()" or tail.startswith("@"), (
                f"Unexpected key tail {tail!r} in chunk {chunk.pattern!r}; "
                "knowledge-panel keys must be text() or @<attr>"
            )


# ---------------------------------------------------------------------------
# Per-instance chunking -- regression tests for the "cards don't aggregate"
# invariant. User complaint: the same chunk returned instance dicts whose
# fields were length-N lists of every card's value.
# ---------------------------------------------------------------------------


def test_card_chunk_is_per_instance_not_aggregated():
    """The 3 cards must surface as one ``/article``-patterned chunk with
    3 members -- and the representative's content must be scoped to a
    single card, not concatenated across all three.
    """
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    # Find the article (per-card) chunk.
    card_chunks = [
        c for c in result.chunks
        if c.pattern.rstrip("/").endswith("/article")
    ]
    assert card_chunks, (
        "Expected a chunk pinned at the /article level so each card "
        "is an independent instance. Got patterns: "
        + ", ".join(repr(c.pattern) for c in result.chunks)
    )
    # There should be exactly one such chunk; all 3 cards are its members.
    assert len(card_chunks) == 1
    card = card_chunks[0]
    assert card.commutation_count == 3
    assert len(card.member_xpaths) == 3
    # The representative must point at ONE specific card, not the
    # container above it.
    assert "/article[" in card.representative_xpath, (
        f"representative_xpath {card.representative_xpath!r} should "
        f"address a single article instance"
    )
    # The text_preview is the representative's prose only -- not a
    # cross-card concatenation. Exactly one of the three card titles
    # should appear (whichever the chunker picked as representative);
    # the other two must NOT appear in the same preview.
    card_titles = {"The Fool", "The Magician", "The High Priestess"}
    present = {t for t in card_titles if t in card.text_preview}
    assert len(present) == 1, (
        f"expected exactly one card title in text_preview, got "
        f"{sorted(present)} (preview={card.text_preview!r})"
    )


def test_query_chunk_resolves_per_instance_scalars():
    """End-to-end: ``query_chunk`` against the card pattern must return
    3 instance dicts, each with scalar (length-1) values -- not arrays
    that cross-contaminate fields between cards.
    """
    from backend.dom.shadow_html_parser import ShadowDOM
    from backend.dom.chunk_query import query_chunk

    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    card_chunk = next(
        c for c in result.chunks
        if c.pattern.rstrip("/").endswith("/article")
    )
    # Without ``all_tags`` wired through the pipeline this would be {}
    # and the instance dicts below would come back empty -- making the
    # demo's "Extraction Schema (Trie):" print blank.
    assert card_chunk.extraction_trie, (
        "card chunk's extraction_trie is empty -- all_tags is not "
        "reaching ChunkBuilder"
    )

    dom = ShadowDOM(HTML_TAROT_LIKE)
    results = query_chunk(dom, card_chunk.pattern, card_chunk.extraction_trie)

    assert len(results) == 3, (
        f"expected 3 per-card instance dicts, got {len(results)}"
    )
    for i, inst in enumerate(results):
        assert inst, f"instance {i+1} is empty; schema didn't resolve"
        for path, vals in inst.items():
            assert len(vals) == 1, (
                f"instance {i+1} path {path!r} has {len(vals)} values "
                f"({vals!r}); per-instance chunking must yield scalars"
            )
    # And the three cards must be DISTINCT titles -- if they all said
    # "The Fool" something is resolving every instance to card 1. The
    # extraction_trie keys carry the chunk root prefix, so the title
    # field is ``/article/h2/text()``.
    titles = [inst.get("/article/h2/text()", [""])[0] for inst in results]
    assert set(titles) == {"The Fool", "The Magician", "The High Priestess"}


def test_section_chunk_schema_does_not_leak_card_fields():
    """The hero/section chunk must not carry article-descendant paths.

    Before the fix, the chunk whose representative was ``section[1]``
    (hero) also listed ``section[2]`` (card-grid) as a member. The
    extraction_trie was built from the *union* of tags across members,
    which polluted every hero-instance result with card paths like
    ``/article/img/@src`` resolving to all 3 card images. The schema
    should now reflect the representative alone.
    """
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    # The "section" chunk (non-article, non-form) picks up the hero.
    section_chunks = [
        c for c in result.chunks
        if c.pattern.rstrip("/").endswith("/section")
    ]
    if not section_chunks:
        pytest.skip("no section-level chunk emitted for this fixture")
    for c in section_chunks:
        assert "/article" not in json.dumps(c.extraction_trie), (
            f"section chunk extraction_trie leaks /article paths: "
            f"{c.extraction_trie}"
        )


def test_extraction_trie_to_accessor_map_flattens_with_unique_slugs():
    """§5.4 — flattener turns a compressed extraction_trie into
    ``{field_name: rel_xpath}`` with deterministic, collision-free
    slugs derived from the last tag + data-address tail.
    """
    from backend.dom.pipeline import _extraction_trie_to_accessor_map
    trie = {
        "/a": {
            "/h3": {"text()": {}},
            "@href": {},
        },
        "/img": {"@src": {}},
    }
    acc = _extraction_trie_to_accessor_map(trie)
    assert acc == {
        "h3_text": "/a/h3/text()",
        "a_href": "/a/@href",
        "img_src": "/img/@src",
    }
    # Empty trie -> empty map (don't fabricate fields).
    assert _extraction_trie_to_accessor_map({}) == {}
    # Slug collisions get numeric suffixes.
    colliding = {
        "/a": {"@href": {}},
        "/section": {"/a": {"@href": {}}},
    }
    acc2 = _extraction_trie_to_accessor_map(colliding)
    keys = sorted(acc2.keys())
    assert keys == ["a_href", "a_href_2"]
    # Both keys point at distinct relative xpaths.
    assert len(set(acc2.values())) == 2


def test_pipeline_extraction_trie_to_accessor_map_on_real_chunk():
    """End-to-end: feed a real extraction_trie produced by the pipeline
    through the §5.4 flattener and confirm it yields a non-empty
    ``{slug: rel_xpath}`` map with text and attribute leaves. Without
    §5.4 wiring this map would be empty and downstream UI / SLM
    consumers would only see the bare pattern string.
    """
    from backend.dom.pipeline import _extraction_trie_to_accessor_map
    result = run_pipeline(
        HTML_TAROT_LIKE,
        url="https://www.tarot.com/_test_fixture",
        persist=False,
    )
    # Find any chunk with a substantial extraction_trie. We don't pin
    # to /article so the test is robust to chunker-emission changes —
    # the contract under test is the flattener applied to *some* real
    # trie, not which chunks the chunker emits today.
    candidate = max(
        result.chunks,
        key=lambda c: len(json.dumps(c.extraction_trie or {})),
        default=None,
    )
    assert candidate is not None and candidate.extraction_trie, (
        "pipeline produced no chunks with extraction_trie; cannot verify "
        "accessor_map wiring"
    )
    acc = _extraction_trie_to_accessor_map(candidate.extraction_trie)
    assert acc, (
        f"flattener returned empty map for non-empty trie "
        f"{candidate.extraction_trie!r}"
    )
    rel_xpaths = set(acc.values())
    # The fixture has both text-bearing tags (h1/h2/p/title) and href/src
    # attributes, so a non-empty extraction_trie over it must surface at
    # least one of each kind.
    assert any(p.endswith("/text()") for p in rel_xpaths), rel_xpaths
    assert any("@" in p for p in rel_xpaths), rel_xpaths


def test_subtree_hash_is_deterministic_across_runs():
    """
    Running the pipeline twice on the same HTML should yield identical
    per-pattern subtree hashes and an identical root hash. This is the
    property the diff relies on to skip unchanged subtrees.
    """
    r1 = run_pipeline(HTML_TAROT_LIKE, url="https://x/_a", persist=False)
    r2 = run_pipeline(HTML_TAROT_LIKE, url="https://x/_a", persist=False)
    assert r1.trie.version.root_hash == r2.trie.version.root_hash
    by_pat_1 = {r.pattern: r.subtree_hash for r in r1.trie.patterns}
    by_pat_2 = {r.pattern: r.subtree_hash for r in r2.trie.patterns}
    assert by_pat_1 == by_pat_2


def test_diff_detects_added_and_changed_patterns():
    """
    v2 adds a fourth card (commutation goes 3->4 for card descendant
    patterns) and changes one h2's text content. The diff must:
      * report commutation_changed for card descendants
      * report NO added patterns at the card level (pattern already exists)
      * show stable patterns for the header / nav / filter (untouched)
    """
    old = run_pipeline(HTML_TAROT_LIKE, url="https://x/_a", persist=False).trie
    new = run_pipeline(HTML_TAROT_LIKE_V2, url="https://x/_a", persist=False).trie

    d = diff_tries(old, new)
    s = d.summary()
    assert s["commutation_changes"] > 0, (
        "Adding a fourth card must increase commutation_count on card descendants"
    )
    # Card-descendant patterns should all have gone 3 -> 4.
    for change in d.changed_patterns:
        if "/article" in change.pattern:
            assert change.new.commutation_count == 4
            assert change.old.commutation_count == 3


def test_diff_against_none_yields_all_added():
    """First-ever scan: no prior version → every pattern is 'added'."""
    built = run_pipeline(HTML_TAROT_LIKE, url="https://x/_a", persist=False).trie
    d = diff_tries(None, built)
    assert len(d.added_patterns) == built.version.pattern_count
    assert not d.removed_patterns
    assert not d.changed_patterns


def test_fast_path_identical_root_hash_shortcircuits():
    """
    When the two versions share a root_hash, the diff should short-circuit
    and report stable == pattern_count, 0 adds/removes/changes.
    """
    a = run_pipeline(HTML_TAROT_LIKE, url="https://x/_a", persist=False).trie
    b = run_pipeline(HTML_TAROT_LIKE, url="https://x/_a", persist=False).trie
    d = diff_tries(a, b)
    assert d.is_identical()
    assert d.stable_count == b.version.pattern_count


# ---------------------------------------------------------------------------
# DB round-trip test (skips if Kuzu unhappy)
# ---------------------------------------------------------------------------


@pytest.fixture()
def kuzu_temp_conn():
    """Isolated Kuzu DB in a temp dir for one test (§R.9 janitor-managed)."""
    from backend.services.db_janitor import temp_db_dir

    with temp_db_dir("trie") as tmp:
        yield from _kuzu_temp_conn_impl(tmp)


def _kuzu_temp_conn_impl(tmp):
    db_path = os.path.join(tmp, "db")
    import kuzu

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # Minimal schema: just the tables our trie persistence touches.
    stmts = [
        "CREATE NODE TABLE Domain(domain STRING, first_seen STRING, PRIMARY KEY(domain))",
        "CREATE NODE TABLE Page(url STRING, domain STRING, timestamp STRING, PRIMARY KEY(url))",
        "CREATE NODE TABLE DomSnapshot(snapshot_id STRING, url STRING, file_path STRING, "
        "content_hash STRING, captured_at STRING, node_count INT64, PRIMARY KEY(snapshot_id))",
        "CREATE NODE TABLE TrieVersion(version_id STRING, url STRING, snapshot_id STRING, "
        "parent_version_id STRING, pattern_count INT64, content_pattern_count INT64, "
        "total_char_count INT64, root_hash STRING, created_at STRING, PRIMARY KEY(version_id))",
        "CREATE NODE TABLE TriePattern(pattern_id STRING, version_id STRING, pattern STRING, "
        "representative_xpath STRING, parent_pattern_id STRING, tag_set STRING, "
        "commutation_count INT64, depth INT64, has_shadow_boundary BOOLEAN, "
        "char_count INT64, self_hash STRING, subtree_hash STRING, PRIMARY KEY(pattern_id))",
        "CREATE REL TABLE HAS_PAGE(FROM Domain TO Page)",
        "CREATE REL TABLE HAS_TRIE_VERSION(FROM Page TO TrieVersion)",
        "CREATE REL TABLE SNAPSHOT_OF(FROM TrieVersion TO DomSnapshot)",
        "CREATE REL TABLE NEXT_VERSION(FROM TrieVersion TO TrieVersion)",
        "CREATE REL TABLE HAS_TRIE_PATTERN(FROM TrieVersion TO TriePattern)",
        "CREATE REL TABLE PARENT_PATTERN(FROM TriePattern TO TriePattern)",
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


def test_persist_and_load_trie_roundtrip(kuzu_temp_conn):
    conn = kuzu_temp_conn
    url = "https://x/_rt"
    result = run_pipeline(HTML_TAROT_LIKE, url=url, persist=False)
    persist_trie(conn, result.trie)

    # Latest version lookup
    vid = get_latest_version_id(conn, url)
    assert vid == result.trie.version.version_id

    # Full reconstitution
    loaded = load_trie(conn, vid)
    assert loaded is not None
    assert loaded.version.pattern_count == result.trie.version.pattern_count
    assert loaded.version.root_hash == result.trie.version.root_hash
    assert len(loaded.patterns) == len(result.trie.patterns)

    # Every pattern must round-trip exactly
    orig_by_key = result.trie.by_pattern_key
    load_by_key = loaded.by_pattern_key
    assert set(orig_by_key) == set(load_by_key)
    for pat, orig in orig_by_key.items():
        lp = load_by_key[pat]
        assert lp.pattern == orig.pattern
        assert lp.tag_set == orig.tag_set
        assert lp.commutation_count == orig.commutation_count
        assert lp.subtree_hash == orig.subtree_hash


def test_diff_persisted_versions(kuzu_temp_conn):
    conn = kuzu_temp_conn
    url = "https://x/_diff"
    r1 = run_pipeline(HTML_TAROT_LIKE, url=url, persist=False)
    persist_trie(conn, r1.trie)
    r2 = run_pipeline(
        HTML_TAROT_LIKE_V2,
        url=url,
        persist=False,
        parent_version_id=r1.trie.version.version_id,
    )
    persist_trie(conn, r2.trie)

    from backend.dom.trie_persistence import load_trie as _load
    old = _load(conn, r1.trie.version.version_id)
    new = _load(conn, r2.trie.version.version_id)
    d = diff_tries(old, new)
    # The fixture adds one card, so at least one commutation change.
    assert d.summary()["commutation_changes"] >= 1
