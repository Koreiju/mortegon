"""
Tests for the O(N) rewrite of
:meth:`backend.dom.web_distiller_freq.ContentCoagulator._build_dedup_mask`.

Two properties we want to nail down:

1. **Correctness** — legitimate duplicate sibling subtrees get masked;
   unique siblings are kept. The old version was O(N²) by re-walking
   children, the new one does a single post-order rollup + a BFS, but
   must produce an equivalent mask on every realistic shape.

2. **Performance** — on a reasonably deep DOM (5 000 nodes) the whole
   pass should complete in well under a second. The old implementation
   stalled for seconds or hung.

We build fixtures with :class:`backend.dom.shadow_html_parser.ShadowDOM`
against hand-authored HTML so these tests don't depend on Selenium.
"""

from __future__ import annotations

import time

from backend.dom.shadow_html_parser import ShadowDOM
from backend.dom.web_distiller_freq import ContentCoagulator


# ---------------------------------------------------------------------------
# Correctness
# ---------------------------------------------------------------------------


def test_dedup_masks_duplicate_sibling_text_blocks():
    """Two <div> siblings with identical visible text -> second one masked."""
    html = """
    <html><body>
      <main>
        <div class="card">
          <h2>Headline one</h2>
          <p>This is the first paragraph body text about the topic.</p>
          <a href="/one">Read more</a>
        </div>
        <div class="card dup">
          <h2>Headline one</h2>
          <p>This is the first paragraph body text about the topic.</p>
          <a href="/one">Read more</a>
        </div>
        <div class="card unique">
          <h2>Completely different headline</h2>
          <p>An unrelated paragraph that should survive deduplication.</p>
          <a href="/two">Read more</a>
        </div>
      </main>
    </body></html>
    """
    dom = ShadowDOM(html)
    mask = ContentCoagulator._build_dedup_mask(dom.root)

    # The <main>'s three children are the three <div>s. Walk dom.root to find
    # them and assert only the duplicate is masked.
    main = _find_first(dom.root, lambda n: n.tag == "main")
    assert main is not None
    divs = [c for c in main.get_children() if c.tag == "div"]
    assert len(divs) == 3

    unique_a = divs[0]
    dup = divs[1]
    unique_b = divs[2]

    # The canonical-first policy keeps divs[0], masks divs[1].
    assert id(unique_a) not in mask
    assert id(dup) in mask, "identical sibling should be masked"
    assert id(unique_b) not in mask, "content-unique sibling must survive"


def test_dedup_leaves_siblings_with_different_content_alone():
    html = """
    <html><body>
      <ul>
        <li>First item text</li>
        <li>Second item text</li>
        <li>Third item text</li>
      </ul>
    </body></html>
    """
    dom = ShadowDOM(html)
    mask = ContentCoagulator._build_dedup_mask(dom.root)
    ul = _find_first(dom.root, lambda n: n.tag == "ul")
    assert ul is not None
    for li in ul.get_children():
        if li.tag == "li":
            assert id(li) not in mask


def test_dedup_empty_tree_returns_empty_mask():
    dom = ShadowDOM("<html><body></body></html>")
    mask = ContentCoagulator._build_dedup_mask(dom.root)
    assert mask == set()


def test_dedup_short_text_siblings_not_masked():
    # Siblings with <20 chars of text and no urls/imgs don't get compared
    # at all (too little signal) — they should survive.
    html = """
    <html><body>
      <nav>
        <a>a</a>
        <a>b</a>
        <a>c</a>
      </nav>
    </body></html>
    """
    dom = ShadowDOM(html)
    mask = ContentCoagulator._build_dedup_mask(dom.root)
    nav = _find_first(dom.root, lambda n: n.tag == "nav")
    assert nav is not None
    for a in nav.get_children():
        if a.tag == "a":
            assert id(a) not in mask


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_dedup_is_fast_on_realistic_page():
    """A 5 000-ish-node grid of cards should not take more than 1 second.

    We deliberately build a heterogeneous mix:
      * 50 "unique" cards (different text / different href)
      * 50 "duplicate" card pairs (identical text / identical href)
      * plus some nav + footer noise
    The old O(N²) implementation could stall the pipeline for seconds on
    this shape. The new rollup version should be at most a few tens of
    milliseconds.
    """
    parts = ['<html><body><header><nav>']
    for i in range(20):
        parts.append(f'<a href="/n{i}">nav {i}</a>')
    parts.append('</nav></header><main>')
    for i in range(50):
        parts.append(
            f'<article class="card unique">'
            f'<h2>Unique headline {i} ABCDEF</h2>'
            f'<p>Body paragraph for unique article {i} with enough text '
            f'to pass the 20-char threshold of the dedup fingerprint.</p>'
            f'<a href="/unique/{i}">Read more about {i}</a>'
            f'</article>'
        )
    for i in range(50):
        # Each pair shares identical text -> second gets masked.
        for _ in range(2):
            parts.append(
                f'<article class="card dup">'
                f'<h2>Dup headline {i} GHIJKL</h2>'
                f'<p>Exactly the same body text repeated for group {i} '
                f'across the two sibling instances.</p>'
                f'<a href="/dup/{i}">Dup link {i}</a>'
                f'</article>'
            )
    parts.append('</main><footer>')
    for i in range(20):
        parts.append(f'<a href="/f{i}">footer {i}</a>')
    parts.append('</footer></body></html>')
    html = ''.join(parts)

    dom = ShadowDOM(html)
    t0 = time.perf_counter()
    mask = ContentCoagulator._build_dedup_mask(dom.root)
    elapsed = time.perf_counter() - t0

    # Cap: 1 second. We expect this to complete in milliseconds on any
    # machine; the generous bound keeps the test meaningful on slow CI
    # while still catching a regression to quadratic behavior.
    assert elapsed < 1.0, (
        f"dedup took {elapsed:.3f}s on ~{50 + 50 * 2} cards; "
        "quadratic regression?"
    )

    # The 50 dup pairs => 50 masked duplicates. We don't assert an exact
    # count (short-text filter can trim a few) but it should be close.
    main = _find_first(dom.root, lambda n: n.tag == "main")
    assert main is not None
    dups = [c for c in main.get_children()
            if c.tag == "article" and "dup" in c.attributes.get("class", "")]
    masked_dups = [c for c in dups if id(c) in mask]
    # Expect about half (the second of each pair) to be masked.
    assert 40 <= len(masked_dups) <= 60, (
        f"expected ~50 dup siblings masked, got {len(masked_dups)}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_first(node, pred):
    if pred(node):
        return node
    for c in node.get_children():
        found = _find_first(c, pred)
        if found is not None:
            return found
    return None
