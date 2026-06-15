"""Profile the streaming chunk-build path to verify per-iter cost.

Bypasses Selenium/Kuzu and runs the chunk pipeline directly on a real
distilled HTML snapshot to measure how long ``_build_chunks_for_streaming``
takes vs. the existing post-scan ``chunk()`` call.

The number we care about: per-iter chunk-build (ChunkBuilder.build +
render_all_chunks). That's what gating multiplies by N for an unfettered
absorber, and what 60-node + 1.5s gating reduces to ~3-6 calls per scan.
"""
import sys, time, statistics
sys.path.insert(0, r"C:\Users\isaac\Documents\web_fiber_haptics")

from backend.dom.shadow_html_parser import ShadowDOM
from backend.dom.content_tagger import ContentTagger
from backend.dom.xpath_tree_builder import XPathTreeBuilder, count_content_nodes
from backend.dom.web_distiller_freq import ContentCoagulator
from backend.mapper.chunk_builder import (
    ChunkBuilder,
    build_xpath_node_map,
    build_text_provider_from_dom,
    build_structure_provider_from_dom,
    DEFAULT_CHAR_BUDGET,
)
from backend.mapper.chunk_render import render_all_chunks


def time_call(fn, *a, **kw):
    t0 = time.perf_counter()
    out = fn(*a, **kw)
    return out, (time.perf_counter() - t0) * 1000.0


def profile_one(path):
    print(f"\n=== {path} ===")
    with open(path, encoding="utf-8", errors="ignore") as f:
        html = f.read()
    print(f"raw size: {len(html):,} bytes")

    t0 = time.perf_counter()
    dom = ShadowDOM(html)
    parse_ms = (time.perf_counter() - t0) * 1000.0
    print(f"ShadowDOM parse: {parse_ms:.1f} ms")

    try:
        mask = ContentCoagulator._build_dedup_mask(dom.root)
    except Exception:
        mask = set()
    tagger = ContentTagger(dom, mask=mask)
    tagged, tag_ms = time_call(tagger.tag)
    print(f"ContentTagger.tag: {tag_ms:.1f} ms ({len(tagged.all_content_xpaths())} content xpaths)")

    builder = XPathTreeBuilder()
    builder.add_tagged_content(tagged)
    tree, tree_ms = time_call(builder.build)
    print(f"XPathTreeBuilder.build: {tree_ms:.1f} ms ({count_content_nodes(tree)} content leaves)")

    # Now measure the streaming chunk-build path the absorber uses every emission.
    runs = []
    chunks_count = 0
    instances_count = 0
    for trial in range(5):
        t0 = time.perf_counter()
        xpath_map = build_xpath_node_map(dom)
        tp = build_text_provider_from_dom(dom, xpath_map=xpath_map)
        sp = build_structure_provider_from_dom(dom, xpath_map=xpath_map)
        cb = ChunkBuilder(
            tree, tp,
            char_budget=DEFAULT_CHAR_BUDGET,
            all_tags=tagged.all_tags,
            structure_provider=sp,
        )
        chunks = cb.build(snapshot_id="prof")
        instances = render_all_chunks(chunks, dom, xpath_map=xpath_map) if chunks else []
        runs.append((time.perf_counter() - t0) * 1000.0)
        chunks_count = len(chunks)
        instances_count = len(instances)

    median_ms = statistics.median(runs)
    print(f"streaming chunk-build over {len(runs)} runs:")
    print(f"  median: {median_ms:.1f} ms  min: {min(runs):.1f}  max: {max(runs):.1f}")
    print(f"  chunks: {chunks_count}, instances: {instances_count}")

    # Math: with 60-node + 1.5s gating on an N-iteration scan,
    # we expect ~max(N // 6, 1) emissions plus the final flush.
    # Show what total cost would be at 4 emissions.
    print(f"  cost at 4 emissions/scan: {4 * median_ms:.0f} ms total")
    print(f"  cost at 8 emissions/scan: {8 * median_ms:.0f} ms total")


for path in [
    r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots\noetic.org_blog_our-bodies-know__1776920525_77941366.html",
    r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots\medium.com_@rudyrucker_what-is-cyberpunk-3e8ba09f1feb_1776910018_2e750172.html",
    r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots\archive.org__1776919124_f6d62eb2.html",
    r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots\www.tarot.com_astrology_moon-phases_1777038153_973805de.html",
    r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots\archive.org__1776898851_3ca7f626.html",
]:
    try:
        profile_one(path)
    except Exception as e:
        print(f"  ERROR on {path}: {type(e).__name__}: {e}")
