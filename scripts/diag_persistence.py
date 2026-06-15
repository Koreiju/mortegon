"""
diag_persistence.py — Verify the pipeline → Kuzu → load_all_instances → UMAP
chain end-to-end with the REAL production schema + REAL Nomic v1 GPU embedder,
bypassing Selenium by feeding static HTML directly.

Run with:  python diag_persistence.py

Prints a full trace of what lands in each table. Non-zero exit if anything is
missing / empty / wrong-shape.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile

import kuzu
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backend.database as database
from backend.dom.pipeline import run_pipeline
from backend.services.chunk_instance_embedder import ChunkInstanceEmbedder
from backend.services.chunk_instance_persistence import (
    load_all_instances,
    load_all_page_embeddings,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("diag")


def _gen_card(title: str, text: str, slug: str) -> str:
    return (
        f'<article class="card">'
        f'<img src="/img/{slug}.png" alt="{title}"/>'
        f'<h2>{title}</h2>'
        f'<p>{text}</p>'
        f'<a href="/tarot/{slug}">Read more</a>'
        f'</article>'
    )


_CARDS = [
    ("The Fool", "New beginnings, spontaneity, a free spirit.", "fool"),
    ("The Magician", "Manifestation, resourcefulness, inspired action.", "magician"),
    ("The High Priestess", "Intuition, sacred knowledge, divine feminine.", "priestess"),
    ("The Empress", "Abundance, nurturing, fertility, creativity.", "empress"),
    ("The Emperor", "Authority, structure, father figure, discipline.", "emperor"),
    ("The Hierophant", "Tradition, convention, moral guidance.", "hierophant"),
    ("The Lovers", "Partnership, harmony, choices of the heart.", "lovers"),
    ("The Chariot", "Willpower, determination, victory through control.", "chariot"),
    ("Strength", "Courage, compassion, inner fortitude.", "strength"),
    ("The Hermit", "Soul searching, solitude, introspection.", "hermit"),
    ("Wheel of Fortune", "Cycles, turning points, destiny unfolding.", "wheel"),
    ("Justice", "Fairness, truth, cause and effect, law.", "justice"),
]

HTML = f"""
<!doctype html>
<html><head><title>Diag Tarot</title></head>
<body>
  <main>
    <section class="card-grid">
      {"".join(_gen_card(t, d, s) for t, d, s in _CARDS)}
    </section>
    <section class="filters">
      <form>
        <label for="q">Search readings</label>
        <input id="q" name="q" type="search"
               placeholder="love, career, health..." />
        <button type="submit">Search</button>
      </form>
    </section>
    <nav class="pager">
      <a href="?page=2" rel="next">Next</a>
      <a href="?page=0" rel="prev">Previous</a>
    </nav>
  </main>
</body></html>
""".strip()


def main() -> int:
    # §R.9 — janitor-managed throwaway dir (guaranteed atexit removal).
    from backend.services.db_janitor import new_temp_db_path, register_for_cleanup
    tmpdir = register_for_cleanup(new_temp_db_path("diag_persistence"))
    # Point database.py at a throwaway dir so init_db() creates the full schema
    # there and no live DB is disturbed.
    database.DB_PATH = os.path.join(tmpdir, "kuzu_db")
    log.info("Using temp Kuzu DB at %s", database.DB_PATH)

    database.init_db()
    conn = database.get_connection()

    # -------- 1) Real Nomic v1 GPU embedder ---------------------------
    log.info("Loading REAL Nomic v1 GGUF model on GPU (this may take a moment)...")
    embedder = ChunkInstanceEmbedder()
    inner = embedder._embedder  # EmbeddingService
    log.info(
        "Embedder loaded: model_name=%s device=%s dim=%s",
        inner.model_name, inner.device, inner.dim,
    )
    probe = inner.embed_query("probe")
    log.info(
        "Query embed probe: shape=%s norm=%.4f head=%s",
        probe.shape, float(np.linalg.norm(probe)), probe[:4].tolist(),
    )
    assert probe.ndim == 1 and probe.shape[0] == 768, (
        f"Expected 768-dim probe, got {probe.shape}"
    )

    # -------- 2) Pipeline over static HTML ----------------------------
    url = "https://diag.example/tarot"
    log.info("Running pipeline on static HTML (url=%s)...", url)
    result = run_pipeline(
        html_source=HTML,
        url=url,
        persist=True,
        conn=conn,
        render_instances=True,
        embed_instances=True,
        detect_signal_fields=True,
        embedder=embedder,
    )
    s = result.as_summary()
    log.info("PipelineResult summary: %s", s)

    if not result.saved_to_kuzu:
        log.error("saved_to_kuzu=False — Stage 10 persistence was SKIPPED")
        return 1
    if not result.instances:
        log.error("No rendered instances produced — render path is broken")
        return 1
    if result.embedding_batch is None:
        log.error("embedding_batch is None — embedder path is broken")
        return 1
    if result.page_embedding is None:
        log.error("page_embedding is None — mean_pool failed")
        return 1

    log.info(
        "In-memory: %d instances, %d unique texts, page_vec shape=%s",
        len(result.instances),
        result.embedding_batch.unique_text_count,
        result.page_embedding.shape,
    )
    for i, inst in enumerate(result.instances[:3]):
        log.info(
            "  inst[%d] xpath=%s embed_len=%s text=%r",
            i, inst.absolute_xpath,
            len(inst.embedding) if inst.embedding else None,
            inst.rendered_text[:80],
        )

    # -------- 3) Inspect the DB ---------------------------------------
    res = conn.execute(
        "MATCH (i:ChunkInstance) "
        "RETURN count(i), i.url LIMIT 1"
    )
    count_rows = []
    while res.has_next():
        count_rows.append(res.get_next())
    # Safer separate queries:
    res = conn.execute("MATCH (i:ChunkInstance) RETURN count(i)")
    ci_count = res.get_next()[0] if res.has_next() else 0
    log.info("DB: ChunkInstance row count = %s", ci_count)

    res = conn.execute("MATCH (e:PageEmbedding) RETURN count(e)")
    pe_count = res.get_next()[0] if res.has_next() else 0
    log.info("DB: PageEmbedding row count = %s", pe_count)

    res = conn.execute("MATCH (f:SearchInputField) RETURN count(f)")
    sf_count = res.get_next()[0] if res.has_next() else 0
    log.info("DB: SearchInputField row count = %s", sf_count)

    res = conn.execute("MATCH (f:PaginationField) RETURN count(f)")
    pf_count = res.get_next()[0] if res.has_next() else 0
    log.info("DB: PaginationField row count = %s", pf_count)

    if ci_count == 0:
        log.error("ChunkInstance table is EMPTY — persistence silently failed")
        return 1

    # -------- 4) load_all_instances + shape sanity --------------------
    rows = load_all_instances(conn)
    log.info("load_all_instances returned %d rows", len(rows))
    if not rows:
        log.error("load_all_instances returned zero rows")
        return 1

    bad = [r for r in rows if not r.embedding or len(r.embedding) != 768]
    log.info(
        "  embedding lengths (unique): %s",
        sorted({len(r.embedding) for r in rows}),
    )
    if bad:
        log.error("%d row(s) have missing/wrong-dim embedding", len(bad))
        for r in bad[:3]:
            log.error(
                "  bad row: instance=%s url=%s embed_len=%s",
                r.instance_id, r.url,
                len(r.embedding) if r.embedding else None,
            )
        return 1

    X = np.asarray([r.embedding for r in rows], dtype=np.float32)
    log.info("  stacked embedding matrix shape=%s", X.shape)
    if X.ndim != 2 or X.shape[1] != 768:
        log.error("Embedding matrix has wrong shape: %s", X.shape)
        return 1

    # -------- 5) UMAP sanity -----------------------------------------
    try:
        import umap

        reducer = umap.UMAP(
            n_components=6,
            n_neighbors=min(15, max(2, X.shape[0] - 1)),
            metric="cosine",
            random_state=42,
        )
        Y = reducer.fit_transform(X)
        log.info("UMAP output shape=%s — OK", Y.shape)
    except Exception as exc:
        log.exception("UMAP step failed: %s", exc)
        return 1

    # -------- 6) Cleanup ---------------------------------------------
    try:
        database.close_db()
    except Exception:
        pass
    shutil.rmtree(tmpdir, ignore_errors=True)
    log.info("Diagnostic PASSED — pipeline + persistence + UMAP all green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
