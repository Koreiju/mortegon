"""
label_engine.py — Label propagation, commutation, LCA, and structure tags.

Three label tiers:
  1. Instance labels — user marks a specific xpath as relevant (non-empty label)
  2. Commuted labels — propagated to all xpaths with matching generalized pattern
  3. Structure tags — user-defined group names for collections of labeled instances

Labels are stored as separate DB entities linked to xpaths, not embedded in
the content tree. The content tree remains a pure structural document.
"""

from __future__ import annotations

import re
import json
import time
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict

from backend.database import get_connection
from backend.services.xpath_utils import generalize_xpath  # canonical location


def xpaths_match_pattern(xpath: str, pattern_xpath: str) -> bool:
    """Check if an xpath matches a generalized pattern (ignoring indices)."""
    return generalize_xpath(xpath) == generalize_xpath(pattern_xpath)


# ---------------------------------------------------------------------------
# LCA on xpath tree
# ---------------------------------------------------------------------------

def compute_lca(xpaths: List[str]) -> str:
    """
    Compute the Lowest Common Ancestor xpath for a set of xpaths.

    Works by splitting each xpath into segments and finding the longest
    common prefix across all paths.

    Example:
        ['/html/body/div[1]/ul/li[1]/a',
         '/html/body/div[1]/ul/li[2]/a']
        → '/html/body/div[1]/ul'
    """
    if not xpaths:
        return '/'
    if len(xpaths) == 1:
        # Parent of the single xpath
        parts = xpaths[0].rstrip('/').split('/')
        return '/'.join(parts[:-1]) or '/'

    # Split all xpaths into segments
    all_parts = [x.strip('/').split('/') for x in xpaths]
    min_len = min(len(p) for p in all_parts)

    common = []
    for i in range(min_len):
        segments = {p[i] for p in all_parts}
        if len(segments) == 1:
            common.append(segments.pop())
        else:
            break

    return '/' + '/'.join(common) if common else '/'


def find_lca_subtree_xpaths(content_tree: Dict[str, Any],
                             labeled_xpaths: List[str]) -> List[str]:
    """
    Given a content tree and a set of labeled xpaths, find all xpaths
    in the subtree rooted at their LCA (including the LCA itself).

    This highlights the full connecting structure between labeled nodes.
    """
    if not labeled_xpaths:
        return []

    lca = compute_lca(labeled_xpaths)
    # Collect all xpaths in the tree that are descendants of the LCA
    all_xpaths = _collect_xpaths(content_tree)
    return [x for x in all_xpaths if x.startswith(lca)]


def _collect_xpaths(tree: Dict[str, Any]) -> List[str]:
    """Recursively collect all _xpath values from a content tree."""
    xpaths = []
    for key, subtree in tree.items():
        if key.startswith('_'):
            continue
        if isinstance(subtree, dict):
            xpath = subtree.get('_xpath', key)
            xpaths.append(xpath)
            xpaths.extend(_collect_xpaths(subtree))
    return xpaths


# ---------------------------------------------------------------------------
# Label engine
# ---------------------------------------------------------------------------

class LabelEngine:
    """
    Manages labels, commutation, and structure tags in KuzuDB.

    Label lifecycle:
      1. User applies an instance label to a specific xpath
      2. Engine commutes the label to all matching generalized patterns
      3. Engine computes LCA for same-label groups
      4. User optionally assigns structure tags to group labeled subtrees
    """

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Instance labels
    # ------------------------------------------------------------------

    def apply_label(self, url: str, xpath: str, label: str,
                    snapshot_id: str = None) -> Dict[str, Any]:
        """
        Apply a user label to a specific xpath. Then commute to all
        xpaths in the same snapshot that match the generalized pattern.

        Returns:
            {'labeled': int, 'commuted': int, 'lca': str}
        """
        conn = get_connection()
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')
        pattern = generalize_xpath(xpath)

        # 1. Save the instance label
        label_id = f"{url}:{xpath}:{label}"
        try:
            conn.execute(
                "MERGE (l:NodeLabel {label_id: $lid}) "
                "SET l.url = $url, l.xpath = $xp, l.label = $lbl, "
                "    l.pattern = $pat, l.is_instance = true, "
                "    l.snapshot_id = $sid, l.created_at = $ts;",
                parameters={
                    "lid": label_id, "url": url, "xp": xpath,
                    "lbl": label, "pat": pattern, "sid": snapshot_id or '',
                    "ts": ts,
                }
            )
        except Exception as e:
            print(f"[LabelEngine] Instance label error: {e}")

        # 2. Commute: find all xpaths with same generalized pattern
        commuted = self._commute_label(url, xpath, label, pattern, snapshot_id)

        # 3. Compute LCA for this label group
        group_xpaths = self.get_xpaths_for_label(url, label)
        lca = compute_lca(group_xpaths) if group_xpaths else '/'

        return {
            'labeled': 1,
            'commuted': commuted,
            'lca': lca,
            'pattern': pattern,
        }

    def _commute_label(self, url: str, source_xpath: str, label: str,
                       pattern: str, snapshot_id: str = None) -> int:
        """
        Propagate a label to all xpaths matching the same generalized
        pattern (array-index agnostic).

        Uses the content tree to find all matching xpaths.
        """
        conn = get_connection()
        count = 0

        # Load the content tree for this url to find all xpaths
        try:
            tree_id = f"tree_{snapshot_id}" if snapshot_id else None
            query = (
                "MATCH (t:ContentTree {url: $url}) RETURN t.xpath_json LIMIT 1;"
                if not tree_id else
                "MATCH (t:ContentTree {tree_id: $tid}) RETURN t.xpath_json LIMIT 1;"
            )
            params = {"url": url} if not tree_id else {"tid": tree_id}

            res = conn.execute(query, parameters=params)
            if not res.has_next():
                return 0

            tree_json = json.loads(res.get_next()[0])
            all_xpaths = _collect_xpaths(tree_json)
        except Exception as e:
            print(f"[LabelEngine] Commute tree load error: {e}")
            return 0

        # Find matching xpaths and create commuted labels
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')
        for xp in all_xpaths:
            if xp == source_xpath:
                continue
            if generalize_xpath(xp) == pattern:
                label_id = f"{url}:{xp}:{label}"
                try:
                    conn.execute(
                        "MERGE (l:NodeLabel {label_id: $lid}) "
                        "SET l.url = $url, l.xpath = $xp, l.label = $lbl, "
                        "    l.pattern = $pat, l.is_instance = false, "
                        "    l.snapshot_id = $sid, l.created_at = $ts;",
                        parameters={
                            "lid": label_id, "url": url, "xp": xp,
                            "lbl": label, "pat": pattern,
                            "sid": snapshot_id or '', "ts": ts,
                        }
                    )
                    count += 1
                except Exception:
                    pass

        return count

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_labels_for_url(self, url: str) -> List[Dict[str, Any]]:
        """Get all labels for a URL."""
        conn = get_connection()
        results = []
        try:
            res = conn.execute(
                "MATCH (l:NodeLabel {url: $url}) "
                "RETURN l.label_id, l.xpath, l.label, l.pattern, "
                "       l.is_instance, l.snapshot_id;",
                parameters={"url": url}
            )
            while res.has_next():
                row = res.get_next()
                results.append({
                    'label_id': row[0], 'xpath': row[1],
                    'label': row[2], 'pattern': row[3],
                    'is_instance': row[4], 'snapshot_id': row[5],
                })
        except Exception:
            pass
        return results

    def get_xpaths_for_label(self, url: str, label: str) -> List[str]:
        """Get all xpaths that have a specific label for a URL."""
        conn = get_connection()
        xpaths = []
        try:
            res = conn.execute(
                "MATCH (l:NodeLabel {url: $url, label: $lbl}) "
                "RETURN l.xpath;",
                parameters={"url": url, "lbl": label}
            )
            while res.has_next():
                xpaths.append(res.get_next()[0])
        except Exception:
            pass
        return xpaths

    def get_label_for_xpath(self, url: str, xpath: str) -> Optional[str]:
        """Get the label for a specific xpath, if any."""
        conn = get_connection()
        try:
            res = conn.execute(
                "MATCH (l:NodeLabel {url: $url, xpath: $xp}) "
                "RETURN l.label LIMIT 1;",
                parameters={"url": url, "xp": xpath}
            )
            if res.has_next():
                return res.get_next()[0]
        except Exception:
            pass
        return None

    def get_lca_for_label(self, url: str, label: str) -> Dict[str, Any]:
        """Compute and return the LCA subtree for a label group."""
        xpaths = self.get_xpaths_for_label(url, label)
        lca = compute_lca(xpaths)
        return {
            'label': label,
            'lca_xpath': lca,
            'member_count': len(xpaths),
            'member_xpaths': xpaths,
        }

    # ------------------------------------------------------------------
    # Structure tags
    # ------------------------------------------------------------------

    def create_structure_tag(self, url: str, tag_name: str,
                             label_group: str,
                             description: str = '') -> str:
        """
        Create a structure tag that groups labeled instances by name.

        A structure tag represents a semantic segment of the DOM
        (e.g. 'Product Card', 'Nav Menu') identified by the user
        from a set of instance labels sharing a pattern.
        """
        conn = get_connection()
        tag_id = f"struct_{url}:{tag_name}"
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')

        # Get the generalized pattern from the label group
        xpaths = self.get_xpaths_for_label(url, label_group)
        pattern = generalize_xpath(xpaths[0]) if xpaths else ''
        lca = compute_lca(xpaths)

        try:
            conn.execute(
                "MERGE (st:StructureTag {tag_id: $tid}) "
                "SET st.url = $url, st.tag_name = $name, "
                "    st.label_group = $lg, st.pattern = $pat, "
                "    st.lca_xpath = $lca, st.description = $desc, "
                "    st.created_at = $ts;",
                parameters={
                    "tid": tag_id, "url": url, "name": tag_name,
                    "lg": label_group, "pat": pattern, "lca": lca,
                    "desc": description, "ts": ts,
                }
            )
        except Exception as e:
            print(f"[LabelEngine] Structure tag error: {e}")

        return tag_id

    def get_structure_tags(self, url: str) -> List[Dict[str, Any]]:
        """Get all structure tags for a URL."""
        conn = get_connection()
        results = []
        try:
            res = conn.execute(
                "MATCH (st:StructureTag {url: $url}) "
                "RETURN st.tag_id, st.tag_name, st.label_group, "
                "       st.pattern, st.lca_xpath, st.description;",
                parameters={"url": url}
            )
            while res.has_next():
                row = res.get_next()
                results.append({
                    'tag_id': row[0], 'tag_name': row[1],
                    'label_group': row[2], 'pattern': row[3],
                    'lca_xpath': row[4], 'description': row[5],
                })
        except Exception:
            pass
        return results

    def get_all_labels_with_lca(self, url: str) -> List[Dict[str, Any]]:
        """
        Return all unique labels for a URL with their LCA and member counts.
        Used by the GUI to highlight ontologized subtrees.
        """
        all_labels = self.get_labels_for_url(url)
        label_groups = defaultdict(list)
        for lbl in all_labels:
            label_groups[lbl['label']].append(lbl['xpath'])

        result = []
        for label_name, xpaths in label_groups.items():
            lca = compute_lca(xpaths)
            result.append({
                'label': label_name,
                'lca_xpath': lca,
                'count': len(xpaths),
                'is_commuted': any(
                    not l['is_instance']
                    for l in all_labels if l['label'] == label_name
                ),
                'pattern': generalize_xpath(xpaths[0]) if xpaths else '',
            })
        return result
