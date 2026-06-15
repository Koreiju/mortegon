"""
scripts/verify_retrieval.py -- tail-end quality check on a populated DB.

Runs the two proofs the user asked for after the HTML-budget chunker +
containment-prune work:

1. **Multi-query retrieval returns result cards, not menu items.**
   For each query in ``QUERIES`` we score every persisted chunk with the
   same retrieval path the UI uses (``retrieve_instances_by_urls``) and
   inspect the top-5 hits per URL. "Menu item" heuristic = tag is ``<a>``
   / ``<li>`` with a single link child + no surrounding text of any
   length. "Card" heuristic = at least one text-carrying element with a
   non-trivial body. We print the classification beside each hit so the
   operator can eyeball false positives.

2. **Per-chunk HTML independence.** We sample one instance per chunk
   pattern, print its ``html_raw`` + ``rendered_text``, and run a cheap
   near-duplicate scan (Jaccard over ``html_raw`` token-shingles). If
   two chunks look >80% identical, we flag them -- they're either a
   legitimate repeat pattern of the page (e.g. 20 tarot cards) or a
   sign that the chunker is emitting redundant rollups.

This script does NOT modify the DB and it does NOT add any new
deduplication. It's a reporting tool.

Usage::

    # populate the DB first
    python demo_scanner.py

    # then run the verifier
    python scripts/verify_retrieval.py
    python scripts/verify_retrieval.py --queries "zodiac,horoscope,pricing"
    python scripts/verify_retrieval.py --url https://... --top-k 10
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.database as database  # noqa: E402
from backend.mapper.chunk_builder import HARD_CHAR_LIMIT, HARD_TOKEN_LIMIT  # noqa: E402
from backend.services.chunk_instance_persistence import (  # noqa: E402
    ChunkInstanceRow,
    load_all_instances,
    load_instances_by_urls,
)
from backend.services.chunk_retrieval import (  # noqa: E402
    InstanceHit,
    retrieve_instances_by_urls,
)

logging.basicConfig(level=logging.WARNING)

# Sensible defaults that exercise different slices of a typical scanned page.
# Feel free to pass --queries to override.
DEFAULT_QUERIES = [
    "love reading",
    "zodiac sign daily horoscope",
    "tarot card meaning",
    "pricing subscription plan",
    "sign up account",
]


# ---------------------------------------------------------------------------
# Card / menu classifier
# ---------------------------------------------------------------------------


_MENU_TAG_HINT = re.compile(
    r"^\s*<(?:a|li|nav|ul|button)\b", re.IGNORECASE,
)
_TEXT_TAG_RE = re.compile(
    r"<(?:p|h[1-6]|span|article|section|figcaption|blockquote)\b",
    re.IGNORECASE,
)


def classify_hit(html: str, text: str) -> str:
    """Cheap "card vs menu" classifier.

    We want a label, not a dedup call. The rule set is:

    * If the outer tag is ``<a>`` / ``<li>`` / ``<nav>`` / ``<ul>`` and
      the visible text is <= 40 chars, this is almost certainly a menu
      item.
    * If the HTML contains at least one ``<p>`` / ``<h*>`` / ``<article>``
      AND the rendered text is >= 80 chars, it's a content card.
    * Otherwise it's ambiguous (``other``). That bucket is honest about
      the fact that a lot of real content on modern pages is in generic
      divs with no semantic tag.
    """
    text = (text or "").strip()
    html_stripped = (html or "").lstrip()
    if _MENU_TAG_HINT.match(html_stripped) and len(text) <= 40:
        return "menu"
    if _TEXT_TAG_RE.search(html or "") and len(text) >= 80:
        return "card"
    return "other"


# ---------------------------------------------------------------------------
# Near-duplicate scan
# ---------------------------------------------------------------------------


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _shingles(s: str, k: int = 3) -> set:
    toks = _TOKEN_RE.findall(s or "")
    if len(toks) < k:
        return set(toks)
    return {" ".join(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


# ---------------------------------------------------------------------------
# Pretty-printers
# ---------------------------------------------------------------------------


def _trunc(s: str, n: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def print_retrieval_proof(
    conn, urls: List[str], queries: List[str], top_k: int,
) -> None:
    print("=" * 72)
    print(f"(1) Multi-query retrieval proof — {len(queries)} quer(y|ies)")
    print("=" * 72)

    tally: Dict[str, int] = defaultdict(int)
    for q in queries:
        print(f"\n  query: {q!r}")
        hits: List[InstanceHit] = retrieve_instances_by_urls(
            conn, urls, query=q, limit=top_k,
        )
        if not hits:
            print("    (no hits)")
            continue
        for h in hits:
            kind = classify_hit(h.html_raw, h.rendered_text)
            tally[kind] += 1
            text_preview = _trunc(h.rendered_text, 80)
            html_preview = _trunc(h.html_raw, 120)
            tag = f"[{kind:<5}]"
            print(
                f"    {h.score:+.3f} {tag} "
                f"{h.absolute_xpath}"
            )
            print(f"            text: {text_preview!r}")
            print(f"            html: {html_preview!r}")

    total = sum(tally.values()) or 1
    print("\n  summary of top hits across all queries:")
    for k in ("card", "menu", "other"):
        c = tally.get(k, 0)
        pct = 100.0 * c / total
        print(f"    {k:<5}  {c:>3}  ({pct:5.1f}%)")
    card_pct = 100.0 * tally.get("card", 0) / total
    if card_pct < 40.0:
        print(
            "\n  WARNING: fewer than 40% of top hits classify as real "
            "content cards. Retrieval may be surfacing menu noise."
        )


def print_independence_proof(rows: List[ChunkInstanceRow]) -> None:
    print("\n" + "=" * 72)
    print(f"(2) Per-chunk HTML independence — {len(rows)} instance(s)")
    print("=" * 72)

    # One sample per pattern_id (falls back to chunk_id if pattern_id empty).
    by_pattern: Dict[str, ChunkInstanceRow] = {}
    pattern_counts: Dict[str, int] = defaultdict(int)
    for r in rows:
        key = r.pattern_id or r.chunk_id or r.absolute_xpath
        pattern_counts[key] += 1
        # Keep the first occurrence -- stable sample.
        by_pattern.setdefault(key, r)

    if not by_pattern:
        print("  (no patterns)")
        return

    print(
        f"\n  {len(by_pattern)} distinct pattern(s) across "
        f"{sum(pattern_counts.values())} instance(s).\n"
    )

    sizes: List[Tuple[str, int]] = []
    for key, sample in by_pattern.items():
        n_html = len(sample.html_raw or "")
        n_text = len(sample.rendered_text or "")
        n_inst = pattern_counts[key]
        over_budget = " OVER" if n_html > HARD_CHAR_LIMIT else ""
        sizes.append((key, n_html))
        print(
            f"  pattern [{n_inst}x instance(s)] html={n_html} text={n_text}"
            f"{over_budget}"
        )
        print(f"    sample xpath: {sample.absolute_xpath}")
        print(f"    url:          {sample.url}")
        print(f"    html_raw:     {_trunc(sample.html_raw, 180)!r}")
        print(f"    rendered:     {_trunc(sample.rendered_text, 120)!r}")
        print()

    over = [(k, n) for k, n in sizes if n > HARD_CHAR_LIMIT]
    if over:
        print(f"  WARNING: {len(over)} pattern sample(s) exceed HARD_CHAR_LIMIT "
              f"({HARD_CHAR_LIMIT}):")
        for k, n in over:
            print(f"    {n:>6} chars  {k}")

    # Near-duplicate scan. We only flag non-siblings — two instances of
    # the *same* pattern are expected to be near-identical (e.g. 20
    # tarot cards with swapped titles), so those don't count. Cross-
    # pattern near-duplicates are the worrying ones.
    print("  cross-pattern near-duplicate scan (Jaccard >= 0.80 on "
          "html_raw 3-shingles):")
    keys = list(by_pattern.keys())
    shingle_cache: Dict[str, set] = {
        k: _shingles(by_pattern[k].html_raw or "") for k in keys
    }
    flagged = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            j_score = jaccard(shingle_cache[keys[i]], shingle_cache[keys[j]])
            if j_score >= 0.80:
                flagged += 1
                print(f"    {j_score:.2f}  {keys[i]}  <->  {keys[j]}")
    if not flagged:
        print("    (none — patterns are structurally independent)")
    elif flagged > 10:
        print(
            f"\n  WARNING: {flagged} cross-pattern duplicates flagged. "
            "If these aren't legit page-wide repeats, the chunker may be "
            "emitting redundant rollups."
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _collect_urls(rows: List[ChunkInstanceRow]) -> List[str]:
    seen: List[str] = []
    for r in rows:
        if r.url and r.url not in seen:
            seen.append(r.url)
    return seen


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--queries", type=str, default=None,
        help="Comma-separated list of queries. "
             f"Default: {DEFAULT_QUERIES}",
    )
    ap.add_argument(
        "--url", type=str, default=None,
        help="Scope retrieval to a single URL. "
             "Default: all URLs present in the DB.",
    )
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args(argv)

    queries = (
        [q.strip() for q in args.queries.split(",") if q.strip()]
        if args.queries else list(DEFAULT_QUERIES)
    )

    database.init_db()
    conn = database.get_connection()

    all_rows = load_all_instances(conn)
    print(
        f"verify_retrieval: DB holds {len(all_rows)} ChunkInstance row(s). "
        f"Budget: {HARD_CHAR_LIMIT} chars / {HARD_TOKEN_LIMIT} tokens."
    )
    if not all_rows:
        print(
            "No chunks in DB. Run `python demo_scanner.py` first to "
            "populate, then re-run this verifier."
        )
        return 0

    urls = [args.url] if args.url else _collect_urls(all_rows)
    if args.url:
        rows = load_instances_by_urls(conn, [args.url])
    else:
        rows = all_rows

    print_retrieval_proof(conn, urls, queries, args.top_k)
    print_independence_proof(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
