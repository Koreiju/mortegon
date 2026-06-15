"""
pq_tree.py — PQ-Tree Structural Signatures for DOM Template Groups
===================================================================

A PQ-Tree represents a family of valid child orderings for a DOM template.

Node types:
  - Leaf:    a concrete tag (e.g., 'img', 'h2', 'p')
  - P-node:  children can appear in ANY permutation
  - Q-node:  children must appear in strict left-to-right order
             (or its exact reverse)

The key property: two DOM subtrees that differ only by child ordering
will produce the SAME canonical PQ-Tree string, enabling them to share
a template group without being split by _refine_homogeneity().

Induction algorithm:
  1. Collect child-tag sequences from multiple instances of the same template
  2. For each position, check if the same tag always appears (Q) or varies (P)
  3. Build the PQ-Tree bottom-up, recursing into children

Serialization:
  P-nodes sort children alphabetically for deterministic canonical form.
  Q-nodes preserve the order from the first instance.
  Example: Q-div(P-(h2,img),p)  — div with permutable h2/img, then fixed p

Phase 5 of the algorithmic migration plan.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import List, Optional, Tuple
from collections import Counter


class PQNodeType(Enum):
    LEAF = auto()
    P_NODE = auto()
    Q_NODE = auto()


class PQNode:
    """A node in a PQ-Tree.

    Attributes:
        node_type: LEAF, P_NODE, or Q_NODE
        tag: the DOM tag name (for all node types — the root tag)
        children: list of child PQNode (empty for leaves)
    """
    __slots__ = ('node_type', 'tag', 'children')

    def __init__(self, node_type: PQNodeType, tag: str,
                 children: Optional[List[PQNode]] = None):
        self.node_type = node_type
        self.tag = tag
        self.children = children or []

    def canonical(self) -> str:
        """Produce a deterministic canonical string representation.

        P-nodes sort children alphabetically for canonical form.
        Q-nodes preserve insertion order (first instance's order).
        Leaves return just the tag name.

        Examples:
            Leaf:   'img'
            Q-node: 'Q-div(img,h2,p)'     — strict order
            P-node: 'P-div(h2,img,p)'     — sorted alphabetically
            Mixed:  'Q-div(P-(h2,img),p)'  — Q-root with P-child group
        """
        if self.node_type == PQNodeType.LEAF:
            return self.tag

        child_strs = [c.canonical() for c in self.children]

        if self.node_type == PQNodeType.P_NODE:
            child_strs.sort()  # canonical: alphabetical
            return f"P-{self.tag}({','.join(child_strs)})"
        else:  # Q_NODE
            return f"Q-{self.tag}({','.join(child_strs)})"

    def __repr__(self):
        return self.canonical()

    def __eq__(self, other):
        if not isinstance(other, PQNode):
            return False
        return self.canonical() == other.canonical()

    def __hash__(self):
        return hash(self.canonical())

    @property
    def is_leaf(self) -> bool:
        return self.node_type == PQNodeType.LEAF

    @property
    def is_p_node(self) -> bool:
        return self.node_type == PQNodeType.P_NODE

    @property
    def is_q_node(self) -> bool:
        return self.node_type == PQNodeType.Q_NODE


# ═══════════════════════════════════════════════════════════════════
# PQ-TREE INDUCTION FROM DOM INSTANCES
# ═══════════════════════════════════════════════════════════════════

# Tags to skip during PQ-Tree construction
_PQ_SKIP = frozenset({
    'script', 'style', 'noscript', 'template', 'link', 'meta',
    'head', 'br', 'hr', 'wbr', 'col', 'source',
})


def _get_structural_children(node) -> list:
    """Return direct structural element children of a DOM node."""
    children = []
    for c in (node.get_children(include_shadow=True)
              if hasattr(node, 'get_children') else
              getattr(node, 'children', [])):
        tag = getattr(c, 'tag', '').lower()
        if tag.startswith('#') or tag in _PQ_SKIP:
            continue
        children.append(c)
    return children


def induce_pq_tree(
    nodes: list,
    max_depth: int = 4,
    _depth: int = 0,
) -> Optional[PQNode]:
    """Induce a PQ-Tree from multiple DOM node instances of the same template.

    Examines the child-tag sequences across all instances to determine
    which children maintain strict order (Q-node) vs. which permute (P-node).

    Algorithm:
      1. All instances must share the same root tag
      2. Collect child-tag sequences from each instance
      3. If all sequences are identical → Q-node (strict order)
      4. If sequences differ but share the same tag BAG → P-node (permutable)
      5. Recurse into matched children

    Args:
        nodes: list of ShadowNode instances sharing a template
        max_depth: maximum tree depth to analyze
        _depth: current recursion depth (internal)

    Returns:
        PQNode representing the structural family, or None if empty.
    """
    if not nodes:
        return None

    # All instances must share the same root tag
    tags = set()
    for n in nodes:
        tag = getattr(n, 'tag', '').lower()
        if tag.startswith('#') or tag in _PQ_SKIP:
            continue
        tags.add(tag)

    if len(tags) != 1:
        return None  # heterogeneous roots — cannot form PQ-Tree

    root_tag = tags.pop()

    # Leaf node: at max depth or no structural children in any instance
    if _depth >= max_depth:
        return PQNode(PQNodeType.LEAF, root_tag)

    all_child_seqs: List[List[Tuple[str, object]]] = []
    for n in nodes:
        children = _get_structural_children(n)
        seq = [(getattr(c, 'tag', '').lower(), c) for c in children]
        all_child_seqs.append(seq)

    if not all_child_seqs or all(len(s) == 0 for s in all_child_seqs):
        return PQNode(PQNodeType.LEAF, root_tag)

    # Determine if children are in consistent order across instances
    tag_seqs = [tuple(tag for tag, _ in seq) for seq in all_child_seqs]

    # Filter out empty sequences
    tag_seqs = [s for s in tag_seqs if s]
    if not tag_seqs:
        return PQNode(PQNodeType.LEAF, root_tag)

    # Check: are all tag sequences identical?
    first_seq = tag_seqs[0]
    all_same_order = all(s == first_seq for s in tag_seqs)

    # Check: do all sequences share the same bag of tags?
    first_bag = Counter(first_seq)
    same_bag = all(Counter(s) == first_bag for s in tag_seqs)

    if not same_bag:
        # Different tag compositions — use first instance as Q-node,
        # treat extra/missing children as optional
        # Build from the longest sequence
        longest_idx = max(range(len(all_child_seqs)),
                          key=lambda i: len(all_child_seqs[i]))
        longest = all_child_seqs[longest_idx]
        children_pq = []
        for tag, node_obj in longest:
            # Collect this tag's instances across all sequences
            tag_instances = []
            for seq in all_child_seqs:
                for t, obj in seq:
                    if t == tag:
                        tag_instances.append(obj)
                        break
            if tag_instances:
                child = induce_pq_tree(tag_instances, max_depth, _depth + 1)
                if child:
                    children_pq.append(child)

        if not children_pq:
            return PQNode(PQNodeType.LEAF, root_tag)
        return PQNode(PQNodeType.Q_NODE, root_tag, children_pq)

    if all_same_order:
        # All instances have children in the same order → Q-node
        # Recurse into each child position
        children_pq = []
        for pos in range(len(first_seq)):
            tag_at_pos = first_seq[pos]
            # Gather all instances' children at this position
            child_instances = []
            for seq in all_child_seqs:
                if pos < len(seq):
                    child_instances.append(seq[pos][1])
            if child_instances:
                child = induce_pq_tree(child_instances, max_depth, _depth + 1)
                if child:
                    children_pq.append(child)

        if not children_pq:
            return PQNode(PQNodeType.LEAF, root_tag)
        return PQNode(PQNodeType.Q_NODE, root_tag, children_pq)

    else:
        # Same bag, different order → P-node (children are permutable)
        # Group child instances by tag across all sequences
        tag_to_instances: dict = {}
        for seq in all_child_seqs:
            for tag, obj in seq:
                if tag not in tag_to_instances:
                    tag_to_instances[tag] = []
                tag_to_instances[tag].append(obj)

        children_pq = []
        for tag in sorted(tag_to_instances.keys()):
            instances = tag_to_instances[tag]
            child = induce_pq_tree(instances, max_depth, _depth + 1)
            if child:
                children_pq.append(child)

        if not children_pq:
            return PQNode(PQNodeType.LEAF, root_tag)
        return PQNode(PQNodeType.P_NODE, root_tag, children_pq)


def induce_pq_tree_single(
    node,
    max_depth: int = 4,
    _depth: int = 0,
) -> Optional[PQNode]:
    """Build a PQ-Tree from a single DOM node (all children are Q-ordered).

    Used when only one representative instance is available.
    """
    return induce_pq_tree([node], max_depth, _depth)


def pq_membership_test(pq: PQNode, child_tag_sequence: Tuple[str, ...]) -> bool:
    """Test if a child-tag sequence is a valid member of a PQ-Tree.

    Args:
        pq: a PQNode (must be P_NODE or Q_NODE)
        child_tag_sequence: tuple of tag names to test

    Returns:
        True if the sequence is a valid permutation under the PQ-Tree.
    """
    if pq.is_leaf:
        return len(child_tag_sequence) == 0

    expected_tags = tuple(c.tag for c in pq.children)

    if pq.is_q_node:
        # Q-node: strict order (or reverse)
        return (child_tag_sequence == expected_tags or
                child_tag_sequence == tuple(reversed(expected_tags)))

    if pq.is_p_node:
        # P-node: any permutation of the expected tags
        return Counter(child_tag_sequence) == Counter(expected_tags)

    return False
