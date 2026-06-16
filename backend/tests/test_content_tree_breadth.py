"""test_content_tree_breadth.py — real-ruleset §U content-tree breadth guard.

A fast, CI-runnable subset of `scripts/breadth_content_tree_smoke.py`: it drives
the REAL extraction ruleset offline (`run_pipeline(render_instances=True)` over a
few committed `test_packages/` sites — no Selenium/GPU) and asserts the §U
content-tree OUTPUT INVARIANTS hold on real, messy, multi-site HTML:

  * no raw HTML tags leak (the embedded-HTML strip fix, found by the 61-site run
    where 21 sites leaked tracking <iframe>/<img>/<style> markup);
  * no xpath/structure fragments leak (`#shadow-root`, `/text()`).

Sites are chosen for breadth coverage: a tracking-pixel-heavy news page, a GTM
iframe page, and a CJK video page. The test SKIPS gracefully if the corpus is
absent (stripped checkout) so it never hard-fails CI without the fixtures.
"""

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Keep the pipeline fully offline/real-subsystem-free for this render-only path.
os.environ.setdefault("WFH_FAKE_SLM", "1")
os.environ.setdefault("WFH_FAKE_EMBEDDER", "1")
os.environ.setdefault("NO_WEBDRIVER", "1")

from backend.dom.content_tree import fields_to_content_tree  # noqa: E402

_CORPUS = _ROOT / "test_packages"
# Breadth picks: tracking-pixel news, GTM-iframe page, CJK video page.
_SITES = ["cbc_canews", "rom_on_ca", "youtube_comwatchvuIHfJSPFec"]
_MAX_INSTANCES = 400  # cap per site to keep the test fast


def _html_leak(line: str) -> bool:
    return "<" in line and ">" in line and line.index("<") < line.index(">")


def _xpath_leak(line: str) -> bool:
    return "#shadow-root" in line or "/text()" in line or line.strip() in ("@href", "@src")


@pytest.mark.parametrize("site_name", _SITES)
def test_real_ruleset_content_tree_is_clean(site_name):
    site = _CORPUS / site_name / "source.html"
    if not site.is_file():
        pytest.skip(f"corpus site {site_name} not present")

    from backend.dom.pipeline import run_pipeline  # local import: heavy module

    html = site.read_text(encoding="utf-8", errors="replace")
    res = run_pipeline(html, url=f"https://{site_name}",
                       render_instances=True, persist=False)
    instances = list(getattr(res, "instances", []) or [])[:_MAX_INSTANCES]
    assert instances, f"{site_name}: pipeline produced no instances"

    checked = 0
    for inst in instances:
        fields = getattr(inst, "fields", {}) or {}
        if not fields:
            continue
        tree = fields_to_content_tree(fields)
        for ln in tree.splitlines():
            assert not _html_leak(ln), f"{site_name}: HTML leaked into content tree: {ln[:80]!r}"
            assert not _xpath_leak(ln), f"{site_name}: xpath leaked into content tree: {ln[:80]!r}"
        checked += 1
    assert checked > 0, f"{site_name}: no non-empty content trees to check"
