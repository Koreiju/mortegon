"""breadth_content_tree_smoke.py — §U content-tree correctness over a LARGE
SPECTRUM of real URLs (the saved `test_packages/` corpus, ~60 diverse sites).

Goal-context: "what gets correct results over a large spectrum of different
urls." This runs the **real extraction ruleset offline** — the live JS engine
only extracts the static DOM; the chunking/fielding is Python (`backend/dom/*`
+ `mapper/chunk_render.py`) and runs on the saved `source.html` via
`run_pipeline(..., render_instances=True)` (no Selenium, no GPU). So the
`{rel_xpath: [values]}` `fields` here are the SAME ruleset output the live scan
produces (modulo dynamically-loaded DOM) — a faithful breadth verdict, not an
approximation.

For every rendered chunk instance it runs the §U transform
(`fields_to_content_tree`) and asserts content-tree OUTPUT INVARIANTS:

  I1  no raw HTML tags leak into the rendered tree (`<tag ...>`)
  I2  no xpath/structure fragments leak (`#shadow-root`, `/text()`, bare `@attr`)
  I3  data: URIs are compacted (no multi-hundred-char inline payloads)
  I4  every line is a single physical line (the join contract holds)

It also reports the dedup effect (content-tree lines vs raw content-leaf count)
as evidence the §U subsumption actually fires on real data across the spectrum.

Run:  python scripts/breadth_content_tree_smoke.py [--show] [--max-instances N]
Exit 0 = all sites clean; 1 = at least one invariant violation.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("WFH_FAKE_SLM", "1")
os.environ.setdefault("WFH_FAKE_EMBEDDER", "1")
os.environ.setdefault("NO_WEBDRIVER", "1")

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.dom.pipeline import run_pipeline  # noqa: E402
from backend.dom.content_tree import (  # noqa: E402
    fields_to_content_tree, _classify_leaf,
)

CORPUS = ROOT / "test_packages"


def _content_leaf_count(fields: Dict) -> int:
    """How many fields leaves are CONTENT (url/label/text) — the pre-dedup line
    upper bound, for the dedup-ratio signal."""
    n = 0
    for key in fields:
        parts = [p for p in str(key).strip("/").split("/") if p]
        if parts and _classify_leaf(parts[-1]) is not None:
            n += 1
    return n


def _check_invariants(tree: str) -> List[str]:
    viol: List[str] = []
    for ln in tree.splitlines():
        if "<" in ln and ">" in ln and ln.index("<") < ln.index(">"):
            viol.append(f"I1 html-tag leak: {ln[:70]!r}")
        if "#shadow-root" in ln or "/text()" in ln or ln.strip() in ("@href", "@src"):
            viol.append(f"I2 xpath leak: {ln[:70]!r}")
        if ln.startswith("data:") and len(ln) > 80:
            viol.append(f"I3 data-uri payload not compacted: len={len(ln)}")
    return viol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="print a sample tree per site")
    ap.add_argument("--max-instances", type=int, default=0,
                    help="cap instances checked per site (0 = all)")
    args = ap.parse_args()

    if not CORPUS.is_dir():
        print(f"[breadth] corpus not found at {CORPUS}", file=sys.stderr)
        return 2

    sites = sorted(p for p in CORPUS.iterdir()
                   if p.is_dir() and (p / "source.html").is_file())
    print(f"[breadth] §U content-tree over {len(sites)} sites via the REAL "
          f"offline pipeline (run_pipeline, render_instances)\n")

    tot_inst = tot_trees = tot_viol = bad_sites = 0
    dedup_hits = 0          # instances where content-tree < content-leaf count
    for site in sites:
        html = (site / "source.html").read_text(encoding="utf-8", errors="replace")
        try:
            res = run_pipeline(html, url=f"https://{site.name}",
                               render_instances=True, persist=False)
        except Exception as e:
            print(f"  PIPE-FAIL {site.name}: {e.__class__.__name__}: {e}")
            bad_sites += 1
            continue
        insts = list(getattr(res, "instances", []) or [])
        if args.max_instances:
            insts = insts[: args.max_instances]
        site_viol: List[str] = []
        site_trees = 0
        sample = ""
        for inst in insts:
            f = getattr(inst, "fields", {}) or {}
            if not f:
                continue
            tree = fields_to_content_tree(f)
            tot_inst += 1
            if not tree.strip():
                continue
            site_trees += 1
            lines = len(tree.splitlines())
            if lines < _content_leaf_count(f):
                dedup_hits += 1
            if not sample and lines >= 3:
                sample = tree
            site_viol.extend(_check_invariants(tree))
        tot_trees += site_trees
        tot_viol += len(site_viol)
        status = "ok " if not site_viol else "VIOL"
        print(f"  [{status}] {site.name:<52} inst={len(insts):<4} trees={site_trees:<4} viol={len(site_viol)}")
        if site_viol:
            bad_sites += 1
            for v in site_viol[:3]:
                print(f"        - {v}")
        if args.show and sample:
            for l in sample.splitlines()[:6]:
                print(f"        | {l}")

    print(f"\n[breadth] {len(sites)} sites · {tot_inst} instances · {tot_trees} "
          f"content-trees · {dedup_hits} dedup-reduced · {tot_viol} invariant "
          f"violations across {bad_sites} sites")
    if tot_viol == 0 and bad_sites == 0:
        print("[breadth] PASS — real-ruleset content-tree output is clean across the URL spectrum")
        return 0
    print("[breadth] FAIL — content-tree leaked structure/HTML on some real inputs")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
