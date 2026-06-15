from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from backend.database import init_db
from backend.api.routes import router
import os
import mimetypes
from backend.api.errors import (
    register_workflow_error_handler,
    register_slm_unavailable_handler,
)

# Serve ES modules (.mjs) with the correct MIME so the greenfield fe/ tree
# (the magic-markdown editor, §T/§U/§V) loads as modules. Default Windows
# mimetypes maps .mjs to octet-stream, which browsers refuse for `type=module`.
mimetypes.add_type("text/javascript", ".mjs")

from contextlib import asynccontextmanager
from backend.services.selenium_client import WebBrowserManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Capture the running event loop so worker threads can push WS
        # frames onto it via ``call_soon_threadsafe``. The async WS
        # plumbing in routes.py is a no-op without this reference.
        import asyncio
        from backend.api.routes import set_event_loop
        set_event_loop(asyncio.get_running_loop())

        if os.environ.get("NO_WEBDRIVER") != "1":
            print("Starting Live WebBrowser Client...")
            from backend.api.routes import _get_mapper
            _get_mapper()  # Eagerly initialize the singleton driver!
        else:
            print("Skipping Live WebBrowser Client as per NO_WEBDRIVER.")

        print("Initializing Database...")
        init_db()

        yield
    finally:
        from backend.api.routes import shutdown_browser
        shutdown_browser()

        from backend.database import close_db
        close_db()
    
app = FastAPI(title="web_fiber_haptics — Ontological Warp Workspace API", lifespan=lifespan)

register_workflow_error_handler(app)
register_slm_unavailable_handler(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories for static and templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _asset_version() -> str:
    """Cache-buster for static assets; the latest mtime across JS + CSS.

    Browsers will happily serve a stale ``chunk_projector.js`` from the
    disk cache for minutes after an edit, which looks like "my change
    didn't land". Stamping the filename-ish query string with the source
    file's mtime forces a fresh fetch whenever the developer saves.

    Walks every JS file under static/js (including the cp/ subdirectory)
    so editing a single mixin module bumps the version too. Previously
    the version only tracked chunk_projector.js itself — so edits to
    cp/layout.js, cp/animation.js, etc. didn't invalidate the cached
    module imports.
    """
    paths = [
        os.path.join(STATIC_DIR, "css", "styles.css"),
        os.path.join(TEMPLATES_DIR, "index.html"),
    ]
    js_dir = os.path.join(STATIC_DIR, "js")
    if os.path.isdir(js_dir):
        for root, _dirs, files in os.walk(js_dir):
            for f in files:
                if f.endswith(".js"):
                    paths.append(os.path.join(root, f))
    try:
        return str(int(max(os.path.getmtime(p) for p in paths if os.path.exists(p))))
    except ValueError:
        return "0"


@app.get("/")
def read_root(request: Request):
    """The DEFAULT frontend is now the greenfield magic-markdown editor
    (§T/§U/§V) — the "strip" (T.8): the black-slate `fe/` tier replaces the
    legacy `cp/*` projector as the served app. The legacy projector is demoted
    to ``/legacy`` (kept for reference during the transition; backend links are
    untouched). Same-origin with /api + the workspace WS."""
    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "asset_version": _asset_version()},
    )


# ``/editor`` kept as an explicit alias for the magic-markdown editor.
@app.get("/editor")
def read_editor(request: Request):
    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "asset_version": _asset_version()},
    )


@app.get("/legacy")
def read_legacy(request: Request):
    """The legacy `cp/*` 3D projector, demoted from ``/`` by the §T/§U/§V strip.
    Retained for reference + the 3D chunk field until the projector is folded
    into the editor; not the default surface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "asset_version": _asset_version()},
    )

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8080, reload=True)
