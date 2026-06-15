from enum import Enum
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any
import threading
import time

class SnapshotState(str, Enum):
    IDLE = "idle"
    REQUESTED = "requested"
    SCANNING = "scanning"
    STREAMING = "streaming"
    COMPLETE = "complete"
    FAILED = "failed"
    ABANDONED = "abandoned"

class LabelState(str, Enum):
    UNLABELED = "unlabeled"
    PENDING_APPLY = "pending_apply"
    INSTANCE_LABELED = "instance_labeled"
    COMMUTED = "commuted"
    PENDING_DELETE = "pending_delete"

class FitState(str, Enum):
    UNFIT = "unfit"
    QUEUED = "queued"
    FITTING = "fitting"
    FITTED = "fitted"
    FAILED = "failed"

@dataclass
class SnapshotStateRecord:
    ws_id: int
    url: str
    state: SnapshotState
    error_code: Optional[str]
    created_at: float
    last_frame_at: float

class WorkflowStateTracker:
    """
    In-process registry of current state for every active workflow.
    Backed by threading locks to prevent race conditions (§14.1).
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._snapshots: Dict[int, SnapshotStateRecord] = {}
        self._labels: Dict[Tuple[str, str], LabelState] = {}   # (url, xpath) -> state
        self._fits: Dict[Tuple[str, str], FitState] = {}       # (url, hash) -> state

    def try_begin_snapshot(self, ws_id: int, url: str) -> Tuple[bool, Optional[str]]:
        with self._lock:
            for rec in self._snapshots.values():
                if rec.url == url and rec.state in (SnapshotState.REQUESTED, SnapshotState.SCANNING, SnapshotState.STREAMING):
                    # Debounce window check (Phase 14.3: calls within 2s rejected)
                    if time.time() - rec.created_at < 2.0 or rec.state != SnapshotState.REQUESTED:
                        return False, "snapshot_in_flight"
            
            self._snapshots[ws_id] = SnapshotStateRecord(
                ws_id=ws_id,
                url=url,
                state=SnapshotState.REQUESTED,
                error_code=None,
                created_at=time.time(),
                last_frame_at=time.time()
            )
            return True, None

    def try_begin_label(self, url: str, xpath: str) -> Tuple[bool, Optional[str]]:
        key = (url, xpath)
        with self._lock:
            if self._labels.get(key) in (LabelState.PENDING_APPLY, LabelState.PENDING_DELETE):
                return False, "label_lock_held"
            self._labels[key] = LabelState.PENDING_APPLY
            return True, None

    def try_begin_fit(self, url: str, genome_hash: str) -> Tuple[bool, Optional[str]]:
        key = (url, genome_hash)
        with self._lock:
            if self._fits.get(key) in (FitState.QUEUED, FitState.FITTING):
                return False, "fit_in_flight"
            self._fits[key] = FitState.QUEUED
            return True, None

    def report_snapshot_state(self, ws_id: int, state: SnapshotState, error_code: str = None):
        with self._lock:
            if ws_id in self._snapshots:
                self._snapshots[ws_id].state = state
                if error_code:
                    self._snapshots[ws_id].error_code = error_code
                self._snapshots[ws_id].last_frame_at = time.time()

    def finish_label(self, url: str, xpath: str, state: LabelState):
        with self._lock:
            self._labels[(url, xpath)] = state

    def finish_fit(self, url: str, genome_hash: str, state: FitState):
        with self._lock:
            self._fits[(url, genome_hash)] = state

    def reconcile(self, url: str) -> Dict[str, Any]:
        """Returns the authoritative state of every workflow for this URL (§14.8)."""
        with self._lock:
            url_snapshots = [
                {
                    "snapshot_ws_id": rec.ws_id,
                    "state": rec.state.value,
                    "created_at": rec.created_at
                }
                for rec in self._snapshots.values() if rec.url == url
            ]
            
            active_fits = [
                {"genome_hash": k[1], "state": v.value}
                for k, v in self._fits.items() if k[0] == url and v in (FitState.QUEUED, FitState.FITTING)
            ]

            return {
                "snapshots": url_snapshots,
                "labels": [],  # STUB: will be populated by DB lookup
                "datasets": [],  # STUB: will be populated by DB lookup
                "active_fits": active_fits,
                "latest_run": None,
                "pinned_for_next_run": [],
                "health": {
                    "redis": "down",
                    "kuzu": "ok",
                    "selenium": "ok",
                    "cuda": "down"
                }
            }