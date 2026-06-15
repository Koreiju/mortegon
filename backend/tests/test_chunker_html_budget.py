"""
Unit tests for the HTML-budget walk-up rewrite in
:mod:`backend.mapper.chunk_builder`.

Covered rules:

* Distilled-HTML serialization with strict 60-char attribute and text
  truncation. A single attribute value that would otherwise run 2000+
  chars must not dominate a chunk.
* Hard 128-token ceiling (HARD_CHAR_LIMIT = 512 chars). No emitted
  chunk's distilled HTML may exceed this.
* Parent-contribution heuristic: walking from a card up to the grid
  must stop once the grid would add >80% new distilled HTML on top of
  the current card — even if the usual pattern-commutation check is
  fooled by a heterogeneous sibling layout.
* Containment pruning size gate: legitimate coarse/fine chunk pairs
  both well under the hard limit must *not* be pruned. Only oversized
  monster rollups (> 2× HARD_CHAR_LIMIT) may be dropped.

The fixtures build a synthetic Patricia trie by hand so the tests
don't depend on Selenium / ShadowDOM parsing.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from backend.mapper import chunk_builder as cb_mod
from backend.mapper.chunk_builder import (
    ATTR_TRUNCATE,
    ChunkBuilder,
    DEFAULT_CHAR_BUDGET,
    HARD_CHAR_LIMIT,
    HARD_TOKEN_LIMIT,
    TEXT_TRUNCATE,
)


# ---------------------------------------------------------------------------
# Tiny trie helpers
# ---------------------------------------------------------------------------


def _node(xpath: str, *, content: List[str] | None = None,
          children: Dict[str, Any] | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"_xpath": xpath}
    if content:
        out["_content"] = list(content)
    if children:
        out.update(children)
    return out


def _text_provider_from_map(text_map: Dict[str, str]):
    def _p(xp: str, _cats: List[str]) -> str:
        return text_map.get(xp, "")
    return _p


def _struct_provider_from_map(
    struct_map: Dict[str, tuple[str, Dict[str, str]]],
):
    def _p(xp: str):
        return struct_map.get(xp, ("div", {}))
    return _p


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------


def test_hard_char_limit_matches_token_limit_estimate():
    # 512 tokens × 4 chars/token = 2048 chars. 512 was picked to
    # comfortably hold one fully-populated card's content-structure
    # summary (tarot.com cards serialize ~260 tokens) without letting a
    # 20-card grid (~5000 tokens) swallow the whole page.
    assert HARD_TOKEN_LIMIT == 512
    assert HARD_CHAR_LIMIT == 2048
    assert DEFAULT_CHAR_BUDGET == HARD_CHAR_LIMIT
    assert ATTR_TRUNCATE == TEXT_TRUNCATE == 60


# ---------------------------------------------------------------------------
# HTML-budget accounting — attribute + text truncation
#
# NOTE — the literal `_distilled_html` string serializer was replaced by the
# content-structure SUMMARY pipeline (`_render_summary_fields` /
# `_format_summary`); the 60-char truncation contract survives in the
# BUDGET ACCOUNTING (`_html_chars_xp` / `_html_chars_node`): an attribute
# or text value counts at most ATTR_TRUNCATE / TEXT_TRUNCATE chars toward
# the walk-up budget, so a 2000-char blob can never dominate a chunk.
# These tests pin that live contract.
# ---------------------------------------------------------------------------


def _budget_for(attrs: Dict[str, str], text: str) -> int:
    tree = _node("/html/body/div", content=["text.body"])
    bld = ChunkBuilder(
        tree,
        _text_provider_from_map({"/html/body/div": text}),
        structure_provider=_struct_provider_from_map(
            {"/html/body/div": ("span", attrs)}
        ),
    )
    return bld._html_chars_xp("/html/body/div")


def test_budget_counts_long_attribute_at_attr_truncate():
    # A 2000-char attribute blob counts the same as a 60-char one — the
    # cap, not the blob, drives the budget.
    capped = _budget_for({"data-blob": "x" * ATTR_TRUNCATE}, "hello")
    monstrous = _budget_for({"data-blob": "x" * 2000}, "hello")
    assert monstrous == capped
    # And the absolute size stays card-scale, nowhere near the blob.
    assert monstrous < 200


def test_budget_counts_long_text_at_text_truncate():
    long_text = "a quick brown fox " * 50  # ~900 chars
    capped = _budget_for({}, "y" * TEXT_TRUNCATE)
    monstrous = _budget_for({}, long_text)
    assert monstrous == capped
    # Shorter-than-cap text counts its true length (no padding).
    assert _budget_for({}, "hi") == capped - TEXT_TRUNCATE + 2


def test_format_summary_is_deterministic_and_truncates_links():
    summary = {
        "/li/a/@href": ["https://example.com/" + "p" * 200],
        "/li/h3/text()": ["A title"],
    }
    once = ChunkBuilder._format_summary(summary)
    twice = ChunkBuilder._format_summary(summary)
    assert once == twice  # canonical rendering — token counts agree
    # URL-like attribute values truncate at 120 chars (117 + "...").
    assert "..." in once
    assert "p" * 118 not in once
    assert "A title" in once


# ---------------------------------------------------------------------------
# Hard 128-token ceiling
# ---------------------------------------------------------------------------


def test_walk_up_never_emits_chunk_exceeding_hard_char_limit():
    """
    Build a trie where every node carries ~100 chars of HTML, with 10
    siblings under a root. Walking up from any leaf past 5 siblings
    would exceed the 512-char cap, so the chunker must stop earlier.
    """
    # Shape: /r with 10 children /r/c[i] each carrying a text body.
    root_children = {}
    text_map: Dict[str, str] = {}
    struct_map: Dict[str, tuple[str, Dict[str, str]]] = {"/r": ("div", {})}
    for i in range(1, 11):
        xp = f"/r/c[{i}]"
        text_map[xp] = f"card-{i}-text"
        struct_map[xp] = ("article", {"class": "card"})
        root_children[f"c[{i}]"] = _node(xp, content=["text.body"])
    tree = _node("/r", children=root_children)

    bld = ChunkBuilder(
        tree,
        _text_provider_from_map(text_map),
        structure_provider=_struct_provider_from_map(struct_map),
    )
    chunks = bld.build(snapshot_id="s1")

    # Every chunk's distilled-HTML length must respect the hard cap.
    for ch in chunks:
        html_len = bld._html_chars_xp(ch.representative_xpath)
        assert html_len <= HARD_CHAR_LIMIT, (
            f"chunk {ch.representative_xpath} has {html_len} distilled-HTML "
            f"chars, exceeds HARD_CHAR_LIMIT {HARD_CHAR_LIMIT}"
        )


# ---------------------------------------------------------------------------
# Parent-contribution heuristic
# ---------------------------------------------------------------------------


def test_recursion_descends_past_grid_to_per_card_granularity():
    """
    5 sibling cards under a grid container. The aggregate summary at
    the grid level is ~5× the per-card summary; with a ``char_budget``
    sized just below the grid total but above a single card, the top-
    down chunker must descend past ``/grid`` and emit one Chunk at
    ``/grid/card`` whose members are all five card xpaths.

    A single Chunk with N members is exactly the right shape: the
    ChunkInstance persist stage fans it out into N per-card rows, one
    per member xpath. "N cards at per-card granularity" is 1 Chunk ×
    N members, not N Chunks × 1 member.
    """
    grid_children = {}
    text_map: Dict[str, str] = {}
    struct_map: Dict[str, tuple[str, Dict[str, str]]] = {"/grid": ("section", {})}
    for i in range(1, 6):
        xp = f"/grid/card[{i}]"
        # Unique per-card value so the grid-level summary doesn't
        # dedupe 5 cards into 1 line and fit the budget by accident.
        text_map[xp] = f"card-{i}-unique-body-text-with-some-length"
        struct_map[xp] = ("article", {"class": "card"})
        grid_children[f"card[{i}]"] = _node(xp, content=["text.body"])
    tree = _node("/grid", children=grid_children)

    # Per-card summary is ~ len(f"    /card/text(): ['card-{i}-...']")
    # ≈ 60 chars. 5 cards aggregated ≈ 300 chars. Setting the budget
    # between those two thresholds is the whole test — grid overflows,
    # per-card fits.
    bld = ChunkBuilder(
        tree,
        _text_provider_from_map(text_map),
        structure_provider=_struct_provider_from_map(struct_map),
        char_budget=200,
    )
    chunks = bld.build(snapshot_id="s1")
    reps = {c.representative_xpath for c in chunks}
    patterns = {c.pattern for c in chunks}

    # Must NOT have emitted a /grid chunk that swallows all 5 cards.
    assert "/grid" not in reps, (
        "walk-up overshot: chunker rolled up the whole grid instead of "
        "stopping at per-card granularity."
    )
    # The single Chunk's pattern must be the generalized card xpath,
    # NOT the grid — that's what guarantees 5 ChunkInstance rows on persist.
    # `generalize_xpath` strips the [i] markers entirely, so the pattern
    # string is ``/grid/card`` (same form whether 1 or 50 cards).
    assert "/grid/card" in patterns
    assert "/grid" not in patterns
    # And that Chunk must cover all 5 card xpaths as members.
    card_chunk = next(c for c in chunks if c.pattern == "/grid/card")
    members = set(card_chunk.member_xpaths)
    assert members == {f"/grid/card[{i}]" for i in range(1, 6)}


def test_parent_contribution_allows_small_climb_when_parent_adds_little():
    """
    One card with a tiny wrapping <div> that adds <5% new content.
    The chunker should climb past that wrapper freely (rule 4 must not
    fire when the parent is almost identical to the current subtree).
    """
    # Shape: /wrap > /wrap/article, where /wrap's only extra content is
    # the tag itself + a class attr.
    tree = _node("/wrap", children={
        "article": _node("/wrap/article", content=["text.body"]),
    })
    text_map = {"/wrap/article": "lots of body text " * 10}
    struct_map = {
        "/wrap": ("div", {"class": "wrapper"}),
        "/wrap/article": ("article", {"class": "card"}),
    }

    bld = ChunkBuilder(
        tree,
        _text_provider_from_map(text_map),
        structure_provider=_struct_provider_from_map(struct_map),
    )
    chunks = bld.build(snapshot_id="s1")
    reps = {c.representative_xpath for c in chunks}
    # The climb up from /wrap/article to /wrap is harmless (parent adds
    # basically nothing new), so either xpath is acceptable as the root
    # — but there must be exactly one chunk, not two.
    assert len(chunks) == 1


# ---------------------------------------------------------------------------
# Containment prune size gate
# ---------------------------------------------------------------------------


def test_containment_prune_does_not_touch_card_sized_chunks():
    """
    Two chunks, one a strict ancestor of the other, BOTH within the
    hard budget. The containment pruner must NOT drop the outer chunk
    just because there's a deeper one — that would be "filtering out a
    card by mistake", which the user specifically warned about.
    """
    from backend.services.chunk_containment import filter_redundant_rollups

    class _C:
        def __init__(self, xp, sz):
            self.representative_xpath = xp
            self.sz = sz

    coarse = _C("/card", 300)      # under HARD_CHAR_LIMIT
    fine = _C("/card/title", 120)  # strictly inside /card
    out = filter_redundant_rollups(
        [coarse, fine],
        xpath_of=lambda c: c.representative_xpath,
        size_of=lambda c: c.sz,
        min_rollup_size=2 * HARD_CHAR_LIMIT,
    )
    assert len(out) == 2, "size gate failed — coarse card-sized chunk was dropped"


def test_containment_prune_still_drops_oversized_rollup():
    """
    The 59 KB-monster-plus-20-cards shape from the tarot failure still
    prunes correctly under the size gate.
    """
    from backend.services.chunk_containment import filter_redundant_rollups

    class _C:
        def __init__(self, xp, sz):
            self.representative_xpath = xp
            self.sz = sz

    monster = _C("/main/div", 59000)  # way over the gate
    cards = [_C(f"/main/div/ul/li[{i}]/card", 300) for i in range(1, 21)]
    out = filter_redundant_rollups(
        [monster] + cards,
        xpath_of=lambda c: c.representative_xpath,
        size_of=lambda c: c.sz,
        min_rollup_size=2 * HARD_CHAR_LIMIT,
    )
    assert monster not in out
    for c in cards:
        assert c in out
