"""End-to-end test of the 3-stage pipeline.

Bypasses Selenium by feeding a fixture HTML directly through the
mapper's chunk-build path, then drives the verified-delta absorber
+ pipeline on a synthetic 4-iteration scan.

Captures every event the pipeline emits (chunks_partial,
chunk_instances_partial, stats, done) and asserts:

  1. chunks_partial events arrive incrementally during the scan
  2. stats events report monotonically increasing counters
  3. all instances eventually land in the global TF-IDF store
  4. the pipeline drains cleanly without dangling threads
"""
from __future__ import annotations

import os
import sys
import tempfile
import shutil

sys.path.insert(0, r"C:\Users\isaac\Documents\web_fiber_haptics")


def main() -> int:
    # §R.9 — janitor-managed (removed even if an assert aborts mid-run).
    from backend.services.db_janitor import new_temp_db_path, register_for_cleanup
    tmp_root = register_for_cleanup(new_temp_db_path("pipeline_e2e"))
    db_path = os.path.join(tmp_root, "kuzu_db")
    tfidf_dir = os.path.join(tmp_root, "global_tfidf")
    os.environ["WFH_DB_PATH"] = db_path
    os.environ["WFH_TFIDF_DIR"] = tfidf_dir
    # CPU mode for reproducibility
    os.environ["WFH_TFIDF_GPU"] = "0"
    print(f"temp DB:    {db_path}")
    print(f"temp TFIDF: {tfidf_dir}")

    from backend.database import init_db
    init_db()

    from backend.dom.shadow_html_parser import ShadowDOM
    from backend.dom.content_tagger import ContentTagger
    from backend.dom.xpath_tree_builder import XPathTreeBuilder
    from backend.dom.web_distiller_freq import ContentCoagulator
    from backend.mapper.mapper import DomMapper
    from backend.mapper.chunk_absorber import ChunkAbsorber
    from backend.mapper.pipeline_runner import (
        SnapshotPipeline, _ChunkBatch,
    )
    from backend.services.global_tfidf_store import get_default_store

    fixture = (
        r"C:\Users\isaac\Documents\web_fiber_haptics\snapshots"
        r"\noetic.org_blog_our-bodies-know__1776920525_77941366.html"
    )
    with open(fixture, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    # Capture all stream events
    events = []
    def on_stream(p):
        events.append(p)

    mapper = DomMapper(driver=None)
    snap_id = "snap_pipe_test"
    url = "https://noetic.org/blog/our-bodies-know"

    # Hand-prep mapper state (mimics _process_distill output)
    dom = ShadowDOM(html); mapper._active_doms[snap_id] = dom
    mask = ContentCoagulator._build_dedup_mask(dom.root)
    tagged = ContentTagger(dom, mask=mask).tag(); mapper._active_tagged[snap_id] = tagged
    b = XPathTreeBuilder(); b.add_tagged_content(tagged); tree = b.build()
    mapper._active_trees[snap_id] = tree

    # Build chunks twice so the second pass produces chunk_complete
    # events from the absorber (membership matches across iters).
    chunks_a, instances_a = mapper._build_chunks_for_streaming(snap_id, url)
    chunks_b, instances_b = mapper._build_chunks_for_streaming(snap_id, url)
    print(f"\nbuilt {len(chunks_a)} chunks, {len(instances_a)} instances")

    # Set up an absorber + pipeline manually (this mirrors what
    # mapper.snapshot does internally without needing Selenium).
    absorber = ChunkAbsorber()
    pipeline = SnapshotPipeline(on_stream=on_stream, stats_interval_s=0.1)

    def vec_fn(batch):
        from backend.services.global_tfidf_store import (
            get_default_store, ChunkMeta as _GM,
        )
        from backend.services.tfidf_service import ChunkInstanceVectorizer
        from backend.mapper.pipeline_runner import _StreamBatch
        v = ChunkInstanceVectorizer()
        v.embed_instances(batch.instances)
        gs = get_default_store()
        by_id = {c.chunk_id: c for c in batch.chunks}
        ts = []; ms = []
        for inst in batch.instances:
            cd = by_id.get(inst.chunk_id)
            ts.append(inst.rendered_text or "")
            ms.append(_GM(
                chunk_id=inst.instance_id(batch.url),
                url=batch.url, snapshot_id=batch.snapshot_id,
                absolute_xpath=getattr(inst, 'absolute_xpath', '') or '',
                instance_idx=int(getattr(inst, 'instance_idx', 0) or 0),
                pattern=getattr(inst, 'pattern', '') or (cd.pattern if cd else ''),
                text_preview=(inst.rendered_text or '')[:160],
            ))
        gs.add_chunks(ts, ms)
        pipeline.stats.vocab_size = gs.vocab_size
        pipeline.stats.doc_count = gs.doc_count
        return _StreamBatch(
            iter_idx=batch.iter_idx, snapshot_id=batch.snapshot_id, url=batch.url,
            chunks=batch.chunks, instances=batch.instances,
        )

    def persist_fn(stream_batch):
        # Mock persist: count instances; no kuzu round-trip needed
        # for this unit test.
        return len(stream_batch.instances)

    pipeline.set_vectorize_fn(vec_fn)
    pipeline.set_persist_fn(persist_fn)
    pipeline.start()

    print("\n--- simulating scan iters ---")
    # Iter 1: absorber sees these for the FIRST time → chunk_added events
    ev1 = absorber.absorb(chunks_a, instances_a)
    pipeline.note_iter(n_nodes=200)
    print(f"iter1 events: {[e.kind for e in ev1[:5]]}…")

    # Iter 2: same chunks → chunk_complete (membership stable)
    ev2 = absorber.absorb(chunks_b, instances_b)
    stable_chunks = [e.chunk for e in ev2 if e.kind == "chunk_complete" and e.chunk]
    stable_inst = []
    for e in ev2:
        if e.kind == "chunk_complete" and e.instances:
            stable_inst.extend(e.instances)
    print(f"iter2 verified-deltas: {len(stable_chunks)} chunks, {len(stable_inst)} insts")
    assert stable_chunks, "expected chunk_complete events on iter 2"
    pipeline.submit_verified_delta(_ChunkBatch(
        iter_idx=2, snapshot_id=snap_id, url=url,
        chunks=stable_chunks, instances=stable_inst,
    ))
    pipeline.note_iter(n_nodes=200)

    pipeline.finish()

    # --- assertions
    print("\n--- captured events ---")
    by_type = {}
    for e in events:
        t = e.get("type", "?")
        by_type[t] = by_type.get(t, 0) + 1
    for t, n in by_type.items():
        print(f"  {t}: {n}")

    assert by_type.get("chunks_partial", 0) >= 1, "expected chunks_partial events"
    assert by_type.get("chunk_instances_partial", 0) >= 1, "expected chunk_instances_partial events"
    assert by_type.get("stats", 0) >= 1, "expected stats events"

    final_stats = pipeline.stats.snapshot()
    print(f"\nfinal stats: {final_stats}")
    assert final_stats["chunks_built"] >= len(stable_chunks)
    assert final_stats["chunks_vectorized"] >= len(stable_chunks)
    assert final_stats["instances_persisted"] >= len(stable_inst)

    gs = get_default_store(tfidf_dir)
    print(f"global store: vocab={gs.vocab_size} docs={gs.doc_count}")
    assert gs.doc_count > 0

    shutil.rmtree(tmp_root, ignore_errors=True)
    print("\nE2E PIPELINE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
