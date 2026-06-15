"""
node_registry.py — Cross-scan stable node identity and lifecycle tracking.

Assigns each DOM node a stable UUID based on (url, generalized_xpath, wl_hash)
so that re-scanning the same page can detect which nodes are new, changed,
or removed — enabling delta streaming.

Lifecycle states:
  DISCOVERED  — first seen in this scan
  STABLE      — seen in previous scan, structure unchanged
  MUTATED     — seen in previous scan, structure changed (different wl_hash)
  REMOVED     — was present in previous scan, absent in this one
"""

from __future__ import annotations

import hashlib
import time
from enum import Enum, auto
from typing import Dict, Optional, Set, Tuple


class LifecycleState(Enum):
    DISCOVERED = auto()
    STABLE = auto()
    MUTATED = auto()
    REMOVED = auto()


class NodeRecord:
    """Tracks a node's identity across scans."""
    __slots__ = ('stable_id', 'url', 'generalized_xpath', 'wl_hash',
                 'first_seen', 'last_seen', 'state', 'scan_count')

    def __init__(self, stable_id: str, url: str, generalized_xpath: str,
                 wl_hash: Optional[int] = None):
        self.stable_id = stable_id
        self.url = url
        self.generalized_xpath = generalized_xpath
        self.wl_hash = wl_hash
        self.first_seen = time.time()
        self.last_seen = self.first_seen
        self.state = LifecycleState.DISCOVERED
        self.scan_count = 1


def _make_stable_id(url: str, generalized_xpath: str) -> str:
    """Deterministic UUID from (url, generalized_xpath)."""
    key = f"{url}|{generalized_xpath}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class NodeRegistry:
    """Tracks node identity across re-scans of the same URL.

    Usage:
        registry = get_node_registry()
        diff = registry.update_scan(url, snapshot_id, current_nodes)
        # diff contains 'added', 'stable', 'mutated', 'removed' sets
    """

    def __init__(self):
        # (url, generalized_xpath) → NodeRecord
        self._records: Dict[Tuple[str, str], NodeRecord] = {}
        # url → set of (url, generalized_xpath) keys from last scan
        self._last_scan_keys: Dict[str, Set[Tuple[str, str]]] = {}

    def update_scan(
        self,
        url: str,
        current_nodes: Dict[str, Optional[int]],
    ) -> Dict[str, set]:
        """Process a new scan and compute the diff against the previous scan.

        Args:
            url: the scanned URL
            current_nodes: mapping of generalized_xpath → wl_hash (or None)

        Returns:
            {
                'added': set of stable_ids (new nodes),
                'stable': set of stable_ids (unchanged),
                'mutated': set of stable_ids (structure changed),
                'removed': set of stable_ids (gone),
            }
        """
        now = time.time()
        previous_keys = self._last_scan_keys.get(url, set())
        current_keys: Set[Tuple[str, str]] = set()

        added = set()
        stable = set()
        mutated = set()

        for gxpath, wl_hash in current_nodes.items():
            key = (url, gxpath)
            current_keys.add(key)

            existing = self._records.get(key)
            if existing is None:
                # New node
                sid = _make_stable_id(url, gxpath)
                record = NodeRecord(sid, url, gxpath, wl_hash)
                self._records[key] = record
                added.add(sid)
            else:
                existing.last_seen = now
                existing.scan_count += 1
                if existing.wl_hash != wl_hash and wl_hash is not None:
                    existing.wl_hash = wl_hash
                    existing.state = LifecycleState.MUTATED
                    mutated.add(existing.stable_id)
                else:
                    existing.state = LifecycleState.STABLE
                    stable.add(existing.stable_id)

        # Removed: in previous scan but not in current
        removed_keys = previous_keys - current_keys
        removed = set()
        for key in removed_keys:
            record = self._records.get(key)
            if record:
                record.state = LifecycleState.REMOVED
                removed.add(record.stable_id)

        self._last_scan_keys[url] = current_keys

        return {
            'added': added,
            'stable': stable,
            'mutated': mutated,
            'removed': removed,
        }

    def get_stable_id(self, url: str, generalized_xpath: str) -> Optional[str]:
        """Look up the stable ID for a node, or None if not registered."""
        record = self._records.get((url, generalized_xpath))
        return record.stable_id if record else None

    def get_lifecycle_state(self, url: str, generalized_xpath: str) -> Optional[LifecycleState]:
        """Look up the lifecycle state for a node."""
        record = self._records.get((url, generalized_xpath))
        return record.state if record else None


# Module-level singleton
_node_registry: Optional[NodeRegistry] = None


def get_node_registry() -> NodeRegistry:
    """Return the global NodeRegistry singleton."""
    global _node_registry
    if _node_registry is None:
        _node_registry = NodeRegistry()
    return _node_registry
