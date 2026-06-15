"""
test_pattern_labeler.py — deterministic Phase 3 verification.

The real SLM is nondeterministic and CPU-heavy. For CI we stub the
``generate_json`` call with a tiny router that looks at the knowledge
panel and returns a plausible label. The tests assert the *contract*
between ``PatternLabeler`` and the rest of the pipeline, not the SLM's
generative quality — that's measured live in ``demo_live_tarot``.
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
from backend.services.pattern_labeler import (
    PatternLabeler,
    PatternLabelRow,
    PatternLabelingError,
    persist_pattern_labels,
    load_pattern_labels,
)
from backend.tests.test_trie_pipeline import HTML_TAROT_LIKE  # reuse fixture


# ---------------------------------------------------------------------------
# Stub SLM
# ---------------------------------------------------------------------------


class _StubSLM:
    """Tiny router over knowledge-panel text → plausible label JSON.

    Mirrors how a real SLM would eyeball the panel and pick a role. Keeps
    the test deterministic and fast.
    """

    def __init__(self):
        self.calls: list = []

    def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        self.calls.append(prompt)
        lower = prompt.lower()

        # Card pattern: carries an <img alt>/<h2>/<p>/<a> bundle.
        if "the fool" in lower or "magician" in lower or "priestess" in lower:
            return {
                "role": "card",
                "category": "tarot_card",
                "summary": "A tarot card with image, title, description, and link.",
                "confidence": 0.92,
            }

        # Nav pattern: any primary-nav link label. Under per-instance
        # chunking each ``<a>`` becomes its own chunk, so only the
        # representative's text (e.g. "Horoscopes") reaches the prompt.
        # Under the older aggregate chunking all three link labels
        # appeared together -- OR'ing covers both regimes. We use tokens
        # unique to the nav (card titles never say "horoscopes" or
        # "astrology") so card chunks don't get mis-routed here.
        if "horoscopes" in lower or "astrology" in lower:
            return {
                "role": "nav",
                "category": "primary_nav_link",
                "summary": "A top-level navigation link between major site sections.",
                "confidence": 0.88,
            }

        # Hero / header paragraph.
        if "today's tarot spread" in lower or "focus" in lower:
            return {
                "role": "banner",
                "category": "hero_heading",
                "summary": "Hero section greeting the visitor.",
                "confidence": 0.7,
            }

        # Filter / search form.
        if "search readings" in lower or "placeholder" in lower:
            return {
                "role": "filter",
                "category": "search_box",
                "summary": "Free-text search for readings.",
                "confidence": 0.8,
            }

        # Fallback.
        return {
            "role": "unknown",
            "category": "unknown",
            "summary": "Unclassified repeating region.",
            "confidence": 0.3,
        }


class _BrokenSLM:
    """Always returns empty dict → simulates invalid JSON."""

    def __init__(self):
        self.calls = 0

    def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        self.calls += 1
        return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_phase1_2():
    return run_pipeline(HTML_TAROT_LIKE, url="https://x/_lbl", persist=False)


def _find_card_chunk(chunks):
    """Pick the chunk whose content includes the card grid text."""
    for c in chunks:
        blob = " ".join(v for vs in c.content_fields.values() for v in vs).lower()
        if "fool" in blob or "magician" in blob or "priestess" in blob:
            return c
    raise AssertionError("No card-like chunk found in fixture")


def _find_nav_chunk(chunks):
    """Find the per-instance nav chunk (pattern .../nav/a, members=3).

    Prior to the per-instance chunking fix, the nav chunk aggregated
    all 3 link texts into one chunk's ``content_fields`` -- so the
    old helper scanned for "horoscopes" + "astrology" in the same
    chunk's content. Under the new contract each ``<a>`` instance is
    addressable via ``query_chunk``; within the chunk itself only the
    representative's text appears. Identify the nav chunk by its
    pattern shape instead.
    """
    for c in chunks:
        if c.pattern.rstrip("/").endswith("/nav/a") and c.commutation_count >= 2:
            return c
    # Fallback: the old aggregate-scanning heuristic, so this helper
    # keeps working on hypothetical fixtures where walk-up lands the
    # whole nav into one chunk.
    for c in chunks:
        blob = " ".join(v for vs in c.content_fields.values() for v in vs).lower()
        if "horoscopes" in blob and "astrology" in blob:
            return c
    raise AssertionError("No nav-like chunk found in fixture")


# ---------------------------------------------------------------------------
# 1. Card pattern gets a card-ish label
# ---------------------------------------------------------------------------


def test_card_pattern_is_labeled_card():
    result = _run_phase1_2()
    labeler = PatternLabeler(slm=_StubSLM())
    card = _find_card_chunk(result.chunks)
    pat_row = result.trie.by_pattern_key[card.pattern]
    label = labeler.label_pattern(card, pat_row.tag_set)

    assert label["role"] in {"card", "list_item"}, label
    cat = label["category"].lower()
    assert "card" in cat or "tarot" in cat, f"unexpected category {cat!r}"
    assert isinstance(label["summary"], str) and label["summary"]
    assert 0.0 <= label["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 2. Nav pattern gets role=nav
# ---------------------------------------------------------------------------


def test_nav_pattern_is_labeled_nav():
    result = _run_phase1_2()
    labeler = PatternLabeler(slm=_StubSLM())
    nav = _find_nav_chunk(result.chunks)
    pat_row = result.trie.by_pattern_key[nav.pattern]
    label = labeler.label_pattern(nav, pat_row.tag_set)
    assert label["role"] == "nav"


# ---------------------------------------------------------------------------
# 3. Invalid JSON -> PatternLabelingError
# ---------------------------------------------------------------------------


def test_invalid_slm_output_raises():
    result = _run_phase1_2()
    labeler = PatternLabeler(slm=_BrokenSLM(), max_retries=2)
    card = _find_card_chunk(result.chunks)
    pat_row = result.trie.by_pattern_key[card.pattern]
    with pytest.raises(PatternLabelingError):
        labeler.label_pattern(card, pat_row.tag_set)


def test_invalid_slm_output_retries_before_raising():
    """The labeler must attempt ``max_retries`` times before giving up.

    Missing labels are a data-integrity bug in later phases, so failing
    loud matters — but small models routinely recover on a second pass.
    """
    result = _run_phase1_2()
    broken = _BrokenSLM()
    labeler = PatternLabeler(slm=broken, max_retries=3)
    card = _find_card_chunk(result.chunks)
    pat_row = result.trie.by_pattern_key[card.pattern]
    with pytest.raises(PatternLabelingError):
        labeler.label_pattern(card, pat_row.tag_set)
    assert broken.calls == 3


# ---------------------------------------------------------------------------
# 4. Kuzu round-trip
# ---------------------------------------------------------------------------


@pytest.fixture()
def kuzu_label_conn():
    """Isolated DB with the trie + pattern-label schemas (§R.9 janitor-managed)."""
    from backend.services.db_janitor import temp_db_dir

    with temp_db_dir("pattern_label") as tmp:
        yield from _kuzu_label_conn_impl(tmp)


def _kuzu_label_conn_impl(tmp):
    import kuzu
    db = kuzu.Database(os.path.join(tmp, "db"))
    conn = kuzu.Connection(db)
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
        "char_count INT64, self_hash STRING, subtree_hash STRING, member_xpaths STRING, "
        "PRIMARY KEY(pattern_id))",
        "CREATE NODE TABLE PatternLabel(label_id STRING, pattern_id STRING, version_id STRING, "
        "role STRING, category STRING, summary STRING, confidence DOUBLE, "
        "raw_json STRING, model STRING, created_at STRING, PRIMARY KEY(label_id))",
        "CREATE REL TABLE HAS_PAGE(FROM Domain TO Page)",
        "CREATE REL TABLE HAS_TRIE_VERSION(FROM Page TO TrieVersion)",
        "CREATE REL TABLE SNAPSHOT_OF(FROM TrieVersion TO DomSnapshot)",
        "CREATE REL TABLE NEXT_VERSION(FROM TrieVersion TO TrieVersion)",
        "CREATE REL TABLE HAS_TRIE_PATTERN(FROM TrieVersion TO TriePattern)",
        "CREATE REL TABLE PARENT_PATTERN(FROM TriePattern TO TriePattern)",
        "CREATE REL TABLE LABELS_PATTERN(FROM PatternLabel TO TriePattern)",
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


def test_kuzu_roundtrip_and_idempotence(kuzu_label_conn):
    conn = kuzu_label_conn
    from backend.dom.trie_persistence import persist_trie

    result = _run_phase1_2()
    persist_trie(conn, result.trie)

    labeler = PatternLabeler(slm=_StubSLM())
    rows = labeler.label_trie(result.trie, result.chunks)
    # Every labeled pattern must be a chunk-root (there must be a chunk
    # whose pattern matches the labeled pattern's generalized xpath).
    chunk_patterns = {c.pattern for c in result.chunks if c.content_fields}
    for row in rows:
        pat = result.trie.by_pattern_id[row.pattern_id]
        assert pat.pattern in chunk_patterns, (
            f"Labeled pattern {pat.pattern!r} does not correspond to any chunk"
        )

    # One label per content-bearing chunk.
    content_chunks = [c for c in result.chunks if c.content_fields]
    assert len(rows) == len(content_chunks), (
        f"Expected one label per content-bearing chunk "
        f"(got {len(rows)} labels for {len(content_chunks)} chunks)"
    )

    persist_pattern_labels(conn, rows)
    loaded = load_pattern_labels(conn, result.trie.version.version_id)
    assert len(loaded) == len(rows)

    by_pid_orig = {r.pattern_id: r for r in rows}
    by_pid_load = {r.pattern_id: r for r in loaded}
    assert set(by_pid_orig) == set(by_pid_load)
    for pid, orig in by_pid_orig.items():
        lp = by_pid_load[pid]
        assert lp.role == orig.role
        assert lp.category == orig.category
        assert lp.summary == orig.summary
        assert abs(lp.confidence - orig.confidence) < 1e-6

    # Idempotence: re-persist the same rows, count unchanged.
    persist_pattern_labels(conn, rows)
    loaded_again = load_pattern_labels(conn, result.trie.version.version_id)
    assert len(loaded_again) == len(rows), (
        "Re-running labeling must NOT duplicate rows"
    )
