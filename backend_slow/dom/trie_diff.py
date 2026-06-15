"""
trie_diff.py — Structural diff between two persistent Patricia trie versions.

Two kinds of diffs:
  * :class:`TrieDiff` — cheap, per-pattern: added / removed / changed /
    stable patterns by generalized xpath. The Merkle ``subtree_hash`` lets
    us report "subtree stable" without walking every descendant.
  * Summary numbers on ``TrieDiff`` — pattern_count and content deltas,
    useful as SLM signal ("this page gained 3 new card patterns since
    last scan").

We deliberately compare by generalized *pattern string*, not by
``pattern_id`` — IDs are version-scoped so they never match across
versions. Patterns are the stable identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.dom.trie_persistence import BuiltTrie, PatternRow


@dataclass
class PatternChange:
    """A pattern that exists in both versions but whose properties changed."""

    pattern: str
    old: PatternRow
    new: PatternRow
    tag_set_changed: bool
    commutation_changed: bool
    subtree_changed: bool

    @property
    def is_structural(self) -> bool:
        """True iff anything downstream changed (tag, commutation, or subtree)."""
        return self.tag_set_changed or self.commutation_changed or self.subtree_changed


@dataclass
class TrieDiff:
    """The result of comparing two trie versions."""

    old_version_id: str
    new_version_id: str

    added_patterns: List[PatternRow] = field(default_factory=list)
    removed_patterns: List[PatternRow] = field(default_factory=list)
    changed_patterns: List[PatternChange] = field(default_factory=list)
    stable_count: int = 0

    def summary(self) -> Dict[str, int]:
        """Compact counts for logging or SLM signal."""
        return {
            "added": len(self.added_patterns),
            "removed": len(self.removed_patterns),
            "changed": len(self.changed_patterns),
            "stable": self.stable_count,
            "tag_changes": sum(1 for c in self.changed_patterns if c.tag_set_changed),
            "commutation_changes": sum(
                1 for c in self.changed_patterns if c.commutation_changed
            ),
            "subtree_changes": sum(1 for c in self.changed_patterns if c.subtree_changed),
        }

    def is_identical(self) -> bool:
        """Fastest possible answer: are the root hashes equal?"""
        return (
            not self.added_patterns
            and not self.removed_patterns
            and not self.changed_patterns
        )


def diff_tries(old: Optional[BuiltTrie], new: BuiltTrie) -> TrieDiff:
    """
    Compute the structural delta from ``old`` -> ``new``.

    If ``old`` is None, the diff treats every pattern in ``new`` as added.
    """
    diff = TrieDiff(
        old_version_id=(old.version.version_id if old else ""),
        new_version_id=new.version.version_id,
    )

    if old is None:
        diff.added_patterns = list(new.patterns)
        return diff

    # Fast path: identical root hashes => no changes.
    if old.version.root_hash == new.version.root_hash:
        diff.stable_count = len(new.patterns)
        return diff

    old_by_key = old.by_pattern_key
    new_by_key = new.by_pattern_key

    # Additions & changes: iterate new.
    for pat, nrow in new_by_key.items():
        orow = old_by_key.get(pat)
        if orow is None:
            diff.added_patterns.append(nrow)
            continue

        # Stable fast-path by subtree hash.
        if orow.subtree_hash == nrow.subtree_hash:
            diff.stable_count += 1
            continue

        tag_changed = sorted(orow.tag_set) != sorted(nrow.tag_set)
        comm_changed = orow.commutation_count != nrow.commutation_count
        sub_changed = orow.subtree_hash != nrow.subtree_hash

        if tag_changed or comm_changed or sub_changed:
            diff.changed_patterns.append(
                PatternChange(
                    pattern=pat,
                    old=orow,
                    new=nrow,
                    tag_set_changed=tag_changed,
                    commutation_changed=comm_changed,
                    subtree_changed=sub_changed,
                )
            )
        else:
            diff.stable_count += 1

    # Removals: iterate old, keep those missing from new.
    for pat, orow in old_by_key.items():
        if pat not in new_by_key:
            diff.removed_patterns.append(orow)

    return diff
