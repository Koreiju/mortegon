"""_fixture_server.py — serve saved `test_packages/<site>/source.html` for
DETERMINISTIC live scans (no archive.org bot-throttling / network flakiness).

A real Selenium scan of `http://127.0.0.1:<port>/<site>/` loads the saved DOM —
still a REAL browser + real chunk-extraction (no-mocks holds), but the page is
local, static, and identical every run. The framework points the live-scan
scenarios here via `WFH_TEST_SCAN_URL` when run with `--fixture-scan`.

Run:  python scripts/_fixture_server.py            # port 8099 (WFH_FIXTURE_PORT)
URL:  http://127.0.0.1:8099/archive_org/           # -> test_packages/archive_org/source.html
"""
from __future__ import annotations

import http.server
import os
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "test_packages"
PORT = int(os.environ.get("WFH_FIXTURE_PORT", "8099"))
DEFAULT_SITE = os.environ.get("WFH_FIXTURE_DEFAULT_SITE", "archive_org")


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        site = (self.path.strip("/").split("/", 1)[0] or DEFAULT_SITE)
        f = ROOT / site / "source.html"
        if not f.is_file():
            self.send_error(404, f"no fixture for site {site!r}")
            return
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):  # silence
        pass


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    if not ROOT.is_dir():
        print(f"[fixture] corpus not found at {ROOT}", file=sys.stderr)
        raise SystemExit(2)
    with _Server(("127.0.0.1", PORT), _Handler) as httpd:
        print(f"[fixture] serving {ROOT} at http://127.0.0.1:{PORT}/<site>/ "
              f"(default: /{DEFAULT_SITE}/)", flush=True)
        httpd.serve_forever()
