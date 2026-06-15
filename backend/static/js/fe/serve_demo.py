"""serve_demo.py — minimal static server for the magic-markdown demo.

Serves the `fe/` directory with the correct `text/javascript` MIME for `.mjs`
(Python's default http.server serves .mjs as octet-stream, which browsers
refuse to load as ES modules). Used only for browser verification of the
magic-markdown panel; not part of the app.
"""
import functools
import http.server
import os

DIR = os.path.dirname(os.path.abspath(__file__))
http.server.SimpleHTTPRequestHandler.extensions_map[".mjs"] = "text/javascript"
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIR)

if __name__ == "__main__":
    # ThreadingHTTPServer: the preview browser holds keep-alive connections, so
    # a single-threaded server deadlocks on concurrent requests.
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 8099), Handler)
    print(f"serving {DIR} on http://127.0.0.1:8099/demo.html")
    httpd.serve_forever()
