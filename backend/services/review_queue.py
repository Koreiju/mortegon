"""Agent review queue (Workstream W24; domain anchor §8C.8, §8D.32).

The agent's ``RequestUserReviewAction`` (§8C.8) surfaces a yellow-
bordered card asking the user to inspect / edit / approve before
proceeding. Reviews accumulate in this workspace-scoped queue; the
frontend reads them from ``GET /api/agent/reviews`` and shows a
floating panel listing pending entries. Each entry has accept /
dismiss affordances.

The agent pauses on the review's parameter card until the user
resolves it (the runtime checks ``has_unresolved_reviews()`` on
the next tick).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ReviewEntry:
    review_id: str = ""
    workspace_id: str = ""
    actor: str = ""
    card_ids: List[str] = field(default_factory=list)
    prompt: str = ""
    status: str = "pending"   # pending | accepted | dismissed
    created_at: float = 0.0
    resolved_at: float = 0.0

    def __post_init__(self):
        if not self.review_id:
            self.review_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReviewQueue:
    def __init__(self):
        self._entries: Dict[str, ReviewEntry] = {}
        self._lock = threading.Lock()

    def enqueue(
        self,
        *,
        workspace_id: str = "",
        actor: str = "",
        card_ids: Optional[List[str]] = None,
        prompt: str = "",
    ) -> ReviewEntry:
        entry = ReviewEntry(
            workspace_id=workspace_id,
            actor=actor,
            card_ids=list(card_ids or []),
            prompt=prompt,
        )
        with self._lock:
            self._entries[entry.review_id] = entry
        return entry

    def list_pending(self, workspace_id: Optional[str] = None) -> List[ReviewEntry]:
        with self._lock:
            out = [e for e in self._entries.values()
                   if e.status == "pending"
                   and (workspace_id is None or e.workspace_id == workspace_id)]
        out.sort(key=lambda e: e.created_at, reverse=True)
        return out

    def has_unresolved_reviews(self, workspace_id: Optional[str] = None) -> bool:
        with self._lock:
            for e in self._entries.values():
                if e.status == "pending" and (
                    workspace_id is None or e.workspace_id == workspace_id
                ):
                    return True
        return False

    def resolve(self, review_id: str, decision: str = "accepted") -> Optional[ReviewEntry]:
        with self._lock:
            e = self._entries.get(review_id)
            if e is None:
                return None
            if decision not in ("accepted", "dismissed"):
                decision = "dismissed"
            e.status = decision
            e.resolved_at = time.time()
            return e

    def clear_resolved(self) -> int:
        """Drop entries already resolved more than 60s ago."""
        cutoff = time.time() - 60
        with self._lock:
            drop = [rid for rid, e in self._entries.items()
                    if e.status != "pending" and e.resolved_at < cutoff]
            for rid in drop:
                del self._entries[rid]
        return len(drop)


_QUEUE: Optional[ReviewQueue] = None
_QUEUE_LOCK = threading.Lock()


def get_review_queue() -> ReviewQueue:
    global _QUEUE
    with _QUEUE_LOCK:
        if _QUEUE is None:
            _QUEUE = ReviewQueue()
    return _QUEUE
