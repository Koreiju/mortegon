"""scripts/reset_state.py — Nuke every persistent surface in one shot.

The project keeps state in several places:

  1. ``kuzu_db/``                — main kuzu graph DB (chunks, instances, edges)
  2. ``test_kuzu/``              — test-isolated kuzu DB
  3. ``snapshots/global_tfidf/`` — persistent TF-IDF index (vocab + TF
                                   matrix + meta) shared across scans
  4. ``snapshots/distilled_html/`` — one HTML file per scanned URL,
                                     used by the post-scan distill step
  5. ``snapshots/`` (catch-all)  — any per-scan tfidf_indexes/, html
                                   saves, audit outputs
  6. ``logs/``                   — pipeline + dedup logs
  7. Loose files at the repo root: ``audit.html``, ``chunk_details.json``,
     ``scan_output.log``, ``server_boot.log``, lockfiles like
     ``.lock`` under any of the above

Deleting just ``kuzu_db/`` (as the user did) silently leaves (3) and (4)
behind — and ``/api/chunk_nodes`` rehydrates from the TF-IDF store at
startup, so the projector loads "ghost" nodes from the previous run.
This script wipes all seven surfaces. ``--dry-run`` lists what would be
removed without touching anything.

Usage::

    python scripts/reset_state.py          # nuke everything
    python scripts/reset_state.py --dry-run
    python scripts/reset_state.py --keep snapshots logs   # selective keep
    python scripts/reset_state.py --kill   # kill any process holding the
                                           # kuzu lock first, then nuke
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _find_project_processes() -> list[dict]:
    """Return processes that look like they belong to this project.

    Conservative heuristic — we want to catch the FastAPI/uvicorn server
    and any background scan/scripts.py runs, but NOT VS Code's Python
    language server (which inherits the project's cwd but doesn't run
    our code). So:

      * The cmdline MUST contain the project root path, AND
      * The cmdline MUST mention one of our known entry points
        (``backend.main``, ``backend/main``, ``backend\\main``, ``uvicorn``,
        ``scripts``, ``kuzu_db``).

    Plain ``cwd``-only matches are intentionally ignored — that's the
    case that picks up the language server.

    Quietly returns ``[]`` if ``psutil`` isn't installed.
    """
    try:
        import psutil  # type: ignore
    except Exception:
        print("[reset_state] psutil not installed — cannot auto-identify lock holders.")
        print("[reset_state]   pip install psutil")
        return []
    root_lower = str(ROOT).lower()
    markers = ("backend.main", "backend/main", "backend\\main",
               "uvicorn", "scripts", "kuzu_db", "wfh_db_path")
    me = os.getpid()
    parent = os.getppid()
    out: list[dict] = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
        try:
            pid = p.info["pid"]
            if pid in (me, parent):
                continue
            name = (p.info.get("name") or "").lower()
            if "python" not in name and "uvicorn" not in name:
                continue
            cmd = " ".join(p.info.get("cmdline") or []).lower()
            if root_lower not in cmd:
                continue
            if not any(m in cmd for m in markers):
                continue
            out.append({
                "pid": pid,
                "name": p.info.get("name") or "?",
                "cmdline": " ".join(p.info.get("cmdline") or []),
                "proc": p,
            })
        except Exception:
            continue
    return out


def _kill_lock_holders(dry: bool) -> int:
    """Identify and terminate processes holding the project's kuzu lock.

    Returns the number of processes killed (or that would have been
    killed under ``--dry-run``).
    """
    print("[kill holders]")
    holders = _find_project_processes()
    if not holders:
        print("  (no project python/uvicorn processes detected)")
        print()
        return 0
    killed = 0
    for h in holders:
        cmd = h["cmdline"]
        if len(cmd) > 110:
            cmd = cmd[:107] + "..."
        print(f"  {'WOULD' if dry else 'KILL '} PID={h['pid']:<6} {h['name']:<14} {cmd}")
        if dry:
            killed += 1
            continue
        try:
            proc = h["proc"]
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except Exception:
                proc.kill()
                proc.wait(timeout=2.0)
            killed += 1
        except Exception as e:
            print(f"    (skip: {e})")
    # Give the OS a moment to release file handles before we rmtree.
    if not dry and killed:
        time.sleep(0.5)
    print()
    return killed


def _human_size(p: Path) -> str:
    """Best-effort recursive byte count for a path."""
    try:
        if p.is_file():
            n = p.stat().st_size
        else:
            n = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}TB"
    except Exception:
        return "?"


def _nuke(path: Path, dry: bool) -> bool:
    """Remove a directory or file. Returns True if something existed."""
    if not path.exists():
        return False
    label = "DIR " if path.is_dir() else "FILE"
    size  = _human_size(path)
    print(f"  {'WOULD' if dry else 'NUKE '} {label} {size:>8}  {path.relative_to(ROOT)}")
    if dry:
        return True
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
    else:
        path.unlink(missing_ok=True)
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reset_state.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="List what would be removed; touch nothing.")
    ap.add_argument("--keep", nargs="*", default=[],
                    choices=["db", "snapshots", "logs", "loose", "test"],
                    help="Selective keep. Multiple OK.")
    ap.add_argument("--kill", action="store_true",
                    help="Before deleting, terminate any python/uvicorn "
                         "process whose cwd or cmdline points inside this "
                         "project. Releases the kuzu lock if a stale server "
                         "is still running. Requires psutil.")
    args = ap.parse_args(argv)

    # Group → list of paths.
    groups: dict[str, list[Path]] = {
        # Main kuzu DB and its test sibling.
        "db":        [ROOT / "kuzu_db"],
        "test":      [ROOT / "test_kuzu"],
        # All scan artefacts: persistent TF-IDF store, distilled HTML
        # saves, per-scan tfidf indexes, etc.
        "snapshots": [ROOT / "snapshots"],
        # Pipeline + dedup logs.
        "logs":      [ROOT / "logs"],
        # Loose top-level outputs that the user might also want gone.
        "loose": [
            ROOT / "audit.html",
            ROOT / "chunk_details.json",
            ROOT / "scan_output.log",
            ROOT / "server_boot.log",
            ROOT / "yt_after.log",
            ROOT / "yt_combined.log",
            ROOT / "ddg_after.log",
        ],
    }

    print(f"[reset_state] root: {ROOT}")
    print(f"[reset_state] mode: {'dry-run' if args.dry_run else 'destructive'}")
    if args.keep:
        print(f"[reset_state] keeping groups: {', '.join(args.keep)}")
    if args.kill:
        print(f"[reset_state] --kill: will terminate matching project processes first")
    print()

    killed = 0
    if args.kill:
        killed = _kill_lock_holders(args.dry_run)

    touched = 0
    for group, paths in groups.items():
        if group in args.keep:
            print(f"[skip {group}]")
            continue
        print(f"[{group}]")
        any_in_group = False
        for p in paths:
            if _nuke(p, args.dry_run):
                any_in_group = True
                touched += 1
        if not any_in_group:
            print(f"  (nothing to remove)")
        print()

    # Sweep for stray *.lock files under removed roots — the kuzu DB
    # leaves a *.lock file behind even after the directory rmtree
    # if a process held it open. Surface them so the user sees that
    # a stale process may be the reason a fresh DB still feels old.
    print("[stray locks]")
    stray = 0
    for lock in ROOT.rglob("*.lock"):
        # Don't touch venv / installer / Claude-Code-internal locks.
        SKIP_PARTS = ("venv", "site-packages", "node_modules", ".git", ".claude")
        if any(part in lock.parts for part in SKIP_PARTS):
            continue
        try:
            rel = lock.relative_to(ROOT)
        except ValueError:
            continue
        size = _human_size(lock)
        print(f"  {'WOULD' if args.dry_run else 'NUKE '} FILE {size:>8}  {rel}")
        if not args.dry_run:
            try: lock.unlink()
            except Exception as e: print(f"    (skip: {e})")
        stray += 1
    if stray == 0:
        print("  (no stray .lock files)")
    print()

    total = touched + stray
    suffix = f" (+ {killed} process(es))" if killed else ""
    print(f"[reset_state] {'WOULD touch' if args.dry_run else 'TOUCHED'} {total} item(s){suffix}.")
    if args.dry_run:
        print("[reset_state] re-run without --dry-run to actually wipe.")
    else:
        print("[reset_state] Done. Next /api/chunk_nodes call will return an empty index.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
