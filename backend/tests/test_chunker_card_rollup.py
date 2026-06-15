"""
Repro test for the tarot.com failure: chunker emits leaf-level chunks
(`.../ul/li/row/column/a`, `.../li/a`) instead of rolling up to the
repeating card level (`.../ul/li`). We feed a synthetic trie shaped
exactly like the real tarot result list and assert the chunker returns
*one* chunk pattern at the card level.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.mapper.chunk_builder import ChunkBuilder


def _t(xpath, *, content=None, **children):
    out: Dict[str, Any] = {"_xpath": xpath}
    if content:
        out["_content"] = list(content)
    out.update(children)
    return out


def _build_card(i: int) -> Dict[str, Any]:
    """One sui-result card — image column + details column (breadcrumbs + title + body)."""
    base = f"/html/body/main/div/ul/li[{i}]"
    return _t(
        base,
        **{
            "row": _t(
                f"{base}/row",
                **{
                    "column[1]": _t(
                        f"{base}/row/column[1]",
                        **{
                            "a": _t(
                                f"{base}/row/column[1]/a",
                                content=["urls.link"],
                                **{
                                    "img[1]": _t(
                                        f"{base}/row/column[1]/a/img[1]",
                                        content=["media.image"],
                                    ),
                                    "img[2]": _t(
                                        f"{base}/row/column[1]/a/img[2]",
                                        content=["media.image"],
                                    ),
                                },
                            ),
                        },
                    ),
                    "column[2]": _t(
                        f"{base}/row/column[2]",
                        **{
                            "li[1]": _t(
                                f"{base}/row/column[2]/li[1]",
                                **{
                                    "a[1]": _t(
                                        f"{base}/row/column[2]/li[1]/a[1]",
                                        content=["urls.link", "text.anchor"],
                                    ),
                                    "a[2]": _t(
                                        f"{base}/row/column[2]/li[1]/a[2]",
                                        content=["urls.link", "text.anchor"],
                                    ),
                                },
                            ),
                            "li[2]": _t(
                                f"{base}/row/column[2]/li[2]",
                                **{
                                    "a": _t(
                                        f"{base}/row/column[2]/li[2]/a",
                                        content=["urls.link"],
                                        **{
                                            "h3": _t(
                                                f"{base}/row/column[2]/li[2]/a/h3",
                                                content=["text.heading"],
                                            ),
                                            "p": _t(
                                                f"{base}/row/column[2]/li[2]/a/p",
                                                content=["text.body"],
                                            ),
                                        },
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        },
    )


def _build_tarot_like_trie(n_cards: int = 20) -> Dict[str, Any]:
    ul_children = {f"li[{i}]": _build_card(i)["/html/body/main/div/ul/li[{i}]".format(i=i)]
                   if False else _build_card(i)
                   for i in range(1, n_cards + 1)}
    return _t("/",
              html=_t("/html",
                      body=_t("/html/body",
                              main=_t("/html/body/main",
                                      div=_t("/html/body/main/div",
                                             ul=_t("/html/body/main/div/ul", **ul_children))))))


def _flat_text_provider(xp: str, cats: List[str]) -> str:
    # Unique value per xpath so the summary aggregation doesn't dedupe
    # 20 cards' worth of fields into a single line. We want the
    # aggregate summary at the `/ul` / `/html` level to actually be big
    # (20 unique texts × N fields per card) so the chunker is forced to
    # recurse down to the per-card `<li>` level.
    prefix = (cats[0] if cats else "x").split(".", 1)[0]
    return f"{prefix}-{xp}"


def _flat_struct_provider(xp: str):
    # Cards produce some attr load so the budget actually bites.
    if xp.endswith("]") and "/ul/li[" in xp and xp.count("/") == 6:
        return ("li", {"class": "sui-result"})
    if xp.endswith("/a") or "/a[" in xp:
        return ("a", {"href": "/x", "data-label": "link"})
    if xp.endswith("/img") or "/img[" in xp:
        return ("img", {"src": "/i.jpg", "alt": "thumb"})
    return ("div", {})


def test_card_list_rolls_up_to_li_not_leaf_link():
    """A 20-card result list must produce a chunk whose pattern is the
    card root (`.../ul/li`) covering the full cohort — the original
    tarot.com failure emitted leaf chunks INSTEAD of the rollup.

    NOTE — the chunker now legitimately emits multi-granularity
    companions BELOW the card root (`.../li/row`, `.../a`, …): the
    containment design keeps coarse/fine pairs under the hard budget and
    only prunes oversized monsters (`filter_redundant_rollups`
    size-gate; see test_chunker_html_budget's containment tests). The
    surviving contract is therefore: (a) the card rollup EXISTS with the
    full cohort; (b) nothing rolls up ABOVE the card level (the monster
    failure mode); (c) every companion is a DESCENDANT of the card
    pattern (the cohort grouping is never fragmented across foreign
    subtrees)."""
    trie = _build_tarot_like_trie(n_cards=20)
    cb = ChunkBuilder(
        trie,
        text_provider=_flat_text_provider,
        structure_provider=_flat_struct_provider,
    )
    chunks = cb.build(snapshot_id="test")

    print("\n--- emitted chunks ---")
    for ch in chunks:
        print(f"  pattern={ch.pattern}  members={len(ch.member_xpaths)}  "
              f"rep={ch.representative_xpath}")

    CARD = "/html/body/main/div/ul/li"
    card_level_chunks = [c for c in chunks if c.pattern == CARD]

    # (a) The card pattern is present and covers ALL 20 cards.
    assert card_level_chunks, (
        f"No chunk rolled up to {CARD}. "
        f"Got patterns: {[c.pattern for c in chunks]}"
    )
    assert card_level_chunks[0].commutation_count == 20
    assert len(card_level_chunks[0].member_xpaths) == 20

    # (b) Nothing rolled up ABOVE the card level — a /ul or /div pattern
    # would be the monster-rollup failure mode.
    above = [c.pattern for c in chunks
             if c.pattern != CARD and not c.pattern.startswith(CARD + "/")]
    assert not above, f"chunk(s) rolled up past the card level: {above}"

    # (c) Every companion chunk is a strict descendant of the card
    # pattern (multi-granularity is fine; cross-subtree fragmentation
    # is not).
    for c in chunks:
        assert c.pattern == CARD or c.pattern.startswith(CARD + "/"), (
            f"chunk pattern outside the card subtree: {c.pattern}"
        )
