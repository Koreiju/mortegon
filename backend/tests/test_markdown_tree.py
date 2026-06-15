"""§R.5 — markdown-gesture outline trees (backend strategy).

Verbatim anchor (USER_REQUIREMENTS_VERBATIM.md §R.5): "when tree structures
are modified with markdown editor gestures like dashes, tabs, numbers, and
newlines with trailing text that aren't other newlines, the structure of the
computation graph, the other side of the dialectic representation scheme,
updates accordingly."

Pure-function tests over the real parser — no mocks anywhere (§Q.1 lane:
these functions have no subsystem dependencies to fake).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.compile_pipeline import (
    compute_rendering_tree,
    decompose_top_level,
    looks_like_markdown_tree,
    parse_markdown_tree,
)


# ---------------------------------------------------------------------------
# Gesture gate
# ---------------------------------------------------------------------------

def test_gate_dash_gesture():
    assert looks_like_markdown_tree("- alpha\n- beta")


def test_gate_numbered_gesture():
    assert looks_like_markdown_tree("1. first\n2. second")
    assert looks_like_markdown_tree("1) first\n2) second")


def test_gate_tab_gesture_without_bullets():
    assert looks_like_markdown_tree("opener\n\tnested line")


def test_gate_rejects_pure_prose():
    assert not looks_like_markdown_tree("just one prose sentence")
    # Multi-line prose without any indent/marker gesture is NOT an outline.
    assert not looks_like_markdown_tree("line one of prose\nline two of prose")


def test_gate_rejects_empty():
    assert not looks_like_markdown_tree("")
    assert not looks_like_markdown_tree("\n\n")


# ---------------------------------------------------------------------------
# Dash trees
# ---------------------------------------------------------------------------

def test_dash_kv_run_becomes_dict():
    out = parse_markdown_tree("- alpha: 1\n- beta: two")
    assert out == {"alpha": "1", "beta": "two"}


def test_dash_plain_run_becomes_list():
    out = parse_markdown_tree("- first\n- second\n- third")
    assert out == ["first", "second", "third"]


def test_dash_nesting_via_tabs():
    out = parse_markdown_tree("- parent:\n\t- child_a: 1\n\t- child_b: 2\n- flat: 3")
    assert out == {"parent": {"child_a": "1", "child_b": "2"}, "flat": "3"}


def test_dash_nesting_via_spaces():
    out = parse_markdown_tree("- parent:\n  - child_a: 1\n  - child_b: 2")
    assert out == {"parent": {"child_a": "1", "child_b": "2"}}


# ---------------------------------------------------------------------------
# Numbered trees
# ---------------------------------------------------------------------------

def test_numbered_items_keep_text_order():
    out = parse_markdown_tree("1. first step\n2. second step\n3. third step")
    assert out == ["first step", "second step", "third step"]


def test_numbered_with_nested_dashes():
    out = parse_markdown_tree("1. step one\n\t- detail: a\n2. step two")
    assert out == [{"step one": {"detail": "a"}}, "step two"]


# ---------------------------------------------------------------------------
# Newline-with-trailing-text gesture (bare lines as siblings); blank
# newlines are non-structural.
# ---------------------------------------------------------------------------

def test_bare_trailing_text_lines_are_siblings():
    out = parse_markdown_tree("- alpha: 1\nbare sibling line\n- beta: 2")
    # Mixed run (not all kv) → list, order preserved.
    assert out == ["alpha: 1", "bare sibling line", "beta: 2"]


def test_blank_newlines_are_non_structural():
    out = parse_markdown_tree("- a: 1\n\n\n- b: 2")
    assert out == {"a": "1", "b": "2"}


def test_inline_value_plus_children_keeps_both():
    out = parse_markdown_tree("- key: inline\n\t- sub: x")
    assert out == {"key": ["inline", {"sub": "x"}]}


# ---------------------------------------------------------------------------
# Rendering integration (§8D.20 syntax-free print over §R.5 outlines)
# ---------------------------------------------------------------------------

def test_rendering_tree_strips_markdown_syntax():
    rendered = compute_rendering_tree("- alpha: 1\n- beta:\n\t- gamma: 2")
    # Keys on their own lines, values one tab deeper, no dash markers or
    # colon syntax surviving the §8D.20 print.
    assert "alpha" in rendered and "gamma" in rendered
    lines = rendered.split("\n")
    assert not any(ln.lstrip("\t").startswith("- ") for ln in lines)
    assert not any(":" in ln for ln in lines)
    assert any(ln.startswith("\t") for ln in lines)  # depth present


def test_rendering_tree_plain_prose_passthrough():
    assert compute_rendering_tree("plain prose stays put") == "plain prose stays put"


def test_rendering_tree_json_still_wins():
    rendered = compute_rendering_tree('{"k": "v"}')
    assert rendered.split("\n")[0] == "k"


# ---------------------------------------------------------------------------
# Canonical top-level decomposition (§R.1 commutation anchor)
# ---------------------------------------------------------------------------

def test_decompose_markdown_top_level():
    entries = decompose_top_level("- alpha: 1\n- beta:\n\t- gamma: 2")
    assert [e["key"] for e in entries] == ["alpha", "beta"]
    assert entries[0]["value"] == "1"
    assert "gamma" in entries[1]["value"]


def test_decompose_json_object_top_level():
    entries = decompose_top_level('{"a": 1, "b": {"c": 2}}')
    assert [e["key"] for e in entries] == ["a", "b"]


def test_decompose_indent_tree_top_level():
    entries = decompose_top_level("a: 1\nb: 2\n\tnested under b")
    assert [e["key"] for e in entries] == ["a", "b"]
    assert "nested under b" in entries[1]["value"]


def test_decompose_prose_yields_nothing():
    assert decompose_top_level("no structure here, just words") == []


def test_decompose_numbered_list_uses_labels():
    entries = decompose_top_level("1. first\n2. second")
    assert [e["value"] for e in entries] == ["first", "second"]


# ---------------------------------------------------------------------------
# §R.1 — commutation: markdown → entries → re-render agrees with the
# direct markdown render (representation order doesn't change the record).
# ---------------------------------------------------------------------------

def test_commutation_markdown_vs_entries_render():
    src = "- alpha: 1\n- beta:\n\t- gamma: 2\n\t- delta: 3"
    direct = compute_rendering_tree(src)
    # Rebuild from the decomposed entries as an indent tree (the panel's
    # post-expand parent form) and render again.
    rebuilt = "\n".join(
        f"{e['key']}: {e['value']}" if "\n" not in e["value"]
        else f"{e['key']}:\n" + "\n".join("\t" + ln for ln in e["value"].split("\n"))
        for e in decompose_top_level(src)
    )
    re_rendered = compute_rendering_tree(rebuilt)
    assert direct.split() == re_rendered.split(), (
        f"commutation broke:\n--- direct ---\n{direct}\n--- re_rendered ---\n{re_rendered}"
    )
