"""ui_telemetry_service.py — Frontend → backend DOM-mutation reports.

The frontend installs ``MutationObserver`` listeners on its key
rendered surfaces (concept-card list in the 2D editor, pinned-panel
container, 3D scene root, halo overlays) and POSTs a structured
summary of every meaningful mutation back to the backend. The
backend collects these in a per-workspace ring buffer keyed by
monotonic sequence number so the CLI / agents can drain them in
order.

This is the inverse of the existing CLI → frontend gesture mirror
(``ui_state_service``): the frontend now reports what it actually
rendered, so a CLI session running ``ui-telemetry-stream`` sees
the live shape of the user's screen without screen-scraping or
browser automation.

Report shape (whatever the frontend wants to post; backend stores
verbatim plus a server timestamp + seq):

    {
      "kind":         "concept-card-added" | "billboard-pinned" | ...,
      "target_id":    "card_abc"  (optional),
      "count":         N           (optional — e.g. # cards visible),
      "extra":        {...}        (optional — anything else),
    }

The backend buffer is bounded — old entries roll off at the head
once the cap is reached. Each push also broadcasts a ``ui_telemetry``
WS frame so anyone connected to the workspace WS can react in real
time (the CLI's WS drain picks these up automatically).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional


@dataclass
class TelemetryEntry:
    """One frontend → backend mutation report."""
    seq: int
    workspace_id: str
    received_at: float
    kind: str
    target_id: Optional[str] = None
    count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq":          self.seq,
            "workspace_id": self.workspace_id,
            "received_at":  self.received_at,
            "kind":         self.kind,
            "target_id":    self.target_id,
            "count":        self.count,
            "extra":        dict(self.extra),
        }


class UITelemetryService:
    """Per-workspace bounded deque of frontend mutation reports.

    Thread-safe: the FastAPI request handler thread pushes, the CLI's
    drain thread reads. Singleton via :func:`get_ui_telemetry_service`.
    """

    DEFAULT_CAP = 1024

    def __init__(
        self,
        *,
        broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
        cap: int = DEFAULT_CAP,
    ) -> None:
        self._buffers: Dict[str, Deque[TelemetryEntry]] = {}
        self._lock = threading.Lock()
        self._broadcast = broadcast
        self._cap = int(cap)
        # Monotonic sequence is per-workspace so each subscriber can
        # paginate independently without cross-workspace leaks.
        self._seq: Dict[str, int] = {}

    # -- push -----------------------------------------------------------
    def push(
        self,
        workspace_id: str,
        *,
        kind: str,
        target_id: Optional[str] = None,
        count: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> TelemetryEntry:
        if not kind:
            raise ValueError("telemetry push requires a non-empty kind")
        with self._lock:
            ws = workspace_id or "_default"
            self._seq[ws] = self._seq.get(ws, 0) + 1
            entry = TelemetryEntry(
                seq=self._seq[ws],
                workspace_id=ws,
                received_at=time.time(),
                kind=kind,
                target_id=target_id,
                count=count,
                extra=dict(extra or {}),
            )
            buf = self._buffers.setdefault(ws, deque(maxlen=self._cap))
            buf.append(entry)
        self._emit(entry)
        return entry

    # -- drain ----------------------------------------------------------
    def drain(
        self,
        workspace_id: str,
        *,
        since_seq: int = 0,
        limit: int = 256,
    ) -> List[TelemetryEntry]:
        """Return entries with seq > ``since_seq``, capped at ``limit``.

        Drain is non-destructive (entries stay in the buffer) so multiple
        consumers can each track their own ``since_seq`` cursor without
        racing.
        """
        with self._lock:
            ws = workspace_id or "_default"
            buf = self._buffers.get(ws)
            if not buf:
                return []
            out = [e for e in buf if e.seq > int(since_seq)]
            if len(out) > int(limit):
                out = out[-int(limit):]
            return out

    def clear_workspace(self, workspace_id: str) -> None:
        with self._lock:
            ws = workspace_id or "_default"
            self._buffers.pop(ws, None)
            self._seq.pop(ws, None)

    def head_seq(self, workspace_id: str) -> int:
        """Most-recent seq for ``workspace_id`` (0 if empty). Useful for
        a fresh subscriber that wants only future entries."""
        with self._lock:
            return self._seq.get(workspace_id or "_default", 0)

    # -- internals ------------------------------------------------------
    def _emit(self, entry: TelemetryEntry) -> None:
        if self._broadcast is None:
            return
        try:
            self._broadcast(0, {
                "type":         "ui_telemetry",
                "workspace_id": entry.workspace_id,
                "entry":        entry.to_dict(),
            })
        except Exception:
            pass


_SVC: Optional[UITelemetryService] = None
_SVC_LOCK = threading.Lock()


def get_ui_telemetry_service(
    *,
    broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> UITelemetryService:
    """Process-wide singleton. ``broadcast`` is set on first call."""
    global _SVC
    if _SVC is not None:
        return _SVC
    with _SVC_LOCK:
        if _SVC is None:
            _SVC = UITelemetryService(broadcast=broadcast)
    return _SVC
