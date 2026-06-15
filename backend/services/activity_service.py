"""
Phase 0D — Activity service (section 15C).

Append-only log of system events. Powers the Activity Ticker overlay
and the History Panel with action replay and reification.
"""

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ActivityEntry:
    """A single activity event in the system."""
    entry_id: str = ""
    timestamp: str = ""
    actor: str = ""                # e.g. "user", "slm", "media_pipeline", "evolution"
    actor_type: str = "system"     # "human" | "slm" | "system" | "agent"
    action_verb: str = ""          # e.g. "scanned", "labeled", "embedded", "fitted"
    target_type: str = ""          # e.g. "snapshot", "node", "cluster", "media_asset"
    target_id: str = ""
    summary: str = ""              # Human-readable one-liner
    diff: Optional[Dict] = None    # Field-level diff for edits
    context: Optional[Dict] = None # Additional context
    parent_entry_id: Optional[str] = None  # Causal chain linkage

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ActivityService:
    """
    Manages the activity log: emit, query, causal chains, replay.

    8 integrated subsystems emit into this service:
      fluid, chat, media, embedder, mapper, graph, analytics, retrieval
    """

    def __init__(self, db_conn=None):
        self._entries: List[ActivityEntry] = []
        self._db_conn = db_conn
        self._subscribers: List[Any] = []  # WebSocket connections

    def emit(
        self,
        actor: str,
        action_verb: str,
        target_type: str,
        target_id: str = "",
        summary: str = "",
        actor_type: str = "system",
        diff: Optional[Dict] = None,
        context: Optional[Dict] = None,
        parent_entry_id: Optional[str] = None,
    ) -> ActivityEntry:
        """
        Record an activity event. Returns the created entry.
        Notifies all subscribers (WebSocket connections).
        """
        entry = ActivityEntry(
            actor=actor,
            actor_type=actor_type,
            action_verb=action_verb,
            target_type=target_type,
            target_id=target_id,
            summary=summary or f"{actor} {action_verb} {target_type} {target_id}",
            diff=diff,
            context=context,
            parent_entry_id=parent_entry_id,
        )

        self._entries.append(entry)
        self._persist(entry)
        self._notify(entry)

        logger.info(f"Activity: {entry.summary}")
        return entry

    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        actor_filter: Optional[str] = None,
        target_type_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Return activity history with optional filtering."""
        filtered = self._entries

        if actor_filter:
            filtered = [e for e in filtered if e.actor == actor_filter]
        if target_type_filter:
            filtered = [e for e in filtered if e.target_type == target_type_filter]

        # Reverse chronological
        filtered = list(reversed(filtered))
        return [asdict(e) for e in filtered[offset:offset + limit]]

    def get_causal_chain(self, entry_id: str) -> List[Dict]:
        """
        Walk the parent_entry_id chain backwards to build the
        full causal history of an activity.
        """
        chain = []
        entry_map = {e.entry_id: e for e in self._entries}

        current_id = entry_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            entry = entry_map.get(current_id)
            if entry is None:
                break
            chain.append(asdict(entry))
            current_id = entry.parent_entry_id

        return list(reversed(chain))  # Root cause first

    def get_entry_detail(self, entry_id: str) -> Optional[Dict]:
        """Get full detail of a single entry including diff."""
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return asdict(entry)
        return None

    def subscribe(self, ws):
        """Add a WebSocket subscriber for real-time ticker updates."""
        self._subscribers.append(ws)

    def unsubscribe(self, ws):
        """Remove a WebSocket subscriber."""
        self._subscribers = [s for s in self._subscribers if s is not ws]

    def _persist(self, entry: ActivityEntry):
        """Persist to KuzuDB if connection available."""
        if self._db_conn is None:
            return
        try:
            self._db_conn.execute(
                """
                CREATE (a:ActivityEntry {
                    entry_id: $eid, timestamp: $ts, actor: $actor,
                    actor_type: $at, action_verb: $av, target_type: $tt,
                    target_id: $tid, summary: $sum, diff_json: $diff,
                    context_json: $ctx, parent_entry_id: $pid
                })
                """,
                parameters={
                    "eid": entry.entry_id,
                    "ts": entry.timestamp,
                    "actor": entry.actor,
                    "at": entry.actor_type,
                    "av": entry.action_verb,
                    "tt": entry.target_type,
                    "tid": entry.target_id,
                    "sum": entry.summary,
                    "diff": json.dumps(entry.diff) if entry.diff else "{}",
                    "ctx": json.dumps(entry.context) if entry.context else "{}",
                    "pid": entry.parent_entry_id or "",
                },
            )
        except Exception as e:
            logger.warning(f"Failed to persist activity entry: {e}")

    def _notify(self, entry: ActivityEntry):
        """Push to all WebSocket subscribers."""
        payload = asdict(entry)
        for ws in self._subscribers:
            try:
                # Will be awaited by the caller
                ws.send_json(payload)
            except Exception:
                pass
