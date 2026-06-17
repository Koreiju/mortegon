"""run_full_stack_tests.py — the unified full-stack test framework.

Runs every verification tier against ONE managed backend and prints a unified
pass/fail summary:

  1. pytest            backend/tests/                         (no backend)
  2. repl              sim_frontend.py env-scenario full-smoke (the FULL REPL set)
  3. e2e               Playwright frontend_e2e/*.spec.js        (render)
  4. probes  (--real)  scripts/probe_live_*.py + probe_no_mocks (lodestars)

It boots a single backend (stub by default; `--real` for the all_real CUDA stack),
waits until it is ready, runs the backend-dependent tiers against it, then tears
it down — so the REPL contract and the Playwright suite run in the SAME framework
against the SAME stack.

Usage:
  python scripts/run_full_stack_tests.py                 # stub: pytest + repl + e2e
  python scripts/run_full_stack_tests.py --real          # all_real: + live probes
  python scripts/run_full_stack_tests.py --only e2e      # one tier
  python scripts/run_full_stack_tests.py --only repl --only e2e
  python scripts/run_full_stack_tests.py --no-pytest --port 8090

Exit 0 = every selected tier green.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
STUB_GATES = {"WFH_FAKE_SLM": "1", "WFH_FAKE_EMBEDDER": "1", "NO_WEBDRIVER": "1"}
PROBES = [
    "probe_no_mocks.py",
    "probe_live_archive_scan.py",
    "probe_live_concept_graph.py",
    "probe_live_agent.py",
    "probe_live_iterated_compile.py",
]


def _get(base: str, path: str, timeout: float = 5.0):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def boot_backend(real: bool, port: int) -> subprocess.Popen:
    env = dict(os.environ)
    env["WFH_TEST_PORT"] = str(port)
    if real:
        for k in STUB_GATES:
            env.pop(k, None)          # never gate the real stack
    else:
        env.update(STUB_GATES)
    cmd = [sys.executable, "scripts/_serve_for_tests.py"] + (["--real"] if real else [])
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env, creationflags=flags)


def wait_ready(base: str, real: bool, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            _get(base, "/api/scan_status", timeout=2)
            return True
        except Exception:
            time.sleep(1.0)
    return False


def kill_backend(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)
    else:
        try:
            proc.terminate(); proc.wait(timeout=10)
        except Exception:
            proc.kill()


def run_tier(label: str, cmd, env_extra=None, shell=False) -> bool:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    shown = cmd if shell else " ".join(cmd)
    print(f"\n{'=' * 72}\n▶ {label}\n  $ {shown}\n{'=' * 72}", flush=True)
    rc = subprocess.run(cmd, cwd=str(ROOT), env=env, shell=shell).returncode
    print(f"  → {label}: {'PASS' if rc == 0 else 'FAIL'} (rc={rc})", flush=True)
    return rc == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true",
                    help="boot the all_real CUDA stack + run live probes (default: stub)")
    ap.add_argument("--only", choices=["pytest", "repl", "e2e", "probes"],
                    action="append", help="run only these tier(s); repeatable")
    ap.add_argument("--no-pytest", action="store_true")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--repl-scope", choices=["full-smoke", "all"], default="all",
                    help="REPL set: 'all' = complete env-scenario registry (default); "
                         "'full-smoke' = the curated 92-scenario chain")
    args = ap.parse_args()

    real = args.real
    base = f"http://127.0.0.1:{args.port}"
    tiers = set(args.only) if args.only else (
        {"pytest", "repl", "e2e"} | ({"probes"} if real else set()))
    if args.no_pytest:
        tiers.discard("pytest")
    repl_env = None if real else dict(STUB_GATES)

    results: dict[str, bool] = {}

    # Tier 1 — pytest (no backend)
    if "pytest" in tiers:
        results["pytest  (backend/tests)"] = run_tier(
            "pytest", [sys.executable, "-m", "pytest", "backend/tests/", "-q",
                       "-p", "no:cacheprovider"], dict(STUB_GATES))

    backend_tiers = tiers & {"repl", "e2e", "probes"}
    if backend_tiers:
        print(f"\n[framework] booting {'REAL' if real else 'STUB'} backend on {base} ...", flush=True)
        proc = boot_backend(real, args.port)
        try:
            if not wait_ready(base, real, timeout_s=240 if real else 90):
                print("[framework] backend never became ready", file=sys.stderr)
                return 2
            if real:
                try:
                    s = _get(base, "/api/subsystem_status", timeout=180)
                    print(f"[framework] subsystem_status all_real={s.get('all_real')}", flush=True)
                except Exception as e:
                    print(f"[framework] subsystem_status check failed: {e}", flush=True)
            print("[framework] backend ready.", flush=True)

            if "repl" in tiers:
                scope = args.repl_scope
                results[f"repl    (env-scenario {scope})"] = run_tier(
                    f"REPL {scope}",
                    [sys.executable, "scripts/sim_frontend.py", "--backend", base,
                     "env-scenario", "--name", scope], repl_env)

            if "e2e" in tiers:
                results["e2e     (Playwright frontend)"] = run_tier(
                    "Playwright e2e",
                    "npx playwright test -c frontend_e2e/playwright.config.js",
                    {"WFH_FRONTEND_URL": base, "PW_TEST_REUSE_SERVER": "1"},
                    shell=True)

            if "probes" in tiers and real:
                for probe in PROBES:
                    results[f"probe   ({probe})"] = run_tier(
                        probe, [sys.executable, f"scripts/{probe}", base])
        finally:
            print("\n[framework] tearing down backend ...", flush=True)
            kill_backend(proc)

    print(f"\n{'=' * 72}\n FULL-STACK TEST SUMMARY  ({'REAL' if real else 'STUB'} mode)\n{'=' * 72}")
    all_ok = True
    for k, v in results.items():
        print(f"  {'✓ PASS' if v else '✗ FAIL'}   {k}")
        all_ok = all_ok and v
    print("=" * 72)
    print("ALL GREEN ✓" if all_ok and results else ("FAILURES PRESENT ✗" if results else "(nothing run)"))
    return 0 if (all_ok and results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
