"""
Tests for :mod:`backend.services.chunk_containment` — the strict-ancestor
xpath pruning pass that drops monster "swallow everything" rollup chunks
whose children are already covered by finer-grained chunks.

Fixture design: the tarot.com case we empirically hit (1 × 59 KB rollup
at ``/html/body/main/div/div/div[2]/div/div[2]`` plus 20 per-card chunks
at ``.../ul/li[i]/row/column[2]``) is what we're shaped to kill. The
smaller tests cover the sentinel edges — identical xpaths, prefix-look-
alikes like ``/a/divider`` vs ``/a/div``, empty lists, and the "the rollup
has its own non-rollup siblings" case so we don't accidentally eat them.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.chunk_containment import (
    filter_redundant_rollups,
    is_ancestor_xpath,
)


@dataclass
class _Row:
    """Minimal stand-in for ChunkInstanceRow / InstanceHit / Chunk."""
    id: str
    xpath: str


def _xp(r: _Row) -> str:
    return r.xpath


# ---------------------------------------------------------------------------
# is_ancestor_xpath — predicate correctness
# ---------------------------------------------------------------------------


def test_strict_ancestor_is_true_for_proper_prefix():
    assert is_ancestor_xpath("/a/b", "/a/b/c") is True


def test_strict_ancestor_is_false_for_identity():
    assert is_ancestor_xpath("/a/b", "/a/b") is False


def test_strict_ancestor_is_false_for_sibling():
    assert is_ancestor_xpath("/a/b", "/a/c") is False


def test_strict_ancestor_rejects_prefix_lookalike_without_path_boundary():
    # /html/body/div should NOT be seen as an ancestor of /html/body/divider.
    assert is_ancestor_xpath("/html/body/div", "/html/body/divider/span") is False


def test_strict_ancestor_is_false_when_empty():
    assert is_ancestor_xpath("", "/a") is False
    assert is_ancestor_xpath("/a", "") is False
    assert is_ancestor_xpath("", "") is False


def test_strict_ancestor_handles_indexed_tags():
    # Absolute xpaths carry [i] suffixes; prefix logic must treat them right.
    assert is_ancestor_xpath("/html/body/ul/li[3]", "/html/body/ul/li[3]/a") is True
    assert is_ancestor_xpath("/html/body/ul/li[3]", "/html/body/ul/li[30]") is False


# ---------------------------------------------------------------------------
# filter_redundant_rollups — end-to-end cases
# ---------------------------------------------------------------------------


def test_monster_rollup_is_dropped_while_per_card_chunks_survive():
    """Shape of the real tarot.com failure: one rollup + 20 card chunks.

    Build the fixture programmatically so we don't depend on any particular
    page content — what matters is the *structure* of the xpaths.
    """
    monster = _Row(id="monster", xpath="/html/body/main/div/div/div[2]/div/div[2]")
    sibling_rollup = _Row(
        id="sibling",
        xpath="/html/body/main/div/div/div[2]/div/div[1]",
    )
    cards = [
        _Row(
            id=f"card-{i}",
            xpath=f"/html/body/main/div/div/div[2]/div/div[2]/ul/li[{i}]/row/column[2]",
        )
        for i in range(1, 21)
    ]
    other = _Row(id="unrelated", xpath="/html/body/footer/div")

    survivors = filter_redundant_rollups(
        [monster, sibling_rollup, *cards, other], xpath_of=_xp,
    )
    ids = {r.id for r in survivors}

    # Monster is a strict ancestor of every card ⇒ dropped.
    assert "monster" not in ids
    # Sibling rollup has no chunks under it in this fixture ⇒ KEPT.
    assert "sibling" in ids
    # All 20 cards survive — they have no chunks strictly inside them.
    for i in range(1, 21):
        assert f"card-{i}" in ids
    # Unrelated footer chunk unaffected.
    assert "unrelated" in ids


def test_empty_input_returns_empty():
    assert filter_redundant_rollups([], xpath_of=_xp) == []


def test_single_item_returns_unchanged():
    r = _Row(id="only", xpath="/a")
    assert filter_redundant_rollups([r], xpath_of=_xp) == [r]


def test_input_order_preserved_for_survivors():
    rows = [
        _Row(id="a", xpath="/a/b/c/d"),
        _Row(id="b", xpath="/z/y"),
        _Row(id="c", xpath="/a/b"),  # strict ancestor of "a" → dropped
        _Row(id="d", xpath="/m/n"),
    ]
    survivors = filter_redundant_rollups(rows, xpath_of=_xp)
    assert [r.id for r in survivors] == ["a", "b", "d"]


def test_transitive_ancestor_chain_is_fully_pruned():
    """A → B → C where A and B are both strict ancestors of C. Drop both."""
    rows = [
        _Row(id="A", xpath="/a"),
        _Row(id="B", xpath="/a/b"),
        _Row(id="C", xpath="/a/b/c/d/e"),
    ]
    survivors = filter_redundant_rollups(rows, xpath_of=_xp)
    assert [r.id for r in survivors] == ["C"]


def test_prefix_lookalike_survives():
    """Sibling xpaths sharing a string prefix but not a path prefix must stay."""
    rows = [
        _Row(id="div", xpath="/html/body/div"),
        _Row(id="divider", xpath="/html/body/divider/span"),
    ]
    survivors = filter_redundant_rollups(rows, xpath_of=_xp)
    assert {r.id for r in survivors} == {"div", "divider"}


def test_empty_xpath_rows_are_ignored_not_treated_as_root():
    """A row with xpath="" should not accidentally nuke every other row."""
    rows = [
        _Row(id="blank", xpath=""),
        _Row(id="normal-1", xpath="/a/b"),
        _Row(id="normal-2", xpath="/c/d"),
    ]
    survivors = filter_redundant_rollups(rows, xpath_of=_xp)
    assert {r.id for r in survivors} == {"blank", "normal-1", "normal-2"}
