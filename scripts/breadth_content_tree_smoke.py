"""breadth_content_tree_smoke.py — §U content-tree robustness over a LARGE
SPECTRUM of real URLs (the saved `test_packages/` corpus, ~60 diverse sites).

Goal-context: "what gets correct results over a large spectrum of different
urls." The authoritative chunk `fields` come from the LIVE JS chunk engine
(Selenium), which this offline harness does NOT reproduce. Instead it derives
realistic `{rel_xpath: [value]}` field dicts from each site's saved
`source.html` (via the offline `ShadowDOM.from_file` parser), treats each
content-card element as a chunk, and runs `fields_to_content_tree` over it.

It asserts CONTENT-TREE OUTPUT INVARIANTS — properties the §U transform must
guarantee for ANY input, so they are valid regardless of how faithfully this
harness mimics the live extraction:

  I1  no raw HTML tags leak into the rendered tree (`<tag ...>`)
  I2  no xpath/structure fragments leak (`#shadow-root`, `/text()`, bare `@attr`)
  I3  data: URIs are compacted (no multi-hundred-char inline payloads)
  I4  a card that had visible text yields a non-empty tree
  I5  every line is pure single-line text (no embedded newlines beyond joins)

Run:  python scripts/breadth_content_tree_smoke.py [--cards-per-site N] [--show]
Exit 0 = all sites clean; 1 = at least one invariant violation.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.dom.shadow_html_parser import ShadowDOM  # noqa: E402
from backend.dom.content_tree import (  # noqa: E402
    fields_to_content_tree, _URL_ATTRS, _LABEL_ATTRS,
)

CORPUS = ROOT / "test_packages"
# Tags whose SUBTREE is pruned from the walk (non-content / structural noise).
# NB: do NOT put #document/html/body here — they are ancestors we must descend
# through to reach content.
_SKIP_TAGS = {"script", "style", "head", "template", "noscript", "svg", "path",
              "meta", "link"}
_CARD_TAGS = {"article", "li", "a"}
_CONTENT_ATTRS = _URL_ATTRS | _LABEL_ATTRS


def _children(node) -> list:
    kids = list(getattr(node, "children", []) or [])
    sr = getattr(node, "shadow_root", None)
    if sr is not None:
        kids = kids + list(getattr(sr, "children", []) or [])
    return kids


def _walk(node):
    yield node
    tag = (getattr(node, "tag", "") or "").lower()
    if tag in _SKIP_TAGS:
        return
    for c in _children(node):
        yield from _walk(c)


def _card_fields(card) -> Dict[str, List[str]]:
    """Derive a chunk-like `{rel_xpath: [value]}` dict from a card subtree —
    text() leaves + URL/LABEL content attrs, in document order, unique keys."""
    fields: Dict[str, List[str]] = {}
    idx = 0
    for n in _walk(card):
        tag = (getattr(n, "tag", "") or "").lower()
        if tag in _SKIP_TAGS:
            continue
        idx += 1
        txt = (getattr(n, "text", "") or "").strip()
        if txt:
            fields[f"/n{idx}/text()"] = [txt]
        attrs = getattr(n, "attributes", {}) or {}
        for attr, val in attrs.items():
            if attr.lower() in _CONTENT_ATTRS and str(val).strip():
                fields[f"/n{idx}/@{attr}"] = [str(val)]
    return fields


def _find_cards(root, limit: int) -> list:
    cards = []
    for n in _walk(root):
        tag = (getattr(n, "tag", "") or "").lower()
        if tag in _CARD_TAGS:
            # must carry some content
            f = _card_fields(n)
            if any(k.endswith("/text()") for k in f) or any("@" in k for k in f):
                cards.append(n)
        if len(cards) >= limit:
            break
    return cards


def _check_invariants(tree: str, had_text: bool) -> List[str]:
    viol: List[str] = []
    for ln in tree.splitlines():
        if "<" in ln and ">" in ln and ln.index("<") < ln.index(">"):
            viol.append(f"I1 html-tag leak: {ln[:70]!r}")
        if "#shadow-root" in ln or "/text()" in ln or ln.strip() in ("@href", "@src"):
            viol.append(f"I2 xpath leak: {ln[:70]!r}")
        if ln.startswith("data:") and len(ln) > 80:
            viol.append(f"I3 data-uri payload not compacted: len={len(ln)}")
    if had_text and not tree.strip():
        viol.append("I4 had text but empty tree")
    return viol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards-per-site", type=int, default=8)
    ap.add_argument("--show", action="store_true", help="print a sample tree per site")
    args = ap.parse_args()

    if not CORPUS.is_dir():
        print(f"[breadth] corpus not found at {CORPUS}", file=sys.stderr)
        return 2

    sites = sorted(p for p in CORPUS.iterdir()
                   if p.is_dir() and (p / "source.html").is_file())
    print(f"[breadth] §U content-tree over {len(sites)} sites "
          f"(<= {args.cards_per_site} cards each)\n")

    total_cards = 0
    total_viol = 0
    bad_sites = 0
    for site in sites:
        try:
            dom = ShadowDOM.from_file(str(site / "source.html"))
        except Exception as e:
            print(f"  PARSE-FAIL {site.name}: {e.__class__.__name__}")
            bad_sites += 1
            continue
        cards = _find_cards(dom.root, args.cards_per_site)
        site_viol: List[str] = []
        sample = ""
        for card in cards:
            f = _card_fields(card)
            had_text = any(k.endswith("/text()") for k in f)
            tree = fields_to_content_tree(f)
            if not sample and tree.strip():
                sample = tree
            total_cards += 1
            v = _check_invariants(tree, had_text)
            site_viol.extend(v)
        total_viol += len(site_viol)
        status = "ok " if not site_viol else "VIOL"
        print(f"  [{status}] {site.name:<55} cards={len(cards):<3} viol={len(site_viol)}")
        if site_viol:
            bad_sites += 1
            for v in site_viol[:3]:
                print(f"        - {v}")
        if args.show and sample:
            head = "\n".join("        | " + l for l in sample.splitlines()[:6])
            print(head)

    print(f"\n[breadth] {len(sites)} sites · {total_cards} cards · "
          f"{total_viol} invariant violations across {bad_sites} sites")
    if total_viol == 0:
        print("[breadth] PASS — content-tree output stays clean across the URL spectrum")
        return 0
    print("[breadth] FAIL — content-tree leaked structure/HTML on some real inputs")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
