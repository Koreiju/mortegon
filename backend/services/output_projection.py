"""Live Output Projection (Workstream W7; domain anchor §8D.19,
§8D.41, §9.12).

Implements the rule that **peripheral** concept-graph outputs project
into the 3D scene as new chunks:

  * A concept node is **peripheral** if it has no upstream wires OR
    no downstream wires (§8D.41).
  * Peripheral nodes whose ``rendering`` payload is text-like are
    TF-IDF-indexed and broadcast as part of the workspace's
    ``umap_canonical`` frame, with provenance ``graph-output`` or
    ``agent-output`` per §9.12.
  * Intermediate concept nodes (both upstream and downstream wires
    present) stay symbolic — never projected to 3D.

The service runs on a ~800ms debounce per workspace (§8D.19) so
rapid graph edits don't churn the projector.

Integration: ``/api/concepts`` PATCH/POST handlers call
``OutputProjectionService.schedule_recompute(workspace_id)`` after a
settled cascade. The debounced worker computes the peripheral set,
upserts text-like rendered_value into the TF-IDF index, then triggers
``LayoutService.recompute_and_broadcast`` to fold the new chunks into
the next ``umap_canonical`` frame.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_PROJECTION_DEBOUNCE = 0.8  # seconds (§8D.19)


@dataclass
class PendingProjection:
    """One workspace's pending output-projection state."""

    workspace_id: str = ""
    debounce_until: float = 0.0
    timer: Optional[threading.Timer] = None
    last_committed: Set[str] = field(default_factory=set)


class OutputProjectionService:
    """Debounced peripheral-output projection orchestrator.

    Construct once; share. ``schedule_recompute(workspace_id)`` arms
    a debounce timer; on fire, the worker:

      1. Lists concept nodes for the workspace.
      2. Builds the in/out wiring map.
      3. Identifies peripheral concept nodes (no upstream OR no
         downstream).
      4. For each peripheral with a text-like ``rendering`` field,
         upserts a (graph_id, concept_id, sample_id=0) chunk into
         the workspace's TF-IDF store, tagged with provenance
         ``graph-output`` (or ``agent-output`` if the node's
         provenance matches).
      5. Triggers the Layout Service to refit + broadcast.
      6. Records ``last_committed`` ids and removes any that are
         no longer peripheral (so retired outputs drop from 3D).
    """

    def __init__(
        self,
        broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
        graph_editor: Optional[Any] = None,
        layout_service: Optional[Any] = None,
        debounce_seconds: float = DEFAULT_PROJECTION_DEBOUNCE,
    ):
        self._broadcast = broadcast
        self._graph_editor = graph_editor
        self._layout_service = layout_service
        self._debounce = float(debounce_seconds)
        self._pending: Dict[str, PendingProjection] = {}
        self._lock = threading.Lock()

    def schedule_recompute(self, workspace_id: str = "") -> None:
        """Arm a debounce timer for this workspace's peripheral projection.

        Repeated calls within the debounce window restart the timer —
        only the last call's deadline survives, so a flurry of edits
        coalesces into one projection pass.
        """
        with self._lock:
            pending = self._pending.get(workspace_id)
            if pending is None:
                pending = PendingProjection(workspace_id=workspace_id)
                self._pending[workspace_id] = pending
            if pending.timer is not None:
                try:
                    pending.timer.cancel()
                except Exception:
                    pass
            pending.debounce_until = time.time() + self._debounce
            pending.timer = threading.Timer(
                self._debounce,
                self._fire_recompute,
                args=(workspace_id,),
            )
            pending.timer.daemon = True
            pending.timer.start()

    def _fire_recompute(self, workspace_id: str) -> None:
        """Debounce expired — compute and broadcast (worker thread)."""
        try:
            self.recompute_now(workspace_id)
        except Exception as e:
            logger.warning("OutputProjection recompute failed for ws=%r: %s",
                           workspace_id, e)

    def recompute_now(self, workspace_id: str = "") -> Dict[str, Any]:
        """Synchronous projection recompute. Returns a summary dict."""
        if self._graph_editor is None:
            return {"status": "skipped", "reason": "no graph_editor"}
        # Snapshot concept nodes + edges in the workspace.
        try:
            nodes = self._graph_editor.list_concepts(workspace_id=workspace_id, limit=50000)
            edges = self._graph_editor.list_concept_edges(workspace_id=workspace_id, limit=200000)
        except Exception as e:
            return {"status": "error", "detail": str(e)}

        if not nodes:
            return {"status": "skipped", "reason": "no concept nodes"}

        # Build in/out adjacency.
        in_count: Dict[str, int] = {n.concept_id: 0 for n in nodes}
        out_count: Dict[str, int] = {n.concept_id: 0 for n in nodes}
        for e in edges:
            if e.source_id in out_count:
                out_count[e.source_id] += 1
            if e.target_id in in_count:
                in_count[e.target_id] += 1

        # Identify peripheral nodes (no upstream OR no downstream wires).
        peripherals: List[Any] = []
        for n in nodes:
            cid = n.concept_id
            is_peripheral = (in_count[cid] == 0) or (out_count[cid] == 0)
            if not is_peripheral:
                continue
            # Must have text-like rendering content.
            if not n.rendering or not isinstance(n.rendering, str):
                continue
            if len(n.rendering.strip()) < 4:
                continue
            peripherals.append(n)

        # Determine provenance flags per §9.12. ConceptNode.provenance
        # already carries one of: user-authored | agent-authored |
        # derived-from-chunk | committed-subgraph. Map to projection
        # provenance:
        #   agent-authored          → agent-output
        #   everything else         → graph-output
        # (scanner-emitted chunks are not concept nodes; they project
        # natively from the scanner pathway.)
        from backend.api.ws_frames import Provenance

        def _chunk_key_for(concept_id: str) -> str:
            """Composite id used by the Layout Service + TF-IDF store
            (W7 / §8D.19 — ``graph__<wid>__<cid>__<sid>``). Must match
            the form ``umap_canonical.coords`` keys take so retirement
            removed_ids align with what the 3D scene actually keys on.
            """
            return f"graph__{workspace_id or '_default'}__{concept_id}__0"

        peripheral_chunk_ids: Set[str] = set()
        for n in peripherals:
            peripheral_chunk_ids.add(_chunk_key_for(n.concept_id))

        # Upsert text-like peripheral renderings into the workspace's
        # TF-IDF store. The store is the empirical chunk corpus
        # (§8D.35); graph-output chunks live there alongside
        # scanner-emitted ones.
        added = 0
        try:
            from backend.services.global_tfidf_store import get_default_store
            store = get_default_store()
            for n in peripherals:
                chunk_key = _chunk_key_for(n.concept_id)
                meta = {
                    "url": "",
                    "page_url": "",
                    "concept_id": n.concept_id,
                    "workspace_id": workspace_id or "",
                    "provenance": (
                        Provenance.AGENT_OUTPUT
                        if (n.provenance == "agent-authored") else
                        Provenance.GRAPH_OUTPUT
                    ),
                }
                # Try the store's documented add path; fall back if
                # the API signature is different.
                try:
                    if hasattr(store, "add_chunk"):
                        store.add_chunk(chunk_key, n.rendering, meta=meta)
                        added += 1
                    elif hasattr(store, "add_chunks"):
                        store.add_chunks([{
                            "chunk_id": chunk_key,
                            "text": n.rendering,
                            "meta": meta,
                        }])
                        added += 1
                except Exception:
                    pass
        except Exception:
            pass

        # Compute retired chunk keys (previously projected but no longer
        # peripheral). The Layout Service's next ``umap_canonical``
        # frame carries these in ``removed_ids`` so the 3D scene drops
        # them. ``last_committed`` is in the **chunk_key** space, not
        # concept_id, because that's the id space the projector keys on.
        with self._lock:
            pending = self._pending.setdefault(
                workspace_id, PendingProjection(workspace_id=workspace_id),
            )
            retired = pending.last_committed - peripheral_chunk_ids
            pending.last_committed = set(peripheral_chunk_ids)
            # Tell the TF-IDF store to drop retired chunks so the
            # corpus stays trimmed to currently-projected outputs
            # (otherwise stale renderings linger in the embedding
            # index and skew retrieval).
            if retired:
                try:
                    from backend.services.global_tfidf_store import get_default_store
                    store = get_default_store()
                    if hasattr(store, "remove_chunk"):
                        for cid in retired:
                            try:
                                store.remove_chunk(cid)
                            except Exception:
                                pass
                    elif hasattr(store, "remove_chunks"):
                        try:
                            store.remove_chunks(list(retired))
                        except Exception:
                            pass
                except Exception:
                    pass

        # Trigger the Layout Service to refit + broadcast.
        if self._layout_service is not None:
            try:
                frame = self._layout_service.recompute(
                    workspace_id=workspace_id, min_docs=2,
                )
                if frame is not None and self._broadcast is not None:
                    from backend.api.ws_frames import build_umap_canonical
                    payload = build_umap_canonical(
                        workspace_id=frame.workspace_id or "_default",
                        coords=frame.coords,
                        url_roots=frame.url_roots,
                        provenance=frame.provenance,
                        removed_ids=list(retired) if retired else None,
                    )
                    self._broadcast(0, payload)
            except Exception as e:
                logger.warning("OutputProjection layout broadcast failed: %s", e)

        return {
            "status": "ok",
            "peripheral_count": len(peripherals),
            "added": added,
            "retired_count": len(retired),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_SVC: Optional[OutputProjectionService] = None
_SVC_LOCK = threading.Lock()


def get_output_projection_service(
    broadcast: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    graph_editor: Optional[Any] = None,
    layout_service: Optional[Any] = None,
) -> OutputProjectionService:
    global _SVC
    with _SVC_LOCK:
        if _SVC is None:
            _SVC = OutputProjectionService(
                broadcast=broadcast,
                graph_editor=graph_editor,
                layout_service=layout_service,
            )
        else:
            if broadcast is not None and _SVC._broadcast is None:
                _SVC._broadcast = broadcast
            if graph_editor is not None and _SVC._graph_editor is None:
                _SVC._graph_editor = graph_editor
            if layout_service is not None and _SVC._layout_service is None:
                _SVC._layout_service = layout_service
    return _SVC
