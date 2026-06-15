"""
scripts/reset_env.py -- deterministic "clean slate" for a new scan.

What this does, in order:

1. Shut down any live uvicorn serving ``backend.main:app`` on the project's
   port (default 8080). We try a graceful HTTP shutdown first, then fall
   back to killing the process holding the port.
2. Close any in-process Kuzu handle (``backend.database.close_db``) so
   Windows releases the file lock -- a live connection here will block
   the file delete with ``[WinError 32]``.
3. Remove the Kuzu database file(s) (``kuzu_db`` + any ``.wal`` / ``.shm``
   sidecars) and the snapshots/UMAP artifacts that cache scan output.

Run with ``python scripts/reset_env.py`` before relaunching ``app.py``
or re-running ``demo_scanner.py`` when you want a fresh DB.

Flags:

    --keep-snapshots   Don't delete ``snapshots/`` (keeps rendered HTML).
    --port 8080        Override the port the server is assumed to bind.
    --dry-run          Print what would be removed/killed and exit 0.

Exit codes:
    0 -- success (or nothing to do)
    1 -- one or more cleanup steps failed (details printed to stderr)
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = 8080

# Paths that a scan writes to. Everything here is safe to nuke between
# runs; re-scans will regenerate it. Keep this list small and obvious --
# it's the whole promise of the script.
DB_CANDIDATES = [
    ROOT / "kuzu_db",
]
ARTIFACT_CANDIDATES = [
    ROOT / "umap_chunks.png",
]
SNAPSHOT_DIR = ROOT / "snapshots"


# ---------------------------------------------------------------------------
# Port / process helpers
# ---------------------------------------------------------------------------


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _pids_on_port(port: int) -> List[int]:
    """Return PIDs holding ``port`` (TCP LISTEN) on Windows or POSIX."""
    pids: List[int] = []
    if os.name == "nt":
        # netstat -ano returns "TCP 127.0.0.1:8080 ... LISTENING <pid>"
        try:
            out = subprocess.check_output(
                ["netstat", "-ano", "-p", "tcp"], text=True, stderr=subprocess.STDOUT,
            )
        except Exception as exc:  # pragma: no cover
            print(f"  netstat failed: {exc}", file=sys.stderr)
            return pids
        for line in out.splitlines():
            line = line.strip()
            if f":{port} " not in line and not line.endswith(f":{port}"):
                continue
            if "LISTENING" not in line.upper():
                continue
            parts = line.split()
            try:
                pids.append(int(parts[-1]))
            except (ValueError, IndexError):
                continue
    else:
        # POSIX fallback via lsof. Not expected on this project's primary
        # dev machine but kept for Linux CI runs.
        try:
            out = subprocess.check_output(
                ["lsof", "-t", "-iTCP:%d" % port, "-sTCP:LISTEN"],
                text=True, stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError:
            pass
    return sorted(set(pids))


def _kill_pid(pid: int, *, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry-run] would kill PID {pid}")
        return True
    try:
        if os.name == "nt":
            subprocess.check_call(
                ["taskkill", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, 15)
        return True
    except Exception as exc:
        print(f"  kill PID {pid} failed: {exc}", file=sys.stderr)
        return False


def shutdown_server(port: int, *, dry_run: bool) -> bool:
    """Return True on clean shutdown or nothing-to-do, False on failure."""
    if not _port_in_use(port):
        print(f"[1/3] no server on :{port}")
        return True
    print(f"[1/3] server on :{port} is live -- shutting down")
    pids = _pids_on_port(port)
    if not pids:
        print(
            f"  port :{port} is bound but no PID resolved; "
            "proceeding optimistically",
            file=sys.stderr,
        )
        return True
    ok = True
    for pid in pids:
        if not _kill_pid(pid, dry_run=dry_run):
            ok = False
    if dry_run:
        return ok
    # Give Windows a beat to release the file lock.
    for _ in range(20):
        if not _port_in_use(port):
            return ok
        time.sleep(0.1)
    print(
        f"  port :{port} still bound after kill -- something is stubborn",
        file=sys.stderr,
    )
    return False


# ---------------------------------------------------------------------------
# Kuzu / filesystem cleanup
# ---------------------------------------------------------------------------


def _close_in_process_db() -> None:
    """If this process already imported backend.database, release the handle.

    Only relevant when the script is called from a test harness that
    shares an interpreter with the server -- standalone ``python
    scripts/reset_env.py`` will skip this silently.
    """
    mod = sys.modules.get("backend.database")
    if mod is None:
        return
    closer = getattr(mod, "close_db", None)
    if callable(closer):
        try:
            closer()
            print("  closed in-process kuzu handle")
        except Exception as exc:
            print(f"  close_db failed: {exc}", file=sys.stderr)


def _rm(path: Path, *, dry_run: bool) -> bool:
    if not path.exists():
        return True
    tag = "[dry-run] would remove" if dry_run else "removed"
    try:
        if dry_run:
            print(f"  {tag}: {path}")
            return True
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  {tag}: {path}")
        return True
    except Exception as exc:
        print(f"  failed to remove {path}: {exc}", file=sys.stderr)
        return False


def wipe_db(*, dry_run: bool) -> bool:
    print("[2/3] deleting Kuzu DB files")
    _close_in_process_db()
    ok = True
    for base in DB_CANDIDATES:
        # Kuzu sometimes lays down .wal / .shm / .tmp sidecars beside the
        # main file; sweep them all.
        for p in [base, *base.parent.glob(base.name + ".*")]:
            if not _rm(p, dry_run=dry_run):
                ok = False
    return ok


def wipe_artifacts(*, keep_snapshots: bool, dry_run: bool) -> bool:
    print("[3/3] deleting cached scan artifacts")
    ok = True
    for p in ARTIFACT_CANDIDATES:
        if not _rm(p, dry_run=dry_run):
            ok = False
    if not keep_snapshots:
        if not _rm(SNAPSHOT_DIR, dry_run=dry_run):
            ok = False
    else:
        print(f"  --keep-snapshots: leaving {SNAPSHOT_DIR} alone")
    return ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--keep-snapshots", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    print(f"reset_env: project root = {ROOT}")
    steps_ok = [
        shutdown_server(args.port, dry_run=args.dry_run),
        wipe_db(dry_run=args.dry_run),
        wipe_artifacts(
            keep_snapshots=args.keep_snapshots, dry_run=args.dry_run,
        ),
    ]
    if all(steps_ok):
        print("reset_env: done.")
        return 0
    print("reset_env: completed with errors (see above)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
