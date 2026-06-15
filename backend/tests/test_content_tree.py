"""test_content_tree.py — the §U deduplicated content tree, golden I/O.

Binding golden example: ``USER_REQUIREMENTS_VERBATIM.md`` §U. The input is the
``{rel_xpath: [values]}`` extraction the EXISTING ruleset produces for the §U
archive.org result-card ``<article>`` (attribute + text leaves, in document
order, with the title appearing 3× and the stats split into fragments). The
output must be exactly the §U 10-line deduplicated content tree.

Runnable directly: ``python backend/tests/test_content_tree.py``.
"""

import os
import sys

# Make the repo root importable when run directly.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.dom.content_tree import fields_to_content_tree  # noqa: E402


# The existing ruleset's extraction for the §U <article>, in document order.
# (Shadow-DOM steps + wrapper <div>s included exactly as the live scanner
# emits them — see the live capture in HTML_DEDUP_CONTENT_TREE_GOAL.md §1.5.)
_P = "/tile-dispatcher/#shadow-root/div/a"
_T = _P + "/item-tile/#shadow-root/div/div"
_STATS = _T + "/tile-stats/#shadow-root/div"

GOLDEN_FIELDS = {
    # <a href aria-label> — href is a URL unit; aria-label is the title (1st copy)
    _P + "/@href": ["/details/princetonuniver01librgoog"],
    _P + "/@aria-label": ["Princeton University Library : American Library Association visit, June 29, 1916"],
    # <img alt="" src> — alt empty (dropped); src is a URL unit
    _T + "/div/image-block/#shadow-root/div/item-image/#shadow-root/div/img/@src":
        ["https://archive.org/services/img/princetonuniver01librgoog"],
    # <h3 title>text</h3> — title (2nd copy) + text (3rd copy) of the same string
    _T + "/div/div/h3/@title": ["Princeton University Library : American Library Association visit, June 29, 1916"],
    _T + "/div/div/h3/text()": ["Princeton University Library : American Library Association visit, June 29, 1916"],
    # <span title>by ...</span> — title is a subset of the text ("by" extra) → text wins
    _T + "/div2/span/@title": ["Princeton University Library"],
    _T + "/div2/span/text()": ["by Princeton University Library"],
    # tile-stats <p>Item Stats</p>
    _STATS + "/p/text()": ["Item Stats"],
    # mediatype <li>: <p>Mediatype:</p> + icon <p>Text</p> (no @title) → colon-join
    _STATS + "/ul/li/p/text()": ["Mediatype:"],
    _STATS + "/ul/li/tile-mediatype-icon/#shadow-root/div/p/text()": ["Text"],
    # views <li title>: title subsumes the "all-time views:" + "450" fragments
    _STATS + "/ul/li2/@title": ["450 all-time views"],
    _STATS + "/ul/li2/p/span/text()": ["all-time views:"],
    _STATS + "/ul/li2/p/text()": ["450"],
    # favorites <li title>
    _STATS + "/ul/li3/@title": ["0 favorites"],
    _STATS + "/ul/li3/p/span/text()": ["favorites:"],
    _STATS + "/ul/li3/p/text()": ["0"],
    # reviews <li title>
    _STATS + "/ul/li4/@title": ["0 reviews"],
    _STATS + "/ul/li4/p/span/text()": ["reviews:"],
    _STATS + "/ul/li4/p/text()": ["0"],
    # trailing wrapper text
    "/tile-dispatcher/#shadow-root/div/div/text()": ["Press Down Arrow to preview item details"],
}

GOLDEN_OUTPUT = "\n".join([
    "/details/princetonuniver01librgoog",
    "https://archive.org/services/img/princetonuniver01librgoog",
    "Princeton University Library : American Library Association visit, June 29, 1916",
    "by Princeton University Library",
    "Item Stats",
    "Mediatype: Text",
    "450 all-time views",
    "0 favorites",
    "0 reviews",
    "Press Down Arrow to preview item details",
])


def test_u_golden_io():
    got = fields_to_content_tree(GOLDEN_FIELDS)
    assert got == GOLDEN_OUTPUT, (
        "\n--- EXPECTED ---\n" + GOLDEN_OUTPUT + "\n--- GOT ---\n" + got
    )


def test_dedup_collapses_triplicate_title():
    out = fields_to_content_tree(GOLDEN_FIELDS).splitlines()
    title = "Princeton University Library : American Library Association visit, June 29, 1916"
    assert out.count(title) == 1, "title (aria-label==h3@title==h3 text) must appear once"


def test_href_and_src_surfaced_as_content():
    out = fields_to_content_tree(GOLDEN_FIELDS).splitlines()
    assert out[0] == "/details/princetonuniver01librgoog"
    assert out[1] == "https://archive.org/services/img/princetonuniver01librgoog"


def test_empty_alt_contributes_nothing():
    f = {"/x/img/@alt": [""], "/x/img/@src": ["http://e/i.png"]}
    assert fields_to_content_tree(f) == "http://e/i.png"


def test_label_wins_on_token_equality():
    # <li title="450 all-time views"> over fragments "all-time views:" + "450"
    f = {
        "/ul/li/@title": ["450 all-time views"],
        "/ul/li/p/span/text()": ["all-time views:"],
        "/ul/li/p/text()": ["450"],
    }
    assert fields_to_content_tree(f) == "450 all-time views"


def test_empty_fields():
    assert fields_to_content_tree({}) == ""


def test_data_uri_compacted_to_mediatype_marker():
    # an inline SVG icon src: keep the fact of media, drop the giant payload
    big = "data:image/svg+xml,%3csvg%20viewBox='0%200%20100%20100'" + "%3c" * 200
    f = {"/x/img/@src": [big], "/x/h3/text()": ["Title"]}
    out = fields_to_content_tree(f).splitlines()
    assert out[0] == "data:image/svg+xml", out
    assert "Title" in out


if __name__ == "__main__":
    print("=== content tree for the §U fields ===")
    print(fields_to_content_tree(GOLDEN_FIELDS))
    print("=== running tests ===")
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
