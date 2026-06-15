"""
chunk_absorber.py — Continuous-streaming chunk dedup / merge layer.

Lives strictly DOWNSTREAM of the scanner + distiller. The scanner emits
``(master_tree, added_nodes)`` per scroll iteration; the mapper turns
each iteration into chunks; this absorber decides what to PUSH to the
frontend so the user sees results immediately and progressive scrolls
that grow earlier chunks (e.g. a 12-card grid → 24 cards) replace the
incomplete versions instead of duplicating them.

Why this lives in the mapping process, not the scanner:
* The scanner is structural — it doesn't know what a "chunk" is.
* The distiller is a pure function — given an HTML it returns a
  ContentTree. It also doesn't reason about "earlier" vs. "later"
  chunks.
* Absorption is a SEMANTIC operation (chunk pattern + member-set
  comparison). It belongs next to ``ChunkBuilder`` / ``chunk_render``
  where chunk identity / representativeness is defined.

Contract:
    absorber = ChunkAbsorber()
    for iteration_chunks, iteration_instances in pipeline_iterations:
        events = absorber.absorb(iteration_chunks, iteration_instances)
        for ev in events:
            ev.kind in {"chunk_added", "chunk_replaced", "chunk_unchanged"}
            ev.chunk    -> Chunk           (the latest version)
            ev.instances -> List[render]   (instances tied to that chunk)
            ev.replaced -> Optional[str]   (chunk_id of superseded chunk)

A chunk's identity is its **pattern_xpath** — the generalized xpath
that defines what kind of subtree it represents. When two chunks
share a pattern, the one with the LARGER member set wins; ties go to
the most-recent. This handles:

* Infinite-scroll lists where iter N has 12 cards and iter N+1 has 24.
  → Iter N emits ``chunk_added`` with 12 members; iter N+1 emits
    ``chunk_replaced`` referencing iter N's chunk_id with 24 members.

* Hydration that re-renders the same node set.
  → Member set unchanged → ``chunk_unchanged`` (no event pushed
    downstream by default; callers can suppress).

* Genuinely new patterns appearing later (e.g. a footer revealed on
  scroll). → ``chunk_added`` only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AbsorbEvent:
    """One absorber decision per chunk in the input batch."""

    kind: str                    # "chunk_added" | "chunk_replaced" | "chunk_unchanged"
    chunk: object                # the latest Chunk dataclass (kept loose so we don't import cycles)
    instances: List[object]      # ChunkInstanceRender list bound to this chunk_id
    replaced_chunk_id: Optional[str] = None
    # For UI / stream payloads; the absorber doesn't enforce shape.
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
        # chunk_id -> {member_xpath, ...}  (used for superset comparison)
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
            out.extend(self._instances_by_chunk_id.get(cid, ()))
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
                # New pattern.
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

            # Same chunk_id (rare — chunk_id is content-hashed) AND same
            # member set ⇒ truly idempotent.
            if existing_id == chunk_id and members == existing_members:
                events.append(AbsorbEvent(
                    kind="chunk_unchanged",
                    chunk=self._chunks_by_id[existing_id],
                    instances=self._instances_by_chunk_id.get(existing_id, []),
                ))
                continue

            # Decide who wins. Strict superset → new replaces old.
            # Equal sets but different chunk_id (re-rendered with more
            # text or attribute changes) → new replaces old too. Pure
            # shrinkage (member set lost entries) → keep the old; new
            # pass simply isn't seeing those rows yet (e.g. virtualized
            # list mid-recycle).
            if members >= existing_members and members != existing_members:
                kind = "chunk_replaced"
            elif members == existing_members:
                kind = "chunk_replaced"  # content drift; new wins for freshness
            elif existing_members > members:
                # Old still has more rows — shrinkage. Keep it.
                events.append(AbsorbEvent(
                    kind="chunk_unchanged",
                    chunk=self._chunks_by_id[existing_id],
                    instances=self._instances_by_chunk_id.get(existing_id, []),
                ))
                continue
            else:
                # Disjoint sets despite shared pattern — unusual; treat
                # as a new sibling chunk so nothing gets dropped. We
                # bind it under a synthetic pattern key so the absorber
                # still tracks both.
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
                continue

            # Replacement path
            old_chunk = self._chunks_by_id.pop(existing_id, None)
            self._members_by_chunk_id.pop(existing_id, None)
            self._instances_by_chunk_id.pop(existing_id, None)
            self._pattern_to_chunk_id[pattern] = chunk_id
            self._chunks_by_id[chunk_id] = ch
            self._members_by_chunk_id[chunk_id] = members
            self._instances_by_chunk_id[chunk_id] = inst_by_cid.get(chunk_id, [])
            events.append(AbsorbEvent(
                kind=kind,
                chunk=ch,
                instances=self._instances_by_chunk_id[chunk_id],
                replaced_chunk_id=existing_id,
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
