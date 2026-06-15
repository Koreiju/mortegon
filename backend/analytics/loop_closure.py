"""
Phase 7 — Cross-page loop closure (section 7 + 22).

Detects structural patterns that repeat across different URLs/snapshots.
Uses Patricia tree hashes and WL hashes to find cross-page matches,
enabling the GUI to render cross-graph edges.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)

# Module-level singleton
_pattern_registry: Optional['PatternRegistry'] = None


def get_pattern_registry() -> 'PatternRegistry':
    """Return the global PatternRegistry singleton (created on first call)."""
    global _pattern_registry
    if _pattern_registry is None:
        _pattern_registry = PatternRegistry()
    return _pattern_registry


@dataclass
class StructuralPattern:
    """A reusable structural pattern found across pages."""
    pattern_id: str
    wl_hash: int
    signature: str  # e.g., "div>ul>li*3" canonical form
    occurrences: List[Dict] = field(default_factory=list)
    # Each occurrence: {"url": str, "snapshot_id": str, "xpath": str, "subtree_size": int}


class PatternRegistry:
    """
    Stores structural patterns across snapshots and detects cross-URL matches.

    Used for loop closure: when two different URLs share the same structural
    pattern, a cross-graph edge can be rendered in the 3D GUI.
    """

    def __init__(self):
        # wl_hash -> list of (url, snapshot_id, xpath, subtree_size)
        self._hash_index: Dict[int, List[Dict]] = defaultdict(list)
        # signature -> StructuralPattern
        self._patterns: Dict[str, StructuralPattern] = {}
        self._pattern_counter = 0

    def register_snapshot(
        self,
        url: str,
        snapshot_id: str,
        node_hashes: Dict[str, int],
        node_signatures: Optional[Dict[str, str]] = None,
        subtree_sizes: Optional[Dict[str, int]] = None,
    ) -> int:
        """
        Register all node hashes from a snapshot.
        Returns the number of cross-page matches found.
        """
        cross_matches = 0
        sigs = node_signatures or {}
        sizes = subtree_sizes or {}

        for xpath, wl_hash in node_hashes.items():
            occurrence = {
                "url": url,
                "snapshot_id": snapshot_id,
                "xpath": xpath,
                "subtree_size": sizes.get(xpath, 0),
            }

            existing = self._hash_index[wl_hash]

            # Check for cross-URL matches before adding
            for prev in existing:
                if prev["url"] != url:
                    cross_matches += 1

            existing.append(occurrence)

            # Track pattern if signature available
            sig = sigs.get(xpath, str(wl_hash))
            if sig not in self._patterns:
                self._pattern_counter += 1
                self._patterns[sig] = StructuralPattern(
                    pattern_id=f"pattern_{self._pattern_counter}",
                    wl_hash=wl_hash,
                    signature=sig,
                )
            self._patterns[sig].occurrences.append(occurrence)

        return cross_matches

    def find_cross_page_matches(self, min_subtree_size: int = 3) -> List[Dict]:
        """
        Find all structural patterns that appear on multiple URLs.

        Returns list of match groups:
        [{"pattern_id", "wl_hash", "signature", "urls": [...], "occurrences": [...]}]
        """
        matches = []

        for wl_hash, occurrences in self._hash_index.items():
            # Filter by minimum subtree size
            filtered = [
                o for o in occurrences
                if o["subtree_size"] >= min_subtree_size
            ]

            urls = set(o["url"] for o in filtered)
            if len(urls) < 2:
                continue

            matches.append({
                "wl_hash": wl_hash,
                "urls": list(urls),
                "occurrences": filtered,
                "count": len(filtered),
            })

        # Sort by number of occurrences (most shared patterns first)
        matches.sort(key=lambda m: m["count"], reverse=True)
        return matches

    def get_cross_edges(self, min_subtree_size: int = 3) -> List[Tuple[Dict, Dict]]:
        """
        Generate pairs of (source, target) nodes for cross-graph edge rendering.
        Each pair connects structurally identical nodes on different URLs.
        """
        edges = []

        for wl_hash, occurrences in self._hash_index.items():
            filtered = [
                o for o in occurrences
                if o["subtree_size"] >= min_subtree_size
            ]

            # Group by URL
            by_url: Dict[str, List[Dict]] = defaultdict(list)
            for o in filtered:
                by_url[o["url"]].append(o)

            urls = list(by_url.keys())
            if len(urls) < 2:
                continue

            # Create edges between first occurrence on each pair of URLs
            for i in range(len(urls)):
                for j in range(i + 1, len(urls)):
                    src = by_url[urls[i]][0]
                    tgt = by_url[urls[j]][0]
                    edges.append((src, tgt))

        return edges

    def get_pattern_stats(self) -> Dict:
        """Return summary statistics about registered patterns."""
        all_urls: Set[str] = set()
        total_occurrences = 0

        for occurrences in self._hash_index.values():
            total_occurrences += len(occurrences)
            for o in occurrences:
                all_urls.add(o["url"])

        cross_matches = self.find_cross_page_matches()

        return {
            "total_patterns": len(self._hash_index),
            "total_occurrences": total_occurrences,
            "urls_registered": len(all_urls),
            "cross_page_patterns": len(cross_matches),
        }
