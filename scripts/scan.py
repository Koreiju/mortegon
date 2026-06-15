"""
scripts/scan.py — Standalone real-time web chunk scanner.

Runs the full pipeline (Selenium → delta extraction → bottom-up chunking →
TF-IDF → kuzu persistence) entirely from the terminal, with no running app.py
required.  Live stats, per-chunk events, and stage logs are printed to the
console via the built-in ConsoleStatsReporter.  Optionally writes an HTML
chunk-panel report at the end.

## Two modes of operation

**Backend-delegation mode** (app.py is running):

    python scripts/scan.py https://example.com

    scan.py detects the running backend, delegates the scan via
    GET /api/snapshot, and tails the resulting WebSocket stream to print
    the usual stats to the console.  The frontend GUI receives live sphere
    updates automatically — no Scan button click needed.  DB persistence
    happens in the backend's background thread (parallel, never blocks
    the scanner).

**Standalone mode** (no running app.py):

    python scripts/scan.py https://example.com --no-backend

    Runs entirely in-process using Selenium + DomMapper.  DB persistence
    still happens on a background thread inside the pipeline.  If
    --ws-port N is also passed, an embedded asyncio WebSocket server is
    started so a separately-opened frontend can connect and watch the scan
    live.

Usage::

    python scripts/scan.py https://example.com
    python scripts/scan.py https://news.ycombinator.com --max-duration 60
    python scripts/scan.py https://shop.example.com --report
    python scripts/scan.py https://shop.example.com --no-backend --ws-port 8765
    python scripts/scan.py --help

Flags:

    url                 URL to scan (required, or uses current browser page).
    --max-duration N    Stop scrolling after N seconds.  Default: 120.
    --pause N           Seconds to wait after each scroll.  Default: 0.5.
    --report            Write an HTML chunk-panel report after scanning.
    --report-path PATH  Path for the HTML report.  Default: chunks_report.html.
    --query             After the scan, enter an interactive TF-IDF query loop.
    --no-backend        Force standalone mode even if app.py is running.
    --backend-url URL   Backend base URL (default: http://localhost:8000).
    --ws-port N         Start embedded WS server on port N in standalone mode.
    --quiet             Suppress all console stats (errors still print).
    --no-db             Skip kuzu DB initialisation and chunk persistence.
    --log-level LEVEL   Python logging level.  Default: WARNING.

Environment variables:

    WFH_QUIET=1             Same as --quiet.
    WFH_CHUNK_REPORT=PATH   Same as --report-path PATH (auto-enables --report).
    NO_WEBDRIVER=1          Dry-run mode: skips Selenium and exits early.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import json
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.WARNING)
    logging.basicConfig(
        format="[%(name)s] %(levelname)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )
    for noisy in ("selenium", "urllib3", "httpx", "httpcore",
                  "webdriver_manager", "asyncio", "kuzu"):
        logging.getLogger(noisy).setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

_BANNER = r"""
 ██╗    ██╗███████╗██╗  ██╗    ███████╗ ██████╗ █████╗ ███╗   ██╗
 ██║    ██║██╔════╝██║  ██║    ██╔════╝██╔════╝██╔══██╗████╗  ██║
 ██║ █╗ ██║█████╗  ███████║    ███████╗██║     ███████║██╔██╗ ██║
 ██║███╗██║██╔══╝  ██╔══██║    ╚════██║██║     ██╔══██║██║╚██╗██║
 ╚███╔███╔╝███████╗██║  ██║    ███████║╚██████╗██║  ██║██║ ╚████║
  ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝
  Real-time chunk scanner  •  Ctrl-C to stop early
"""


def _print_banner(url: str) -> None:
    try:
        cols = os.get_terminal_size().columns
    except OSError:
        cols = 80
    print(_BANNER if cols >= 72 else "\n  web-fiber-haptics scan\n")
    print(f"  target : {url}")
    print(f"  root   : {ROOT}")
    print()


# ---------------------------------------------------------------------------
# WebDriver + DB helpers
# ---------------------------------------------------------------------------

def _get_driver():
    from backend.services.selenium_client import WebBrowserManager
    print("[scan.py] Connecting to Firefox WebDriver…", flush=True)
    mgr = WebBrowserManager()
    return mgr.get_driver()


def _init_db() -> None:
    try:
        import backend.database as _db
        _db.init_db()
    except Exception as exc:
        print(f"[scan.py] WARNING: DB init failed ({exc}). Chunks won't be persisted.",
              file=sys.stderr)


# ---------------------------------------------------------------------------
# Graceful interrupt
# ---------------------------------------------------------------------------

_scan_cancelled = False


def _setup_sigint() -> None:
    def _handler(sig, frame):
        global _scan_cancelled
        if not _scan_cancelled:
            _scan_cancelled = True
            print("\n\n[scan.py] Ctrl-C received — stopping after current iteration…",
                  flush=True)
        else:
            print("\n[scan.py] Force exit.", flush=True)
            sys.exit(130)
    signal.signal(signal.SIGINT, _handler)


# ---------------------------------------------------------------------------
# Console frame renderer
# ---------------------------------------------------------------------------

def _print_scan_frame(frame: dict) -> None:
    """Print a compact representation of a WS frame to the console."""
    t = frame.get("type")
    if t == "stats":
        print(
            f"  iter {frame.get('iter_count', 0):3d}"
            f"  nodes {frame.get('nodes_streamed', 0):4d}"
            f"  built/vec {frame.get('chunks_built', 0):3d}/{frame.get('chunks_vectorized', 0):3d}"
            f"  persist {frame.get('instances_persisted', 0):4d}"
            f"  vocab {frame.get('vocab_size', 0):5d}"
            f"  [{frame.get('elapsed_s', 0):.1f}s]",
            flush=True,
        )
    elif t == "log":
        stage = (frame.get("stage") or "").upper()[:6].ljust(6)
        msg   = (frame.get("message") or "").replace("\n", " ")
        print(f"  [{stage}] {msg}")
    elif t == "chunk_added":
        ch = frame.get("chunk") or {}
        cid = ch.get("chunk_id", "?")[:8]
        chars = ch.get("char_count") or ch.get("subtree_text_budget") or "?"
        print(f"  ++ [{cid}]  chars={chars}")
    elif t == "chunk_removed":
        cid = (frame.get("chunk_id") or "?")[:8]
        print(f"  -- [{cid}]")
    elif t == "done":
        print("\n[scan.py] Scan complete (backend reported done)\n", flush=True)
    elif t == "cached":
        print("[scan.py] Page unchanged since last scan — using cached snapshot\n",
              flush=True)
    elif t == "error":
        print(f"[scan.py] ERROR: {frame.get('error', 'unknown')}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Embedded WebSocket server (standalone mode, optional)
# ---------------------------------------------------------------------------

class ScanStreamServer:
    """
    Minimal asyncio WebSocket broadcast server for standalone mode.

    When app.py is NOT running and --ws-port N is supplied, this server lets
    the frontend (opened separately, pointed at localhost:N) receive live
    chunk events from a standalone scan.py session.

    Silently skips setup if the 'websockets' package is not installed.
    """

    def __init__(self, port: int = 8765) -> None:
        self.port      = port
        self._clients: set = set()
        self._loop:    Optional["asyncio.AbstractEventLoop"] = None
        self._thread:  Optional[threading.Thread] = None
        self._ready    = threading.Event()
        self._started  = False

    def start(self) -> bool:
        """Launch the WS server on a daemon thread.  Returns True on success."""
        try:
            import websockets  # noqa: F401
        except ImportError:
            print("[scan.py] 'websockets' not installed — embedded WS server unavailable.",
                  file=sys.stderr)
            return False

        import asyncio

        async def _handler(ws):
            self._clients.add(ws)
            try:
                await ws.wait_closed()
            finally:
                self._clients.discard(ws)

        async def _serve():
            import websockets as _ws
            # websockets ≥11 uses serve() as a context manager
            async with _ws.serve(_handler, "localhost", self.port):
                self._ready.set()
                await asyncio.Future()  # run until cancelled

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(_serve())
            except Exception:
                self._ready.set()  # unblock caller even on error

        self._thread = threading.Thread(target=_run, daemon=True, name="ScanWS")
        self._thread.start()
        if self._ready.wait(timeout=3):
            self._started = True
            print(f"[scan.py] Embedded WS server → ws://localhost:{self.port}")
            return True
        return False

    def broadcast(self, payload: dict) -> None:
        """Thread-safe broadcast to all connected frontend clients."""
        if not self._started or not self._loop or not self._clients:
            return
        import asyncio

        msg = json.dumps(payload, ensure_ascii=False, default=str)

        async def _do():
            dead = set()
            for ws in list(self._clients):
                try:
                    await ws.send(msg)
                except Exception:
                    dead.add(ws)
            self._clients -= dead

        asyncio.run_coroutine_threadsafe(_do(), self._loop)


# ---------------------------------------------------------------------------
# Backend-delegation mode
# ---------------------------------------------------------------------------

def _backend_is_reachable(base_url: str, timeout: float = 1.5) -> bool:
    """Return True if the backend server answers a lightweight health probe."""
    try:
        req = urllib.request.Request(
            f"{base_url}/api/scan_status",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _try_backend_delegation(
    url: str,
    backend_base: str = "http://localhost:8000",
    quiet: bool = False,
) -> bool:
    """
    Delegate the scan to the running backend server.

    1. POST to GET /api/snapshot?url=<url>  →  get ws_url.
    2. Tail the WebSocket stream, printing stats to the console.
    3. The frontend auto-detects the active scan via GET /api/scan_status
       and attaches to the same WS stream (see checkForActiveScan in
       scanner.js).
    4. DB writes happen in the backend's background thread — never blocking
       the scanner or the WS stream.

    Returns True if delegation succeeded, False if the backend is unreachable
    or the scan endpoint returned an error.
    """
    if not _backend_is_reachable(backend_base):
        return False

    try:
        import websockets  # needed for WS tailing
    except ImportError:
        print("[scan.py] 'websockets' not installed — cannot tail live WS stream.")
        print("[scan.py] Backend delegation still works; use the GUI to watch progress.")
        # Trigger the scan on the backend but don't tail (no console output).
        try:
            encoded = urllib.parse.quote(url, safe='')
            req = urllib.request.Request(f"{backend_base}/api/snapshot?url={encoded}")
            with urllib.request.urlopen(req, timeout=10) as r:
                dispatch = json.loads(r.read())
            print(f"[scan.py] Scan triggered — ws_url: {dispatch.get('ws_url')}")
        except Exception as exc:
            print(f"[scan.py] Backend scan trigger failed: {exc}", file=sys.stderr)
        return True  # partial success — no console tailing

    import asyncio

    async def _run_delegation() -> bool:
        import websockets as _ws

        # ── Trigger the scan ──────────────────────────────────────────────
        try:
            encoded = urllib.parse.quote(url, safe='')
            req = urllib.request.Request(
                f"{backend_base}/api/snapshot?url={encoded}",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                dispatch = json.loads(r.read())
        except Exception as exc:
            print(f"[scan.py] Backend scan trigger failed: {exc}", file=sys.stderr)
            return False

        ws_path = dispatch.get("ws_url") or f"/api/ws/nodes/{dispatch.get('snapshot_ws_id', 0)}"
        # Convert http(s) base to ws(s)
        ws_base = backend_base.replace("https://", "wss://").replace("http://", "ws://")
        ws_url  = f"{ws_base}{ws_path}?resume=0"

        gui_url = f"{backend_base}/"
        print(f"[scan.py] Backend running — scan delegated.")
        print(f"[scan.py] GUI  → {gui_url}  (live updates active)")
        print(f"[scan.py] WS   → {ws_url}")
        print()

        # ── Tail the WS stream for console output ─────────────────────────
        try:
            async with _ws.connect(ws_url) as ws_conn:
                async for raw in ws_conn:
                    try:
                        frame = json.loads(raw)
                    except Exception:
                        continue
                    if not quiet:
                        _print_scan_frame(frame)
                    if frame.get("type") == "done":
                        break
        except KeyboardInterrupt:
            print("\n[scan.py] Interrupted.", flush=True)
        except Exception as exc:
            print(f"[scan.py] WS tail error: {exc}", file=sys.stderr)

        return True

    try:
        return asyncio.run(_run_delegation())
    except Exception as exc:
        print(f"[scan.py] Delegation error: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Interactive query loop
# ---------------------------------------------------------------------------

def _run_interactive_query(url: str, export_data: dict):
    """Interactive TF-IDF query loop with rich per-hit summaries.

    For each hit we print the same headline info the audit.html shows for
    a card: title, hyperlink, image URL, item-count badge, snippet, and
    the full content_fields_full table. Previously only the joined text
    preview was printed, which made it impossible to tell from the
    terminal whether the retrieved chunk actually carried the URL/image
    fields needed downstream.
    """
    from backend.services.global_tfidf_store import get_default_store
    # Reuse the audit-side helpers so terminal output and audit.html
    # surface fields the same way.
    from backend.mapper.console_reporter import _summarise_card_fields

    store = get_default_store()
    if store.doc_count == 0:
        print("\n[query] No documents in the TF-IDF store — nothing to search.\n")
        return

    chunk_data  = export_data.get("chunks", {})
    member_data = export_data.get("members", {})

    print(f"\n[query] Store has {store.doc_count} documents, {store.vocab_size} vocabulary terms")
    sample_urls = list(set(m.url for m in store._chunk_meta))[:5]
    print(f"  Indexed URLs: {sample_urls}")
    print(f"  Query URL:    {url}")

    # Patricia-trie top-pattern summary so the user can see the rollup
    # counts the spec calls for ("×N instances" across the trie, with
    # the ×subtree count above for sibling-rich grids).
    trie_rows = export_data.get("trie_rows") or []
    if trie_rows:
        print(f"\n  Top patterns (Patricia trie summary, {len(trie_rows)} pattern-owning nodes):")
        for full_p, here, sub, attr_tags in trie_rows[:10]:
            # Reuse the audit-side helper to render the forward-truncated path.
            from backend.mapper.pattern_trie import forward_truncate as _ft
            tag_str = ", ".join(attr_tags) if attr_tags else ""
            display = _ft(full_p, 3, attr_tag=tag_str)
            print(f"    ×{here:>3}  subtree={sub:>3}   {display}")

    pattern_tags = export_data.get("pattern_tags") or {}
    if pattern_tags:
        labelled = sum(len(v) for v in pattern_tags.values())
        kinds = {}
        for tags in pattern_tags.values():
            for t in tags:
                kinds[t] = kinds.get(t, 0) + 1
        kind_str = ", ".join(f"{k}={n}" for k, n in sorted(kinds.items()))
        print(f"\n  Specialized detectors fired: {labelled} pattern-tag(s) — {kind_str}")

    print("\n" + "=" * 60)
    print(" TF-IDF Query Loop")
    print(" Enter a search query to find matching chunks.")
    print(" Type 'END' (or Ctrl-C) to exit.")
    print("=" * 60)

    def _truncate(s: str, n: int = 280) -> str:
        s = s or ""
        return s if len(s) <= n else s[:n] + "…"

    def _middle_ellipsis_xpath(xp: str, max_len: int = 96) -> str:
        """Compress a long absolute xpath to ``/html/body[1]/.../article[117]``.

        Keeps the two head segments (``html``, ``body[1]``) verbatim and the
        deepest tail segments that still fit under max_len; everything in
        the middle collapses to ``...``. SLM-friendly: short enough for one
        terminal line, long enough to identify which DOM region the chunk
        lives in.
        """
        if not xp:
            return ""
        if len(xp) <= max_len:
            return xp
        parts = [p for p in xp.split("/") if p]
        head_keep = parts[:2]
        tail_keep = []
        running = len("/".join(head_keep)) + len("/.../") + 4
        for p in reversed(parts[len(head_keep):]):
            if running + len(p) + 1 > max_len:
                break
            tail_keep.insert(0, p)
            running += len(p) + 1
        if not tail_keep:
            return "/" + "/".join(head_keep) + "/..."
        return "/" + "/".join(head_keep) + "/.../" + "/".join(tail_keep)

    # ---- classification used for the aligned fields table -------------
    # Mirrors backend/mapper/console_reporter.py's _classify_field_value
    # so terminal output and audit.html agree on what's a URL / text /
    # meta value. We only repeat the suffix sets here to avoid forcing a
    # cross-module import for one helper.
    _URL_SUFFIXES   = ("/@href", "/@src", "/@srcset", "/@data-src",
                       "/@data-image", "/@data-original", "/@poster",
                       "/@action", "/@data-href")
    _TITLE_SUFFIXES = ("/@title", "/@aria-label", "/@alt",
                       "/h1/text()", "/h2/text()", "/h3/text()",
                       "/h4/text()", "/text()")

    def _classify_field(key: str) -> str:
        klow = key.lower()
        if any(klow.endswith(s) for s in _URL_SUFFIXES):
            return "url"
        if klow.endswith("/text()") or any(klow.endswith(s) for s in _TITLE_SUFFIXES):
            return "text"
        return "meta"

    def _print_hit(rank: int, hit, detail: dict) -> None:
        """Per-hit render that mirrors the audit.html card layout exactly:
        headline metadata + the FULL content_fields_full table with each
        row aligned by key column width and tagged by value type. The
        previous version dropped the table for "SLM-minimal" output, but
        for retrieval triage the user wants to see every field the chunk
        actually carries — same information audit.html surfaces in its
        ``fields-table``.
        """
        pattern_full    = detail.get("pattern") or hit.meta.pattern or "?"
        pattern_display = detail.get("pattern_display") or pattern_full
        instances       = detail.get("commutation_count") or 1
        subtree         = detail.get("subtree_count") or instances
        detector_tags   = detail.get("detector_tags") or []
        fields = (
            detail.get("content_fields_full")
            or detail.get("content_fields")
            or {}
        )
        card = _summarise_card_fields(fields, page_url=url)

        title      = card["title"] or "(no title)"
        link       = card["link"]
        image      = card["image"]
        item_count = card["item_count"]
        rep_xp     = detail.get("representative_xpath", "")

        chips = [f"×{instances} instances"]
        if subtree and subtree != instances:
            chips.append(f"subtree {subtree}")
        if detector_tags:
            chips.append("/".join(detector_tags))
        chip_str = "  ".join(chips)
        print(f"\n  {rank}. [{hit.score:.4f}] chunk_id={hit.chunk_id}   {chip_str}")
        # Forward-truncated pattern is the SLM-facing identifier. Full
        # xpath is collapsed via middle-ellipsis so a 12-deep DDG path
        # doesn't spill across multiple terminal lines.
        print(f"     pattern : {_truncate(pattern_display, 110)}")
        print(f"     full xp : {_middle_ellipsis_xpath(rep_xp or pattern_full, 96)}")
        print(f"     title   : {_truncate(title, 160)}")
        if link:
            print(f"     link    : {_truncate(link, 160)}")
        if image:
            print(f"     image   : {_truncate(image, 160)}")
        if item_count:
            print(f"     count   : {item_count}")

        snippet = card["all_text"] or detail.get("rendered_text") or hit.meta.text_preview or ""
        if snippet.strip():
            print(f"     snippet : {_truncate(snippet, 200)}")

        # ---- audit-equivalent fields table ----------------------------
        # Sorted for deterministic output. Each row shows:
        #   <marker>  <key, padded to common column width>  =  <value>
        # Markers: 🔗 url-shaped fields, 📝 prose / @title / @aria-label /
        # /text(), ·  other meta (data-* slugs, etc.).
        # The key column is sized to the widest key but capped at 72 so
        # a single absurdly-nested xpath doesn't push values off-screen.
        if fields:
            sorted_keys = sorted(fields.keys())
            # Truncate each key to the cap BEFORE computing column width
            # so the alignment isn't dictated by one outlier.
            KEY_CAP = 72
            display_keys = {k: (k if len(k) <= KEY_CAP else k[:KEY_CAP - 1] + "…")
                            for k in sorted_keys}
            key_width = min(KEY_CAP, max((len(v) for v in display_keys.values()), default=0))
            print(f"     fields  ({len(fields)} keys):")
            for k in sorted_keys:
                cls   = _classify_field(k)
                marker = {"url": "🔗", "text": "📝", "meta": " ·"}.get(cls, "  ")
                # URL values get a slightly longer display budget than text/meta.
                v_limit = 200 if cls == "url" else 160
                v_str   = _truncate(str(fields[k]), v_limit)
                print(f"       {marker} {display_keys[k].ljust(key_width)} = {v_str}")

    try:
        while True:
            try:
                q = input("\nQuery> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.upper() == "END":
                break
            if not q:
                continue

            from backend.services.global_tfidf_store import _tokens
            tokens   = _tokens(q)
            in_vocab = [t for t in tokens if t in store._vocab]
            print(f"  Tokens:       {tokens}")
            print(f"  In vocab:     {in_vocab}")

            hits = store.search(q, k=5, urls=[url])
            if not hits:
                print("  (no matching chunks)")
                continue

            for rank, hit in enumerate(hits, 1):
                detail = member_data.get(hit.chunk_id)
                if detail is None:
                    base_id = hit.chunk_id.rsplit("_", 1)[0] if "_" in hit.chunk_id else hit.chunk_id
                    detail  = chunk_data.get(base_id) or chunk_data.get(hit.chunk_id) or {}
                try:
                    _print_hit(rank, hit, detail)
                except Exception as exc:
                    # Never let a single bad chunk's render kill the loop.
                    print(f"     (render error: {exc})")
    except KeyboardInterrupt:
        pass
    print("\n[query] Exiting.\n")


# ---------------------------------------------------------------------------
# Core scan runner
# ---------------------------------------------------------------------------

def run_scan(
    url: str,
    *,
    max_duration: int = 120,
    pause: float = 0.5,
    report: bool = False,
    report_path: str = "chunks_report.html",
    full_report: bool = False,
    char_budget: int = 256,
    query: bool = False,
    continuous: bool = False,
    speed: float = 0.03,
    capture_interval: int = 80,
    quiet: bool = False,
    no_db: bool = False,
    no_backend: bool = False,
    backend_url: str = "http://localhost:8000",
    ws_port: Optional[int] = None,
    log_level: str = "WARNING",
) -> int:
    """Run a full scan against ``url`` and return an exit code (0 = success)."""
    _configure_logging(log_level)
    _print_banner(url)
    _setup_sigint()

    # ── Mode A: Backend-delegation ────────────────────────────────────────────
    if not no_backend:
        print(f"[scan.py] Checking for running backend at {backend_url}…", flush=True)
        if _try_backend_delegation(url, backend_base=backend_url, quiet=quiet):
            return 0
        print("[scan.py] Backend not reachable — falling back to standalone mode.\n",
              flush=True)

    # ── Mode B: Standalone (Selenium in-process) ───────────────────────────────

    # Environment flags
    if quiet:
        os.environ["WFH_QUIET"] = "1"
    if report:
        os.environ["WFH_CHUNK_REPORT"] = report_path
    elif "WFH_CHUNK_REPORT" in os.environ and not report:
        report      = True
        report_path = os.environ["WFH_CHUNK_REPORT"]

    # Standalone scans use the user's saved Firefox profile by default —
    # the uBlock-Origin profile is the same environment the user has been
    # browsing in, and archive.org renders correctly there. The empty-body
    # symptom we initially blamed on uBlock turned out to be the chunk
    # engine never piercing <app-root>'s shadow DOM. Set WFH_NO_PROFILE=1
    # on the command line to force a clean profile when explicitly needed.
    if full_report:
        os.environ["WFH_FULL_REPORT"] = "1"
    # Always set the env var so downstream chunkers see the chosen
    # budget — previously gated on `!= 2048` (the old default), which
    # silently dropped the now-default 256 because the gate became
    # `!= 2048` ⇒ truthy at 256 anyway. Explicit is safer.
    os.environ["WFH_CHAR_BUDGET"] = str(char_budget)
    os.environ["WFH_STRICT_HASH_MATCH"] = "0"
    if continuous:
        os.environ["WFH_CONTINUOUS_SCAN"]     = "1"
        os.environ["WFH_SCROLL_SPEED"]        = str(speed)
        os.environ["WFH_CAPTURE_INTERVAL_MS"] = str(capture_interval)

    # DB init
    if not no_db:
        _init_db()
    else:
        print("[scan.py] --no-db: skipping DB init, chunks won't be persisted.\n",
              flush=True)

    # Dry-run guard
    if os.environ.get("NO_WEBDRIVER") == "1":
        print("[scan.py] NO_WEBDRIVER=1: dry-run mode, exiting.\n")
        return 0

    # Optional embedded WS server so the GUI can watch standalone scans.
    ws_server   = None
    on_stream_cb = None
    if ws_port:
        ws_server = ScanStreamServer(port=ws_port)
        if ws_server.start():
            on_stream_cb = ws_server.broadcast
            print(f"[scan.py] Point the GUI at ws://localhost:{ws_port} to watch live.\n",
                  flush=True)

    # WebDriver
    try:
        driver = _get_driver()
    except Exception as exc:
        print(f"\n[scan.py] FATAL: could not start WebDriver: {exc}", file=sys.stderr)
        print("  Make sure Firefox is installed and geckodriver is on PATH.",
              file=sys.stderr)
        return 2

    # Mapper
    from backend.mapper.mapper import DomMapper
    from backend.mapper.pipeline_config import get_config

    mapper = DomMapper(driver=driver)
    cfg    = get_config()
    cfg.hard_char_limit = char_budget

    print(f"[scan.py] Starting standalone scan — max_duration={max_duration}s  "
          f"pause={pause}s\n", flush=True)
    t0 = time.time()

    try:
        result = mapper.snapshot(
            url=url,
            max_duration=max_duration,
            pause=pause,
            # ConsoleStatsReporter is auto-wired inside snapshot() for console
            # output.  We ALSO pass the WS broadcast callback (if the embedded
            # server is running) so the GUI gets real-time updates.
            on_stream=on_stream_cb,
            no_persist=no_db,
        )
    except KeyboardInterrupt:
        print("\n[scan.py] Interrupted.", flush=True)
        return 130
    except Exception as exc:
        logging.exception("[scan.py] snapshot() raised an exception")
        print(f"\n[scan.py] FATAL: scan failed: {exc}", file=sys.stderr)
        return 1

    elapsed = time.time() - t0
    chunks  = result.get("chunk_count", 0)
    nodes   = result.get("node_count", 0)
    snap_id = result.get("snapshot_id", "?")

    print(f"\n[scan.py] Done in {elapsed:.1f}s  •  snapshot_id={snap_id}"
          f"  nodes={nodes}  chunks={chunks}")

    # Signal done to any connected WS clients.
    if on_stream_cb:
        on_stream_cb({"type": "done"})

    # Optional interactive query loop.
    if query:
        export_data = result.get("chunk_details", {"chunks": {}, "members": {}})
        details_path = os.path.join(
            os.path.dirname(report_path) or ".", "chunk_details.json"
        )
        with open(details_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"  → Chunk details saved to {details_path}")
        _run_interactive_query(url, export_data)

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="scan.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("url", nargs="?", default=None,
                    help="URL to scan.  If omitted, uses the browser's current page.")
    ap.add_argument("--max-duration", metavar="N",  type=int,   default=180,
                    help="Stop scrolling after N seconds (default: 180).")
    ap.add_argument("--pause",        metavar="N",  type=float, default=0.5,
                    help="Pause between scrolls in seconds (default: 0.5).")
    ap.add_argument("--report",       action="store_true",
                    help="Write an HTML chunk-panel report after the scan.")
    ap.add_argument("--report-path",  metavar="PATH", default="chunks_report.html",
                    help="Path for the HTML report (default: chunks_report.html).")
    ap.add_argument("--query",        action="store_true",
                    help="After the scan, enter an interactive TF-IDF query loop.")
    ap.add_argument("--continuous",   action="store_true",
                    help="Use smooth continuous scrolling instead of step-wise.")
    ap.add_argument("--speed",        metavar="F", type=float, default=0.03,
                    help="Scroll step fraction for continuous mode (default: 0.03).")
    ap.add_argument("--capture-interval", metavar="MS", type=int, default=80,
                    help="Mutation polling interval ms for continuous mode (default: 80).")
    ap.add_argument("--full-report",  action="store_true",
                    help="Expand all content fields in the HTML report.")
    ap.add_argument("--char-budget",  metavar="N", type=int, default=256,
                    help="Maximum prose characters per chunk (default: 256). "
                         "Smaller budgets produce more chunks (finer granularity); "
                         "larger budgets produce fewer chunks (coarser).")
    ap.add_argument("--quiet",        action="store_true",
                    help="Suppress console stats output.")
    ap.add_argument("--no-db",        action="store_true",
                    help="Skip kuzu DB init and chunk persistence.")
    ap.add_argument("--log-level",    metavar="LEVEL", default="WARNING",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    help="Python logging level (default: WARNING).")
    # Backend-delegation flags
    ap.add_argument("--no-backend",   action="store_true",
                    help="Force standalone mode; do not try to delegate to app.py.")
    ap.add_argument("--backend-url",  metavar="URL", default="http://localhost:8000",
                    help="Backend base URL to probe (default: http://localhost:8000).")
    ap.add_argument("--ws-port",      metavar="N", type=int, default=None,
                    help="Start embedded WS server on port N in standalone mode "
                         "so the GUI can connect directly.")
    return ap


def main(argv: Optional[list] = None) -> int:
    ap   = _build_parser()
    args = ap.parse_args(argv)

    url = args.url
    if not url:
        if os.environ.get("NO_WEBDRIVER") != "1":
            try:
                driver = _get_driver()
                url    = driver.current_url
                if not url or url in ("about:blank", "about:newtab"):
                    url = None
            except Exception:
                url = None
        if not url:
            ap.error(
                "No URL supplied and the browser has no active page.\n"
                "Usage: python scripts/scan.py https://example.com"
            )

    return run_scan(
        url,
        max_duration=args.max_duration,
        pause=args.pause,
        report=args.report,
        report_path=args.report_path,
        full_report=args.full_report,
        char_budget=args.char_budget,
        query=args.query,
        continuous=args.continuous,
        speed=args.speed,
        capture_interval=args.capture_interval,
        quiet=args.quiet,
        no_db=args.no_db,
        no_backend=args.no_backend,
        backend_url=args.backend_url,
        ws_port=args.ws_port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    sys.exit(main())
