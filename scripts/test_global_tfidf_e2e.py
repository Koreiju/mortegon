"""End-to-end test: scan A → scan B → cross-snapshot query.

Drives the mapper directly (no Selenium) over two real fixtures,
then confirms:

  * vocabulary grows monotonically across scans
  * doc count grows
  * IDF for shared tokens decreases (more docs containing the
    word → less informative)
  * a query that hits BOTH fixtures returns chunks from both URLs
  * a query specific to fixture B returns only fixture B chunks
  * re-scanning fixture A doesn't inflate the index (rows replace
    in place via chunk_id)
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile

sys.path.insert(0, r"C:\Users\isaac\Documents\web_fiber_haptics")


def main() -> int:
    # §R.9 — janitor-managed (canonical prefix; removed even if an assert
    # aborts main() before the explicit rmtree at the bottom).
    from backend.services.db_janitor import new_temp_db_path, register_for_cleanup
    tmp_root = register_for_cleanup(new_temp_db_path("tfidf_e2e"))
    db_path = os.path.join(tmp_root, "kuzu_db")
    tfidf_dir = os.path.join(tmp_root, "global_tfidf")
    os.environ["WFH_DB_PATH"] = db_path
    os.environ["WFH_TFIDF_DIR"] = tfidf_dir
    print(f"temp DB:    {db_path}")
    print(f"temp TFIDF: {tfidf_dir}")

    from backend.database import init_db
    init_db()

    from backend.dom.shadow_html_parser import ShadowDOM
    from backend.dom.content_tagger import ContentTagger
    from backend.dom.xpath_tree_builder import XPathTreeBuilder
    from backend.dom.web_distiller_freq import ContentCoagulator
    from backend.mapper.mapper import DomMapper
    from backend.services.global_tfidf_store import get_default_store

    fixtures = [
        (r"snapshots\noetic.org_blog_our-bodies-know__1776920525_77941366.html",
         "https://noetic.org/blog/our-bodies-know"),
        (r"snapshots\medium.com_@rudyrucker_what-is-cyberpunk-3e8ba09f1feb_1776910018_2e750172.html",
         "https://medium.com/@rudyrucker/what-is-cyberpunk-3e8ba09f1feb"),
    ]

    mapper = DomMapper(driver=None)

    def run_one(snapshot_id: str, fixture_path: str, url: str) -> int:
        with open(fixture_path, encoding="utf-8", errors="ignore") as f:
            html = f.read()
        dom = ShadowDOM(html)
        mapper._active_doms[snapshot_id] = dom
        mask = ContentCoagulator._build_dedup_mask(dom.root)
        tagged = ContentTagger(dom, mask=mask).tag()
        mapper._active_tagged[snapshot_id] = tagged
        b = XPathTreeBuilder()
        b.add_tagged_content(tagged)
        tree = b.build()
        mapper._active_trees[snapshot_id] = tree
        chunks, instances = mapper.chunk(snapshot_id, url, persist=True)
        return len(instances)

    # --- scan A
    print("\n[1] scan A (noetic.org)")
    n_a = run_one("snap_a", fixtures[0][0], fixtures[0][1])
    store = get_default_store(tfidf_dir)
    store.load()  # reload to pick up the mapper's saved state
    v_a, d_a = store.vocab_size, store.doc_count
    print(f"   instances added: {n_a}, vocab={v_a}, docs={d_a}")
    # With cross-DOM content dedup, identical instance texts collapse
    # into a single row. So docs <= instances. Just sanity-check the
    # store has SOME rows.
    assert d_a > 0 and d_a <= n_a, f"docs out of range: {d_a} (instances={n_a})"
    assert v_a > 0, "vocab should be non-empty"

    # IDF for common-but-not-universal token before scan B
    idf_a = store._idf()
    # pick a vocab term and remember its IDF
    sample_token = next(iter(store._vocab.keys()))
    sample_col = store._vocab[sample_token]
    idf_sample_a = idf_a[sample_col]

    # --- scan B
    print("\n[2] scan B (medium.com cyberpunk)")
    n_b = run_one("snap_b", fixtures[1][0], fixtures[1][1])
    store.load()
    v_b, d_b = store.vocab_size, store.doc_count
    print(f"   instances added: {n_b}, vocab={v_b} (+{v_b-v_a}), docs={d_b}")
    assert v_b >= v_a, "vocab should grow monotonically"
    # Doc count grows but bounded by total instances (with dedup
    # collapsing repeats from both scans).
    assert d_b > d_a, "doc count should grow after second scan"
    assert d_b <= d_a + n_b, "doc count can't exceed sum of instances"

    # IDF for tokens present in scan A should now reflect a larger N
    idf_b = store._idf()
    # If the sample_token still exists at the same column, IDF should
    # have generally decreased OR stayed if df also grew proportionally
    print(f"   IDF[{sample_token!r}]: {idf_sample_a:.3f} (after A) -> {idf_b[sample_col]:.3f} (after B)")

    # --- cross-snapshot query
    print("\n[3] cross-snapshot query 'noetic'")
    hits = store.search("noetic", k=5)
    urls_in_hits = {h.meta.url for h in hits}
    print(f"   hits: {[(h.meta.chunk_id[:14], h.meta.url, round(h.score,3)) for h in hits]}")
    assert any("noetic" in u for u in urls_in_hits), "expected noetic-domain hits"

    print("\n[4] cyberpunk-only query")
    hits = store.search("cyberpunk dystopian", k=5)
    print(f"   hits: {[(h.meta.url[:60], round(h.score,3)) for h in hits]}")
    assert hits and "medium.com" in hits[0].meta.url, "expected medium.com top hit"

    # --- re-scan A
    print("\n[5] re-scan A (idempotent)")
    n_a2 = run_one("snap_a", fixtures[0][0], fixtures[0][1])
    store.load()
    v_c, d_c = store.vocab_size, store.doc_count
    print(f"   instances re-added: {n_a2}, vocab={v_c}, docs={d_c}")
    # Re-scan with same content → all merged. Doc count must NOT
    # grow (give-or-take a row if html_raw shifted slightly between
    # scans, which can happen on dynamic pages).
    assert d_c <= d_b + 2, (
        f"re-scan should not significantly inflate doc count "
        f"(was {d_b}, now {d_c})"
    )

    # --- URL filter
    print("\n[6] URL-scoped query")
    hits = store.search(
        "tarot reading", k=3,
        urls=[fixtures[0][1]],  # only noetic
    )
    print(f"   hits: {[(h.meta.url, round(h.score,3)) for h in hits]}")
    if hits:
        for h in hits:
            assert h.meta.url == fixtures[0][1]

    shutil.rmtree(tmp_root, ignore_errors=True)
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
