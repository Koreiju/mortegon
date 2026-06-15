"""
demo_agent_loop.py -- Phase 5 console demo of the full 4-node loop.

Runs a single intent against a URL and prints every intermediate stage:

    Observation  - scan stats (trie pattern count, chunk count, wall time)
    Perception   - top-10 labeled patterns with role/category/summary
    Cognition    - intent -> top-5 candidates with cosine scores -> final plan
    Action       - xpath used + whether the Selenium click landed

Usage
-----
    python -m backend.demos.demo_agent_loop \
        --url https://www.tarot.com/ \
        --intent "click the first tarot card"

    # Without Selenium (parse a local HTML file):
    python -m backend.demos.demo_agent_loop \
        --no-browser path/to/page.html \
        --intent "click the first tarot card"
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent.langgraph_loop import AgentDeps, run_agent_once


BANNER = "=" * 72


def _hr(title: str) -> None:
    print()
    print(BANNER)
    print(f"  {title}")
    print(BANNER)


def _truncate(text: str, limit: int = 100) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "..."
    return text


def _print_observation(state: Dict[str, Any]) -> None:
    _hr("Observation")
    r = state.get("pipeline_result")
    if r is None:
        print("(no pipeline result)")
        return
    summary = r.as_summary()
    for k, v in summary.items():
        if k == "diff":
            continue
        print(f"  {k:<22}  {v}")


def _print_perception(state: Dict[str, Any]) -> None:
    _hr("Perception -- labeled scene graph (top 10 by commutation_count)")
    scene = state.get("scene_graph") or {}
    labels = state.get("labels") or []
    embeddings = state.get("embeddings") or []
    print(f"  Total labels:     {len(labels)}")
    print(f"  Total embeddings: {len(embeddings)}")
    print(f"  Scene nodes:      {len(scene)}")

    ranked = sorted(
        scene.items(),
        key=lambda kv: (-int(kv[1].get("commutation_count", 0)), kv[0]),
    )[:10]
    print()
    print(f"  {'n':>3}  {'role':<10}  {'category':<22}  pattern  ->  summary")
    print(f"  {'-'*3}  {'-'*10}  {'-'*22}  {'-'*48}")
    for _, info in ranked:
        role = info.get("role", "?")
        cat = info.get("category", "?")
        n = info.get("commutation_count", 0)
        summary = _truncate(info.get("summary", ""), 90)
        print(
            f"  {n:>3}  {role:<10}  {cat:<22}  "
            f"{_truncate(info.get('pattern',''), 40):<40}  ->  {summary}"
        )


def _print_cognition(state: Dict[str, Any]) -> None:
    _hr(f"Cognition -- intent: {state.get('user_intent')!r}")
    candidates: List[Dict[str, Any]] = state.get("candidates") or []
    print(f"  Candidates (top {min(5, len(candidates))} by cosine):")
    for idx, c in enumerate(candidates[:5], 1):
        score = c.get("score", 0.0)
        print(
            f"    {idx}. score={score:.3f}  role={c.get('role','?')}  "
            f"category={c.get('category','?')}  "
            f"summary={_truncate(c.get('summary',''), 70)}"
        )
    plan = state.get("plan") or {}
    print()
    print(f"  Plan:")
    for key in ("action", "target_pattern_id", "concrete_xpath",
                "instance_index", "score", "role", "category", "summary",
                "reason"):
        if key in plan:
            val = plan[key]
            if isinstance(val, str) and len(val) > 100:
                val = val[:97] + "..."
            print(f"    {key:<18}  {val}")


def _print_action(state: Dict[str, Any]) -> None:
    _hr("Action")
    print(f"  result: {state.get('result')}")


def _build_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/147.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://www.tarot.com/")
    parser.add_argument(
        "--intent",
        default="click the first tarot card",
        help="Natural-language action to execute",
    )
    parser.add_argument(
        "--no-browser", metavar="PATH",
        help="Skip Selenium and read HTML from a local file",
    )
    parser.add_argument("--single-pass", action="store_true", default=True)
    parser.add_argument(
        "--dry-run-resolver", action="store_true",
        help="Record the intended click/fill instead of invoking Selenium",
    )
    args = parser.parse_args(argv)

    html_source = None
    driver = None
    try:
        if args.no_browser:
            with open(args.no_browser, "r", encoding="utf-8") as fh:
                html_source = fh.read()
        else:
            driver = _build_driver()

        deps = AgentDeps(
            driver=driver,
            html_source=html_source,
            single_pass=args.single_pass,
            persist=False,
        )

        if args.dry_run_resolver:
            from backend.agent.shadow_resolver import ShadowResolver

            class _DryResolver(ShadowResolver):
                def click(self, pattern_id, index=0):
                    xp = self._pick(pattern_id, index)
                    print(f"[dry-run]  would click {xp}")
                    return xp

                def fill(self, pattern_id, value, index=0):
                    xp = self._pick(pattern_id, index)
                    print(f"[dry-run]  would fill {xp} with {value!r}")
                    return xp

            deps.resolver_factory = lambda d, dom, built: _DryResolver(d, dom, built)

        t0 = time.perf_counter()
        state = run_agent_once(
            url=args.url,
            user_intent=args.intent,
            deps=deps,
        )
        elapsed = time.perf_counter() - t0

        _print_observation(state)
        _print_perception(state)
        _print_cognition(state)
        _print_action(state)

        _hr("Timing")
        print(f"  total wall: {elapsed*1000:.1f} ms")
        return 0
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
