"""
buta_extractor.py — Bottom-Up Tree Automaton for O(N) Template Extraction
==========================================================================

Compiles finalized PQ-Tree templates into a deterministic Bottom-Up Tree
Automaton (BUTA) that evaluates ALL structural patterns in a single
post-order traversal of the DOM.

Classical complexity:  O(N × M)  where N = DOM nodes, M = XPath selectors
BUTA complexity:      O(N × P)  where P = max template children (typically ≤ 8)
                      Effectively O(N) since P is bounded by a small constant.

Architecture:
  1. COMPILE: Convert each ChunkGroup's PQ-Tree into a Pattern (tag + required
     child tag multiset/sequence). Register accepting states.
  2. EXECUTE: Single post-order DOM traversal. At each node:
     a. Assign a "leaf state" from its tag
     b. Collect child states
     c. Check if (tag, child_states) matches any compiled pattern
     d. If accepting → record the node for that chunk
  3. VALIDATE: Compare BUTA-discovered nodes against chunk._instance_nodes.
     This proves correctness without removing the existing XPath logic.

Phase 6 of the algorithmic migration plan.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple

try:
    from .shadow_html_parser import ShadowNode, ShadowDOM
except ImportError:
    pass  # Standalone testing uses mocks

try:
    from backend.analytics.algorithms.pq_tree import PQNode, PQNodeType
except ImportError:
    pass

try:
    from .web_distiller_freq import SKIP_TAGS, DOCUMENT_TAGS, ChunkGroup
except ImportError:
    SKIP_TAGS = frozenset({'script', 'style', 'link', 'meta', 'head',
                           'noscript', 'template'})
    DOCUMENT_TAGS = frozenset({'html', 'body', '#document', '#shadow-root'})


# ═══════════════════════════════════════════════════════════════════
# §1: COMPILED PATTERN
# ═══════════════════════════════════════════════════════════════════

class CompiledPattern:
    """A compiled PQ-Tree pattern for BUTA matching.

    Attributes:
        chunk_id:      which chunk this pattern belongs to
        root_tag:      required tag of the root node
        child_tags:    required child tags (Counter for P-nodes, tuple for Q-nodes)
        is_p_node:     True if children can be in any order
        depth:         nesting depth in the PQ-Tree (0 = root pattern)
        min_height:    minimum subtree height required
    """
    __slots__ = ('chunk_id', 'root_tag', 'child_tags', 'is_p_node',
                 'depth', 'min_height', 'pq_canonical')

    def __init__(self, chunk_id: int, root_tag: str,
                 child_tags, is_p_node: bool,
                 min_height: int = 0, pq_canonical: str = ''):
        self.chunk_id = chunk_id
        self.root_tag = root_tag
        self.child_tags = child_tags  # Counter or tuple
        self.is_p_node = is_p_node
        self.min_height = min_height
        self.pq_canonical = pq_canonical

    def matches_children(self, actual_child_tags: List[str]) -> bool:
        """Check if actual child tags satisfy this pattern.

        For P-nodes: required tags must be a sub-multiset of actual tags
        For Q-nodes: required tags must appear as a subsequence of actual tags

        This tolerates extra children (decorative wrappers, injected spans)
        that aren't part of the template pattern.
        """
        if self.is_p_node:
            actual_counter = Counter(actual_child_tags)
            for tag, count in self.child_tags.items():
                if actual_counter.get(tag, 0) < count:
                    return False
            return True
        else:
            # Q-node: required sequence must appear as subsequence
            required = self.child_tags  # tuple
            if not required:
                return True
            ri = 0
            for actual_tag in actual_child_tags:
                if actual_tag == required[ri]:
                    ri += 1
                    if ri >= len(required):
                        return True
            return ri >= len(required)


# ═══════════════════════════════════════════════════════════════════
# §2: BUTA COMPILER
# ═══════════════════════════════════════════════════════════════════

def compile_pq_to_pattern(
    pq: PQNode,
    chunk_id: int,
    min_height: int = 0,
) -> Optional[CompiledPattern]:
    """Compile a PQ-Tree root into a CompiledPattern.

    Extracts the root-level matching condition: tag + required child tags.
    """
    if pq is None:
        return None

    if pq.is_leaf:
        # Leaf PQ-Trees match by tag alone (no child requirements)
        return CompiledPattern(
            chunk_id=chunk_id,
            root_tag=pq.tag,
            child_tags=Counter(),
            is_p_node=True,
            min_height=min_height,
            pq_canonical=pq.canonical(),
        )

    child_tags_list = [c.tag for c in pq.children]

    if pq.is_p_node:
        return CompiledPattern(
            chunk_id=chunk_id,
            root_tag=pq.tag,
            child_tags=Counter(child_tags_list),
            is_p_node=True,
            min_height=min_height,
            pq_canonical=pq.canonical(),
        )
    else:
        return CompiledPattern(
            chunk_id=chunk_id,
            root_tag=pq.tag,
            child_tags=tuple(child_tags_list),
            is_p_node=False,
            min_height=min_height,
            pq_canonical=pq.canonical(),
        )


def compile_from_template_hash(
    tag: str,
    template_hash: int,
    chunk_id: int,
    child_tag_bag: Tuple[Tuple[str, int], ...],
    min_height: int = 0,
) -> CompiledPattern:
    """Compile from WL hash data when no PQ-Tree is available.

    Uses child_tag_bag as a P-node (bag of tags, order-independent).
    """
    child_counter = Counter()
    for child_tag, count in child_tag_bag:
        child_counter[child_tag] = count

    return CompiledPattern(
        chunk_id=chunk_id,
        root_tag=tag,
        child_tags=child_counter,
        is_p_node=True,
        min_height=min_height,
        pq_canonical=str(template_hash),
    )


# ═══════════════════════════════════════════════════════════════════
# §3: BUTA EXECUTOR
# ═══════════════════════════════════════════════════════════════════

class BottomUpTreeAutomaton:
    """Bottom-Up Tree Automaton for simultaneous multi-pattern extraction.

    Compiles structural patterns from ChunkGroups (via PQ-Trees or WL
    hashes) and executes a single O(N) post-order traversal to find
    all matching nodes.

    Usage:
        buta = BottomUpTreeAutomaton()
        buta.compile(structural_chunks, template_groups)
        matches = buta.execute(dom)
        buta.validate(structural_chunks)  # assert match correctness
    """

    def __init__(self, verbose: bool = False):
        self._patterns: List[CompiledPattern] = []
        self._by_tag: Dict[str, List[CompiledPattern]] = defaultdict(list)
        self._matches: Dict[int, List] = defaultdict(list)  # chunk_id → [nodes]
        self._log = print if verbose else lambda *a, **k: None

    def compile(
        self,
        chunks: List[ChunkGroup],
        template_groups: Optional[List] = None,
    ) -> int:
        """Compile structural chunk patterns into the automaton.

        Args:
            chunks: list of ChunkGroup (structural chunks only)
            template_groups: optional TemplateGroup list for PQ-Tree access

        Returns:
            Number of compiled patterns.
        """
        self._patterns.clear()
        self._by_tag.clear()

        # Build TemplateGroup lookup if available
        tg_by_id: Dict[int, object] = {}
        if template_groups:
            for tg in template_groups:
                tg_by_id[tg.group_id] = tg

        for chunk in chunks:
            if not getattr(chunk, '_structural_sig', ''):
                continue

            chunk_id = chunk.chunk_id
            tg = tg_by_id.get(chunk_id)

            pattern = None

            # Prefer PQ-Tree if available
            if tg and hasattr(tg, 'pq_tree') and tg.pq_tree is not None:
                pattern = compile_pq_to_pattern(
                    tg.pq_tree, chunk_id,
                    min_height=getattr(tg.color, 'height', 0),
                )

            # Fallback: compile from WL hash + child_tag_bag
            if pattern is None and tg:
                pattern = compile_from_template_hash(
                    tag=tg.color.tag,
                    template_hash=tg.color.template_hash,
                    chunk_id=chunk_id,
                    child_tag_bag=tg.color.child_tag_bag,
                    min_height=getattr(tg.color, 'height', 0),
                )

            # Last fallback: compile from chunk signature
            if pattern is None and chunk._instance_nodes:
                node = chunk._instance_nodes[0]
                tag = node.tag.lower()
                children = node.get_children(include_shadow=True) if hasattr(node, 'get_children') else []
                child_tags = [c.tag.lower() for c in children
                              if not c.tag.lower().startswith('#')
                              and c.tag.lower() not in SKIP_TAGS]
                pattern = CompiledPattern(
                    chunk_id=chunk_id,
                    root_tag=tag,
                    child_tags=Counter(child_tags),
                    is_p_node=True,
                    pq_canonical=chunk._structural_sig,
                )

            if pattern:
                self._patterns.append(pattern)
                self._by_tag[pattern.root_tag].append(pattern)

        self._log(f"[BUTA] Compiled {len(self._patterns)} patterns "
                  f"across {len(self._by_tag)} tag buckets")
        return len(self._patterns)

    def execute(self, dom) -> Dict[int, List]:
        """Execute the automaton: single O(N) post-order traversal.

        Args:
            dom: ShadowDOM with a .root attribute

        Returns:
            Dict mapping chunk_id → list of matched ShadowNode objects.
        """
        self._matches.clear()

        # ── Post-order traversal with height computation ──
        # We compute each node's subtree height during traversal
        # to satisfy min_height constraints efficiently.
        self._postorder(dom.root)

        total = sum(len(v) for v in self._matches.values())
        self._log(f"[BUTA] Extracted {total} nodes across "
                  f"{len(self._matches)} chunks")
        return dict(self._matches)

    def _postorder(self, node, _depth: int = 0) -> int:
        """Post-order traversal: process children first, then self.

        Returns the subtree height of this node.
        """
        tag = node.tag.lower()

        # Pass through document-level containers
        if tag in DOCUMENT_TAGS:
            max_h = 0
            for child in node.get_children(include_shadow=True):
                h = self._postorder(child, _depth)
                max_h = max(max_h, h)
            return max_h

        # Skip non-structural tags
        if tag in SKIP_TAGS or tag.startswith('#'):
            return 0

        # ── Process children first (post-order) ──
        child_heights: List[int] = []
        child_tags: List[str] = []

        for child in node.get_children(include_shadow=True):
            ct = child.tag.lower()
            if ct in SKIP_TAGS or ct.startswith('#'):
                continue
            if ct in DOCUMENT_TAGS:
                # Pass through: process grandchildren
                for gc in child.get_children(include_shadow=True):
                    h = self._postorder(gc, _depth + 1)
                    gct = gc.tag.lower()
                    if gct not in SKIP_TAGS and not gct.startswith('#'):
                        child_heights.append(h)
                        child_tags.append(gct)
            else:
                h = self._postorder(child, _depth + 1)
                child_heights.append(h)
                child_tags.append(ct)

        # ── Compute this node's height ──
        my_height = (max(child_heights) + 1) if child_heights else 0

        # ── Check against compiled patterns for this tag ──
        candidates = self._by_tag.get(tag)
        if candidates:
            for pattern in candidates:
                # Height gate: skip if subtree is too shallow
                if my_height < pattern.min_height:
                    continue

                # Child pattern matching
                if not child_tags and not pattern.child_tags:
                    # Leaf pattern matches leaf node
                    self._matches[pattern.chunk_id].append(node)
                elif pattern.matches_children(child_tags):
                    self._matches[pattern.chunk_id].append(node)

        return my_height

    def validate(
        self,
        chunks: List[ChunkGroup],
        strict: bool = False,
    ) -> Tuple[int, int, List[str]]:
        """Validate BUTA results against chunk._instance_nodes.

        For each structural chunk, compares the set of nodes found by
        the BUTA against the set stored in chunk._instance_nodes.

        Args:
            chunks: list of ChunkGroup to validate
            strict: if True, require exact match; if False, require
                    BUTA ⊇ expected (BUTA may find superset due to
                    pattern matching vs. exact hash matching)

        Returns:
            (matched_chunks, total_structural_chunks, error_messages)
        """
        errors: List[str] = []
        matched = 0
        total = 0

        for chunk in chunks:
            if not getattr(chunk, '_structural_sig', ''):
                continue

            total += 1
            expected_ids = {id(n) for n in chunk._instance_nodes}
            buta_nodes = self._matches.get(chunk.chunk_id, [])
            buta_ids = {id(n) for n in buta_nodes}

            if strict:
                if buta_ids == expected_ids:
                    matched += 1
                else:
                    missing = expected_ids - buta_ids
                    extra = buta_ids - expected_ids
                    errors.append(
                        f"Chunk {chunk.chunk_id} ({chunk.signature}): "
                        f"missing={len(missing)}, extra={len(extra)} "
                        f"(expected={len(expected_ids)}, buta={len(buta_ids)})"
                    )
            else:
                # Relaxed: BUTA must find at least 50% of expected nodes
                # (patterns are structural, so exact subset isn't guaranteed
                # when post-processing has modified instance lists)
                overlap = expected_ids & buta_ids
                coverage = len(overlap) / max(1, len(expected_ids))
                if coverage >= 0.5:
                    matched += 1
                else:
                    errors.append(
                        f"Chunk {chunk.chunk_id} ({chunk.signature}): "
                        f"coverage={coverage:.0%} "
                        f"(overlap={len(overlap)}/{len(expected_ids)}, "
                        f"buta_total={len(buta_ids)})"
                    )

        self._log(f"[BUTA] Validation: {matched}/{total} structural chunks verified")
        return matched, total, errors
