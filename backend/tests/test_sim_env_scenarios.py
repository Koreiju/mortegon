"""Pytest wrapper for the no-backend env-scenarios in scripts/sim_frontend.py.

These are the scenarios that run entirely in-process via the chunker
pipeline + FrontendEnv self-introspection — no Selenium, no DB, no
HTTP server required. Running them under pytest gives us CI gating
on the harness machinery itself + the §4.3 chunker emission contract.

Scenarios that need a live backend (route-mount-smoke, fixture-
delete-guard, concept-lifecycle, etc.) are intentionally NOT wrapped
here — they belong in an integration test job that knows how to spin
the backend up first.

If you add a new no-backend scenario to ``_ENV_SCENARIOS``, just
extend the parametrise list below.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Same bootstrap as the script — makes ``import scripts.sim_frontend`` work
# from a clean pytest invocation.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sim_frontend import FrontendEnv, _ENV_SCENARIOS, _ACTIONS


# Scenarios that DON'T need a live backend (everything routes either
# through env-local action-registry inspection or the no-backend
# ``pipeline`` action). Add new entries here when you ship more
# offline-runnable scenarios.
_NO_BACKEND_SCENARIOS = [
    "action-registry-coverage",
    "route-coverage",
    "routes-list-shape",
    "actions-by-category-coverage",
    "chunker-regression",
    "chunker-edge-cases",
]


@pytest.fixture
def offline_env():
    """A FrontendEnv pointed at a deliberately-bad backend URL so any
    accidental network call fails fast instead of hanging on the
    real server.

    The env's WS drain still starts (it'll just fail to connect and
    log a warning), but no scenario in ``_NO_BACKEND_SCENARIOS``
    actually uses the WS surface.
    """
    env = FrontendEnv("http://127.0.0.1:1", workspace_id="_pytest")
    # Don't call start() — that would block waiting for a WS connect
    # we know won't succeed. The no-backend scenarios don't need it.
    yield env
    try:
        env.ws.stop()
    except Exception:
        pass


@pytest.mark.parametrize("scenario_name", _NO_BACKEND_SCENARIOS)
def test_env_scenario_passes_offline(offline_env, scenario_name):
    """Each no-backend env-scenario exits with code 0 under pytest.

    Uses parametrize so a failure points at the exact scenario name.
    """
    scenario = _ENV_SCENARIOS[scenario_name]
    rc = scenario(offline_env)
    assert rc == 0, (
        f"scenario {scenario_name!r} returned {rc} "
        f"(expected 0; see the captured stdout for the failure detail)"
    )


def test_action_registry_is_non_empty():
    """Trivial sanity — the registry has at least the documented actions.

    Catches a circular-import or registration ordering bug that would
    silently empty out ``_ACTIONS`` without breaking imports.
    """
    assert len(_ACTIONS) >= 40, (
        f"_ACTIONS shrunk unexpectedly: {len(_ACTIONS)} entries"
    )
    # A few representative actions that should always be present.
    for required in ("concept-create", "edge-create", "pipeline",
                     "apparitions", "purge", "assert-frame"):
        assert required in _ACTIONS, f"missing action: {required}"


def test_env_scenarios_registry_is_non_empty():
    """Trivial sanity — the scenarios registry is populated."""
    assert len(_ENV_SCENARIOS) >= 10, (
        f"_ENV_SCENARIOS shrunk unexpectedly: {len(_ENV_SCENARIOS)} entries"
    )
    for required in ("chunker-regression", "fixture-delete-guard",
                     "full-smoke"):
        assert required in _ENV_SCENARIOS, f"missing scenario: {required}"
