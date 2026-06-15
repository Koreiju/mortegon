"""Backing-pointer version sequencer (domain anchor §8D.39.6).

Compiled-in-from-scans concept nodes carry a backing-pointer version
that is monotone per ``(workspace_id, backing_pointer)``. Every scan
that materially updates the backing implementation bumps the version
even when the visible ``data`` field text is byte-identical. The
lifecycle dispatcher reads the version into the ``ConceptDiff`` and
treats a bump as an effective ``data_changed`` so dependent compiles
re-fire against the new implementation.

Per §8D.39.6, rollback of a backing-pointer version is **not**
supported through the evolution log — the scanner subsystem is
authoritative for the version. The evolution log records the
compile-output changes caused by version bumps; rolling back a
rendering does not roll back the version. The next cascade re-fires
against the current version.

The registry is in-process with on-disk persistence so versions
survive process restart. Persistence is best-effort: on read failure
the registry starts at version 0 per key.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


# (workspace_id, backing_pointer) -> int
_VERSIONS: Dict[Tuple[str, str], int] = {}
_LOCK = threading.Lock()

_PERSIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "snapshots",
    "backing_versions.json",
)
_PERSIST_LOCK = threading.Lock()
_LOADED = False


def _load_persisted() -> None:
    """Best-effort hydrate from disk on first access."""
    global _LOADED
    if _LOADED:
        return
    with _PERSIST_LOCK:
        if _LOADED:
            return
        try:
            with open(_PERSIST_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                with _LOCK:
                    for key_str, seq in raw.items():
                        if "::" not in key_str:
                            continue
                        ws, bp = key_str.split("::", 1)
                        try:
                            _VERSIONS[(ws, bp)] = int(seq)
                        except (TypeError, ValueError):
                            continue
                logger.debug("[backing_version] loaded %d entries from %s",
                             len(_VERSIONS), _PERSIST_PATH)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("[backing_version] failed to load persisted versions: %s", e)
        _LOADED = True


def _persist_locked() -> None:
    """Persist current versions to disk. Caller holds ``_LOCK``."""
    try:
        os.makedirs(os.path.dirname(_PERSIST_PATH), exist_ok=True)
        with _PERSIST_LOCK:
            with open(_PERSIST_PATH, "w", encoding="utf-8") as fh:
                json.dump(
                    {f"{ws}::{bp}": seq for (ws, bp), seq in _VERSIONS.items()},
                    fh,
                )
    except Exception as e:
        logger.warning("[backing_version] failed to persist versions: %s", e)


def current(workspace_id: str, backing_pointer: str) -> int:
    """Return the current version seq for ``(workspace_id, backing_pointer)``.

    Returns 0 if the key has never been bumped. Caller treats 0 as
    "unversioned" — a concept that has never had its backing
    implementation versioned (i.e., user-authored or freshly-materialised).
    """
    if not backing_pointer:
        return 0
    _load_persisted()
    with _LOCK:
        return int(_VERSIONS.get((workspace_id or "", backing_pointer), 0))


def bump(workspace_id: str, backing_pointer: str) -> int:
    """Bump the version seq for ``(workspace_id, backing_pointer)`` by 1.

    Returns the new seq value. Callers in the scanner subsystem invoke
    this when they materially update a backing implementation — e.g.,
    a SearchableURL's accessor dict gains a new field selector, a
    DetectedAccessor's observed type sharpens, an XPathPattern's
    instance roster gains new instances, or a URL concept node's
    web-ontology edge set changes (§8D.39.6).
    """
    if not backing_pointer:
        return 0
    _load_persisted()
    with _LOCK:
        key = (workspace_id or "", backing_pointer)
        new_seq = int(_VERSIONS.get(key, 0)) + 1
        _VERSIONS[key] = new_seq
        _persist_locked()
    logger.debug("[backing_version] bumped ws=%s bp=%s → %d",
                 workspace_id, backing_pointer, new_seq)
    return new_seq


def reset(workspace_id: str = "") -> None:
    """Drop versions for a workspace (or all if blank). Used by purge."""
    _load_persisted()
    with _LOCK:
        if not workspace_id:
            _VERSIONS.clear()
        else:
            for key in list(_VERSIONS.keys()):
                if key[0] == workspace_id:
                    del _VERSIONS[key]
        _persist_locked()


def snapshot() -> Dict[str, int]:
    """Test/diagnostic view — current versions, serialisable shape."""
    _load_persisted()
    with _LOCK:
        return {f"{ws}::{bp}": seq for (ws, bp), seq in _VERSIONS.items()}
