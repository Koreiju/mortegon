"""Centralised runtime configuration (Settings dataclass).

Replaces the scattered module-level constants
(``_CASCADE_DEBOUNCE_SEC``, ``_SPAWN_MAX_PER_WORKSPACE_PER_MIN``,
``_AGENT_TOKEN_BUFFER_SIZE``, ``_CADENCE_DEFAULT_SEC``,
``DEFAULT_PROJECTION_DEBOUNCE``, etc.) with a single ``Settings``
record. Each field can be overridden via env so deployments tune
without code changes.

Pattern: configuration as code. The class is frozen so callers can't
mutate live settings — to override at runtime, construct a new
``Settings`` and call ``configure(settings)``. Reading goes through
``get_settings()`` which is a per-process singleton.

Env var naming convention: ``WFH_<UPPER_SNAKE_OF_FIELD>``.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, fields
from typing import Any, Optional


def _env_float(name: str, default: float) -> float:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """All runtime-tunable knobs in one place. Frozen — to change a
    value at runtime, build a new instance and call ``configure(s)``.

    Per-subsystem grouping by field-name prefix so a reader scanning
    the dataclass can quickly find the right knob.
    """

    # --- Cascade scheduler (§8D.38.1) --------------------------------
    cascade_debounce_sec: float = 1.0
    cascade_max_ticks_per_min: int = 20

    # --- Agent self-extension (§8D.32.2) -----------------------------
    spawn_max_per_workspace_per_min: int = 5

    # --- Agent token ring (§8D.8) ------------------------------------
    agent_token_buffer_size: int = 4000

    # --- Concept index batch cadence (§11.6) -------------------------
    concept_index_cadence_sec: float = 300.0

    # --- Output projection debounce (§8D.19) -------------------------
    projection_debounce_sec: float = 0.8

    # --- Reservoir rollout: async readout perimeter (§7.8.3) ---------
    # Max un-acked async readout-perimeter deltas per workspace before
    # per-node coalescing (keep-latest). constants.md §3.
    readout_delta_max_inflight: int = 64

    # --- WebSocket queues (backpressure) -----------------------------
    ws_queue_max: int = 1000

    # --- Idempotency dedup window ------------------------------------
    idempotency_ttl_sec: float = 300.0
    # Hard ceiling on cached responses; oldest 25 % evicted when full.
    # Caps memory under retry storms (e.g. a misbehaving client looping
    # PATCH calls). 10k × ~1 KB response ≈ 10 MB which is generous.
    idempotency_cache_max: int = 10000

    # --- Evolution log diff truncation -------------------------------
    evolution_log_max_field_bytes: int = 64 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        """Build a Settings instance with env overrides applied.

        Each field maps to env var ``WFH_<UPPER_FIELD_NAME>``.
        Floats fall back to default on parse error.
        """
        kwargs = {}
        for f in fields(cls):
            env_name = "WFH_" + f.name.upper()
            type_name = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", "")
            if type_name == "float":
                kwargs[f.name] = _env_float(env_name, f.default)
            elif type_name == "int":
                kwargs[f.name] = _env_int(env_name, f.default)
            else:
                kwargs[f.name] = os.environ.get(env_name, f.default)
        return cls(**kwargs)


_SETTINGS: Optional[Settings] = None
_SETTINGS_LOCK = threading.Lock()


def get_settings() -> Settings:
    """Return the process-wide Settings singleton, env-loaded on
    first call. Subsequent calls return the same instance unless
    ``configure(...)`` overrides."""
    global _SETTINGS
    with _SETTINGS_LOCK:
        if _SETTINGS is None:
            _SETTINGS = Settings.from_env()
        return _SETTINGS


def configure(settings: Settings) -> None:
    """Override the singleton (e.g. from a test fixture or a
    deployment-specific init script that constructs a Settings
    instance programmatically rather than via env)."""
    global _SETTINGS
    with _SETTINGS_LOCK:
        _SETTINGS = settings


def reset_to_env() -> None:
    """Drop any programmatic override and reload from env on next
    access. Test fixtures call this in teardown to undo ``configure``.
    """
    global _SETTINGS
    with _SETTINGS_LOCK:
        _SETTINGS = None
