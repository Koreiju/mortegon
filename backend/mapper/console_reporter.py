"""
console_reporter.py — Scrapy-style real-time console stats for the chunk pipeline.

Subscribes to the same event stream (stats, log, chunk_added, chunk_replaced,
chunk_removed, done) that is sent to the WebSocket GUI and mirrors them to
stdout.  No architectural changes to the pipeline are required; it is wired
in mapper.snapshot() by composing it around the existing on_stream callback.

Usage (automatic — wired by mapper.snapshot):
    The reporter activates whenever the server is started and a scan runs.
    Set WFH_QUIET=1 to suppress console output.
    Set WFH_CHUNK_REPORT=<path> to also write an HTML chunk-panel file on completion.

Output format:
    Live stats line (overwrites in-place on TTYs):
        iter  4  nodes   312  built/vec  18/12  persist   9  vocab  1.4k  [  8.3s]

    Per-chunk events (new line each):
        ++ [abc123ef] chars=740  ×3  /html/body/main/ul/li  🖼  e-commerce card

    Stage log excerpts:
        [tfidf ] TF-IDF vectorized 6 chunks in 0.018s

    Final summary after 'done':
        ─────────────────────────────────────────────
        SCAN COMPLETE  18 chunks  54 instances  [11.2s]
        ─────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Callable, Dict, Optional

# Force UTF-8 on Windows consoles that default to cp1252 so that box-drawing
# characters, check marks, and emoji survive the journey to the terminal.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# ANSI colour helpers (disabled automatically on non-TTY / Windows without VT)
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stdout.isatty() and os.name != "nt" or (
    os.name == "nt" and os.environ.get("WT_SESSION")  # Windows Terminal
)


def _c(code: str, text: str) -> str:
    """Wrap text in an ANSI escape if colour is enabled."""
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


_DIM   = "2"
_BOLD  = "1"
_GREEN = "32"
_CYAN  = "36"
_YELLOW = "33"
_RED   = "31"
_MAGENTA = "35"


# ---------------------------------------------------------------------------
# ConsoleStatsReporter
# ---------------------------------------------------------------------------

class ConsoleStatsReporter:
    """Prints pipeline events to stdout in a compact, Scrapy-style format.

    Handles four event types:
        stats         — live counters; reprints the stats line in-place
        log           — stage worker messages; printed selectively
        chunk_added / chunk_replaced / chunk_removed  — per-chunk events
        done          — final summary; optionally triggers HTML report

    Parameters
    ----------
    quiet:
        Suppress all output (useful in tests).  Defaults to WFH_QUIET env var.
    report_path:
        If set, write an HTML chunk-panel report to this path when 'done'
        fires.  Defaults to WFH_CHUNK_REPORT env var (empty = no report).
    on_done:
        Optional callback invoked with the final delta_pattern_chunks and
        summary_cache dicts when the scan completes, so the caller can
        trigger additional processing.
    """

    # How often the stats line refreshes (seconds)
    STATS_INTERVAL = 1.0
    # Stages whose log messages we always print
    VERBOSE_STAGES = frozenset({"tfidf", "stream"})
    # Keywords that promote a log line to visible even at lower verbosity
    PROMOTE_KEYWORDS = ("vectorized", "persisted", "fragment", "delta")

    def __init__(
        self,
        quiet: bool = False,
        report_path: str = "",
        on_done: Optional[Callable[[dict, dict], None]] = None,
    ) -> None:
        self._quiet = quiet or bool(os.environ.get("WFH_QUIET"))
        self._report_path = report_path or os.environ.get("WFH_CHUNK_REPORT", "")
        self._on_done = on_done
        self._full_report = bool(os.environ.get("WFH_FULL_REPORT"))
        self._is_tty = sys.stdout.isatty()
        try:
            self._cols = os.get_terminal_size().columns
        except OSError:
            self._cols = 120

        self._last_stats_print = 0.0
        self._stats_line_active = False  # True once we've printed the first stats line
        self._chunk_count = 0
        self._instance_count = 0

        # Accumulated delta chunks/summary forwarded from mapper on 'done'
        self._final_pattern_chunks: Dict[str, Any] = {}
        self._final_summary_cache: Dict[str, Any] = {}
        # Patricia-trie summary rows for the audit's "pattern trie" panel
        # (forward-truncated pattern, instances here, subtree size,
        # attr_tags). Optional — left empty when the caller doesn't
        # supply one. See attach_pattern_chunks.
        self._final_trie_rows: list = []
        # Per-pattern detector tags (search / pagination / etc.) — used
        # by the audit to label specialized chunks.
        self._final_pattern_tags: Dict[str, list] = {}
        # URL of the scan, for resolving relative @href / @src values.
        self._final_page_url: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_event(self, event: Dict[str, Any]) -> None:
        """Dispatch an event to the appropriate handler."""
        if self._quiet:
            return
        t = event.get("type", "")
        if t == "stats":
            self._on_stats(event)
        elif t == "log":
            self._on_log(event)
        elif t == "chunk_added":
            self._on_chunk(event, symbol="++", color=_GREEN)
        elif t == "chunk_replaced":
            self._on_chunk(event, symbol="~~", color=_CYAN)
        elif t == "chunk_removed":
            self._on_chunk_removed(event)
        elif t == "done":
            self._on_done_event(event)

    def attach_pattern_chunks(
        self,
        pattern_chunks: dict,
        summary_cache: dict,
        trie_rows: Optional[list] = None,
        pattern_tags: Optional[Dict[str, list]] = None,
        page_url: str = "",
    ) -> None:
        """Called by mapper.snapshot() at scan-end to supply the final chunk
        state for the HTML report.  Calling this before the 'done' event
        arrives ensures the report has all data.

        ``trie_rows`` is the Patricia trie's ``iter_summaries()`` output —
        a list of ``(full_pattern, instances_here, subtree_size, attr_tags)``
        rows the audit renders in a top-of-page summary panel so the user
        can see the rollups across nested prefixes (e.g. the homepage's
        whole grid contains 217 chunks, of which 43 are tile cards).
        ``pattern_tags`` is a per-pattern label dict (e.g. {"<pattern>":
        ["search", "pagination"]}) used to surface specialized chunks
        with a distinct visual badge.
        """
        self._final_pattern_chunks = pattern_chunks
        self._final_summary_cache = summary_cache
        self._final_trie_rows = list(trie_rows or [])
        self._final_pattern_tags = dict(pattern_tags or {})
        self._final_page_url = page_url or ""

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_stats(self, stats: dict) -> None:
        now = time.time()
        if now - self._last_stats_print < self.STATS_INTERVAL:
            return
        self._last_stats_print = now

        iters   = stats.get("iter_count", 0)
        nodes   = stats.get("nodes_streamed", 0)
        built   = stats.get("chunks_built", 0)
        vect    = stats.get("chunks_vectorized", 0)
        persist = stats.get("instances_persisted", 0)
        elapsed = stats.get("elapsed_s", 0.0)
        vocab   = stats.get("vocab_size", 0)
        docs    = stats.get("doc_count", 0)
        complete = stats.get("complete", False)

        vocab_str = f"{vocab / 1000:.1f}k" if vocab >= 1000 else str(vocab)

        # Build the plain text first; if it fits, add colour codes.
        # This avoids the ANSI-mid-sequence truncation bug.
        plain = (
            f"iter {iters:3d}  "
            f"nodes {nodes:5d}  "
            f"built/vec {built:3d}/{vect:3d}  "
            f"persist {persist:4d}  "
            f"vocab {vocab_str:>5}  docs {docs:4d}  "
            f"[{elapsed:5.1f}s]"
        )
        if complete:
            plain += "  ✓ done"

        # Truncate plain text to terminal width, then optionally colourize.
        if len(plain) > self._cols - 1:
            plain = plain[:self._cols - 4] + "..."
            line = plain  # already truncated; skip colours to stay safe
        else:
            line = (
                f"iter {_c(_BOLD, f'{iters:3d}')}  "
                f"nodes {_c(_CYAN, f'{nodes:5d}')}  "
                f"built/vec {_c(_GREEN, f'{built:3d}')}/{_c(_GREEN, f'{vect:3d}')}  "
                f"persist {persist:4d}  "
                f"vocab {_c(_YELLOW, vocab_str):>5}  docs {docs:4d}  "
                f"[{elapsed:5.1f}s]"
            )
            if complete:
                line += _c(_GREEN, "  ✓ done")

        if self._is_tty:
            # Overwrite current line
            sys.stdout.write(f"\033[2K\r{line}")
        else:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()
        self._stats_line_active = True

    def _on_log(self, log: dict) -> None:
        stage = log.get("stage", "?")
        msg   = log.get("message", "")
        # Skip noise; only print promoted stages or keyword-matched messages
        should_print = (
            stage in self.VERBOSE_STAGES
            or any(kw in msg for kw in self.PROMOTE_KEYWORDS)
        )
        if not should_print:
            return
        self._newline_if_needed()
        stage_str = _c(_MAGENTA, f"[{stage:<6}]")
        print(f"  {stage_str} {msg}")

    def _on_chunk(self, event: dict, symbol: str, color: str) -> None:
        chunk = event.get("chunk", {})
        if not chunk:
            return
        self._chunk_count += 1
        cid     = (chunk.get("chunk_id") or "")[:8]
        chars   = chunk.get("char_count", 0)
        count   = chunk.get("commutation_count", 1)
        pattern = chunk.get("pattern", "")
        has_img = chunk.get("has_image", False)
        img_str = " 🖼" if has_img else ""
        # Shorten pattern for display
        pat_short = _shorten_pattern(pattern, 50)
        self._newline_if_needed()
        line = (
            f"  {_c(color, symbol)} [{_c(_DIM, cid)}]"
            f"  chars={chars:4d}"
            f"  ×{count}"
            f"  {_c(_DIM, pat_short)}"
            f"{img_str}"
        )
        print(line)

    def _on_chunk_removed(self, event: dict) -> None:
        cid = (event.get("chunk_id") or "")[:8]
        self._newline_if_needed()
        print(f"  {_c(_RED, '--')} [{_c(_DIM, cid)}]  {_c(_DIM, 'removed')}")

    def _on_done_event(self, event: dict) -> None:
        self._newline_if_needed()
        chunk_count  = self._chunk_count
        persist      = event.get("chunk_count", 0)
        width = min(self._cols, 60)
        bar = _c(_GREEN, "─" * width)
        print(f"\n{bar}")
        print(
            _c(_BOLD, f"  SCAN COMPLETE")
            + f"  {_c(_GREEN, str(chunk_count))} chunks streamed"
            + (f"  •  {_c(_YELLOW, str(persist))} persisted" if persist else "")
        )
        print(bar)

        if self._on_done:
            try:
                self._on_done(self._final_pattern_chunks, self._final_summary_cache)
            except Exception:
                pass

        if self._report_path and self._final_pattern_chunks:
            write_chunk_report(
                self._final_pattern_chunks,
                self._final_summary_cache,
                self._report_path,
                full_report=self._full_report,
                page_url=self._final_page_url,
                trie_rows=self._final_trie_rows,
                pattern_tags=self._final_pattern_tags,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _newline_if_needed(self) -> None:
        """Move off the stats line before printing a block message."""
        if self._is_tty and self._stats_line_active:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._stats_line_active = False


# ---------------------------------------------------------------------------
# HTML chunk-panel report writer
# ---------------------------------------------------------------------------

_REPORT_CSS = """
body { font-family: system-ui, sans-serif; margin: 2rem; color: #222; background: #f8f8f8; }
h1 { border-bottom: 2px solid #333; padding-bottom: .5rem; }
.chunk { background: white; border: 1px solid #ddd; border-radius: 8px;
         padding: 1rem 1.25rem; margin-bottom: 1.25rem; box-shadow: 0 1px 3px #0001;
         display: grid; grid-template-columns: 140px 1fr; gap: 1rem; align-items: start; }
.chunk .left { min-width: 0; }
.chunk .right { min-width: 0; }
.chunk h2.pattern { font-size: .8rem; color: #555; margin: 0 0 .25rem;
                    font-family: ui-monospace, monospace; word-break: break-all; }
.chunk h3.title { font-size: 1.05rem; margin: 0 0 .35rem; line-height: 1.25; }
.chunk h3.title a { color: #1a4ea2; text-decoration: none; }
.chunk h3.title a:hover { text-decoration: underline; }
.meta { font-size: .75rem; color: #888; margin-bottom: .5rem; }
.meta span { margin-right: 1rem; }
.meta .badge { background: #eef; color: #224; padding: .1rem .5rem;
               border-radius: 999px; font-weight: 500; }
img.preview { width: 130px; height: 130px; object-fit: cover;
              border-radius: 6px; border: 1px solid #eee; background: #fafafa; }
.no-image { width: 130px; height: 130px; border: 1px dashed #ccc;
            border-radius: 6px; display: flex; align-items: center; justify-content: center;
            color: #aaa; font-size: .75rem; background: #fbfbfb; }
.snippet { font-size: .85rem; line-height: 1.45; color: #333; margin: .25rem 0 .5rem;
           white-space: pre-wrap; word-wrap: break-word; }
.fields-table { width: 100%; border-collapse: collapse; font-size: .75rem;
                font-family: ui-monospace, monospace; margin-top: .5rem; }
.fields-table th { text-align: left; color: #777; font-weight: 500;
                   padding: .15rem .4rem; border-bottom: 1px solid #eee; width: 35%; }
.fields-table td { padding: .15rem .4rem; border-bottom: 1px solid #f4f4f4;
                   word-break: break-all; }
.fields-table td.url { color: #1a4ea2; }
.fields-table td.text { color: #333; }
details summary { cursor: pointer; font-size: .75rem; color: #777; margin-top: .5rem; }
details pre { font-size: .7rem; background: #fafafa; padding: .5rem;
              overflow: auto; max-height: 220px; border-radius: 3px;
              border: 1px solid #eee; }
hr { display: none; }
"""


# Heuristics — pulled out so they're easy to tune without touching the writer.
_TITLE_ATTR_PRIORITY = (
    "/@title",
    "/@aria-label",
    "/@alt",
    "/h1/text()",
    "/h2/text()",
    "/h3/text()",
    "/h4/text()",
    "/text()",
)
_IMAGE_ATTR_KEYS = ("/@src", "/@data-src", "/@data-original", "/@data-image", "/@poster", "/@srcset")
_LINK_ATTR_KEYS = ("/@href", "/@data-href")
# Match "12,345 items" / "12k items" / "5 items" — surface as item-count badge.
import re as _re_audit
_ITEM_COUNT_RE = _re_audit.compile(
    r"\b([\d,.]+\s*[KkMmBb]?)\s*(items?|results?|videos?|recipes?|songs?|texts?|articles?|images?|files?)\b",
    _re_audit.IGNORECASE,
)


def _pick_first_field(fields: dict, suffix_priority: tuple) -> tuple:
    """Return (key, value) of the first field whose key endswith one of the
    given suffixes, walking suffix_priority in order."""
    if not fields:
        return ("", "")
    for suf in suffix_priority:
        for k, v in fields.items():
            if k.endswith(suf) and v:
                return (k, str(v))
    return ("", "")


def _resolve_url(raw: str, base: str = "") -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if raw.startswith(("http://", "https://", "data:", "blob:")):
        return raw
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("/") and base:
        try:
            from urllib.parse import urlparse
            p = urlparse(base)
            return f"{p.scheme}://{p.netloc}{raw}"
        except Exception:
            return raw
    return raw


def _summarise_card_fields(fields: dict, page_url: str = "") -> dict:
    """Pull title / link / image / item-count from a chunk's content_fields.

    Cards on archive.org / similar grids encode each piece of info in a
    different attribute (title in @aria-label or h3/text, image in @src,
    link in @href, item count in trailing text). This single pass surfaces
    them so the audit can render a real card preview instead of a JSON dump.
    """
    if not fields:
        return {"title": "", "link": "", "image": "", "item_count": "", "all_text": ""}

    title_key, title_val = _pick_first_field(fields, _TITLE_ATTR_PRIORITY)
    link_key, link_val = _pick_first_field(fields, _LINK_ATTR_KEYS)
    img_key, img_val = _pick_first_field(fields, _IMAGE_ATTR_KEYS)

    # Concatenated text for snippet + item-count regex
    text_chunks = [v for k, v in fields.items() if k.endswith("/text()") and v]
    all_text = " ".join(text_chunks)
    item_count = ""
    m = _ITEM_COUNT_RE.search(all_text)
    if m:
        item_count = f"{m.group(1).strip()} {m.group(2).lower()}"

    return {
        "title": title_val,
        "title_key": title_key,
        "link": _resolve_url(link_val, page_url),
        "image": _resolve_url(img_val, page_url),
        "item_count": item_count,
        "all_text": all_text,
    }


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
                  .replace('"', "&quot;"))


def _classify_field_value(key: str, val: str) -> str:
    """Return 'url' / 'text' / 'meta' for table-cell styling."""
    klow = key.lower()
    if any(klow.endswith(suf) for suf in _IMAGE_ATTR_KEYS + _LINK_ATTR_KEYS):
        return "url"
    if klow.endswith("/text()") or any(klow.endswith(suf) for suf in _TITLE_ATTR_PRIORITY):
        return "text"
    return "meta"


def _pick_representative(chunks: list) -> dict:
    """Pick the richest chunk in a pattern bucket to render as the card.

    Score = (#fields × 2) + char_count. Ties broken by chunk_id so
    audit output is deterministic between runs."""
    if not chunks:
        return {}
    def score(c):
        f = c.get("content_fields_full") or c.get("content_fields") or {}
        return (len(f) * 2 + (c.get("char_count") or 0), c.get("chunk_id") or "")
    return max(chunks, key=score)


def _forward_truncate_display(pattern: str, last_n: int = 3, attr_tag: str = "") -> str:
    """Local mirror of pattern_trie.forward_truncate so the audit module
    doesn't require importing the trie just to render a path. Keeps both
    sides of the rendering pipeline visually consistent."""
    segs = [s for s in pattern.split("/") if s]
    tail = segs[-last_n:] if len(segs) > last_n else segs
    head = "…/" if len(segs) > last_n else ""
    out = head + "/".join(tail)
    if attr_tag:
        if not attr_tag.startswith(("/", "@", ".")):
            attr_tag = "/" + attr_tag
        out += attr_tag
    return out


def write_chunk_report(
    pattern_chunks: dict,
    summary_cache: dict,
    output_path: str = "chunks_report.html",
    full_report: bool = False,
    page_url: str = "",
    trie_rows: Optional[list] = None,
    pattern_tags: Optional[Dict[str, list]] = None,
) -> None:
    """Write an HTML file: ONE card per pattern, with ``×N instances`` badge.

    Earlier behaviour was one card per chunk_id, which blew the audit up
    to hundreds of near-duplicate rows on grid pages (every YouTube tile,
    every archive.org collection card). The chunks themselves are still
    distinct in the TF-IDF index — the audit just rolls them up by
    pattern for readability.

    For each chunk we surface:
      - the title (h1/h2/h3 text or @aria-label/@title fallback)
      - the hyperlink (@href)
      - the image (@src / @data-src / @poster — first hit wins)
      - the item count parsed out of the prose ("12,345 items", "5 results")
      - a snippet of joined text() values
      - the full content_fields_full table (xpath:attr → value) so
        nothing is hidden — the user can verify all required fields are
        present without scrolling JSON.

    ``trie_rows`` is the Patricia trie's ``iter_summaries()`` output. When
    supplied we render a top-of-page panel showing rollup counts under
    each prefix — answers "how many cards are under this whole grid?"
    in addition to "how many sibling cards share this exact pattern?".
    ``pattern_tags`` adds a detector-type chip ("search input",
    "pagination", etc.) to patterns surfaced by the specialized
    detectors in the JS engine.
    """
    pattern_tags = pattern_tags or {}
    total = sum(len(cl) for cl in pattern_chunks.values())
    pattern_count = len(pattern_chunks)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html><html lang='en'><head>")
        f.write("<meta charset='utf-8'>")
        f.write(f"<title>Chunk Report — {pattern_count} patterns / {total} chunks</title>")
        f.write(f"<style>{_REPORT_CSS}</style>")
        f.write("</head><body>")
        f.write(
            f"<h1>Chunk Report <small style='font-weight:400;font-size:.7em;'>"
            f"— {pattern_count} patterns / {total} chunks</small></h1>\n"
        )

        # Patricia-trie summary panel: shows rollup counts under every
        # prefix that owns chunks. Truncated to last 3 segments + the
        # attr-tag set, like the spec's "great-grandparents" form.
        if trie_rows:
            f.write('<section style="background:white;border:1px solid #ddd;'
                    'border-radius:8px;padding:1rem 1.25rem;margin-bottom:1.5rem;">'
                    '<h2 style="margin:0 0 .5rem;font-size:1rem;">Pattern trie '
                    '<small style="font-weight:400;color:#888;">'
                    f'({len(trie_rows)} pattern-owning nodes)</small></h2>')
            f.write('<table class="fields-table"><thead><tr>'
                    '<th style="width:55%">forward-truncated pattern</th>'
                    '<th>here</th><th>subtree</th><th>attr tags</th>'
                    '</tr></thead><tbody>')
            for full_p, here, sub, attr_tags in trie_rows[:60]:
                trunc = _forward_truncate_display(full_p, 3,
                    attr_tag=",".join(attr_tags) if attr_tags else "")
                f.write('<tr>')
                f.write(f'<td class="text">{_esc(trunc)}</td>')
                f.write(f'<td class="meta">×{here}</td>')
                f.write(f'<td class="meta">{sub}</td>')
                f.write(f'<td class="meta">{_esc(", ".join(attr_tags)) if attr_tags else "—"}</td>')
                f.write('</tr>')
            if len(trie_rows) > 60:
                f.write(f'<tr><td colspan="4" class="meta">… {len(trie_rows) - 60} more</td></tr>')
            f.write('</tbody></table></section>')

        # Sort: patterns with more instances first, then alphabetical for
        # stable diffs. Singletons fall to the bottom.
        sorted_patterns = sorted(
            pattern_chunks.items(),
            key=lambda kv: (-len(kv[1]), kv[0]),
        )

        for pattern, chunk_list in sorted_patterns:
            instance_count = len(chunk_list)
            c = _pick_representative(chunk_list)
            rep_xp   = c.get("representative_xpath", "") or ""
            chunk_id = c.get("chunk_id", "") or ""
            chars    = c.get("char_count", 0) or 0

            fields = (
                c.get("content_fields_full")
                or c.get("content_fields")
                or {}
            )
            # Allow summary_cache (legacy bottom-up chunker path) to
            # override with richer field data when present.
            cache_entry = summary_cache.get(rep_xp + "__summary", {})
            if cache_entry.get("content_fields_full"):
                fields = cache_entry["content_fields_full"]

            card = _summarise_card_fields(fields, page_url=page_url)
            title = card["title"] or pattern
            link = card["link"]
            image = card["image"]
            item_count = card["item_count"]
            snippet = card["all_text"] or c.get("rendered_text", "") or ""
            if len(snippet) > 320:
                snippet = snippet[:320] + "…"

            f.write('<div class="chunk">\n')

            # ---- LEFT: image preview or empty placeholder ----
            f.write('<div class="left">')
            if image:
                f.write(
                    f'<img class="preview" src="{_esc(image)}" '
                    f'alt="card image" loading="lazy" '
                    f'onerror="this.outerHTML=&quot;'
                    f'<div class=\\&quot;no-image\\&quot;>(image failed)</div>&quot;">'
                )
            else:
                f.write('<div class="no-image">no image</div>')
            f.write('</div>')

            # ---- RIGHT: title, meta, snippet, fields table ----
            f.write('<div class="right">')
            # Use the forward-truncated pattern (last 3 segments) in the
            # card header so the audit reads as a compact xpath:attr
            # form per the original spec. Full xpath is still shown in
            # the meta row.
            display_pat = _forward_truncate_display(pattern, 3)
            f.write(f'<h2 class="pattern" title="{_esc(pattern)}">{_esc(display_pat)}</h2>')
            if link:
                f.write(
                    f'<h3 class="title"><a href="{_esc(link)}" target="_blank" '
                    f'rel="noopener">{_esc(title)}</a></h3>'
                )
            else:
                f.write(f'<h3 class="title">{_esc(title)}</h3>')

            # Detector tags (search input, pagination, etc.) — only
            # printed when the JS engine emits the chunk via one of the
            # specialized detector channels.
            tags = pattern_tags.get(pattern, [])
            if tags:
                f.write('<div class="meta" style="margin-top:.1rem;">')
                for tg in tags:
                    f.write(
                        f'<span class="badge" style="background:#fdf6e3;'
                        f'color:#8a6d3b;">{_esc(tg)}</span>'
                    )
                f.write('</div>')

            f.write('<div class="meta">')
            f.write(
                f'<span class="badge" title="chunks sharing this pattern">'
                f'×{instance_count} instances</span>'
            )
            f.write(f'<span>repr id <code>{_esc(chunk_id[:12])}</code></span>')
            f.write(f'<span>chars {chars}</span>')
            if item_count:
                f.write(f'<span class="badge">{_esc(item_count)}</span>')
            if image:
                f.write('<span>🖼</span>')
            if link:
                f.write('<span>🔗</span>')
            f.write(f'<span style="opacity:.55">xp {_esc(rep_xp)}</span>')
            f.write('</div>\n')

            if snippet.strip():
                f.write(f'<div class="snippet">{_esc(snippet)}</div>')

                if fields:
                    if full_report:
                        # Inline table — every key visible at a glance.
                        f.write('<table class="fields-table">')
                        f.write('<thead><tr><th>field</th><th>value</th></tr></thead><tbody>')
                        for k in sorted(fields.keys()):
                            v = fields[k]
                            cls = _classify_field_value(k, v)
                            if cls == "url" and v:
                                resolved = _resolve_url(v, page_url)
                                v_html = (
                                    f'<a href="{_esc(resolved)}" target="_blank" '
                                    f'rel="noopener">{_esc(v)}</a>'
                                )
                            else:
                                v_html = _esc(v)
                            f.write(f'<tr><th>{_esc(k)}</th><td class="{cls}">{v_html}</td></tr>')
                        f.write('</tbody></table>')
                    else:
                        fields_json = json.dumps(fields, indent=2, ensure_ascii=False)
                        f.write('<details><summary>Full content fields</summary>')
                        f.write(f'<pre>{_esc(fields_json)}</pre></details>')

                f.write('</div>')   # /.right
                f.write('</div>\n')  # /.chunk

        f.write("</body></html>\n")

    print(f"\n  ✓ Chunk report → {output_path}  ({total} chunks)")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences to measure true display width."""
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


def _shorten_pattern(pattern: str, max_len: int) -> str:
    """Keep the last N characters of the pattern (the meaningful part)."""
    if len(pattern) <= max_len:
        return pattern
    return "…" + pattern[-(max_len - 1):]


# ---------------------------------------------------------------------------
# Factory — creates a wired on_stream composer
# ---------------------------------------------------------------------------

def make_console_stream(
    on_stream: Optional[Callable[[Dict[str, Any]], None]],
    reporter: Optional[ConsoleStatsReporter] = None,
    **reporter_kwargs: Any,
) -> "tuple[Callable[[Dict[str, Any]], None], ConsoleStatsReporter]":
    """Return a composed on_stream that feeds both the console reporter and the
    original WebSocket callback.

    Usage::

        composed, reporter = make_console_stream(original_on_stream)
        pipeline = SnapshotPipeline(on_stream=composed)

    Parameters
    ----------
    on_stream:
        The original WebSocket callback (may be None).
    reporter:
        If supplied, use this reporter instance; otherwise create one from
        ``reporter_kwargs``.

    Returns
    -------
    composed_on_stream, reporter
    """
    if reporter is None:
        reporter = ConsoleStatsReporter(**reporter_kwargs)

    def _composed(event: Dict[str, Any]) -> None:
        try:
            reporter.handle_event(event)
        except Exception:
            pass  # Never let reporting crash the scan
        if on_stream is not None:
            on_stream(event)

    return _composed, reporter
