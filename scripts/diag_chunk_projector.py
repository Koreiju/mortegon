"""
diag_chunk_projector.py -- exercise chunk_projector_service + chunk_search
against the LIVE production Kuzu DB (the one left behind by demo_scanner).

Runs without FastAPI -- directly imports and calls the service functions.
Prints the first few projector nodes and the drill-down for a sample
query. Exits non-zero on any missing piece.
"""

from __future__ import annotations

import json
import logging
import sys

import backend.database as database
from backend.services.chunk_projector_service import (
    build_chunk_projector_nodes, node_to_dict,
)
from backend.services.chunk_instance_embedder import ChunkInstanceEmbedder
from backend.services.chunk_retrieval import retrieve_with_drilldown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("diag_projector")


def main() -> int:
    log.info("Using production Kuzu DB at %s", database.DB_PATH)
    conn = database.get_connection()

    # 1) Projector nodes -----------------------------------------------
    log.info("Calling build_chunk_projector_nodes ...")
    nodes = build_chunk_projector_nodes(conn)
    log.info("Got %d projector nodes", len(nodes))
    if not nodes:
        log.error("Empty node list -- check DB has >= 4 ChunkInstance rows")
        return 1

    # Print the first 3 with truncated html_raw so the log is readable.
    for i, n in enumerate(nodes[:3]):
        d = node_to_dict(n)
        d["html_raw"] = (d["html_raw"] or "")[:120] + ("..." if len(d.get("html_raw","")) > 120 else "")
        d["rendered_text"] = (d["rendered_text"] or "")[:80]
        log.info("  node[%d] = %s", i, json.dumps(d, indent=2, default=str))

    # Sanity-check position/color ranges.
    xs = [n.x for n in nodes]
    ys = [n.y for n in nodes]
    zs = [n.z for n in nodes]
    rs = [n.r for n in nodes]
    gs = [n.g for n in nodes]
    bs = [n.b for n in nodes]
    log.info(
        "  x in [%.2f, %.2f]  y in [%.2f, %.2f]  z in [%.2f, %.2f]",
        min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
    )
    log.info(
        "  r in [%.3f, %.3f]  g in [%.3f, %.3f]  b in [%.3f, %.3f]",
        min(rs), max(rs), min(gs), max(gs), min(bs), max(bs),
    )
    for c, lo, hi in [("r", min(rs), max(rs)),
                      ("g", min(gs), max(gs)),
                      ("b", min(bs), max(bs))]:
        if not (0.0 <= lo <= hi <= 1.0):
            log.error("color channel %s out of [0,1]: [%s, %s]", c, lo, hi)
            return 1

    # 2) Chunk search end-to-end (same path as /api/chunk_search) -----
    log.info("Loading nomic-v1 GPU embedder for chunk_search ...")
    embedder = ChunkInstanceEmbedder()

    q = "love reading"
    log.info("Running retrieve_with_drilldown(%r) ...", q)
    pairs = retrieve_with_drilldown(
        conn, q, page_limit=3, instance_limit_per_page=3,
        embedder=embedder._embedder,
    )
    log.info("Drill-down returned %d page buckets", len(pairs))
    if not pairs:
        log.error("No pages returned -- something is wrong with PageEmbedding rows")
        return 1

    for i, (page, insts) in enumerate(pairs):
        log.info("  [%d] page=%s score=%.3f (%d instances)",
                 i, page.url, page.score, page.instance_count)
        for j, h in enumerate(insts):
            log.info("       inst[%d] score=%.3f xpath=%s text=%r",
                     j, h.score, h.absolute_xpath[:120],
                     (h.rendered_text or "")[:80])

    log.info("Projector + chunk_search diagnostic PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
