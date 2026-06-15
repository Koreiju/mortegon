"""Evolution log + cross-session rollback (Workstream C5; domain
anchor §8D.33).

Every edit to the workspace — user or agent, concept or edge,
create / modify / delete — produces a provenance-tagged diff in
the persistent evolution log. Provenance is what enables freedom:
agents can self-modify; users can revise wholesale; both can
experiment because every edit is diff-reversible.

This module:

  * Defines the ``EditDiff`` record (§8D.33.1).
  * Provides ``log_edit(...)`` for write-time recording.
  * Provides ``rollback_single(edit_id)``, ``rollback_range(...)``,
    and ``rollback_actor_since(...)`` (§8D.33.2).
  * Persists the log to a JSONL file alongside the workspace's
    other state.

Idempotency: rollback records itself as a new edit, so re-doing
(re-applying a reverted edit) is just another diff. The log grows
monotonically.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

EVOLUTION_LOG_DIR = os.environ.get(
    "WFH_EVOLUTION_LOG_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "kuzu_db")),
)


# ---------------------------------------------------------------------------
# Diff record
# ---------------------------------------------------------------------------

@dataclass
class EditDiff:
    """One edit record (§8D.33.1)."""

    edit_id: int = 0
    actor: str = "user:_anon"      # e.g. user:session_id | agent:agent_card_id
    timestamp: float = 0.0
    target: str = ""               # card:<id> | edge:<id> | agent_body:<id>
    kind: str = ""                 # create | modify | delete | link | unlink | rename | rollback
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    causing_edit_id: Optional[int] = None
    workspace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EditDiff":
        return cls(
            edit_id=int(d.get("edit_id", 0)),
            actor=d.get("actor", "user:_anon"),
            timestamp=float(d.get("timestamp", 0.0)),
            target=d.get("target", ""),
            kind=d.get("kind", ""),
            before=d.get("before"),
            after=d.get("after"),
            causing_edit_id=d.get("causing_edit_id"),
            workspace_id=d.get("workspace_id", ""),
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EvolutionLog:
    """Append-only diff log with rollback (§8D.33).

    Persisted as JSONL files per workspace under
    ``WFH_EVOLUTION_LOG_DIR``. The in-memory cache holds the full
    log for fast queries; on disk we never truncate (retention
    policies can be applied externally per §8D.33.6).
    """

    def __init__(self, graph_editor=None, broadcast=None):
        self._graph_editor = graph_editor
        # Optional ``broadcast(snapshot_id, payload)`` hook so every
        # log append fans out as an ``evolution_log_diff`` WS frame.
        # First caller wires it; subsequent ``get_evolution_log`` calls
        # may pass a fresh hook and the singleton picks it up.
        self._broadcast = broadcast
        self._diffs: Dict[str, List[EditDiff]] = {}  # workspace_id -> list
        self._next_id: Dict[str, int] = {}
        self._lock = threading.Lock()
        try:
            os.makedirs(EVOLUTION_LOG_DIR, exist_ok=True)
        except Exception:
            pass

    # -------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------

    def _log_path(self, workspace_id: str) -> str:
        safe = (workspace_id or "_default").replace("/", "_").replace("\\", "_")
        return os.path.join(EVOLUTION_LOG_DIR, f"evolution_log_{safe}.jsonl")

    def _load(self, workspace_id: str) -> List[EditDiff]:
        path = self._log_path(workspace_id)
        out: List[EditDiff] = []
        if not os.path.exists(path):
            return out
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        out.append(EditDiff.from_dict(d))
                    except Exception:
                        continue
        except Exception:
            return out
        return out

    def _append_disk(self, workspace_id: str, diff: EditDiff) -> None:
        try:
            with open(self._log_path(workspace_id), "a", encoding="utf-8") as f:
                f.write(json.dumps(diff.to_dict()) + "\n")
        except Exception:
            pass

    def _ensure_loaded(self, workspace_id: str) -> List[EditDiff]:
        with self._lock:
            if workspace_id in self._diffs:
                return self._diffs[workspace_id]
        loaded = self._load(workspace_id)
        with self._lock:
            self._diffs[workspace_id] = loaded
            if loaded:
                self._next_id[workspace_id] = max(d.edit_id for d in loaded) + 1
            else:
                self._next_id[workspace_id] = 1
        return loaded

    # -------------------------------------------------------------------
    # Recording
    # -------------------------------------------------------------------

    # Fix: cap per-field size on diffs so a card whose ``data`` is
    # a 1 MB blob doesn't write a 2 MB diff (before + after) on
    # every keystroke. The cap is large enough for any reasonable
    # user-authored content but truncates pathological large data.
    _MAX_DIFF_FIELD_BYTES = 64 * 1024  # 64 KB per field

    @classmethod
    def _truncate_for_diff(cls, payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if payload is None:
            return None
        out: Dict[str, Any] = {}
        for k, v in payload.items():
            if isinstance(v, str) and len(v) > cls._MAX_DIFF_FIELD_BYTES:
                head = v[: cls._MAX_DIFF_FIELD_BYTES - 64]
                out[k] = head + f"\n... [truncated {len(v) - len(head)} bytes for log]"
            else:
                out[k] = v
        return out

    def log(
        self,
        *,
        workspace_id: str = "",
        actor: str = "user:_anon",
        target: str = "",
        kind: str = "",
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        causing_edit_id: Optional[int] = None,
    ) -> EditDiff:
        """Append one diff to the log."""
        self._ensure_loaded(workspace_id)
        # Truncate oversized field values so the on-disk log
        # doesn't balloon under repeated edits of large concepts.
        # Rollback still works because the user's authored content
        # is usually << 64 KB; only pathologically-large data blobs
        # are clipped, and the clipped marker is human-visible.
        before_t = self._truncate_for_diff(before)
        after_t = self._truncate_for_diff(after)
        with self._lock:
            eid = self._next_id.get(workspace_id, 1)
            self._next_id[workspace_id] = eid + 1
            diff = EditDiff(
                edit_id=eid,
                actor=actor,
                timestamp=time.time(),
                target=target,
                kind=kind,
                before=before_t,
                after=after_t,
                causing_edit_id=causing_edit_id,
                workspace_id=workspace_id,
            )
            self._diffs.setdefault(workspace_id, []).append(diff)
        self._append_disk(workspace_id, diff)
        # Live broadcast — any open evolution-log panel (or rollback
        # consumer) updates immediately instead of polling
        # /api/evolution_log every N seconds.
        if self._broadcast is not None:
            try:
                from backend.api.ws_frames import build_evolution_log_diff
                self._broadcast(0, build_evolution_log_diff(
                    workspace_id=workspace_id or "_default",
                    diff=diff.to_dict(),
                ))
            except Exception:
                pass
        return diff

    def list_diffs(
        self,
        workspace_id: str = "",
        *,
        actor: Optional[str] = None,
        target_prefix: Optional[str] = None,
        since_timestamp: Optional[float] = None,
        limit: int = 1000,
    ) -> List[EditDiff]:
        diffs = self._ensure_loaded(workspace_id)
        out: List[EditDiff] = []
        for d in reversed(diffs):  # newest first
            if actor is not None and d.actor != actor:
                continue
            if target_prefix is not None and not (d.target or "").startswith(target_prefix):
                continue
            if since_timestamp is not None and d.timestamp < since_timestamp:
                continue
            out.append(d)
            if len(out) >= limit:
                break
        return out

    # -------------------------------------------------------------------
    # Rollback (§8D.33.2)
    # -------------------------------------------------------------------

    def rollback_single(self, edit_id: int, workspace_id: str = "") -> Dict[str, Any]:
        """Revert exactly one diff.

        Walks the cascade: if other diffs have ``causing_edit_id ==
        edit_id``, those are reverted too (in cascade order — most
        recent first).
        """
        diffs = self._ensure_loaded(workspace_id)
        target = next((d for d in diffs if d.edit_id == edit_id), None)
        if target is None:
            return {"ok": False, "error": f"edit_id {edit_id} not found"}
        # Cascade: revert dependents first.
        dependents = [d for d in diffs if d.causing_edit_id == edit_id]
        dependents.sort(key=lambda d: d.edit_id, reverse=True)
        results = []
        for d in dependents:
            results.append(self._apply_reverse(d, workspace_id))
        results.append(self._apply_reverse(target, workspace_id))
        # Record the rollback itself as a new diff.
        self.log(
            workspace_id=workspace_id,
            actor="system:rollback",
            target=target.target,
            kind="rollback",
            before=target.after,
            after=target.before,
            causing_edit_id=target.edit_id,
        )
        return {"ok": True, "reverted": [r for r in results if r is not None]}

    def rollback_range(
        self,
        edit_id_low: int,
        edit_id_high: int,
        workspace_id: str = "",
    ) -> Dict[str, Any]:
        diffs = self._ensure_loaded(workspace_id)
        in_range = [d for d in diffs
                    if edit_id_low <= d.edit_id <= edit_id_high]
        in_range.sort(key=lambda d: d.edit_id, reverse=True)
        results = []
        for d in in_range:
            results.append(self._apply_reverse(d, workspace_id))
        self.log(
            workspace_id=workspace_id,
            actor="system:rollback_range",
            target=f"range:{edit_id_low}-{edit_id_high}",
            kind="rollback",
            before=None,
            after={"low": edit_id_low, "high": edit_id_high},
        )
        return {"ok": True, "count": len(in_range)}

    def rollback_actor_since(
        self,
        actor: str,
        since_timestamp: float,
        workspace_id: str = "",
    ) -> Dict[str, Any]:
        diffs = self._ensure_loaded(workspace_id)
        matching = [d for d in diffs
                    if d.actor == actor and d.timestamp >= since_timestamp]
        matching.sort(key=lambda d: d.edit_id, reverse=True)
        for d in matching:
            self._apply_reverse(d, workspace_id)
        self.log(
            workspace_id=workspace_id,
            actor="system:rollback_actor",
            target=f"actor:{actor}",
            kind="rollback",
            before=None,
            after={"actor": actor, "since": since_timestamp,
                   "count": len(matching)},
        )
        return {"ok": True, "count": len(matching)}

    # -------------------------------------------------------------------
    # Reverse application
    # -------------------------------------------------------------------

    def _apply_reverse(self, diff: EditDiff, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Apply a diff in reverse via the graph_editor."""
        if self._graph_editor is None:
            return None
        kind = (diff.kind or "").lower()
        target = diff.target or ""
        try:
            if target.startswith("card:"):
                cid = target[len("card:"):]
                if kind == "create":
                    # Reverse a create = delete.
                    self._graph_editor.delete_concept(cid)
                    return {"target": target, "action": "deleted"}
                elif kind == "delete":
                    # Reverse a delete = re-create from ``before``.
                    if diff.before:
                        b = diff.before
                        self._graph_editor.create_concept(
                            concept_id=cid,
                            name=b.get("name", ""),
                            description=b.get("description", ""),
                            data=b.get("data", ""),
                            rendering=b.get("rendering", ""),
                            backing_pointer=b.get("backing_pointer", ""),
                            provenance=b.get("provenance", "user-authored"),
                            workspace_id=b.get("workspace_id", workspace_id),
                            type_hint=b.get("type_hint", ""),
                        )
                        return {"target": target, "action": "restored"}
                elif kind in ("modify", "update", "rename"):
                    # Reverse a modify = restore ``before`` fields.
                    if diff.before:
                        b = diff.before
                        self._graph_editor.update_concept(
                            cid,
                            name=b.get("name", ""),
                            description=b.get("description", ""),
                            data=b.get("data", ""),
                            rendering=b.get("rendering", ""),
                        )
                        return {"target": target, "action": "modified-back"}
            elif target.startswith("edge:"):
                eid = target[len("edge:"):]
                if kind == "create":
                    self._graph_editor.delete_concept_edge(eid)
                    return {"target": target, "action": "edge-deleted"}
                elif kind == "delete" and diff.before:
                    b = diff.before
                    self._graph_editor.create_concept_edge(
                        source_id=b.get("source_id", ""),
                        target_id=b.get("target_id", ""),
                        edge_type=b.get("edge_type", "RELATES_TO"),
                        source_port=b.get("source_port", ""),
                        target_port=b.get("target_port", ""),
                        weight=b.get("weight"),
                        variable_name=b.get("variable_name", ""),
                        workspace_id=b.get("workspace_id", workspace_id),
                    )
                    return {"target": target, "action": "edge-restored"}
            elif target.startswith("rollout:"):
                # §3.3 — reverse a rollout sample-boundary: re-seat the
                # signal-stream cursor to its ``before`` index so a rollback
                # restores the iteration position together with the data.
                if kind == "sample_boundary" and diff.before:
                    key = target[len("rollout:"):]
                    card_id, _, field_path = key.partition("::")
                    b = diff.before
                    try:
                        from backend.services.ui_state_service import get_ui_state_service
                        get_ui_state_service().set_signal_stream(
                            workspace_id, card_id,
                            total=int(b.get("signal_total") or 0),
                            signal_index=int(b.get("signal_index") or 0),
                            field_path=field_path or "",
                        )
                    except Exception:
                        pass
                    return {"target": target, "action": "signal-reseated",
                            "signal_index": int(b.get("signal_index") or 0)}
        except Exception as e:
            return {"target": target, "action": "error", "error": str(e)}
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_LOG: Optional[EvolutionLog] = None
_LOG_LOCK = threading.Lock()


def get_evolution_log(graph_editor=None, broadcast=None) -> EvolutionLog:
    """Process-wide singleton (first caller wires graph_editor + broadcast)."""
    global _LOG
    with _LOG_LOCK:
        if _LOG is None:
            _LOG = EvolutionLog(graph_editor=graph_editor, broadcast=broadcast)
        else:
            if graph_editor is not None and _LOG._graph_editor is None:
                _LOG._graph_editor = graph_editor
            if broadcast is not None and _LOG._broadcast is None:
                _LOG._broadcast = broadcast
    return _LOG
