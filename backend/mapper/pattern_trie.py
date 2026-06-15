"""
pattern_trie.py — Patricia trie for generalized chunk patterns.

The spec's "chunk pattern containment ledger" is a Patricia trie whose
edges are generalized xpath segments (e.g. ``app-root``, ``ytd-rich-grid-
renderer``, ``article``) and whose leaf nodes carry the *instance set*
of every chunk that materialised at that pattern path. Optionally, the
leaf node also carries an *attribute tag* (e.g. ``@href``, ``@src``,
``text()``) so two siblings that share the same xpath skeleton but
extract different field types remain distinct.

Why a Patricia trie and not a flat ``Dict[pattern, list[chunk_id]]``?

  1. Up-recursion (the spec's "iteratively recurse upwards"): when
     re-walking from a mutated leaf, we want to know which ancestor
     prefix already has *some* chunk family attached. The trie answers
     that in O(depth) without scanning every pattern.

  2. Down-recursion (the spec's "downwards recursion on mutated parent
     containers"): when a parent subtree mutates we want to find every
     pattern under it. The trie's subtree-iteration answers that in
     O(descendants) without filtering the whole pattern dict.

  3. ``×N instances`` rollup at every internal node: the trie keeps
     a running count of chunk instances under each prefix, so the
     audit can render ``ytd-app/.../ytd-rich-grid-renderer (×217)``
     above the per-card ``…/ytd-rich-item-renderer (×43)`` rows. The
     previous flat counter only knew about leaf totals.

  4. Forward-truncated display: when the user wants the last 3 path
     steps + attr tag (the spec's "great-grandparents" cap), the
     trie lets us produce that view without re-parsing the source
     pattern string each time.

Threading: this trie is owned by the mapper and is mutated only from
the scanner-callback path (single Python thread). No locks needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple


# A path segment is the tag-name fragment between two slashes in a
# generalized xpath. Index suffixes (``[3]``) are kept for region-
# anchored segments and stripped below the anchor — that decision is
# made upstream in the JS engine's ``generalizedXpath``; this trie just
# splits on '/'.
_SEG_RE = re.compile(r"/")


def _split_pattern(pattern: str) -> List[str]:
    """Split a generalized xpath into segments, dropping empty parts."""
    return [seg for seg in pattern.split("/") if seg]


def forward_truncate(pattern: str, last_n: int = 3, attr_tag: str = "") -> str:
    """Return the *trailing* ``last_n`` segments of ``pattern`` plus an
    optional attribute tag, in the spec's "great-grandparents" form.

        /html/body/main/section/article/h2  + @href  →  section/article/h2/@href

    The leading ellipsis is omitted when the source pattern is already
    short enough.
    """
    segs = _split_pattern(pattern)
    tail = segs[-last_n:] if len(segs) > last_n else segs
    out = "/".join(tail)
    if attr_tag:
        if not attr_tag.startswith("/") and not attr_tag.startswith("@") and not attr_tag.startswith("."):
            attr_tag = "/" + attr_tag
        out = out + attr_tag
    if len(segs) > last_n:
        out = "…/" + out
    return out


@dataclass
class _TrieNode:
    """One node in the Patricia trie.

    ``segment`` is the *edge label* leading INTO this node (root has "").
    For Patricia compression we collapse single-child chains into a
    single multi-segment edge label — the segment string then contains
    "/" internally. Splitting is unambiguous because xpath segments
    themselves cannot contain "/".
    """

    segment: str = ""
    children: Dict[str, "_TrieNode"] = field(default_factory=dict)
    # chunk_ids of instances that end exactly at this node. Multiple
    # chunks may share a leaf (sibling cards on a grid) — that's the
    # ×N instances rollup point.
    instances: Set[str] = field(default_factory=set)
    # Subtree instance count (sum of self + every descendant's
    # ``len(instances)``). Kept incrementally so audit rendering is O(1).
    subtree_size: int = 0
    # Generalized attribute tags collected at this node — e.g. ``@href``,
    # ``@src``, ``text()``. Only meaningful at leaves; intermediate
    # nodes may still see them when a parent pattern itself is content-
    # bearing (e.g. an <a> with both an @href and direct text).
    attr_tags: Set[str] = field(default_factory=set)


class PatternTrie:
    """Patricia trie over generalized xpath patterns.

    Public surface:

      * ``add(pattern, chunk_id, attr_tags=None)`` — register an instance.
      * ``remove(pattern, chunk_id)`` — unregister an instance.
      * ``instance_count(pattern)`` — # chunks at exactly this pattern.
      * ``subtree_count(pattern)`` — # chunks under this prefix.
      * ``forward_pattern(pattern, attr_tag="")`` — short display form.
      * ``iter_summaries()`` — yields ``(pattern, instances_at_node,
        subtree_size, attr_tags)`` for every node that owns chunks,
        sorted by subtree_size desc. Used by audit + query rendering.
    """

    def __init__(self, *, truncate_last_n: int = 3) -> None:
        self.root = _TrieNode()
        self._truncate_last_n = truncate_last_n
        # chunk_id → (pattern, attr_tag) so removes are O(1) without
        # re-walking the trie.
        self._chunk_index: Dict[str, Tuple[str, str]] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def add(
        self,
        pattern: str,
        chunk_id: str,
        attr_tags: Optional[Iterable[str]] = None,
    ) -> None:
        if not pattern or not chunk_id:
            return
        # Remove any prior registration for this chunk_id so re-emits
        # don't double-count.
        prev = self._chunk_index.get(chunk_id)
        if prev is not None:
            self.remove(chunk_id_or_pattern=chunk_id)

        node = self._walk_or_create(pattern)
        node.instances.add(chunk_id)
        if attr_tags:
            for t in attr_tags:
                if t:
                    node.attr_tags.add(t)
        # Bump subtree counters back to root.
        self._bump_subtree(pattern, +1)
        self._chunk_index[chunk_id] = (pattern, "")

    def remove(self, chunk_id_or_pattern: str, chunk_id: Optional[str] = None) -> bool:
        """Remove an instance. Call as ``remove(chunk_id)`` (O(1) via
        the chunk_index) or ``remove(pattern, chunk_id)`` (still O(1)
        but explicit). Returns True if a chunk was actually removed."""
        if chunk_id is None:
            # Single-arg form: chunk_id only.
            cid = chunk_id_or_pattern
            prev = self._chunk_index.pop(cid, None)
            if prev is None:
                return False
            pattern, _ = prev
        else:
            pattern = chunk_id_or_pattern
            cid = chunk_id
            self._chunk_index.pop(cid, None)

        node = self._walk(pattern)
        if node is None or cid not in node.instances:
            return False
        node.instances.discard(cid)
        self._bump_subtree(pattern, -1)
        return True

    def clear(self) -> None:
        self.root = _TrieNode()
        self._chunk_index.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def instance_count(self, pattern: str) -> int:
        n = self._walk(pattern)
        return len(n.instances) if n else 0

    def subtree_count(self, pattern: str) -> int:
        n = self._walk(pattern)
        return n.subtree_size if n else 0

    def forward_pattern(self, pattern: str, attr_tag: str = "") -> str:
        """Trailing-N path segments + attribute tag, audit-display ready."""
        return forward_truncate(pattern, self._truncate_last_n, attr_tag)

    def iter_summaries(self) -> Iterator[Tuple[str, int, int, List[str]]]:
        """Yield (full_pattern, instances_here, subtree_size, attr_tags)
        for every node that carries at least one instance, sorted by
        subtree_size descending."""
        rows: List[Tuple[str, int, int, List[str]]] = []
        stack: List[Tuple[List[str], _TrieNode]] = [([], self.root)]
        while stack:
            path, node = stack.pop()
            if node.instances:
                full = "/" + "/".join(path) if path else "/"
                rows.append((
                    full,
                    len(node.instances),
                    node.subtree_size,
                    sorted(node.attr_tags),
                ))
            for seg, child in node.children.items():
                stack.append((path + seg.split("/"), child))
        rows.sort(key=lambda r: (-r[2], r[0]))
        return iter(rows)

    def stats(self) -> Dict[str, int]:
        """Quick summary: # patterns, # instances, max subtree size."""
        n_patterns = 0
        n_instances = 0
        max_sub = 0
        for full, here, sub, _tags in self.iter_summaries():
            n_patterns += 1
            n_instances += here
            if sub > max_sub:
                max_sub = sub
        return {
            "patterns": n_patterns,
            "instances": n_instances,
            "max_subtree": max_sub,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _walk(self, pattern: str) -> Optional[_TrieNode]:
        segs = _split_pattern(pattern)
        node = self.root
        for seg in segs:
            child = node.children.get(seg)
            if child is None:
                # Fall back to Patricia-style edge-label match: child
                # may be a multi-segment compressed edge. Find one whose
                # first segment matches and whose internal segments
                # continue our pattern.
                matched = False
                for edge, c in node.children.items():
                    if edge == seg or edge.startswith(seg + "/"):
                        # Edge is longer than our remaining; can't fully
                        # consume — treat as miss.
                        if edge != seg:
                            return None
                        node = c
                        matched = True
                        break
                if not matched:
                    return None
            else:
                node = child
        return node

    def _walk_or_create(self, pattern: str) -> _TrieNode:
        segs = _split_pattern(pattern)
        node = self.root
        for seg in segs:
            child = node.children.get(seg)
            if child is None:
                child = _TrieNode(segment=seg)
                node.children[seg] = child
            node = child
        return node

    def _bump_subtree(self, pattern: str, delta: int) -> None:
        # Walk from root to the pattern and increment subtree_size on
        # every node we pass through (including root and the leaf).
        segs = _split_pattern(pattern)
        self.root.subtree_size += delta
        node = self.root
        for seg in segs:
            child = node.children.get(seg)
            if child is None:
                return
            child.subtree_size += delta
            node = child
