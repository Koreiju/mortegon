"""§E.1 — the remaining strategies of the ONE recursive descent.

Verbatim anchor (USER_REQUIREMENTS_VERBATIM.md §E.1): "JSON, bracketed
lists, indented trees, HTML element trees, plain text — all handled by the
same routine."

JSON / markdown / indent-tree landed earlier (test_markdown_tree.py); this
file pins the HTML-element-tree and non-JSON bracketed-list strategies on
the same backend descent, plus their canonical top-level decompositions
(§R.1 commutation anchor). Pure functions, real code, no fakes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.compile_pipeline import (
    compute_rendering_tree,
    decompose_top_level,
    looks_like_bracketed_list,
    looks_like_html_tree,
    parse_bracketed_list,
    parse_html_tree,
)


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def test_html_gate():
    assert looks_like_html_tree("<article><h2>T</h2></article>")
    assert looks_like_html_tree("<img src='x'/>")
    assert not looks_like_html_tree("a < b and b > c")     # prose with <
    assert not looks_like_html_tree("plain text")
    assert not looks_like_html_tree("")


def test_bracket_gate():
    assert looks_like_bracketed_list("[alpha, beta]")       # unquoted → not JSON
    assert looks_like_bracketed_list("(a, b, c)")
    assert not looks_like_bracketed_list('["a", "b"]')      # strict JSON — JSON owns it
    assert not looks_like_bracketed_list("[1, 2, 3]")       # strict JSON
    assert not looks_like_bracketed_list("plain")
    assert not looks_like_bracketed_list("[unclosed")


# ---------------------------------------------------------------------------
# HTML element trees
# ---------------------------------------------------------------------------

def test_html_single_element_text():
    assert parse_html_tree("<p>hello world</p>") == {"p": "hello world"}


def test_html_nested_structure():
    out = parse_html_tree("<article><h2>Title</h2><p>Body text</p></article>")
    assert out == {"article": {"h2": "Title", "p": "Body text"}}


def test_html_repeated_siblings_fold_to_list():
    out = parse_html_tree("<ul><li>one</li><li>two</li><li>three</li></ul>")
    assert out == {"ul": {"li": ["one", "two", "three"]}}


def test_html_interleaved_text_and_children_keeps_both():
    out = parse_html_tree("<div>intro <b>bold</b></div>")
    assert out == {"div": ["intro", {"b": "bold"}]}


def test_html_void_elements_do_not_swallow_siblings():
    out = parse_html_tree("<div><img src='x.png'><p>after</p></div>")
    assert out["div"]["p"] == "after"


def test_html_rendering_strips_markup():
    rendered = compute_rendering_tree(
        "<article><h2>Card Title</h2><p>Card body</p></article>")
    assert "Card Title" in rendered and "Card body" in rendered
    assert "<" not in rendered and ">" not in rendered     # §8D.20 clean text
    assert any(ln.startswith("\t") for ln in rendered.split("\n"))


def test_html_decompose_yields_children_as_entries():
    entries = decompose_top_level(
        "<article><h2>Card Title</h2><p>Card body</p></article>")
    assert [e["key"] for e in entries] == ["h2", "p"]
    assert entries[0]["value"] == "Card Title"


# ---------------------------------------------------------------------------
# Bracketed lists (non-JSON)
# ---------------------------------------------------------------------------

def test_bracketed_simple():
    assert parse_bracketed_list("[alpha, beta, gamma]") == ["alpha", "beta", "gamma"]


def test_bracketed_parens():
    assert parse_bracketed_list("(a, b, c)") == ["a", "b", "c"]


def test_bracketed_nested():
    assert parse_bracketed_list("[a, [b, c], d]") == ["a", ["b", "c"], "d"]


def test_bracketed_quoted_commas_guarded():
    assert parse_bracketed_list("[\"x, y\", z]") == ["x, y", "z"]


def test_bracketed_rendering_strips_syntax():
    rendered = compute_rendering_tree("[alpha, beta, gamma]")
    assert rendered.split("\n") == ["alpha", "beta", "gamma"]
    assert "[" not in rendered and "," not in rendered


def test_bracketed_decompose_positional_entries():
    entries = decompose_top_level("[alpha, beta]")
    assert [e["key"] for e in entries] == ["0", "1"]
    assert [e["value"] for e in entries] == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# Precedence — the one descent never mis-routes a syntax
# ---------------------------------------------------------------------------

def test_strict_json_array_still_owned_by_json():
    # ["a","b"] is valid JSON — the JSON strategy renders it, not the
    # bracketed-list strategy (identical output shape, but decompose
    # entries must come from the parsed JSON values).
    entries = decompose_top_level('["a", "b"]')
    assert [e["value"] for e in entries] == ["a", "b"]


def test_markdown_still_engages_after_new_strategies():
    entries = decompose_top_level("- alpha: 1\n- beta: 2")
    assert [e["key"] for e in entries] == ["alpha", "beta"]


def test_plain_text_still_falls_through():
    assert decompose_top_level("just words, nothing structural") == []
    assert compute_rendering_tree("just prose") == "just prose"


# ---------------------------------------------------------------------------
# §R.1 commutation — HTML → entries → indent-tree re-render agrees
# ---------------------------------------------------------------------------

def test_commutation_html_vs_entries_render():
    """HTML → canonical entries → indent-tree re-render must reproduce the
    direct render MINUS the root level: decompose intentionally splits out
    the root element's CHILDREN (the root tag is implicit in the parent
    card's structural position, §4.5), so the re-render is the direct tree
    dedented by exactly one level."""
    src = "<article><h2>Title</h2><p>Body</p></article>"
    direct = compute_rendering_tree(src)
    direct_lines = direct.split("\n")
    assert direct_lines[0] == "article"
    dedented = "\n".join(ln[1:] for ln in direct_lines[1:])  # strip one tab

    rebuilt = "\n".join(
        f"{e['key']}: {e['value']}" for e in decompose_top_level(src)
    )
    re_rendered = compute_rendering_tree(rebuilt)
    assert re_rendered == dedented, (
        f"--- direct(dedented) ---\n{dedented}\n--- re_rendered ---\n{re_rendered}"
    )
