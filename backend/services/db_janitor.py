"""DB Janitor — the one garbage-cleanup module over database creation (§R.9).

Verbatim anchor (USER_REQUIREMENTS_VERBATIM.md §R.9):

    "Please also build in very important and simple garbage cleanup modules
    over database creation and such when running tests so that we don't get
    an explosion of one-off databases with different filenames."

Before this module, one-off Kuzu DBs were created via ``tempfile.mkdtemp``
under a zoo of unique prefixes (``kuzu_inst_test_``, ``kuzu_trie_test_``,
``wfh_reservoir_probe_``, …) and mostly never removed, and the repo
``kuzu_db/`` directory accreted per-workspace side files
(``concept_index_<ws>.json`` / ``evolution_log_<ws>.jsonl`` /
``layout_frame_<ws>.json``) for every one-off scenario workspace.

This module is the single, simple answer. Three surfaces:

1. ``temp_db_dir(label)`` — context manager every test/probe/demo uses to
   create a throwaway DB directory. ONE canonical prefix (``wfh_test_``),
   guaranteed ``rmtree`` on exit, ``atexit`` net behind it.

2. ``register_for_cleanup(path)`` — for module-import-time DB paths (probes
   that must set ``WFH_DB_PATH`` before importing the backend) where a
   context manager can't wrap the lifetime. Cleaned at process exit.

3. ``sweep_stale_tmp()`` + ``sweep_workspace_sidefiles()`` — retention
   sweeps. The first removes stale one-off temp DB dirs (canonical prefix
   AND the legacy prefix zoo). The second removes per-workspace side files
   for **test-convention workspaces only** (``ws_``-prefixed, the REPL
   scenario convention) — it NEVER touches ``_default`` or any
   non-test-named workspace, so user data cannot be swept (§8D.33.6: the
   evolution log is append-only in-band; the janitor is the sanctioned
   *external* retention policy).

No third-party deps; safe-by-default (every removal is best-effort and
bounded to known patterns). Loud only via the returned report — callers
decide whether to print.
"""

from __future__ import annotations

import atexit
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Canonical naming
# ---------------------------------------------------------------------------

#: The ONE prefix every new throwaway DB directory uses (§R.9 — no more
#: per-call-site unique prefixes; the *label* disambiguates inside the name).
TEST_TMP_PREFIX = "wfh_test_"

#: The legacy prefix zoo this module supersedes. Kept ONLY so the sweep can
#: collect strays produced by older runs / older checkouts. Do not add new
#: call sites with these prefixes — use :func:`temp_db_dir`.
LEGACY_TMP_PREFIXES: Sequence[str] = (
    "kuzu_inst_test_", "kuzu_sig_test_", "kuzu_trie_test_",
    "kuzu_lbl_test_", "kuzu_emb_test_", "kuzu_demo_",
    "diag_kuzu_", "wfh_pattern_map_probe_", "wfh_imports_probe_",
    "wfh_reservoir_probe_", "wfh_e2e_", "wfh_test_mapper_",
    "wfh_pipeline_",
)

#: Test-convention workspace ids. The REPL scenario convention is
#: ``ws_<slug>`` (plus the bare ``ws`` some scenarios use); the live
#: probes mint ``probe_<slug>_<timestamp>`` workspaces per run — exactly
#: the one-off-per-run accretion §R.9 bans. Only side files whose
#: workspace suffix matches are sweep-eligible; everything else is
#: presumed real user data.
_TEST_WS_RE = re.compile(r"^(ws|ws_[A-Za-z0-9_\-]+|probe_[A-Za-z0-9_\-]+)$")

#: Per-workspace side-file shapes that accrete in the artifact dir.
_SIDEFILE_PATTERNS = (
    ("concept_index_", ".json"),
    ("evolution_log_", ".jsonl"),
    ("layout_frame_", ".json"),
    ("ontology_frame_", ".json"),
)


def _artifact_dir() -> str:
    """The directory the per-workspace side files live in (the same default
    the three services use: ``<repo>/kuzu_db``, overridable per-service via
    their env knobs — the janitor honours ``WFH_DB_PATH``'s parent layout by
    reusing the services' own defaults)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.environ.get(
        "WFH_ARTIFACT_DIR",
        os.path.abspath(os.path.join(here, "..", "..", "kuzu_db")),
    )


# ---------------------------------------------------------------------------
# Registry + atexit net
# ---------------------------------------------------------------------------

_registered: List[str] = []
_registered_lock = threading.Lock()


def _rmtree_quiet(path: str) -> bool:
    """Best-effort removal of a directory OR file (file-mode kuzu ≥0.11
    creates the DB as a file — plus a ``.wal`` sibling — at what callers
    registered as a dir path). Returns True iff the path is gone
    afterwards. Retries once after a short beat for Windows file-lock
    latency (a just-closed kuzu handle can hold the path a moment)."""
    if not path or not os.path.exists(path):
        return True
    for attempt in (0, 1):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
                for sibling in (path + ".wal", path + ".shadow"):
                    try:
                        if os.path.exists(sibling):
                            os.remove(sibling)
                    except Exception:
                        pass
        except Exception:
            pass
        if not os.path.exists(path):
            return True
        if attempt == 0:
            time.sleep(0.25)
    return not os.path.exists(path)


def register_for_cleanup(path: str) -> str:
    """Register ``path`` for guaranteed removal at process exit.

    For probes that must pin ``WFH_DB_PATH`` at import time (before the
    backend modules load) and therefore can't scope the DB's lifetime in a
    ``with`` block. Returns the path unchanged so call sites can inline it::

        os.environ["WFH_DB_PATH"] = register_for_cleanup(new_temp_db_path("my_probe"))
    """
    with _registered_lock:
        _registered.append(path)
    return path


def _atexit_sweep_registered() -> None:
    with _registered_lock:
        paths = list(_registered)
        _registered.clear()
    for p in paths:
        _rmtree_quiet(p)


atexit.register(_atexit_sweep_registered)


# ---------------------------------------------------------------------------
# Creation surfaces
# ---------------------------------------------------------------------------

def new_temp_db_path(label: str = "") -> str:
    """Create (and return the path of) a fresh throwaway DB directory under
    the canonical prefix. The caller owns the lifetime — pair with
    :func:`register_for_cleanup` unless inside :func:`temp_db_dir`."""
    safe = re.sub(r"[^A-Za-z0-9_\-]+", "_", label or "db").strip("_") or "db"
    name = f"{TEST_TMP_PREFIX}{safe}_{uuid.uuid4().hex[:8]}"
    path = os.path.join(tempfile.gettempdir(), name)
    os.makedirs(path, exist_ok=True)
    return path


@contextmanager
def temp_db_dir(label: str = "") -> Iterator[str]:
    """Context-managed throwaway DB directory (§R.9 primary surface).

    Usage::

        with temp_db_dir("chunk_instance") as db_root:
            db = kuzu.Database(os.path.join(db_root, "db"))
            ...

    The directory (canonical ``wfh_test_<label>_<hex>``) is removed on exit
    no matter how the block ends; an ``atexit`` net catches the case where
    the interpreter dies inside the block. Kuzu holds an OS lock on the DB
    dir — close/del your ``kuzu.Database`` before exit for a clean first-try
    removal (the janitor still retries + falls back to the atexit net).
    """
    path = new_temp_db_path(label)
    register_for_cleanup(path)
    try:
        yield path
    finally:
        _rmtree_quiet(path)
        with _registered_lock:
            try:
                _registered.remove(path)
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Retention sweeps
# ---------------------------------------------------------------------------

def sweep_stale_tmp(max_age_hours: float = 24.0) -> Dict[str, Any]:
    """Remove stale one-off temp DB directories from the OS temp dir.

    Targets the canonical ``wfh_test_`` prefix AND the legacy prefix zoo.
    ``max_age_hours`` guards live runs — a dir younger than the cutoff is
    skipped (another process may still hold it). Pass ``0`` to sweep
    everything matching (used by the REPL hygiene scenario, which creates
    and abandons a dir on purpose).

    Returns ``{scanned, removed: [name], skipped_young: [name], failed: [name]}``.
    """
    tmp = tempfile.gettempdir()
    cutoff = time.time() - max_age_hours * 3600.0
    prefixes = (TEST_TMP_PREFIX,) + tuple(LEGACY_TMP_PREFIXES)
    removed: List[str] = []
    skipped: List[str] = []
    failed: List[str] = []
    scanned = 0
    try:
        entries = os.listdir(tmp)
    except Exception:
        entries = []
    for name in entries:
        if not any(name.startswith(p) for p in prefixes):
            continue
        full = os.path.join(tmp, name)
        if not os.path.isdir(full):
            continue
        scanned += 1
        try:
            mtime = os.path.getmtime(full)
        except Exception:
            mtime = 0.0
        if mtime > cutoff:
            skipped.append(name)
            continue
        (removed if _rmtree_quiet(full) else failed).append(name)
    return {
        "scanned": scanned, "removed": removed,
        "skipped_young": skipped, "failed": failed,
    }


def sweep_workspace_sidefiles(
    *,
    keep: Sequence[str] = ("_default",),
    artifact_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove per-workspace side files left by one-off TEST workspaces.

    Eligibility is deliberately narrow: the workspace suffix must match the
    test convention (``ws_<slug>``) AND not be in ``keep``. ``_default`` and
    any human-named workspace are never touched — the sweep is a test-
    hygiene tool, not a data-retention hammer.

    Returns ``{scanned, removed: [filename], kept: [filename]}``.
    """
    root = artifact_dir or _artifact_dir()
    removed: List[str] = []
    kept: List[str] = []
    scanned = 0
    try:
        entries = os.listdir(root)
    except Exception:
        entries = []
    keep_set = set(keep or ())
    for name in entries:
        for prefix, suffix in _SIDEFILE_PATTERNS:
            if not (name.startswith(prefix) and name.endswith(suffix)):
                continue
            ws = name[len(prefix):-len(suffix)]
            scanned += 1
            if ws in keep_set or not _TEST_WS_RE.match(ws):
                kept.append(name)
                break
            full = os.path.join(root, name)
            try:
                os.remove(full)
                removed.append(name)
            except Exception:
                kept.append(name)
            break
    return {"scanned": scanned, "removed": removed, "kept": kept}


def sweep_all(max_age_hours: float = 24.0) -> Dict[str, Any]:
    """Run both sweeps; the one-call retention entry point.

    Wired as ``POST /api/maintenance/cleanup_test_artifacts`` so the REPL
    can hard-verify hygiene through the integrated stack (§R.8), and
    callable directly (``python -m backend.services.db_janitor``)."""
    return {
        "tmp": sweep_stale_tmp(max_age_hours=max_age_hours),
        "sidefiles": sweep_workspace_sidefiles(),
    }


if __name__ == "__main__":
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description="WFH test-DB garbage janitor (§R.9)")
    ap.add_argument("--max-age-hours", type=float, default=24.0,
                    help="temp dirs younger than this are skipped (default 24h)")
    args = ap.parse_args()
    print(_json.dumps(sweep_all(max_age_hours=args.max_age_hours), indent=2))
