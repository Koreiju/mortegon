"""
demo_live_tarot.py --End-to-end console demo of the Phase 1 pipeline.

Runs an actual Selenium headless scan of tarot.com, drives the full
content-tag -> Patricia-trie -> chunk pipeline, persists the trie version
to a throwaway Kuzu database, and prints verification output that makes
the shape of the pipeline inspectable by eye:

    * Scan + parse + chunking wall time
    * Trie stats (pattern count, content patterns, root hash)
    * Top-N most-repeated patterns (high commutation_count = card/list)
    * Sample knowledge panels for the three most interesting chunks
    * Billboard vs sphere breakdown
    * Diff summary against a prior run (if any)

Usage
-----
    python -m backend.demos.demo_live_tarot
    python -m backend.demos.demo_live_tarot --url https://www.tarot.com/
    python -m backend.demos.demo_live_tarot --single-pass           (faster, no scroll)
    python -m backend.demos.demo_live_tarot --no-browser FILE.html  (parse local HTML)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from typing import Optional

# Let the script be launched both as `python backend/demos/demo_live_tarot.py`
# and as `python -m backend.demos.demo_live_tarot`.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from backend.dom.pipeline import run_pipeline, run_pipeline_live
from backend.dom.trie_diff import diff_tries
from backend.dom.trie_persistence import (
    get_latest_version_id,
    load_trie,
    persist_trie,
)


BANNER = "=" * 72


def _hr(title: str) -> None:
    print()
    print(BANNER)
    print(f"  {title}")
    print(BANNER)


def _format_tags(tags: list) -> str:
    return ", ".join(tags) if tags else "(none)"


def _format_preview(text: str, max_len: int = 180) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text


def _print_top_patterns(result, limit: int = 10) -> None:
    rows = sorted(
        result.trie.patterns,
        key=lambda r: (-r.commutation_count, -len(r.tag_set), r.pattern),
    )[:limit]
    print(f"\nTop {len(rows)} patterns by commutation_count:")
    print(f"  {'n':>4}  {'depth':>5}  {'tags':<40}  pattern")
    print(f"  {'-'*4}  {'-'*5}  {'-'*40}  {'-'*40}")
    for r in rows:
        tags = ",".join(r.tag_set)[:40]
        print(f"  {r.commutation_count:>4}  {r.depth:>5}  {tags:<40}  {r.pattern}")


def _print_chunk_samples(result, n: int = 5) -> None:
    """Print knowledge-panel payloads for the N most interesting chunks.

    'Interesting' = largest subtree * highest commutation_count. This
    surfaces the card-grid and nav-list chunks that drive the SLM
    hand-off.
    """
    ranked = sorted(
        result.chunks,
        key=lambda c: (-c.commutation_count * max(c.char_count, 1), -len(c.content_fields)),
    )[:n]
    print(f"\nSampled {len(ranked)} chunks (highest commutation x char_count):")
    for idx, chunk in enumerate(ranked, 1):
        print()
        print(f"  [{idx}] pattern              = {chunk.pattern}")
        print(f"      representative_xpath = {chunk.representative_xpath}")
        print(f"      commutation_count    = {chunk.commutation_count}")
        print(f"      char_count           = {chunk.char_count}")
        print(f"      has_image            = {bool(chunk.image_urls)}")
        if chunk.image_urls:
            first_img = next(iter(chunk.image_urls.values()))
            print(f"      first_image_url      = {_format_preview(first_img, 120)}")
        print(f"      text_preview         = {_format_preview(chunk.text_preview, 200)}")
        if chunk.content_fields:
            print(f"      knowledge_panel:")
            for cat, values in chunk.content_fields.items():
                sample = values[0] if values else ""
                print(
                    f"        {cat:<24}  n={len(values):<3}"
                    f"  e.g. {_format_preview(sample, 80)}"
                )


def _print_billboard_summary(result) -> None:
    bb = [c for c in result.chunks if c.image_urls]
    sp = [c for c in result.chunks if not c.image_urls]
    print(f"\nBillboard vs Sphere breakdown:")
    print(f"  Billboarded (media present):   {len(bb)} chunks")
    print(f"  Sphere (text/structural only): {len(sp)} chunks")


def _print_diff_summary(diff) -> None:
    if diff is None:
        print("\nDiff: first run --no prior version to compare.")
        return
    if diff.is_identical():
        print(f"\nDiff vs prior version {diff.old_version_id}: identical (root hash match).")
        return
    s = diff.summary()
    print(f"\nDiff vs prior version {diff.old_version_id}:")
    for k, v in s.items():
        print(f"  {k:<22}  {v}")


def _build_driver():
    """Launch a headless Chrome via Selenium Manager (no manual driver install)."""
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


def _build_temp_conn():
    """Throwaway Kuzu DB so the demo doesn't pollute kuzu_db.

    §R.9 — janitor-managed: canonical prefix + guaranteed atexit removal."""
    import kuzu
    from backend.services.db_janitor import new_temp_db_path, register_for_cleanup

    tmp = register_for_cleanup(new_temp_db_path("demo_tarot"))
    db_path = os.path.join(tmp, "db")
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    stmts = [
        "CREATE NODE TABLE Domain(domain STRING, first_seen STRING, PRIMARY KEY(domain))",
        "CREATE NODE TABLE Page(url STRING, domain STRING, timestamp STRING, PRIMARY KEY(url))",
        "CREATE NODE TABLE DomSnapshot(snapshot_id STRING, url STRING, file_path STRING, "
        "content_hash STRING, captured_at STRING, node_count INT64, PRIMARY KEY(snapshot_id))",
        "CREATE NODE TABLE TrieVersion(version_id STRING, url STRING, snapshot_id STRING, "
        "parent_version_id STRING, pattern_count INT64, content_pattern_count INT64, "
        "total_char_count INT64, root_hash STRING, created_at STRING, PRIMARY KEY(version_id))",
        "CREATE NODE TABLE TriePattern(pattern_id STRING, version_id STRING, pattern STRING, "
        "representative_xpath STRING, parent_pattern_id STRING, tag_set STRING, "
        "commutation_count INT64, depth INT64, has_shadow_boundary BOOLEAN, "
        "char_count INT64, self_hash STRING, subtree_hash STRING, "
        "member_xpaths STRING, PRIMARY KEY(pattern_id))",
        "CREATE NODE TABLE PatternLabel(label_id STRING, pattern_id STRING, version_id STRING, "
        "role STRING, category STRING, summary STRING, confidence DOUBLE, "
        "raw_json STRING, model STRING, created_at STRING, PRIMARY KEY(label_id))",
        "CREATE NODE TABLE PatternEmbedding(embedding_id STRING, pattern_id STRING, "
        "version_id STRING, text_source STRING, embedding FLOAT[768], "
        "created_at STRING, PRIMARY KEY(embedding_id))",
        "CREATE REL TABLE HAS_PAGE(FROM Domain TO Page)",
        "CREATE REL TABLE HAS_TRIE_VERSION(FROM Page TO TrieVersion)",
        "CREATE REL TABLE SNAPSHOT_OF(FROM TrieVersion TO DomSnapshot)",
        "CREATE REL TABLE NEXT_VERSION(FROM TrieVersion TO TrieVersion)",
        "CREATE REL TABLE HAS_TRIE_PATTERN(FROM TrieVersion TO TriePattern)",
        "CREATE REL TABLE PARENT_PATTERN(FROM TriePattern TO TriePattern)",
        "CREATE REL TABLE LABELS_PATTERN(FROM PatternLabel TO TriePattern)",
        "CREATE REL TABLE EMBEDDING_OF(FROM PatternEmbedding TO TriePattern)",
    ]
    for s in stmts:
        conn.execute(s)

    return conn, tmp


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", default="https://www.tarot.com/", help="URL to scan (default: tarot.com)"
    )
    parser.add_argument(
        "--no-browser",
        metavar="PATH",
        help="Skip Selenium and read HTML from a local file (for dev without network)",
    )
    parser.add_argument(
        "--single-pass",
        action="store_true",
        help="One-shot capture without scroll loop (faster)",
    )
    parser.add_argument(
        "--max-duration", type=int, default=20, help="Seconds for the scroll loop"
    )
    parser.add_argument(
        "--budget", type=int, default=256, help="Chunk text budget in chars"
    )
    parser.add_argument(
        "--local-html-root",
        default=None,
        help="Save raw HTML ground-truth to this directory (spec Task 1.1)",
    )
    parser.add_argument(
        "--double-scan",
        action="store_true",
        help="Run the scan twice and show the diff against the first run",
    )
    parser.add_argument(
        "--label",
        action="store_true",
        help="Phase 3: label every content chunk via the SLM and print the top 10",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Phase 4: embed labeled patterns and persist the vectors",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Phase 4: after --embed, run a cosine search for this query",
    )
    args = parser.parse_args(argv)

    conn, tmp_dir = _build_temp_conn()

    try:
        _hr(f"Phase 1 live demo --{args.url}")
        t0 = time.perf_counter()

        if args.no_browser:
            with open(args.no_browser, "r", encoding="utf-8") as fh:
                html = fh.read()
            result = run_pipeline(
                html_source=html,
                url=args.url,
                char_budget=args.budget,
                persist=True,
                conn=conn,
                local_html_root=args.local_html_root,
            )
        else:
            driver = _build_driver()
            try:
                result = run_pipeline_live(
                    driver,
                    args.url,
                    max_duration=args.max_duration,
                    persist=True,
                    conn=conn,
                    char_budget=args.budget,
                    local_html_root=args.local_html_root,
                    single_pass=args.single_pass,
                )
            finally:
                driver.quit()

        elapsed = time.perf_counter() - t0

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        summary = result.as_summary()
        print()
        print(f"Pipeline summary (wall: {elapsed*1000:.1f} ms):")
        for k, v in summary.items():
            if k == "diff":
                continue
            print(f"  {k:<22}  {v}")

        _print_top_patterns(result, limit=15)
        _print_chunk_samples(result, n=5)
        _print_billboard_summary(result)
        _print_diff_summary(result.diff)

        # Kuzu sanity: read back what we persisted and confirm the version
        # lookup + pattern count match.
        vid = get_latest_version_id(conn, args.url)
        loaded = load_trie(conn, vid) if vid else None
        assert loaded is not None, "Persisted trie must be loadable"
        assert loaded.version.pattern_count == result.trie.version.pattern_count
        print(
            f"\nKuzu round-trip OK: version {vid} has "
            f"{loaded.version.pattern_count} patterns / "
            f"{loaded.version.content_pattern_count} content patterns."
        )

        # ------------------------------------------------------------------
        # Optional Phase 3 --SLM labeling
        # ------------------------------------------------------------------
        labels = None
        if args.label or args.embed or args.query:
            from backend.services.pattern_labeler import (
                PatternLabeler,
                persist_pattern_labels,
            )

            _hr("Phase 3 --SLM labeling")
            labeler = PatternLabeler()

            def _progress(idx, total, pattern):
                print(f"  [{idx:>3}/{total}]  labeling  {pattern[:60]}")

            t_lbl = time.perf_counter()
            labels = labeler.label_trie(result.trie, result.chunks, progress_cb=_progress)
            print(f"\n  Labeled {len(labels)} patterns in "
                  f"{(time.perf_counter() - t_lbl):.1f}s")
            persist_pattern_labels(conn, labels)

            top_n = min(10, len(labels))
            print(f"\n  Top {top_n} labels (by confidence):")
            print(f"    {'role':<10}  {'category':<24}  {'conf':>5}  summary")
            print(f"    {'-'*10}  {'-'*24}  {'-'*5}  {'-'*40}")
            for lbl in sorted(labels, key=lambda l: -l.confidence)[:top_n]:
                pat = result.trie.by_pattern_id.get(lbl.pattern_id)
                print(
                    f"    {lbl.role:<10}  {lbl.category[:24]:<24}  "
                    f"{lbl.confidence:>5.2f}  {_format_preview(lbl.summary, 80)}"
                )
                if pat:
                    print(f"        pattern: {pat.pattern}")

        # ------------------------------------------------------------------
        # Optional Phase 4 --Embedding + semantic query
        # ------------------------------------------------------------------
        if args.embed or args.query:
            from backend.services.pattern_embedder import (
                PatternEmbedder,
                persist_pattern_embeddings,
            )

            _hr("Phase 4 --Pattern embeddings")
            if labels is None:
                print("  --embed requires --label; skipping.")
            else:
                embedder = PatternEmbedder()
                t_emb = time.perf_counter()
                emb_rows = embedder.embed_labeled_patterns(
                    result.trie, result.chunks, labels
                )
                print(f"  Embedded {len(emb_rows)} patterns in "
                      f"{(time.perf_counter() - t_emb):.1f}s")
                persist_pattern_embeddings(conn, emb_rows)

                if args.query:
                    _hr(f"Phase 4 query --{args.query!r}")
                    ranked = embedder.rank_patterns(args.query, emb_rows, top_k=5)
                    if not ranked:
                        print("  (no results)")
                    else:
                        for idx, (row, score) in enumerate(ranked, 1):
                            pat = result.trie.by_pattern_id.get(row.pattern_id)
                            # Find label for pretty print
                            label = next(
                                (l for l in labels if l.pattern_id == row.pattern_id),
                                None,
                            )
                            role = label.role if label else "?"
                            cat = label.category if label else "?"
                            xp = pat.representative_xpath if pat else "?"
                            print(f"  [{idx}] score={score:.3f}  role={role}  "
                                  f"category={cat}")
                            print(f"      xpath: {xp}")
                            if label:
                                print(f"      summary: "
                                      f"{_format_preview(label.summary, 120)}")

        # ------------------------------------------------------------------
        # Optional double-scan -> show diff
        # ------------------------------------------------------------------
        if args.double_scan:
            _hr("Second scan --diff against first run")
            if args.no_browser:
                with open(args.no_browser, "r", encoding="utf-8") as fh:
                    html2 = fh.read()
                r2 = run_pipeline(
                    html_source=html2,
                    url=args.url,
                    char_budget=args.budget,
                    persist=True,
                    conn=conn,
                    parent_version_id=result.trie.version.version_id,
                )
            else:
                driver = _build_driver()
                try:
                    r2 = run_pipeline_live(
                        driver,
                        args.url,
                        max_duration=args.max_duration,
                        persist=True,
                        conn=conn,
                        char_budget=args.budget,
                        single_pass=args.single_pass,
                    )
                finally:
                    driver.quit()
            _print_diff_summary(r2.diff)

        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
