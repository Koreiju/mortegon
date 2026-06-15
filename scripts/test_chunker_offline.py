"""Offline test -- run the chunker on a cached tarot snapshot and
verify each chunk's ``char_count`` matches the length of its printed
content-structure summary.

This doesn't spin up Selenium; it just loads a saved .html file,
runs the pipeline, and prints the first-instance-per-chunk preview
alongside a parity check: is ``chunk.char_count`` == len(the exact
summary string we print)?
"""

from __future__ import annotations

import sys
from pathlib import Path

from backend.dom.pipeline import run_pipeline
from backend.mapper.chunk_builder import ChunkBuilder, HARD_CHAR_LIMIT

SNAPSHOT = Path(
    "snapshots/www.tarot.com_search_q_love_size_n_20_n_1776900499_db0499e4.html"
)


def _fmt_summary(fields):
    """Reproduce the exact string used for char_count so we can verify."""
    return ChunkBuilder._format_summary(fields, truncate_links=True)


def main() -> None:
    html = SNAPSHOT.read_text(encoding="utf-8", errors="replace")
    print(f"Loaded snapshot: {SNAPSHOT.name} ({len(html)} bytes)")

    result = run_pipeline(
        html_source=html,
        url="https://www.tarot.com/search?q=love&size=n_20_n",
        persist=False,
        render_instances=True,
        embed_instances=False,
    )

    print(
        f"\nSnapshot {result.snapshot_id} | "
        f"patterns={len(result.trie.patterns)} | "
        f"chunks={len(result.chunks)} | "
        f"instances={len(result.instances)} | "
        f"HARD_CHAR_LIMIT={HARD_CHAR_LIMIT}"
    )

    by_chunk = {}
    for inst in result.instances:
        by_chunk.setdefault(inst.chunk_id, []).append(inst)

    print(
        "\nchar_count parity check -- column 'chunk.char_count' vs "
        "'len(printed_summary)' must agree."
    )
    header = f"{'ch_cnt':>7} {'printed':>7} {'dlt':>5}  {'members':>7}  pattern"
    print(header)

    worst_delta = 0
    for ch in result.chunks:
        insts = by_chunk.get(ch.chunk_id, [])
        if not insts:
            continue
        inst = sorted(insts, key=lambda r: r.instance_idx)[0]
        fields = getattr(inst, "fields", {}) or {}
        printed = _fmt_summary(fields)
        delta = len(printed) - ch.char_count
        worst_delta = max(worst_delta, abs(delta))
        sign = "+" if delta > 0 else ""
        print(
            f"{ch.char_count:>7} {len(printed):>7} {sign}{delta:>4}  "
            f"{len(ch.member_xpaths):>7}  {ch.pattern}"
        )

    print(f"\nworst |dlt| across chunks: {worst_delta}")

    print("\n--- first instance of each chunk ---")
    for ch in result.chunks[:3]:
        insts = by_chunk.get(ch.chunk_id, [])
        if not insts:
            continue
        inst = sorted(insts, key=lambda r: r.instance_idx)[0]
        fields = getattr(inst, "fields", {}) or {}
        print(
            f"\n[Chunk] pattern={ch.pattern!r}\n"
            f"  members={len(ch.member_xpaths)}  "
            f"rendered={len(insts)}  char_count={ch.char_count}\n"
            f"  first instance @ {inst.absolute_xpath}"
        )
        print("    content-structure summary:")
        for k, v in fields.items():
            print(f"      {k}: {v}")


if __name__ == "__main__":
    sys.exit(main() or 0)
