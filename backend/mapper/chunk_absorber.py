"""
chunk_absorber.py — Continuous-streaming chunk dedup / merge layer.

Lives strictly DOWNSTREAM of the scanner + distiller. The scanner
(via ``scan_verified()``) emits already-settled deltas; the mapper
turns each iteration into chunks; this absorber decides what to PUSH
to the frontend so progressive scrolls that grow earlier chunks
(e.g. a 12-card grid → 24 cards) replace the incomplete versions
instead of duplicating them.

Contract:
    absorber = ChunkAbsorber()
    for iteration_chunks, iteration_instances in pipeline_iterations:
        events = absorber.absorb(iteration_chunks, iteration_instances)
        for ev in events:
            ev.kind in {"chunk_added", "chunk_replaced", "chunk_unchanged"}
            ev.chunk             -> Chunk      (the latest version)
            ev.instances         -> List[render] (instances tied to that chunk)
            ev.replaced_chunk_id -> Optional[str] (chunk_id of superseded chunk)

A chunk's identity is its **pattern_xpath** — the generalized xpath
that defines what kind of subtree it represents. When two chunks
share a pattern, the one with the LARGER member set wins:

* Infinite-scroll lists where iter N has 12 cards and iter N+1 has 24
  → Iter N emits ``chunk_added`` with 12 members; iter N+1 emits
    ``chunk_replaced`` with 24 members so the GUI can update the chunk
    in place.

* Hydration that re-renders the same node set.
  → Member set unchanged → ``chunk_unchanged`` (caller may filter out).

* Genuinely new patterns (e.g. a footer revealed on scroll).
  → ``chunk_added`` only.

History note: this module previously carried a ``STABILITY_THRESHOLD``
two-iteration verification gate that emitted a ``chunk_complete``
event after a chunk was seen identical for two consecutive iters.
That gate was made redundant by the scanner-level verified-delta gate
(``ShadowDOMScanner.scan_verified``) which provides already-settled
DOM, and was fully removed. The absorber is now a pure pattern→chunk
dedup with three event kinds; nothing downstream of this module
distinguishes ``chunk_added`` from ``chunk_replaced`` for verification
purposes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AbsorbEvent:
    """One absorber decision per chunk in the input batch.

    Event kinds:
      * ``chunk_added``     — pattern not seen before. First sighting.
      * ``chunk_replaced``  — pattern existed but its membership grew
        (strict superset). The new chunk replaces the prior version;
        ``replaced_chunk_id`` carries the prior id so consumers can
        evict it from any local state.
      * ``chunk_unchanged`` — pattern + membership identical to the
        previous iteration. Caller may filter these out from streaming;
        they exist so the absorber can announce an explicit decision
        for every input chunk rather than silently dropping it.
    """

    kind: str
    chunk: object
    instances: List[object]
    replaced_chunk_id: Optional[str] = None
    extra: Dict = field(default_factory=dict)


class ChunkAbsorber:
    """Stateful merger of progressively-emitted chunk batches.

    One absorber instance corresponds to ONE snapshot's lifetime — a
    new scan should construct a fresh absorber so cross-snapshot
    chunks don't accidentally merge.

    Thread-safety: NOT internally synchronized. The caller (mapper)
    drives iterations sequentially from one worker, so adding a lock
    would be pure overhead. If you ever fan out chunking across
    threads, wrap calls in your own mutex.
    """

    def __init__(self):
        # pattern_xpath -> currently-winning chunk_id
        self._pattern_to_chunk_id: Dict[str, str] = {}
        # chunk_id -> Chunk
        self._chunks_by_id: Dict[str, object] = {}
        # chunk_id -> frozenset of member xpaths (for superset comparison)
        self._members_by_chunk_id: Dict[str, frozenset] = {}
        # chunk_id -> list[ChunkInstanceRender]
        self._instances_by_chunk_id: Dict[str, List[object]] = {}

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def current_chunks(self) -> List[object]:
        """Return the latest-winning chunk for every tracked pattern."""
        return [self._chunks_by_id[cid] for cid in self._pattern_to_chunk_id.values()]

    def current_instances(self) -> List[object]:
        out: List[object] = []
        for cid in self._pattern_to_chunk_id.values():
            out.extend(self._instances_by_chunk_id.get(cid, []))
        return out

    # ------------------------------------------------------------------
    # Core merge
    # ------------------------------------------------------------------

    def absorb(
        self,
        chunks: Sequence[object],
        instances: Sequence[object] = (),
    ) -> List[AbsorbEvent]:
        """Fold one iteration's chunks + instances into the running state.

        Parameters
        ----------
        chunks:
            The iteration's chunks (whatever ``ChunkBuilder.build()``
            returned for the latest distilled HTML).
        instances:
            Optional matching list of ``ChunkInstanceRender`` rows so
            the absorber can also evict instance lists belonging to a
            superseded chunk_id. Pass ``[]`` if you only stream chunks.

        Returns
        -------
        list[AbsorbEvent]
            One event per input chunk. Events for chunks that were
            wholly subsumed by an existing later one are emitted with
            ``kind="chunk_unchanged"`` so the caller sees an explicit
            decision and can choose to skip pushing them.
        """
        # Bucket instances by their chunk_id once so each chunk's instance
        # list is an O(1) lookup instead of an O(N) filter per chunk.
        inst_by_cid: Dict[str, List[object]] = {}
        for inst in instances:
            cid = getattr(inst, "chunk_id", None)
            if cid is None:
                continue
            inst_by_cid.setdefault(cid, []).append(inst)

        events: List[AbsorbEvent] = []
        for ch in chunks:
            chunk_id = getattr(ch, "chunk_id", None) or getattr(ch, "id", None)
            pattern = (
                getattr(ch, "pattern_xpath", None)
                or getattr(ch, "pattern", None)
            )
            if chunk_id is None or pattern is None:
                # Without identity we can't dedup. Treat as fire-and-
                # forget add but log so a buggy emitter is visible.
                logger.warning(
                    "ChunkAbsorber: chunk lacks chunk_id or pattern — "
                    "passing through without dedup."
                )
                events.append(AbsorbEvent(
                    kind="chunk_added",
                    chunk=ch,
                    instances=inst_by_cid.get(chunk_id, []),
                ))
                continue

            members = frozenset(getattr(ch, "member_xpaths", ()) or ())
            existing_id = self._pattern_to_chunk_id.get(pattern)

            if existing_id is None:
                # New pattern — first sighting.
                self._pattern_to_chunk_id[pattern] = chunk_id
                self._chunks_by_id[chunk_id] = ch
                self._members_by_chunk_id[chunk_id] = members
                self._instances_by_chunk_id[chunk_id] = inst_by_cid.get(chunk_id, [])
                events.append(AbsorbEvent(
                    kind="chunk_added",
                    chunk=ch,
                    instances=self._instances_by_chunk_id[chunk_id],
                ))
                continue

            existing_members = self._members_by_chunk_id.get(existing_id, frozenset())

            # Same pattern + same membership ⇒ no change. Caller may
            # filter chunk_unchanged out of the streaming path.
            if members == existing_members:
                events.append(AbsorbEvent(
                    kind="chunk_unchanged",
                    chunk=self._chunks_by_id[existing_id],
                    instances=self._instances_by_chunk_id.get(existing_id, []),
                ))
                continue

            # Strict superset → membership grew (e.g. infinite-scroll
            # list expanded from 12 → 24 cards). Replace the prior
            # chunk in our state and emit chunk_replaced so the GUI /
            # persistence layer updates in place. Carry the old
            # chunk_id in ``replaced_chunk_id`` so the consumer can
            # evict it.
            if members > existing_members:
                self._chunks_by_id.pop(existing_id, None)
                self._members_by_chunk_id.pop(existing_id, None)
                self._instances_by_chunk_id.pop(existing_id, None)
                self._pattern_to_chunk_id[pattern] = chunk_id
                self._chunks_by_id[chunk_id] = ch
                self._members_by_chunk_id[chunk_id] = members
                self._instances_by_chunk_id[chunk_id] = inst_by_cid.get(chunk_id, [])
                events.append(AbsorbEvent(
                    kind="chunk_replaced",
                    chunk=ch,
                    instances=self._instances_by_chunk_id[chunk_id],
                    replaced_chunk_id=existing_id,
                ))
                continue

            # Pure shrinkage (member set lost entries) → keep the old
            # chunk. The new pass simply isn't seeing those rows yet
            # (virtualized list mid-recycle, e.g.).
            if existing_members > members:
                events.append(AbsorbEvent(
                    kind="chunk_unchanged",
                    chunk=self._chunks_by_id[existing_id],
                    instances=self._instances_by_chunk_id.get(existing_id, []),
                ))
                continue

            # Disjoint sets despite shared pattern — unusual; treat
            # as a new sibling chunk so nothing gets dropped. Bind it
            # under a synthetic pattern key so the absorber still
            # tracks both views.
            synthetic_pattern = f"{pattern}::{chunk_id}"
            self._pattern_to_chunk_id[synthetic_pattern] = chunk_id
            self._chunks_by_id[chunk_id] = ch
            self._members_by_chunk_id[chunk_id] = members
            self._instances_by_chunk_id[chunk_id] = inst_by_cid.get(chunk_id, [])
            events.append(AbsorbEvent(
                kind="chunk_added",
                chunk=ch,
                instances=self._instances_by_chunk_id[chunk_id],
            ))

        return events

    # ------------------------------------------------------------------
    # Convenience helpers for stream payload construction
    # ------------------------------------------------------------------

    @staticmethod
    def event_to_payload(event: AbsorbEvent, *, snapshot_id: str, url: str) -> Dict:
        """Render one event as a flat dict suitable for the WebSocket stream.

        Mirrors the existing ``chunks`` and ``chunk_instances`` payload
        shapes the frontend already understands but adds ``replaced``
        so the GUI can drop the superseded chunk from the projector
        before drawing the new one.
        """
        ch = event.chunk
        out: Dict = {
            "type": event.kind,  # chunk_added / chunk_replaced / chunk_unchanged
            "snapshot_id": snapshot_id,
            "url": url,
            "chunk": ch.as_dict() if hasattr(ch, "as_dict") else ch,
        }
        if event.replaced_chunk_id:
            out["replaced_chunk_id"] = event.replaced_chunk_id
        if event.instances:
            out["instances"] = [
                {
                    "chunk_id": getattr(inst, "chunk_id", None),
                    "instance_id": (
                        inst.instance_id(url) if hasattr(inst, "instance_id") else None
                    ),
                    "instance_idx": getattr(inst, "instance_idx", None),
                    "pattern": getattr(inst, "pattern", None),
                    "absolute_xpath": getattr(inst, "absolute_xpath", None),
                    "html_raw": getattr(inst, "html_raw", None),
                    "rendered_text": getattr(inst, "rendered_text", None),
                    "fields": getattr(inst, "fields", None),
                    "embedding": getattr(inst, "embedding", None),
                    "image_url": getattr(inst, "image_url", None),
                    "link_url": getattr(inst, "link_url", None),
                }
                for inst in event.instances
            ]
        return out
