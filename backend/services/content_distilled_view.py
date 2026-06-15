from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from collections import defaultdict
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class ContentDistilledView:
    snapshot_id: str
    xpaths: List[str]                # distilled xpaths in DFS order
    tree: Dict[str, Any]             # nested tree view (for GUI rendering)
    lca: Optional[str]               # LCA of current label set, if any
    node_count: int
    content_categories: Dict[str, int]
    generalized_pattern_counts: Dict[str, int]

class ContentDistilledService:
    """
    Assemble a ContentDistilledView from a snapshot's content tree,
    attached tagged content categories, and the currently-committed label set (§14.4).
    """

    def __init__(self, mapper, state_tracker=None):
        self.mapper = mapper
        self.state_tracker = state_tracker
        self._cache = {}  # STUB: Replace with TwoTierCache in Phase 17

    def view(self, snapshot_id: str) -> ContentDistilledView:
        if snapshot_id in self._cache:
            return self._cache[snapshot_id]

        # Load content-distilled tree from mapper's active memory or database
        tree = self.mapper._active_trees.get(snapshot_id)
        if not tree:
            tree = self.mapper.store.load_content_tree(snapshot_id)
            if not tree:
                raise ValueError(f"Content tree not found for snapshot {snapshot_id}")

        xpaths = []
        content_categories = defaultdict(int)
        generalized_pattern_counts = defaultdict(int)

        def walk_tree(subtree: Dict[str, Any]):
            for key, child in subtree.items():
                if key.startswith('_') or not isinstance(child, dict):
                    continue
                
                node_xpath = child.get('_xpath', key)
                
                # Check for structural significance or content
                child_paths = [k for k in child.keys() if not k.startswith('_')]
                has_content = bool(child.get('_content'))
                is_branching = len(child_paths) > 1
                
                # Patricia compression: only keep nodes with content or branching structure
                if has_content or is_branching:
                    xpaths.append(node_xpath)
                    
                    # Track generalized patterns for nodes that actually matter
                    gen_path = re.sub(r'\[\d+\]', '', node_xpath)
                    generalized_pattern_counts[gen_path] += 1

                # Track content categories mapped by distillation
                for cat in child.get('_content', []):
                    content_categories[cat] += 1
                    
                walk_tree(child)

        walk_tree(tree)
        lca = None # STUB: Calculate LCA from active label set

        result = ContentDistilledView(
            snapshot_id=snapshot_id,
            xpaths=xpaths,
            tree=tree,
            lca=lca,
            node_count=len(xpaths),
            content_categories=dict(content_categories),
            generalized_pattern_counts=dict(generalized_pattern_counts)
        )
        
        self._cache[snapshot_id] = result
        return result