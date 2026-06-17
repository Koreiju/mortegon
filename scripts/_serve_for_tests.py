"""_serve_for_tests.py — boot the backend for the test framework.

A single-process (NO reload) uvicorn launcher so the orchestrator and Playwright
can start/stop it cleanly. Stub by default (WFH_FAKE_* gates); `--real` boots the
all_real stack (CUDA SLM/nomic + Selenium). Port via WFH_TEST_PORT (default 8080).

Used by:
  * scripts/run_full_stack_tests.py  (the full-stack orchestrator)
  * frontend_e2e/playwright.config.js  webServer (standalone `npm run test:e2e`)
"""
import os
import sys

# Make `backend` importable regardless of CWD (sys.path[0] is scripts/).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_REAL = "--real" in sys.argv

if not _REAL:
    # harness stub gates (only when not running the real stack)
    os.environ.setdefault("WFH_FAKE_SLM", "1")
    os.environ.setdefault("WFH_FAKE_EMBEDDER", "1")
    os.environ.setdefault("NO_WEBDRIVER", "1")
else:
    os.environ.setdefault("WFH_SLM_DEVICE", "cuda")
    os.environ.setdefault("WFH_EMBEDDER_DEVICE", "cuda")

import uvicorn  # noqa: E402

if __name__ == "__main__":
    port = int(os.environ.get("WFH_TEST_PORT", "8080"))
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        # reload=False (default) — single process, cleanly killable
    )
