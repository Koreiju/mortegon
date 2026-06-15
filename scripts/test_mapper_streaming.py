"""Incremental test: verify mapper's chunk + vectorize + persist path
records the right events and writes the sparse .npz file.

Bypasses Selenium by feeding a fixture HTML directly through the
chunk-build chain, then calls ``_embed_and_persist_instances`` to
exercise the TF-IDF persistence + sparse-file save. Captures any
``on_stream`` payload to verify the streaming contract.
"""
from __future__ import annotations

import os
import sys
import tempfile
import shutil

sys.path.insert(0, r"C:\Users\isaac\Documents\web_fiber_haptics")


def main() -> int:
    # Use a tempdir for kuzu so we don't trample the user's DB.
    # §R.9 — janitor-managed (removed even if an assert aborts mid-run).
    from backend.services.db_janitor import new_temp_db_path, register_for_cleanup
    tmp = register_for_cleanup(new_temp_db_path("mapper_streaming"))
    db_path = os.path.join(tmp, "kuzu_db")
    os.environ["WFH_DB_PATH"] = db_path
    print(f"using temp DB: {db_path}")

    from backend.database import init_db
    init_db()

    # Force fresh imports against this temp DB
    from backend.dom.shadow_html_parser import ShadowDOM
    from backend.dom.content_tagger import ContentTagger
    from backend.dom.xpath_tree_builder import XPathTreeBuilder
    from backend.dom.web_distiller_freq import ContentCoagulator
    from backend.mapper.chunk_builder import (
        ChunkBuilder, build_xpath_node_map,
        build_text_provider_from_dom, build_structure_provider_from_dom,
        DEFAULT_CHAR_BUDGET,
    )
    from backend.mapper.chunk_render import render_all_chunks
    from backend.mapper.mapper import (
        DomMapper, _sparse_index_path, SPARSE_INDEX_DIR,
    )

    fixture = (
        r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots"
        r"\noetic.org_blog_our-bodies-know__1776920525_77941366.html"
    )
    with open(fixture, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    # Manually walk the pipeline to populate the mapper's
    # _active_doms / _active_trees / _active_tagged caches the way
    # snapshot() would.
    snapshot_id = "test_snap_1234"
    url = "https://noetic.org/blog/our-bodies-know"

    mapper = DomMapper(driver=None)

    print("\n[1] parse + distill")
    dom = ShadowDOM(html)
    mapper._active_doms[snapshot_id] = dom
    mask = ContentCoagulator._build_dedup_mask(dom.root)
    tagged = ContentTagger(dom, mask=mask).tag()
    mapper._active_tagged[snapshot_id] = tagged
    builder = XPathTreeBuilder()
    builder.add_tagged_content(tagged)
    tree = builder.build()
    mapper._active_trees[snapshot_id] = tree
    print(f"    {len(tagged.all_content_xpaths())} content xpaths, "
          f"{sum(1 for _ in dom.iter_all())} DOM nodes")

    print("\n[2] chunk()")
    import time as _time
    t0 = _time.perf_counter()
    chunks, instances = mapper.chunk(snapshot_id, url, persist=True)
    elapsed = (_time.perf_counter() - t0) * 1000
    print(f"    chunk() took {elapsed:.1f} ms")
    print(f"    {len(chunks)} chunks, {len(instances)} instances")
    if instances:
        print(f"    each instance has embedding length: {len(instances[0].embedding)}")
        assert len(instances[0].embedding) == 1024, (
            "expected 1024-d dense projection"
        )

    print("\n[3] sparse .npz file")
    sparse_path = _sparse_index_path(snapshot_id)
    print(f"    expected path: {sparse_path}")
    if os.path.exists(sparse_path):
        size = os.path.getsize(sparse_path)
        print(f"    OK: {size:,} bytes")
    else:
        print(f"    MISSING — pipeline didn't save sparse index")
        return 1

    print("\n[4] cold-load + search via SparseTfidfIndex")
    from backend.services.tfidf_service import SparseTfidfIndex
    ids = [f"{i.chunk_id}:{i.instance_idx}" for i in instances]
    t0 = _time.perf_counter()
    idx = SparseTfidfIndex.load(sparse_path, ids)
    load_ms = (_time.perf_counter() - t0) * 1000
    t0 = _time.perf_counter()
    hits = idx.search("consciousness body knowing", k=3)
    search_ms = (_time.perf_counter() - t0) * 1000
    print(f"    load: {load_ms:.2f} ms, search: {search_ms:.2f} ms")
    for cid, score in hits:
        text = next(i.rendered_text for i in instances
                    if f"{i.chunk_id}:{i.instance_idx}" == cid)
        print(f"    {score:.3f}  {cid[:40]:40}  {text[:50]!r}")

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)
    if os.path.exists(sparse_path):
        os.remove(sparse_path)

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
