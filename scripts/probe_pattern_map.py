"""§15.8 LIVE-pipeline evidence — golden-trio joint-presence gate (§15.8.1)
+ the live ``pattern_map`` ConceptNode (§15.8.2 / ChunkPatternSchema.md).

Drives the REAL DOM pipeline (``run_pipeline``, the same persist branch
``run_pipeline_live`` uses for Selenium scans) against a fixture card-grid +
nav page, then asserts:

  * a ``pattern_map`` ConceptNode materialises as a PEER (id ``pattern_map::*``,
    type_hint ``pattern_map``) whose ``data`` carries the recursive schema tree;
  * the content card pattern resolves a golden trio (title+link+content) and
    its members enter ``sampled_chunks``;
  * the nav pattern is REJECTED by the joint-presence gate (empty trio, no
    sampled chunks) — the §15.8.1 nav/footer/sidebar filter;
  * a second scan ACCRETES into the same node (sampled_chunks union; the
    pattern's first-discovery ``url_root`` stays anchored — §3.3 / §7 #3).

Offline + deterministic: uses a temp Kuzu DB (WFH_DB_PATH), the fake SLM /
embedder gates, and NO_WEBDRIVER, so it runs in CI without a browser.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Deterministic, browserless: set BEFORE importing backend.database so the temp
# DB path + fake gates take effect at import time. §R.9 — the janitor owns the
# throwaway dir (canonical prefix + guaranteed atexit removal); db_janitor is
# import-safe here (it never touches backend.database).
from backend.services.db_janitor import new_temp_db_path, register_for_cleanup

_TMPDB = register_for_cleanup(new_temp_db_path("pattern_map_probe"))
os.environ["WFH_DB_PATH"] = _TMPDB
os.environ.setdefault("WFH_FAKE_SLM", "1")
os.environ.setdefault("WFH_FAKE_EMBEDDER", "1")
os.environ.setdefault("NO_WEBDRIVER", "1")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


_FIXTURE_HTML = """<html><body><main><ul>
 <li><a href="/item/1"><h3>First Result Title</h3><p>A long descriptive paragraph about the first result with plenty of body text to exceed thresholds here now.</p></a></li>
 <li><a href="/item/2"><h3>Second Result Title</h3><p>A long descriptive paragraph about the second result with plenty of body text to exceed thresholds here now.</p></a></li>
 <li><a href="/item/3"><h3>Third Result Title</h3><p>A long descriptive paragraph about the third result with plenty of body text to exceed thresholds here now.</p></a></li>
</ul></main>
<nav><ul><li><a href="/home">Home</a></li><li><a href="/about">About</a></li></ul></nav>
</body></html>"""


def check_golden_trio_unit() -> None:
    """§15.8.1 — the joint-presence gate, in isolation."""
    from backend.mapper.chunk_builder import extract_golden_trio

    # Nav label: link + short text → REJECTED (the substance gate filters it).
    _assert(
        extract_golden_trio({
            "/nav/ul/li/a/text()": ["Home"],
            "/nav/ul/li/a/@href": ["/home"],
        }) is None,
        "nav block must fail the joint-presence gate",
    )

    # Production multi-tag card → distinct (title, link, content).
    trio = extract_golden_trio({
        "/li/a/h3/text()": ["Princeton University Library Chronicle"],
        "/li/a/@href": ["/x"],
        "/li/a/p/text()": ["A long descriptive paragraph about the holdings "
                            "spanning decades and a great deal more text."],
    })
    _assert(trio is not None, "multi-tag card must resolve a golden trio")
    _assert(trio[0].endswith("/h3/text()"), f"title should be the heading: {trio}")
    _assert(trio[1].endswith("/@href"), f"link should be the href: {trio}")
    _assert(trio[2].endswith("/p/text()"), f"content should be the para: {trio}")

    # Aggregated single-text card → degraded trio (title==content), link kept.
    agg = extract_golden_trio({
        "/li/text()": ["Second Result Title A long descriptive paragraph about "
                       "the result with plenty of body text here now."],
        "/li/a/@href": ["/item/2"],
    })
    _assert(agg is not None, "aggregated card must still resolve a trio")
    _assert(agg[1].endswith("/@href"), f"aggregated trio link wrong: {agg}")

    # Link with no substantial text → None.
    _assert(
        extract_golden_trio({"/li/a/@href": ["/x"]}) is None,
        "a bare link with no content must fail the gate",
    )
    print("  golden-trio joint-presence gate OK (card resolves, nav rejected)")


def check_pattern_map_pipeline() -> None:
    """§15.8.2 — the live pattern_map ConceptNode through the real pipeline."""
    from backend.database import get_connection, init_db
    init_db()
    from backend.dom.pipeline import run_pipeline

    conn = get_connection()
    run_pipeline(_FIXTURE_HTML, "https://example.org/search?q=library",
                 persist=True, conn=conn)

    def _load_pattern_map():
        rows = conn.execute(
            "MATCH (n:ConceptNode) WHERE n.type_hint = 'pattern_map' "
            "RETURN n.concept_id, n.backing_pointer, n.data"
        )
        out = []
        while rows.has_next():
            out.append(rows.get_next())
        return out

    pm = _load_pattern_map()
    _assert(len(pm) == 1, f"expected exactly one pattern_map node, got {len(pm)}")
    cid, backing, data_str = pm[0]
    _assert(str(cid).startswith("pattern_map::"),
            f"pattern_map must be a fixture-peer id, got {cid}")
    _assert(str(backing).startswith("pattern_map::"),
            f"pattern_map backing pointer wrong: {backing}")

    data = json.loads(data_str)
    patterns = data.get("patterns") or {}
    _assert(patterns, "pattern_map.data must carry a patterns tree")

    trio_patterns = [s for s in patterns.values() if any(s.get("golden_trio") or [])]
    nav_patterns = [s for s in patterns.values() if not any(s.get("golden_trio") or [])]
    _assert(trio_patterns, "the content card pattern must resolve a golden trio")

    card = trio_patterns[0]
    _assert(card["golden_trio"] == ["title", "link", "content"],
            f"golden_trio slugs wrong: {card['golden_trio']}")
    for slug in ("title", "link", "content"):
        _assert(slug in card["accessor_map"],
                f"accessor_map missing {slug}: {card['accessor_map']}")
    _assert(len(card.get("sampled_chunks") or []) >= 1,
            "content card members must enter sampled_chunks")
    # The nav pattern (if present) must have been gated out.
    for nav in nav_patterns:
        _assert(not (nav.get("sampled_chunks") or []),
                f"a trio-less (nav) pattern must have no sampled_chunks: {nav}")
    # §2/§4 — pagerank is a real chunk-pattern-graph centrality, not the old
    # 0.0 placeholder. The content card (with sampled members) must rank above 0.
    _assert(float(card.get("pagerank") or 0.0) > 0.0,
            f"content card pagerank must be > 0 (chunk-pattern centrality): {card.get('pagerank')}")
    print(f"  pattern_map node OK ({len(patterns)} patterns; "
          f"{len(trio_patterns)} with golden trio, {len(nav_patterns)} gated out; "
          f"card pagerank={card.get('pagerank')})")

    # --- accretion: a second scan extends the same node (§3.3 / §7 #3). ---
    sampled_before = set(card.get("sampled_chunks") or [])
    url_root_before = card.get("url_root")
    accessor_before = dict(card.get("accessor_dict") or card.get("accessor_map") or {})
    run_pipeline(_FIXTURE_HTML, "https://example.org/page-2",
                 persist=True, conn=conn)
    pm2 = _load_pattern_map()
    _assert(len(pm2) == 1, "second scan must NOT spawn a second pattern_map node")
    data2 = json.loads(pm2[0][2])
    card2 = next(s for s in (data2.get("patterns") or {}).values()
                 if any(s.get("golden_trio") or []))
    sampled_after = set(card2.get("sampled_chunks") or [])
    _assert(sampled_before.issubset(sampled_after),
            "sampled_chunks must be a union across scans (extend, don't respawn)")
    _assert(card2.get("url_root") == url_root_before,
            "pattern url_root must stay anchored to first discovery (§3.3)")
    # §2.2 — the persistent accessor table entry for (domain, pattern_hash)
    # survives a repeat scan (the table is consulted/reused, not rebuilt fresh).
    accessor_after = dict(card2.get("accessor_dict") or card2.get("accessor_map") or {})
    for slug in ("title", "link", "content"):
        if slug in accessor_before:
            _assert(accessor_after.get(slug) == accessor_before.get(slug),
                    f"accessor table entry {slug} must persist across scans (§2.2): "
                    f"{accessor_before.get(slug)} != {accessor_after.get(slug)}")
    print(f"  accretive merge OK (sampled {len(sampled_before)} → "
          f"{len(sampled_after)}; url_root anchored; accessor table reused §2.2)")


def main() -> int:
    print("[probe_pattern_map] verifying §15.8 golden-trio + live pattern_map")
    try:
        check_golden_trio_unit()
        check_pattern_map_pipeline()
        print("[probe_pattern_map] ALL CHECKS PASS")
        return 0
    finally:
        shutil.rmtree(_TMPDB, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
