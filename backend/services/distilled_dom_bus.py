"""
distilled_dom_bus.py — in-memory pub/sub for content-distilled DOM snapshots.

The scanner publishes fresh distilled trees here as a scan progresses.
Retrieval and patricia-trie streaming services subscribe independently and
react to each update without coupling back into the scanner pipeline.

A snapshot_id's state is a single DistilledSnapshotState object holding the
latest tree, url, and monotonically-increasing revision counter. Subscribers
register a callback that receives the state on each publish. Callbacks run
synchronously on the publisher thread, so they must be cheap (typically they
just drop work onto their own queue).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DistilledSnapshotState:
    snapshot_id: str
    url: str
    tree: Dict[str, Any]
    revision: int = 0
    done: bool = False


Subscriber = Callable[[DistilledSnapshotState], None]


class DistilledDomBus:
    """Thread-safe pub/sub for distilled-DOM snapshots."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._states: Dict[str, DistilledSnapshotState] = {}
        self._subs_by_snapshot: Dict[str, List[Subscriber]] = {}
        self._global_subs: List[Subscriber] = []

    # -- publication -------------------------------------------------

    def publish(self, snapshot_id: str, url: str, tree: Dict[str, Any],
                done: bool = False) -> DistilledSnapshotState:
        """Publish a new distilled tree for `snapshot_id`.

        Called by the scanner on each iteration. The tree may be a partial
        view — subscribers must tolerate growth across revisions.
        """
        with self._lock:
            prior = self._states.get(snapshot_id)
            revision = (prior.revision + 1) if prior else 1
            state = DistilledSnapshotState(
                snapshot_id=snapshot_id, url=url, tree=tree,
                revision=revision, done=done,
            )
            self._states[snapshot_id] = state
            subs = list(self._subs_by_snapshot.get(snapshot_id, ()))
            globals_ = list(self._global_subs)

        for cb in subs + globals_:
            try:
                cb(state)
            except Exception as e:
                logger.error(f"[DistilledDomBus] subscriber raised: {e}", exc_info=True)
        return state

    def mark_done(self, snapshot_id: str) -> None:
        """Mark the snapshot as fully scanned. Emits one final event."""
        with self._lock:
            prior = self._states.get(snapshot_id)
            if not prior:
                return
            url, tree = prior.url, prior.tree
        self.publish(snapshot_id, url, tree, done=True)

    # -- subscription ------------------------------------------------

    def subscribe(self, snapshot_id: str, cb: Subscriber,
                  replay_current: bool = True) -> Callable[[], None]:
        """Subscribe to updates for a specific snapshot.

        If `replay_current=True` and a state already exists, the subscriber is
        invoked immediately with the latest state so late joiners catch up.
        Returns an unsubscribe callable.
        """
        with self._lock:
            self._subs_by_snapshot.setdefault(snapshot_id, []).append(cb)
            current = self._states.get(snapshot_id) if replay_current else None

        if current is not None:
            try:
                cb(current)
            except Exception as e:
                logger.error(f"[DistilledDomBus] replay raised: {e}", exc_info=True)

        def unsubscribe() -> None:
            with self._lock:
                subs = self._subs_by_snapshot.get(snapshot_id)
                if subs and cb in subs:
                    subs.remove(cb)
        return unsubscribe

    def subscribe_all(self, cb: Subscriber) -> Callable[[], None]:
        with self._lock:
            self._global_subs.append(cb)

        def unsubscribe() -> None:
            with self._lock:
                if cb in self._global_subs:
                    self._global_subs.remove(cb)
        return unsubscribe

    # -- lookup ------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[DistilledSnapshotState]:
        with self._lock:
            return self._states.get(snapshot_id)

    def drop(self, snapshot_id: str) -> None:
        """Forget state and subscribers for a completed snapshot."""
        with self._lock:
            self._states.pop(snapshot_id, None)
            self._subs_by_snapshot.pop(snapshot_id, None)


_bus: Optional[DistilledDomBus] = None
_bus_lock = threading.Lock()


def get_distilled_dom_bus() -> DistilledDomBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = DistilledDomBus()
    return _bus
