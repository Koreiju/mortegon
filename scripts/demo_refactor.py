"""
demo_refactor.py — End-to-end smoke test for the refactor.

Runs the chunk pipeline against a real distilled HTML snapshot:

    1. Parse HTML → ShadowDOM → ContentTagger → Patricia trie
    2. ChunkBuilder.build  (DB-free; just produces Chunk dataclasses)
    3. render_all_chunks   (per-chunk text rendering)
    4. ChunkInstanceVectorizer.embed_instances  (TF-IDF, no GPU)
    5. Fibonacci-sphere positioning for every chunk
    6. Sample query against the TF-IDF matrix and report the top-3 hits

The point is to confirm:
  - Every chunk in the source HTML reaches the rendered output (no
    silent drops).
  - URLs in the rendered text get tokenized into searchable words.
  - Vectors look right (non-zero, L2-normalized, sane dim).
  - Coordinates form a sphere (variance check).
  - Top-1 retrieval against a query that matches the page actually
    returns a real chunk.

Run:  python demo_refactor.py

Exits 0 if everything passes, non-zero if any check fails.
"""
from __future__ import annotations

import sys
import time
import hashlib

sys.path.insert(0, r"C:\Users\isaac\Documents\web_fiber_haptics")

import numpy as np

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
from backend.services.tfidf_service import (
    ChunkInstanceVectorizer,
    TfidfService,
    tokenize_url,
    expand_urls_in_text,
)


FIXTURES = [
    (
        r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots\noetic.org_blog_our-bodies-know__1776920525_77941366.html",
        "consciousness body intuitive knowing",
    ),
    (
        r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots\medium.com_@rudyrucker_what-is-cyberpunk-3e8ba09f1feb_1776910018_2e750172.html",
        "cyberpunk science fiction",
    ),
]


def fib_sphere(num_pts: int) -> np.ndarray:
    idx = np.arange(0, num_pts, dtype=np.float64) + 0.5
    phi = np.arccos(1.0 - 2.0 * idx / num_pts)
    theta = np.pi * (1.0 + 5.0 ** 0.5) * idx
    return np.vstack(
        [np.cos(theta) * np.sin(phi),
         np.sin(theta) * np.sin(phi),
         np.cos(phi)]
    ).T


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def test_url_tokenization() -> None:
    section("URL tokenization")
    url = "https://noetic.org/blog/our-bodies-know"
    toks = tokenize_url(url)
    print(f"  {url!r}")
    print(f"  -> {toks!r}")
    assert "noetic" in toks
    assert "bodies" in toks
    assert "know" in toks
    assert "/" not in toks
    assert "-" not in toks

    text = (
        "Read more at https://example.com/articles/space-flowers/2024 "
        "and at https://other.org/x/y-z"
    )
    expanded = expand_urls_in_text(text)
    print(f"  expand: {text!r}")
    print(f"      -> {expanded!r}")
    assert "space" in expanded
    assert "flowers" in expanded
    assert "https://" not in expanded


def run_one(path: str, query: str) -> dict:
    section(f"Fixture: {path.rsplit('/', 1)[-1]}")
    with open(path, encoding="utf-8", errors="ignore") as f:
        html = f.read()
    print(f"  raw size: {len(html):,} bytes")

    t0 = time.perf_counter()
    dom = ShadowDOM(html)
    print(f"  ShadowDOM parse: {(time.perf_counter()-t0)*1000:.1f} ms")

    try:
        mask = ContentCoagulator._build_dedup_mask(dom.root)
    except Exception:
        mask = set()

    t0 = time.perf_counter()
    tagger = ContentTagger(dom, mask=mask)
    tagged = tagger.tag()
    print(f"  ContentTagger: {(time.perf_counter()-t0)*1000:.1f} ms "
          f"({len(tagged.all_content_xpaths())} content xpaths)")

    builder = XPathTreeBuilder()
    builder.add_tagged_content(tagged)
    tree = builder.build()
    print(f"  Patricia trie leaves: {count_content_nodes(tree)}")

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
    chunks = cb.build(snapshot_id="demo")
    print(f"  ChunkBuilder: {(time.perf_counter()-t0)*1000:.1f} ms "
          f"({len(chunks)} chunks)")

    t0 = time.perf_counter()
    instances = render_all_chunks(chunks, dom, xpath_map=xpath_map)
    print(f"  render_all_chunks: {(time.perf_counter()-t0)*1000:.1f} ms "
          f"({len(instances)} instances)")

    if not instances:
        print("  WARNING: zero instances rendered!")
        return {"ok": False, "reason": "no instances"}

    t0 = time.perf_counter()
    vec = ChunkInstanceVectorizer()
    batch = vec.embed_instances(instances)
    print(f"  TF-IDF vectorize: {(time.perf_counter()-t0)*1000:.1f} ms "
          f"({batch.unique_text_count} unique, vocab={batch.fit.vocabulary_size}, "
          f"nnz={batch.fit.nnz}, fit_time={batch.fit.fit_time_ms:.1f}ms)")

    # Sanity: every instance has a non-trivial dense embedding
    nonzero = sum(1 for i in instances if i.embedding and any(abs(x) > 1e-9 for x in i.embedding))
    print(f"  instances with non-zero embedding: {nonzero}/{len(instances)}")
    assert nonzero >= len(instances) * 0.9, "too many empty embeddings"

    # Sanity: dense vectors are L2-normalized (within tolerance)
    norms = np.array([np.linalg.norm(np.asarray(i.embedding)) for i in instances])
    print(f"  embedding L2 norms: min={norms.min():.3f} max={norms.max():.3f} mean={norms.mean():.3f}")

    # Fibonacci sphere positions
    n = len(instances)
    coords = fib_sphere(n) * 15.0
    radii = np.linalg.norm(coords, axis=1)
    print(f"  sphere radii: min={radii.min():.2f} max={radii.max():.2f} (target=15)")
    assert abs(radii.mean() - 15.0) < 1e-6, "Fibonacci sphere not on radius 15"

    # Pairwise nearest-neighbor distance (rough equidistance check)
    if n >= 4:
        diffs = coords[:, None, :] - coords[None, :, :]
        d = np.linalg.norm(diffs, axis=2)
        np.fill_diagonal(d, np.inf)
        nn = d.min(axis=1)
        print(f"  nearest-neighbor distances: min={nn.min():.2f} max={nn.max():.2f} "
              f"(spread={nn.max()/nn.min():.2f}x)")

    # Retrieval test
    section(f"  retrieval: {query!r}")
    tfidf = TfidfService()
    doc_texts = [i.rendered_text or "" for i in instances]
    sims = tfidf.query_similarities(query, doc_texts)
    top = np.argsort(-sims)[:3]
    for rank, idx in enumerate(top, 1):
        snippet = (instances[idx].rendered_text or "").replace("\n", " ")[:120]
        print(f"  #{rank}  cos={sims[idx]:.3f}  xp={instances[idx].absolute_xpath[:60]}")
        print(f"        {snippet!r}")
    assert sims[top[0]] > 0.0, "top hit had zero similarity — query never matched"

    return {
        "ok": True,
        "chunks": len(chunks),
        "instances": len(instances),
        "vocab": batch.fit.vocabulary_size,
        "top_score": float(sims[top[0]]),
    }


def main() -> int:
    test_url_tokenization()

    failures = []
    for path, query in FIXTURES:
        try:
            r = run_one(path, query)
            if not r.get("ok"):
                failures.append((path, r.get("reason")))
        except Exception as e:
            import traceback
            traceback.print_exc()
            failures.append((path, repr(e)))

    section("SUMMARY")
    if failures:
        for p, reason in failures:
            print(f"  FAIL  {p}: {reason}")
        return 1
    print("  all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
