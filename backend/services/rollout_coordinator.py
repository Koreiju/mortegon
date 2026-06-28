"""RolloutCoordinator — the iteration driver (§7.5 / RolloutCoordinator.md).

The workspace's outer loop: it advances the *signal index* of an iterable-
bearing field (a ``pattern_map``'s ``pattern_hash``, a ``url_set``'s ``url``, a
chunk-sample bank, a ``concept_ids`` batch) one element at a time — the
"iteration" half of recursion-over-iteration (§12.2.1).

It owns **no truth that survives a reload** beyond the iteration index, which
lives in the ``UIStateService`` ``signal_stream`` + ``rollout_state`` mirror
fields (§2.4). The four controls are thin wrappers over the signal-stream:

  * ``play``  — mark the rollout playing (``paused=False``) + emit
    ``rollout_resumed``. On a single-user on-device app the per-interval
    advance cadence is driven by the frontend play control (or a REPL loop)
    calling ``advance``; the backend owns the *state* + the *advance primitive*
    (the §6 anti-pattern guard "advance fires a per-sample cascade re-fire" is
    enforced at the compile layer, not here).
  * ``pause`` — halt at the current sample (``paused=True``) + ``rollout_paused``.
  * ``step``  — one ``advance`` then re-pause (``rollout_paused``).
  * ``reset`` — return the cursor to 0.
  * ``advance`` — the single-step primitive (also ``POST /api/ui/signal_advance``).
"""

from __future__ import annotations

from typing import Optional

from backend.services.ui_state_service import get_ui_state_service, UIState


class RolloutCoordinator:
    def __init__(self, ui_state_service=None, broadcast=None, graph_editor=None):
        self._ui = ui_state_service or get_ui_state_service(broadcast=broadcast)
        # Kept for the §R.7 per-sample cascade re-fire (renderings settle
        # through the lifecycle, which broadcasts via this hook). The graph
        # editor is injectable for tests; production falls back to the
        # shared default-instance accessor.
        self._broadcast = broadcast
        self._ge = graph_editor

    # -- helpers ---------------------------------------------------------
    def _entry(self, workspace_id: str, card_id: str) -> dict:
        st = self._ui.get_state(workspace_id)
        return dict((st.signal_stream or {}).get(card_id) or {})

    # -- controls --------------------------------------------------------
    def play(self, workspace_id: str, card_id: str, field_path: str = "",
             *, interval_ms: int = 1000) -> UIState:
        e = self._entry(workspace_id, card_id)
        total = int(e.get("total") or 0)
        idx = int(e.get("signal_index") or 0)
        fp = field_path or e.get("field_path", "") or ""
        self._ui.set_signal_stream(
            workspace_id, card_id, total=total, signal_index=idx,
            signal_id=e.get("signal_id"), paused=False, field_path=fp,
        )
        return self._ui.set_rollout_state(
            workspace_id, card_id=card_id, field_path=fp, paused=False,
            signal_index=idx, signal_total=total, interval_ms=interval_ms,
            kind="rollout_resumed",
        )

    def pause(self, workspace_id: str, card_id: str, field_path: str = "",
              *, node_id: Optional[str] = None) -> UIState:
        e = self._entry(workspace_id, card_id)
        total = int(e.get("total") or 0)
        idx = int(e.get("signal_index") or 0)
        fp = field_path or e.get("field_path", "") or ""
        self._ui.set_signal_stream(
            workspace_id, card_id, total=total, signal_index=idx,
            signal_id=e.get("signal_id"), paused=True, field_path=fp,
        )
        return self._ui.set_rollout_state(
            workspace_id, card_id=card_id, field_path=fp, paused=True,
            signal_index=idx, signal_total=total, node_id=node_id,
            kind="rollout_paused",
        )

    def step(self, workspace_id: str, card_id: str, field_path: str = "") -> UIState:
        # One advance, then re-pause (§2.2 "step is one advance then re-pause").
        # Route through self.advance so the §3.3 sample-boundary diff is logged.
        self.advance(workspace_id, card_id, field_path, step=1)
        return self.pause(workspace_id, card_id, field_path)

    def reset(self, workspace_id: str, card_id: str, field_path: str = "") -> UIState:
        e = self._entry(workspace_id, card_id)
        total = int(e.get("total") or 0)
        fp = field_path or e.get("field_path", "") or ""
        self._ui.set_signal_stream(
            workspace_id, card_id, total=total, signal_index=0,
            signal_id=e.get("signal_id"), paused=True, field_path=fp,
        )
        return self._ui.set_rollout_state(
            workspace_id, card_id=card_id, field_path=fp, paused=True,
            signal_index=0, signal_total=total, kind="rollout",
        )

    def advance(self, workspace_id: str, card_id: str, field_path: str = "",
                *, step: int = 1, ordered: Optional[list] = None) -> UIState:
        e = self._entry(workspace_id, card_id)
        prior_idx = int(e.get("signal_index") or 0)
        total = int(e.get("total") or 0)
        fp = field_path or e.get("field_path", "") or ""
        # STEP-01 / D10 — thread the optional ordered sampled-chunk list
        # through to advance_signal, which re-resolves signal_id at the new
        # index (either from THIS call's ordered, or the list already
        # stored on the entry by a prior set_signal_stream registration).
        snap = self._ui.advance_signal(
            workspace_id, card_id, step=int(step), field_path=field_path,
            ordered=ordered)
        new_e = (snap.signal_stream or {}).get(card_id) or {}
        # NOTE: index 0 is a legitimate cursor position (the modulo wrap
        # lands there) — `or prior_idx` would swallow it and report a
        # phantom "no move", skipping the boundary log + §R.7 re-fire.
        _raw_idx = new_e.get("signal_index")
        new_idx = prior_idx if _raw_idx is None else int(_raw_idx)
        # §3.3 — record the sample boundary as an EvolutionLog diff so a
        # rollback restores the iteration index together with the data state
        # (the reverse re-seats signal_stream — see EvolutionLog._apply_reverse
        # "rollout:" branch). Best-effort: a logging hiccup never blocks the
        # advance itself.
        try:
            from backend.services.evolution_log import get_evolution_log
            get_evolution_log().log(
                workspace_id=workspace_id,
                actor="rollout",
                target=f"rollout:{card_id}::{fp}",
                kind="sample_boundary",
                before={"signal_index": prior_idx, "signal_total": total},
                after={"signal_index": new_idx, "signal_total": total},
            )
        except Exception:
            pass
        # §R.7 / §4.6.1 — "the cascade re-fires PER VISIBLE SIGNAL, not once
        # for the whole iterable": when the cursor actually moved, recompile
        # the iterable card's transitive {ref}-consumers so the dialectic
        # graph-panel renderings track the new sample (dynamic signal
        # rendering over iteration). The bounded BFS in concept_lifecycle is
        # cycle-safe + depth-capped; renderings settle through the lifecycle
        # (whose actor guard prevents re-entry). Best-effort — a compile
        # hiccup never blocks the advance.
        if new_idx != prior_idx:
            try:
                from backend.services.concept_lifecycle import (
                    _cascade_recompile_consumers,
                )
                ge = self._ge
                if ge is None:
                    from backend.services.graph_editor import get_default_graph_editor
                    ge = get_default_graph_editor()
                node = ge.get_concept(card_id) if ge is not None else None
                if node is not None:
                    _cascade_recompile_consumers(node, ge, push_fn=self._broadcast)
            except Exception:
                pass
        return snap


_SINGLETON: Optional[RolloutCoordinator] = None


def get_rollout_coordinator(broadcast=None) -> RolloutCoordinator:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = RolloutCoordinator(broadcast=broadcast)
    return _SINGLETON
