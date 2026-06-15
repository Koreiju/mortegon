import logging
import os
import sys

# Ensure backend can be resolved from the root path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Capture EVERYTHING the process emits — stdout, stderr, Python logging,
# uvicorn access logs, mapper profiler lines — into ``logs.txt`` next to
# this script. The user wants a single tail-able file rather than having
# to scroll the live console; without this every print() / logger call
# was vanishing into the terminal that launched the process.
# ---------------------------------------------------------------------------

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs.txt")


class _Tee:
    """A file-like proxy that writes to BOTH the original stream AND
    a log file. Used to mirror stdout/stderr so the live terminal
    still shows progress while the file accumulates the durable
    record."""

    def __init__(self, original, log_file):
        self._original = original
        self._log = log_file

    def write(self, data):
        try:
            self._original.write(data)
        except Exception:
            pass
        try:
            self._log.write(data)
            self._log.flush()
        except Exception:
            pass
        return len(data) if isinstance(data, str) else 0

    def flush(self):
        try:
            self._original.flush()
        except Exception:
            pass
        try:
            self._log.flush()
        except Exception:
            pass

    def isatty(self):
        try:
            return self._original.isatty()
        except Exception:
            return False

    def fileno(self):
        # Some libraries probe fileno() — delegate to the original
        # so anything that needs a real fd (e.g. uvicorn's reload
        # watcher) keeps working.
        return self._original.fileno()


def _setup_file_logging() -> None:
    # Truncate per process start so each run is its own log. Switch
    # to ``"a"`` if you want cumulative history.
    log_file = open(LOG_PATH, "w", encoding="utf-8", buffering=1)  # line-buffered

    # Mirror stdout + stderr to the file via Tee.
    sys.stdout = _Tee(sys.__stdout__, log_file)
    sys.stderr = _Tee(sys.__stderr__, log_file)

    # Also wire Python's ``logging`` module so any code that calls
    # ``logger.info(...)`` (mapper, pipeline, scanner, tfidf …) lands
    # in the same file with a consistent timestamp prefix.
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    file_handler = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.__stderr__)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Clear any handlers uvicorn / our test harness installed first
    # so we don't end up with duplicate lines.
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Make uvicorn's access + error loggers feed through the root
    # so they land in logs.txt too.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        lg.propagate = True

    print(f"[app] Logging mirrored to {LOG_PATH}")


_setup_file_logging()


import uvicorn  # noqa: E402  (deferred so logging is set up first)
from backend.main import app  # noqa: E402


def _serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Plain server mode — no REPL. Equivalent to the historical
    behaviour of this script."""
    print(f"Starting Web Fiber Haptics GUI on http://{host}:{port} ...")
    uvicorn.run(app, host=host, port=port)


def _serve_with_repl(host: str = "127.0.0.1", port: int = 8080) -> int:
    """Run uvicorn in a background thread and drop the same console
    into the FrontendEnv REPL pointed at the just-started backend.

    Single-terminal workflow: ``python app.py --repl`` serves the
    frontend AND gives the operator a typed prompt to drive it. Any
    browser tab loading ``http://127.0.0.1:8080/`` connects to the
    same backend; its MutationObservers (cp/telemetry.js) post DOM
    changes back here, drainable via ``ui-telemetry`` /
    ``ui-telemetry-stream``.

    Shutdown: Ctrl-D / ``quit`` in the REPL exits this script
    cleanly (uvicorn is a daemon thread; the process exits when the
    main thread returns).
    """
    import threading
    import time as _time
    import urllib.request

    # Run uvicorn on a daemon thread so REPL Ctrl-D / quit drops the
    # whole process without explicit teardown.
    config = uvicorn.Config(app, host=host, port=port,
                            log_level="warning", access_log=False)
    server = uvicorn.Server(config)

    def _run_server() -> None:
        try:
            server.run()
        except Exception as exc:
            print(f"[app] uvicorn crashed: {exc}", file=sys.__stderr__)

    thread = threading.Thread(target=_run_server, daemon=True, name="uvicorn")
    thread.start()

    base = f"http://{host}:{port}"
    print(f"[app] Backend starting on {base} ...")
    # Poll /api/scan_status until the server answers; bail with a clear
    # message if it never comes up.
    deadline = _time.time() + 30.0
    while _time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/api/scan_status", timeout=1) as r:
                if r.status == 200:
                    break
        except Exception:
            pass
        _time.sleep(0.5)
    else:
        print("[app] Server didn't respond within 30s. Aborting REPL.",
              file=sys.__stderr__)
        return 2
    print(f"[app] Backend ready. Frontend → {base}/  ·  type 'help' for actions.")

    # Defer the import until after backend is up — sim_frontend.py
    # adds backend/ to sys.path on import and we don't want it
    # racing the logging setup above.
    from scripts.sim_frontend import FrontendEnv, _run_repl
    env = FrontendEnv(base, workspace_id="_default")
    try:
        return _run_repl(env)
    finally:
        try:
            env.ws.stop()
        except Exception:
            pass
        # Signal uvicorn to shut down; the daemon thread dies when
        # the main thread exits anyway, but a graceful stop flushes
        # any pending broadcasts.
        try:
            server.should_exit = True
        except Exception:
            pass


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        prog="app.py",
        description="Web Fiber Haptics backend — serves the frontend at "
                    "http://127.0.0.1:8080/. Use --repl to also get an "
                    "interactive console in this same terminal.",
    )
    ap.add_argument("--repl", action="store_true",
                    help="Drop into the FrontendEnv REPL after the backend "
                         "is ready — same terminal, two surfaces.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    if args.repl:
        sys.exit(_serve_with_repl(args.host, args.port))
    _serve(args.host, args.port)
