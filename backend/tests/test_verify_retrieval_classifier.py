"""
Tests for :mod:`scripts.verify_retrieval` -- card/menu classifier and the
cross-pattern Jaccard near-duplicate heuristic.

These are deliberately small, synthetic fixtures. The point is to catch
regressions in the classifier thresholds before they silently misclassify
results in the tail-end verification runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ isn't a package; add the project root so we can "from
# scripts.verify_retrieval import ...".
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.verify_retrieval import (  # noqa: E402
    classify_hit,
    jaccard,
    _shingles,
)


# ---------------------------------------------------------------------------
# classify_hit
# ---------------------------------------------------------------------------


def test_classify_short_anchor_is_menu():
    html = '<a href="/pricing" class="nav-link">Pricing</a>'
    text = "Pricing"
    assert classify_hit(html, text) == "menu"


def test_classify_short_li_is_menu():
    html = '<li><a href="#">Docs</a></li>'
    assert classify_hit(html, "Docs") == "menu"


def test_classify_nav_wrapper_is_menu():
    html = '<nav><a href="#">Home</a><a href="#">About</a></nav>'
    assert classify_hit(html, "Home About") == "menu"


def test_classify_article_with_body_is_card():
    html = (
        '<article><h2>Daily love horoscope</h2>'
        '<p>Today your sign is drawn toward new connections...</p></article>'
    )
    text = (
        "Daily love horoscope Today your sign is drawn toward new "
        "connections and lingering questions about an old flame."
    )
    assert classify_hit(html, text) == "card"


def test_classify_heading_and_paragraph_is_card():
    html = '<section><h1>Title</h1><p>' + ("body text " * 20) + '</p></section>'
    text = "Title " + "body text " * 20
    assert classify_hit(html, text) == "card"


def test_classify_plain_div_with_long_text_is_other():
    # No <p>/<h*>/<article>/etc. and starts with <div>, so it doesn't match
    # either rule cleanly.
    html = '<div>' + "X" * 500 + '</div>'
    text = "X" * 500
    assert classify_hit(html, text) == "other"


def test_classify_empty_inputs_is_other():
    assert classify_hit("", "") == "other"
    assert classify_hit(None, None) == "other"  # defensive


def test_classify_long_anchor_with_description_is_not_menu():
    # A wrapping <a> that encloses a real card body (120+ chars of text)
    # is a product card / blog-post card, not a menu item.
    html = (
        '<a href="/posts/1"><h3>Five Minute Tarot</h3>'
        '<p>A short guide to the major arcana with quick card meanings.</p></a>'
    )
    text = (
        "Five Minute Tarot A short guide to the major arcana with quick "
        "card meanings that you can read at a glance."
    )
    # Not "menu" -- text > 40 chars -- and has <h3>/<p> + text >= 80 => "card".
    assert classify_hit(html, text) == "card"


# ---------------------------------------------------------------------------
# Jaccard / shingles
# ---------------------------------------------------------------------------


def test_shingles_small_string_returns_tokens():
    s = _shingles("hello world")  # only 2 tokens, k=3 -> fallback to tokens
    assert s == {"hello", "world"}


def test_shingles_produces_3grams():
    s = _shingles("the quick brown fox jumps", k=3)
    assert s == {"the quick brown", "quick brown fox", "brown fox jumps"}


def test_jaccard_identical_is_one():
    a = _shingles("the quick brown fox jumps")
    assert jaccard(a, a) == 1.0


def test_jaccard_disjoint_is_zero():
    a = _shingles("the quick brown fox")
    b = _shingles("completely different words here")
    assert jaccard(a, b) == 0.0


def test_jaccard_partial_overlap_between_0_and_1():
    a = _shingles("alpha beta gamma delta")
    b = _shingles("alpha beta gamma epsilon")  # shares the first 3-gram
    score = jaccard(a, b)
    assert 0.0 < score < 1.0


def test_jaccard_both_empty_is_one():
    assert jaccard(set(), set()) == 1.0
