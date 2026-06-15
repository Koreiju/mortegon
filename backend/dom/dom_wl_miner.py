"""
WL Structural Coloring Engine for DOM Template Mining — v2 (with v13+ refinements)
====================================================================================
Added post‑processing phases from web_distiller_freq.py:
  - Content‑based deduplication within groups
  - Anchor‑interior splitting (fragments inside <a> tags)
  - Structural homogeneity refinement (ordered tree signatures)
  - Cross‑chunk content deduplication (text + URL)
  - CIST (Cross‑Instance Sub‑Template Mining)
  - TextContentCollector and navigation grouping
  - Purity‑dominance filter
  - Sibling group merging (for decoupled columns)
  - Container preservation in subsumption
  - Enhanced media deduplication mask
  - Product‑ID based URL deduplication
  - Debug logging for test diagnostics
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any, Dict, FrozenSet, Iterator, List, Optional, Set, Tuple,
)

from .shadow_html_parser import ShadowNode, ShadowDOM

from backend.analytics.algorithms.pq_tree import PQNode, PQNodeType, induce_pq_tree, induce_pq_tree_single

from .buta_extractor import BottomUpTreeAutomaton

from .web_distiller_freq import (
    SKIP_TAGS,
    DOCUMENT_TAGS,
    MEDIA_TAGS,
    ContentCategory,
    ContentNode,
    ChunkGroup,
    URLExtractor,
    AttributeTokenizer,
    AgnosticAttr,
    ContentScanner,
    ChunkSampler,
    TokenizedXPathSelector,
    SearchInputCollector,
    PaginationCollector,
    TextContentCollector,
    cached_xpath,
    cached_signature,
    iter_elements,
    _node_has_nav_url,
    signature_height,
)

# Ensure get_ordered_subtree_signature is available
try:
    from .web_distiller_freq import get_ordered_subtree_signature
except ImportError:
    def get_ordered_subtree_signature(node: ShadowNode, max_depth: int = -1) -> str:
        """Ordered tree canonical certificate – preserves DOM sibling order."""
        tag = node.tag.lower()
        if tag.startswith('#') and tag != '#shadow-root':
            tag = '#'
        if max_depth == 0:
            return tag
        children = node.get_children(include_shadow=True)
        child_sigs = []
        for child in children:
            if child.tag.startswith('#') and child.tag != '#shadow-root':
                continue
            next_depth = max_depth - 1 if max_depth > 0 else -1
            child_sigs.append(get_ordered_subtree_signature(child, next_depth))
        if not child_sigs:
            return tag
        return f"{tag}({','.join(child_sigs)})"


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS (existing + new)
# ═══════════════════════════════════════════════════════════════════════════

MIN_TEMPLATE_FREQ = 2
MIN_TEMPLATE_HEIGHT = 1
MIN_SINGLETON_TEXT = 150
MIN_SINGLETON_NODES = 3
ENTROPY_THRESHOLD = 3.5


# Text-like attrs: per-instance human content, MUST be excluded from
# structural fingerprint or identical templates get fragmented.
_TEXT_ATTRS = frozenset({
    'title', 'alt', 'aria-label', 'aria-description',
    'aria-roledescription', 'aria-placeholder', 'aria-valuetext',
    'placeholder', 'label', 'content', 'summary', 'name',
    'value', 'data-original-title', 'data-content',
})
_RUNTIME_ATTRS = frozenset({
    'style', 'onclick', 'onload', 'onerror', 'onmouseover',
    'onmouseout', 'onfocus', 'onblur', 'onchange', 'onsubmit',
    'onkeydown', 'onkeyup', 'onkeypress', 'ontouchstart',
    'srcdoc', 'xmlns', 'tabindex',
})
_EXCLUDED_ATTRS = _TEXT_ATTRS | _RUNTIME_ATTRS

# ── New constants for post‑processing ─────────────────────────────────────
MIN_CONTENT_TEXT_LEN = 20          # ignore very short instances
CONTENT_FINGERPRINT_MAX_LEN = 500
MIN_ANCHOR_PROMOTION_FREQ = 2      # after promotion, group must have at least this many instances
ORDERED_SIG_DEPTH = 8               # depth for ordered subtree signature (reduced to avoid over‑splitting)
CROSS_DEDUP_TEXT_MIN_LEN = 20

# CIST mining
CIST_MIN_HEIGHT = 2
PRESENTATIONAL_ROOTS = {'svg', 'canvas', 'video', 'audio', 'defs', 'g',
                        'filter', 'fecolormatrix', 'fegaussianblur',
                        'femerge', 'feoffset', 'fecomponenttransfer',
                        'style', 'noscript', 'template'}

# Purity dominance
PURITY_RATIO_THRESHOLD = 0.75
TOP_CONTENT_RATIO = 0.30
TOP_MAX_FREQ = 2
SUBSUME_RATIO = 0.90
SUBSUME_MIN_CHILDREN = 2
TRIVIAL_MIN_FREQ = 3

UNIQUENESS_THRESHOLD = 0.10

# Container class tokens that should never be suppressed
CONTAINER_CLASS_TOKENS = {'moreStoriesList', 'gallery', 'submenu', 'fl-col', 'category'}

# Debug flag (set to True for verbose test diagnostics)
DEBUG = True


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

class ContentTier(Enum):
    TEMPLATE = auto()
    SINGLETON = auto()
    ORPHAN = auto()


@dataclass
class WLColor:
    exact_hash: int
    template_hash: int
    tag: str
    height: int
    child_tag_bag: Tuple[Tuple[str, int], ...]
    attr_fingerprint: FrozenSet[Tuple[str, str]]


@dataclass
class ColoredNode:
    node: ShadowNode
    color: WLColor
    xpath: str
    depth: int
    is_content_bearing: bool
    is_structural_hub: bool
    is_anchor_descendant: bool
    content_types: FrozenSet[ContentCategory]
    subtree_text_len: int
    subtree_content_count: int
    subtree_link_count: int
    ancestral_path: Tuple[str, ...] = field(default_factory=tuple)


@dataclass
class TemplateGroup:
    group_id: int
    color: WLColor
    instances: List[ColoredNode]
    tier: ContentTier
    parent_group_ids: Set[int] = field(default_factory=set)
    child_group_ids: Set[int] = field(default_factory=set)
    suppressed: bool = False
    suppressed_by: Optional[int] = None
    promoted_xpaths: Optional[List[str]] = None
    _parent_chunk_id: int = -1
    pq_tree: Optional[PQNode] = None  # Phase 5: formal PQ-Tree signature
    canonical_template: Optional[ShadowNode] = None  # Phase 4a: MCS shared structural skeleton

    @property
    def frequency(self) -> int:
        return len(self.instances)

    @property
    def xpaths(self) -> List[str]:
        return [cn.xpath for cn in self.instances]

    @property
    def pq_signature(self) -> str:
        """Canonical PQ-Tree string, or fallback to hash."""
        if self.pq_tree is not None:
            return self.pq_tree.canonical()
        return str(self.color.template_hash)


# ═══════════════════════════════════════════════════════════════════════════
# ATTRIBUTE FINGERPRINTING
# ═══════════════════════════════════════════════════════════════════════════

def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


class JenksEntropySplitter:
    """V-Optimal Quantization for dynamic entropy thresholding.

    Replaces the hardcoded ENTROPY_THRESHOLD = 3.5 with a page-adaptive
    threshold computed from the actual distribution of Shannon entropies
    across all attribute tokens on the current page.

    Algorithm:
      1. Collect all (token, entropy) pairs from the page's attributes
      2. Sort by entropy
      3. Find the split point that minimizes within-bucket SSE
         (Sum of Squared Errors) for exactly K=2 buckets
      4. The threshold is the midpoint between the last value in
         bucket 1 and the first value in bucket 2

    Complexity: O(A log A) for sorting, O(A) for the DP sweep,
    where A = total unique attribute tokens.

    Degenerate cases:
      - All tokens have similar entropy → between-bucket variance < 0.1
        → fall back to the default threshold (3.5)
      - Fewer than 4 tokens → fall back to default (not enough data)
    """

    DEFAULT_THRESHOLD = ENTROPY_THRESHOLD  # 3.5

    @classmethod
    def compute_threshold(
        cls,
        dom: ShadowDOM,
        verbose: bool = False,
    ) -> float:
        """Scan all attribute tokens and compute optimal entropy threshold.

        Args:
            dom: parsed ShadowDOM tree
            verbose: if True, log diagnostic info

        Returns:
            Dynamic entropy threshold (float), or DEFAULT_THRESHOLD
            if data is insufficient.
        """
        log = print if verbose else lambda *a, **k: None

        # ── Step 1: Collect all attribute token entropies ──
        entropies: List[float] = []
        for node in iter_elements(dom.root):
            tag = node.tag.lower()
            if tag in SKIP_TAGS or tag in DOCUMENT_TAGS:
                continue
            attrs = node.get_all_attrs() if hasattr(node, 'get_all_attrs') else (node.attributes or {})
            for key, val in attrs.items():
                kl = key.lower()
                if kl in _EXCLUDED_ATTRS:
                    continue
                if not val or not isinstance(val, str):
                    continue
                vs = val.strip()
                if len(vs) > 200 or AgnosticAttr.is_url(vs):
                    continue
                for tok in AttributeTokenizer.tokenize(vs):
                    if len(tok) >= 2:
                        entropies.append(_shannon_entropy(tok))

        n = len(entropies)
        if n < 4:
            log(f"[VOptimal] Too few tokens ({n}), using default {cls.DEFAULT_THRESHOLD}")
            return cls.DEFAULT_THRESHOLD

        # ── Step 2: Sort and deduplicate for the DP sweep ──
        entropies.sort()

        # ── Step 3: V-Optimal DP for K=2 buckets ──
        # Compute prefix sums for O(1) range SSE queries
        # SSE(i,j) = Σ(x - μ)² = Σx² - (Σx)²/(j-i+1)
        pfx_sum = [0.0]   # prefix sum of values
        pfx_sq = [0.0]    # prefix sum of squares
        for e in entropies:
            pfx_sum.append(pfx_sum[-1] + e)
            pfx_sq.append(pfx_sq[-1] + e * e)

        def sse(lo: int, hi: int) -> float:
            """SSE for entropies[lo..hi] (inclusive, 0-indexed)."""
            count = hi - lo + 1
            if count <= 0:
                return 0.0
            s = pfx_sum[hi + 1] - pfx_sum[lo]
            sq = pfx_sq[hi + 1] - pfx_sq[lo]
            return sq - (s * s) / count

        best_split = -1
        best_sse = float('inf')

        # Sweep all possible split points: bucket1=[0..i], bucket2=[i+1..n-1]
        # Minimum bucket size: 2 elements each
        for i in range(1, n - 2):
            total_sse = sse(0, i) + sse(i + 1, n - 1)
            if total_sse < best_sse:
                best_sse = total_sse
                best_split = i

        if best_split < 0:
            log(f"[VOptimal] No valid split, using default {cls.DEFAULT_THRESHOLD}")
            return cls.DEFAULT_THRESHOLD

        # ── Step 4: Compute threshold as midpoint ──
        threshold = (entropies[best_split] + entropies[best_split + 1]) / 2.0

        # ── Degenerate check: are the two buckets meaningfully different? ──
        mean_lo = pfx_sum[best_split + 1] / (best_split + 1)
        mean_hi = (pfx_sum[n] - pfx_sum[best_split + 1]) / (n - best_split - 1)
        gap = abs(mean_hi - mean_lo)

        if gap < 0.1:
            log(f"[VOptimal] Between-bucket gap {gap:.3f} < 0.1, using default {cls.DEFAULT_THRESHOLD}")
            return cls.DEFAULT_THRESHOLD

        log(f"[VOptimal] {n} tokens → threshold={threshold:.3f} "
            f"(lo_mean={mean_lo:.2f}, hi_mean={mean_hi:.2f}, gap={gap:.2f})")
        return threshold


def _compute_attr_fingerprint(
    node: ShadowNode,
    entropy_threshold: float = ENTROPY_THRESHOLD,
) -> FrozenSet[Tuple[str, str]]:
    """Compute structural attribute fingerprint for a DOM node.

    Args:
        node: the ShadowNode to fingerprint
        entropy_threshold: Shannon entropy ceiling for token inclusion.
            Tokens with entropy above this are treated as machine-generated
            hashes and excluded from the fingerprint.
    """
    tokens: List[Tuple[str, str]] = []
    attrs = node.get_all_attrs() if hasattr(node, 'get_all_attrs') else (node.attributes or {})
    for key, val in attrs.items():
        kl = key.lower()
        if kl in _EXCLUDED_ATTRS:
            continue
        if not val or not isinstance(val, str):
            continue
        vs = val.strip()
        if len(vs) > 200 or AgnosticAttr.is_url(vs):
            continue
        for tok in AttributeTokenizer.tokenize(vs):
            if len(tok) >= 2 and _shannon_entropy(tok) <= entropy_threshold:
                tokens.append((kl, tok))
    return frozenset(tokens)


# ═══════════════════════════════════════════════════════════════════════════
# NODE CONTENT CLASSIFICATION (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

def _classify_node(node: ShadowNode) -> Set[ContentCategory]:
    cats: Set[ContentCategory] = set()
    tag = node.tag.lower()
    if tag.startswith('#') or tag in SKIP_TAGS or tag in DOCUMENT_TAGS:
        return cats
    if AgnosticAttr.is_input_like(node):
        cats.add(ContentCategory.INPUT)
    if AgnosticAttr.is_button_like(node):
        cats.add(ContentCategory.BUTTON)
    if URLExtractor.extract_from_node(node):
        cats.add(ContentCategory.LINK)
    text = ((node.text or '').strip() + ' ' + (node.tail or '').strip()).strip()
    if len(text) > 2:
        cats.add(ContentCategory.TEXT)
    if tag in MEDIA_TAGS:
        cats.add(ContentCategory.LINK)
    return cats


# ═══════════════════════════════════════════════════════════════════════════
# WL COLOR ENGINE v2 — Colors ALL non-skip nodes (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

class WLColorEngine:
    def __init__(self, dom: ShadowDOM, verbose: bool = False):
        self.dom = dom
        self._verbose = verbose
        self._log = print if verbose else lambda *a, **k: None
        self.colored_nodes: Dict[int, ColoredNode] = {}
        self.containment_edges: Set[Tuple[int, int]] = set()
        self._content_ids: Set[int] = set()
        self._entropy_threshold: float = ENTROPY_THRESHOLD

    def color(self) -> Dict[int, ColoredNode]:
        # ── Phase 1: V-Optimal entropy threshold ──
        self._entropy_threshold = JenksEntropySplitter.compute_threshold(
            self.dom, verbose=self._verbose,
        )

        scanner = ContentScanner(self.dom)
        content_map = scanner.scan()
        self._content_ids = set(content_map.keys())
        self._log(f"[WL] ContentScanner: {len(self._content_ids)} nodes")
        self._color_post(self.dom.root, depth=0, in_anchor=False, path=())
        unique_templates = len(set(
            cn.color.template_hash for cn in self.colored_nodes.values()
        ))
        self._log(f"[WL] Colored: {len(self.colored_nodes)} nodes, "
                  f"{unique_templates} unique template_hashes")
        return self.colored_nodes

    def _color_post(
        self, node: ShadowNode, depth: int, in_anchor: bool,
        path: Tuple[str, ...] = (),
    ) -> Optional[WLColor]:
        tag = node.tag.lower()
        if tag in DOCUMENT_TAGS:
            best = None
            for child in node.get_children(include_shadow=True):
                c = self._color_post(child, depth, in_anchor, path)
                if c is not None:
                    best = c
            return best
        if tag in SKIP_TAGS:
            return None

        is_anchor = in_anchor or (tag == 'a' and 'href' in (node.attributes or {}))

        child_colors: List[WLColor] = []
        child_tag_counts: Counter = Counter()
        st_text = 0
        st_content = 0
        st_links = 0
        content_desc = 0

        child_path = path + (tag,)

        for child in node.get_children(include_shadow=True):
            ct = child.tag.lower()
            if ct.startswith('#') and ct != '#shadow-root':
                continue
            cc = self._color_post(child, depth + 1, is_anchor, child_path)
            if cc is not None:
                child_colors.append(cc)
                child_tag_counts[cc.tag] += 1
            ccn = self.colored_nodes.get(id(child))
            if ccn:
                st_text += ccn.subtree_text_len
                st_content += ccn.subtree_content_count
                st_links += ccn.subtree_link_count
                if ccn.is_content_bearing:
                    content_desc += 1
                content_desc += ccn.subtree_content_count

        own_types = _classify_node(node)
        own_text = ((node.text or '').strip() + ' ' + (node.tail or '').strip()).strip()
        own_links = URLExtractor.extract_from_node(node) if own_types else []
        st_text += len(own_text)
        st_content += (1 if own_types else 0)
        st_links += len(own_links)

        is_content = bool(own_types) or id(node) in self._content_ids
        is_hub = content_desc >= 2

        all_types: Set[ContentCategory] = set(own_types)
        for child in node.get_children(include_shadow=True):
            ccn = self.colored_nodes.get(id(child))
            if ccn:
                all_types.update(ccn.content_types)
        all_types_frozen = frozenset(all_types)

        attr_fp = _compute_attr_fingerprint(node, self._entropy_threshold)
        height = (max(cc.height for cc in child_colors) + 1) if child_colors else 0

        ordered = tuple(cc.exact_hash for cc in child_colors)
        exact_hash = hash((tag, attr_fp, ordered, all_types_frozen))

        sorted_child_templates = tuple(sorted(cc.template_hash for cc in child_colors))
        template_hash = hash((tag, sorted_child_templates, all_types_frozen))

        bag = tuple(sorted(child_tag_counts.items()))

        color = WLColor(
            exact_hash=exact_hash, template_hash=template_hash,
            tag=tag, height=height, child_tag_bag=bag,
            attr_fingerprint=attr_fp,
        )
        cn = ColoredNode(
            node=node, color=color, xpath=cached_xpath(node),
            depth=depth, is_content_bearing=is_content,
            is_structural_hub=is_hub, is_anchor_descendant=is_anchor,
            content_types=all_types_frozen,
            subtree_text_len=st_text, subtree_content_count=st_content,
            subtree_link_count=st_links,
            ancestral_path=path,
        )
        self.colored_nodes[id(node)] = cn

        for cc in child_colors:
            if cc.template_hash != template_hash:
                self.containment_edges.add((template_hash, cc.template_hash))

        return color


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATE GROUPER — Three-Tier (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

class TemplateGrouper:
    def __init__(self, colored: Dict[int, ColoredNode], dom: ShadowDOM,
                 verbose: bool = False):
        self.colored = colored
        self.dom = dom
        self._log = print if verbose else lambda *a, **k: None

    def group(self) -> List[TemplateGroup]:
        groups: List[TemplateGroup] = []
        nid = 0

        templates, covered = self._templates()
        for tg in templates:
            tg.group_id = nid; groups.append(tg); nid += 1
        self._log(f"[WL] Tier 1: {len(templates)} templates, {len(covered)} covered")

        singletons = self._singletons(covered)
        for sg in singletons:
            sg.group_id = nid; groups.append(sg); nid += 1
            for cn in sg.instances:
                covered.add(id(cn.node))
                for d in cn.node.iter_descendants():
                    covered.add(id(d))
        self._log(f"[WL] Tier 2: {len(singletons)} singletons")

        orphans = self._orphans(covered)
        for og in orphans:
            og.group_id = nid; groups.append(og); nid += 1
        self._log(f"[WL] Tier 3: {len(orphans)} orphan groups")

        return groups

    def _templates(self) -> Tuple[List[TemplateGroup], Set[int]]:
        by_h: Dict[int, List[ColoredNode]] = defaultdict(list)
        for cn in self.colored.values():
            if cn.is_content_bearing or cn.is_structural_hub:
                by_h[cn.color.template_hash].append(cn)

        cands = {h: ns for h, ns in by_h.items()
                 if len(ns) >= MIN_TEMPLATE_FREQ
                 and ns[0].color.height >= MIN_TEMPLATE_HEIGHT}

        # Subsumption
        desc_idx: Dict[int, Set[int]] = {}
        for h, ns in cands.items():
            s: Set[int] = set()
            for cn in ns:
                for d in cn.node.iter_descendants():
                    s.add(id(d))
            desc_idx[h] = s

        by_height = sorted(cands.keys(),
                           key=lambda h: cands[h][0].color.height, reverse=True)
        subsumed: Set[int] = set()
        for h in by_height:
            if h in subsumed:
                continue
            for oh in by_height:
                if oh == h or oh in subsumed:
                    continue
                if cands[oh][0].color.height >= cands[h][0].color.height:
                    continue
                if all(id(cn.node) in desc_idx[h] for cn in cands[oh]):
                    subsumed.add(oh)

        groups: List[TemplateGroup] = []
        covered: Set[int] = set()
        for h in by_height:
            if h in subsumed:
                continue
            ns = cands[h]
            if all(cn.is_anchor_descendant for cn in ns):
                continue
            groups.append(TemplateGroup(-1, ns[0].color, ns, ContentTier.TEMPLATE))
            for cn in ns:
                covered.add(id(cn.node))
                for d in cn.node.iter_descendants():
                    covered.add(id(d))
        return groups, covered

    def _singletons(self, covered: Set[int]) -> List[TemplateGroup]:
        uncov = [cn for cn in self.colored.values()
                 if id(cn.node) not in covered
                 and cn.is_content_bearing and cn.subtree_text_len > 0]
        if not uncov:
            return []

        by_par: Dict[int, List[ColoredNode]] = defaultdict(list)
        for cn in uncov:
            pid = id(cn.node.parent) if cn.node.parent else 0
            by_par[pid].append(cn)

        secs: List[TemplateGroup] = []
        used_pids: Set[int] = set()
        for pid, kids in by_par.items():
            txt = sum(cn.subtree_text_len for cn in kids)
            if txt < MIN_SINGLETON_TEXT or len(kids) < MIN_SINGLETON_NODES:
                continue

            parent = kids[0].node.parent
            if parent is None:
                continue

            pcn = self.colored.get(id(parent))
            if pcn is None:
                pcn = self._synth(kids, parent)
            if pcn is None or id(pcn.node) in covered:
                continue

            # Dedup: skip if ancestor of existing section
            skip = False
            for ex in secs:
                if self._is_anc(ex.instances[0].node, pcn.node):
                    skip = True; break
                if self._is_anc(pcn.node, ex.instances[0].node):
                    secs.remove(ex); break
            if skip:
                continue

            secs.append(TemplateGroup(-1, pcn.color, [pcn], ContentTier.SINGLETON))
            used_pids.add(pid)
        return secs

    def _synth(self, kids: List[ColoredNode], parent: ShadowNode) -> Optional[ColoredNode]:
        tag = parent.tag.lower()
        if tag in SKIP_TAGS or tag in DOCUMENT_TAGS:
            return None
        all_t: Set[ContentCategory] = set()
        for cn in kids:
            all_t.update(cn.content_types)
        return ColoredNode(
            node=parent,
            color=WLColor(
                exact_hash=hash(('_sec', id(parent))),
                template_hash=hash(('_sec', id(parent))),
                tag=tag,
                height=max(cn.color.height for cn in kids) + 1,
                child_tag_bag=tuple(sorted(Counter(cn.color.tag for cn in kids).items())),
                attr_fingerprint=_compute_attr_fingerprint(parent),
            ),
            xpath=cached_xpath(parent), depth=kids[0].depth - 1,
            is_content_bearing=True, is_structural_hub=True,
            is_anchor_descendant=False, content_types=frozenset(all_t),
            subtree_text_len=sum(cn.subtree_text_len for cn in kids),
            subtree_content_count=sum(cn.subtree_content_count for cn in kids),
            subtree_link_count=sum(cn.subtree_link_count for cn in kids),
        )

    def _orphans(self, covered: Set[int]) -> List[TemplateGroup]:
        by_pt: Dict[Tuple[int, str], List[ColoredNode]] = defaultdict(list)
        for cn in self.colored.values():
            if id(cn.node) in covered or not cn.is_content_bearing:
                continue
            if not (cn.content_types - {ContentCategory.STRUCTURE}):
                continue
            pid = id(cn.node.parent) if cn.node.parent else 0
            pt = 'link' if ContentCategory.LINK in cn.content_types else 'text'
            by_pt[(pid, pt)].append(cn)
        return [
            TemplateGroup(-1, ns[0].color, ns, ContentTier.ORPHAN)
            for ns in by_pt.values() if len(ns) >= 2
        ]

    @staticmethod
    def _is_anc(a: ShadowNode, b: ShadowNode) -> bool:
        cur = b.parent
        while cur:
            if cur is a:
                return True
            cur = cur.parent
        return False


# ═══════════════════════════════════════════════════════════════════════════
# CONTAINMENT DAG + POINCARÉ EMBEDDER (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

class ContainmentDAG:
    def __init__(self):
        self.edges: Dict[int, Set[int]] = defaultdict(set)
        self.reverse: Dict[int, Set[int]] = defaultdict(set)
        self.roots: Set[int] = set()

    def build(self, groups: List[TemplateGroup],
              colored_nodes: Dict[int, ColoredNode],
              color_edges: Optional[Set[Tuple[int, int]]] = None):
        h2g: Dict[int, int] = {}
        g_height: Dict[int, int] = {}
        g_nodes: Dict[int, Set[int]] = defaultdict(set)

        for g in groups:
            h2g[g.color.template_hash] = g.group_id
            g_height[g.group_id] = g.color.height
            for inst in g.instances:
                g_nodes[g.group_id].add(id(inst.node))

        raw_edges: Set[Tuple[int, int]] = set()

        for g in groups:
            child_gid = g.group_id
            child_height = g.color.height

            for inst in g.instances:
                cursor = inst.node.parent
                while cursor is not None:
                    cn = colored_nodes.get(id(cursor))
                    if cn is not None:
                        parent_gid = h2g.get(cn.color.template_hash)
                        if parent_gid is not None and parent_gid != child_gid:
                            parent_height = g_height.get(parent_gid, 0)
                            if parent_height > child_height:
                                raw_edges.add((parent_gid, child_gid))
                            break
                    cursor = cursor.parent

        for pg, cg in raw_edges:
            self.edges[pg].add(cg)
            self.reverse[cg].add(pg)

        self._transitive_reduce()
        self.roots = {g.group_id for g in groups} - set(self.reverse)

        for g in groups:
            g.parent_group_ids = set(self.reverse.get(g.group_id, set()))
            g.child_group_ids = set(self.edges.get(g.group_id, set()))

    def _transitive_reduce(self):
        redundant: Set[Tuple[int, int]] = set()
        for parent, children in list(self.edges.items()):
            if len(children) < 2:
                continue
            for child in children:
                for sibling in children:
                    if sibling == child:
                        continue
                    if self._reachable(sibling, child, exclude_direct={parent}):
                        redundant.add((parent, child))
                        break

        for pg, cg in redundant:
            self.edges[pg].discard(cg)
            self.reverse[cg].discard(pg)

    def _reachable(self, source: int, target: int,
                   exclude_direct: Set[int], _max_depth: int = 10) -> bool:
        visited = set()
        frontier = [source]
        for _ in range(_max_depth):
            if not frontier:
                return False
            nxt = []
            for n in frontier:
                if n == target:
                    return True
                if n in visited:
                    continue
                visited.add(n)
                for ch in self.edges.get(n, set()):
                    if ch not in visited:
                        nxt.append(ch)
            frontier = nxt
        return False

    def depth(self, gid: int, _m: Optional[Dict[int,int]] = None,
              _visiting: Optional[Set[int]] = None) -> int:
        if _m is None: _m = {}
        if _visiting is None: _visiting = set()
        if gid in _m: return _m[gid]
        if gid in _visiting: return 0
        _visiting.add(gid)
        ps = self.reverse.get(gid, set())
        d = 0 if not ps else 1 + min(self.depth(p, _m, _visiting) for p in ps)
        _visiting.discard(gid)
        _m[gid] = d
        return d


# ═══════════════════════════════════════════════════════════════════════════
# ZHANG-SHASHA TREE EDIT DISTANCE (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════
#
# Replaces the heuristic PoincaréBallEmbedder and _containment_ratio
# with a formal mathematical proof of structural redundancy.
#
# The Zhang-Shasha algorithm computes the minimum number of node
# insertions, deletions, and relabelings required to transform one
# ordered rooted tree into another. For subsumption checking, a low
# TED between a parent group's representative subtree and a child
# group's representative subtree proves that the parent is a thin
# structural wrapper adding negligible semantic value.
#
# Complexity: O(|T₁| × |T₂| × min(depth₁, leaves₁) × min(depth₂, leaves₂))
# With max_depth=4 truncation: effectively O(1) per comparison.
#
# Reference: K. Zhang and D. Shasha, "Simple Fast Algorithms for the
# Editing Distance between Trees and Related Problems", SIAM J. Comput. 1989.

MAX_SUBSUME_TED = 3    # parent wrapper (1) + up to 2 decorative siblings
TED_MAX_DEPTH = 4      # truncate subtrees for performance

# ── Phase 4a: MCS + Hungarian Algorithm ──
MCS_MAX_DEPTH = 4          # truncate subtrees for MCS computation
MCS_MERGE_THRESHOLD = 0.80 # merge if MCS covers ≥ 80% of smaller tree
MCS_MIN_NODES = 3          # don't bother comparing trivially small trees


def _ted_linearize(node: ShadowNode, max_depth: int = TED_MAX_DEPTH
                   ) -> Tuple[List[str], List[int], List[int]]:
    """Linearize a DOM subtree into postorder for Zhang-Shasha.

    Traverses the tree in left-to-right postorder, truncated at
    max_depth. Returns three parallel arrays:

      labels[i]  — tag name of node i (postorder index, 1-based)
      l_vals[i]  — leftmost leaf descendant of node i (1-based)
      parents[i] — parent index of node i (0 = root has no parent)

    The 0-th index in each array is unused (sentinel).
    """
    labels: List[str] = ['']   # 1-indexed sentinel
    l_vals: List[int] = [0]
    parents: List[int] = [0]

    # Stack-based postorder with depth tracking
    # Each entry: (node, depth, parent_postorder_idx, children_processed)
    index_map: Dict[int, int] = {}  # id(node) → postorder index

    def _recurse(n: ShadowNode, depth: int, par_idx: int):
        tag = n.tag.lower()
        if tag in SKIP_TAGS or tag.startswith('#'):
            return

        children = []
        if depth < max_depth:
            for c in n.get_children(include_shadow=True):
                ct = c.tag.lower()
                if ct in SKIP_TAGS or ct.startswith('#'):
                    continue
                if ct in DOCUMENT_TAGS:
                    # Pass through document tags
                    for gc in c.get_children(include_shadow=True):
                        gct = gc.tag.lower()
                        if gct not in SKIP_TAGS and not gct.startswith('#'):
                            children.append(gc)
                else:
                    children.append(c)

        # Recurse children first (postorder: children before parent)
        my_idx = -1  # will be assigned after children
        for child in children:
            _recurse(child, depth + 1, -1)  # parent set below

        # Assign postorder index
        my_idx = len(labels)  # next available 1-based index
        labels.append(tag)
        index_map[id(n)] = my_idx

        # Leftmost leaf descendant
        if not children or depth >= max_depth:
            l_vals.append(my_idx)  # leaf: leftmost is self
        else:
            # Leftmost leaf is the leftmost leaf of first child
            first_child_idx = index_map.get(id(children[0]))
            if first_child_idx is not None and first_child_idx < len(l_vals):
                l_vals.append(l_vals[first_child_idx])
            else:
                l_vals.append(my_idx)

        parents.append(par_idx)

        # Fix parent references for children
        for child in children:
            child_idx = index_map.get(id(child))
            if child_idx is not None and child_idx < len(parents):
                parents[child_idx] = my_idx

    _recurse(node, 0, 0)
    return labels, l_vals, parents


def zhang_shasha_ted(
    tree1: ShadowNode,
    tree2: ShadowNode,
    max_depth: int = TED_MAX_DEPTH,
) -> int:
    """Compute the Zhang-Shasha Tree Edit Distance between two subtrees.

    Returns the minimum number of node insertions, deletions, and
    relabelings (tag-name substitutions) to transform tree1 into tree2.

    Args:
        tree1, tree2: root ShadowNode of each subtree
        max_depth: truncate trees at this depth for performance

    Returns:
        Integer edit distance. 0 = identical trees.
    """
    labels1, l1, parents1 = _ted_linearize(tree1, max_depth)
    labels2, l2, parents2 = _ted_linearize(tree2, max_depth)

    n1 = len(labels1) - 1  # number of nodes in tree1
    n2 = len(labels2) - 1  # number of nodes in tree2

    if n1 == 0 and n2 == 0:
        return 0
    if n1 == 0:
        return n2
    if n2 == 0:
        return n1

    # ── Compute keyroots ──
    # A keyroot is a node whose leftmost-leaf-descendant differs
    # from its parent's leftmost-leaf-descendant, plus the tree root.
    def _keyroots(l_vals, parents, n):
        kr = set()
        for i in range(1, n + 1):
            p = parents[i]
            if p == 0 or l_vals[i] != l_vals[p]:
                kr.add(i)
        return sorted(kr)

    kr1 = _keyroots(l1, parents1, n1)
    kr2 = _keyroots(l2, parents2, n2)

    # ── Tree distance matrix ──
    td = [[0] * (n2 + 1) for _ in range(n1 + 1)]

    # ── Forest distance computation for each keyroot pair ──
    for x in kr1:
        for y in kr2:
            # Compute forest distance for subtrees rooted at x and y
            lx = l1[x]
            ly = l2[y]

            # fd[i][j] = forest distance between
            #   forest of nodes l1[x]..i  and  forest of nodes l2[y]..j
            m = x - lx + 2
            k = y - ly + 2
            fd = [[0] * k for _ in range(m)]

            # Base cases
            fd[0][0] = 0
            for i in range(1, m):
                fd[i][0] = fd[i - 1][0] + 1  # delete
            for j in range(1, k):
                fd[0][j] = fd[0][j - 1] + 1  # insert

            for i in range(1, m):
                for j in range(1, k):
                    ni = lx + i - 1  # actual node index in tree1
                    nj = ly + j - 1  # actual node index in tree2

                    cost_del = fd[i - 1][j] + 1
                    cost_ins = fd[i][j - 1] + 1

                    if l1[ni] == lx and l2[nj] == ly:
                        # Both are in the same "leftmost path" as their
                        # respective keyroots — tree distance case
                        relabel = 0 if labels1[ni] == labels2[nj] else 1
                        cost_match = fd[i - 1][j - 1] + relabel
                        fd[i][j] = min(cost_del, cost_ins, cost_match)
                        td[ni][nj] = fd[i][j]
                    else:
                        # Forest distance case — use previously computed
                        # tree distances
                        li = l1[ni] - lx
                        lj = l2[nj] - ly
                        cost_match = fd[li][lj] + td[ni][nj]
                        fd[i][j] = min(cost_del, cost_ins, cost_match)

    return td[n1][n2]


# ═══════════════════════════════════════════════════════════════════════════
# MAXIMUM COMMON SUBTREE (MCS) + HUNGARIAN ALGORITHM — Phase 4a
# ═══════════════════════════════════════════════════════════════════════════

def _mcs_count_nodes(node: ShadowNode, max_depth: int = MCS_MAX_DEPTH,
                     _depth: int = 0) -> int:
    """Count structural nodes in a depth-truncated subtree."""
    tag = node.tag.lower()
    if tag in SKIP_TAGS or tag.startswith('#'):
        return 0
    count = 1
    if _depth >= max_depth:
        return count
    for child in node.get_children(include_shadow=True):
        ct = child.tag.lower()
        if ct in SKIP_TAGS or ct.startswith('#'):
            continue
        if ct in DOCUMENT_TAGS:
            for gc in child.get_children(include_shadow=True):
                count += _mcs_count_nodes(gc, max_depth, _depth + 1)
        else:
            count += _mcs_count_nodes(child, max_depth, _depth + 1)
    return count


def _mcs_get_structural_children(node: ShadowNode) -> List[ShadowNode]:
    """Return direct structural children, passing through DOCUMENT_TAGS."""
    children = []
    for child in node.get_children(include_shadow=True):
        ct = child.tag.lower()
        if ct in SKIP_TAGS or ct.startswith('#'):
            continue
        if ct in DOCUMENT_TAGS:
            for gc in child.get_children(include_shadow=True):
                gct = gc.tag.lower()
                if gct not in SKIP_TAGS and not gct.startswith('#'):
                    children.append(gc)
        else:
            children.append(child)
    return children


def mcs_bipartite(
    tree1: ShadowNode, tree2: ShadowNode,
    max_depth: int = MCS_MAX_DEPTH, _depth: int = 0,
) -> int:
    """Compute Maximum Common Subtree size using Hungarian matching.

    Children are matched via scipy.optimize.linear_sum_assignment,
    making the comparison resilient to CSS-reordered elements.
    """
    tag1 = tree1.tag.lower()
    tag2 = tree2.tag.lower()
    if tag1 in SKIP_TAGS or tag1.startswith('#'):
        return 0
    if tag2 in SKIP_TAGS or tag2.startswith('#'):
        return 0
    if tag1 != tag2:
        return 0
    if _depth >= max_depth:
        return 1

    children1 = _mcs_get_structural_children(tree1)
    children2 = _mcs_get_structural_children(tree2)
    if not children1 or not children2:
        return 1

    n1, n2 = len(children1), len(children2)
    score_matrix = [[mcs_bipartite(c1, c2, max_depth, _depth + 1)
                     for c2 in children2] for c1 in children1]

    size = max(n1, n2)
    padded = [[0] * size for _ in range(size)]
    for i in range(n1):
        for j in range(n2):
            padded[i][j] = score_matrix[i][j]

    try:
        from scipy.optimize import linear_sum_assignment
        import numpy as np
        cost = np.array([[-padded[i][j] for j in range(size)]
                         for i in range(size)])
        row_ind, col_ind = linear_sum_assignment(cost)
        total = sum(padded[r][c] for r, c in zip(row_ind, col_ind)
                    if r < n1 and c < n2)
    except ImportError:
        used: Set[int] = set()
        total = 0
        for i in sorted(range(n1),
                        key=lambda i: max(score_matrix[i]), reverse=True):
            best_j, best_s = -1, 0
            for j in range(n2):
                if j not in used and score_matrix[i][j] > best_s:
                    best_s, best_j = score_matrix[i][j], j
            if best_j >= 0 and best_s > 0:
                used.add(best_j)
                total += best_s

    return 1 + total


def _extract_mcs_skeleton(tree1: ShadowNode, tree2: ShadowNode, max_depth: int = MCS_MAX_DEPTH, _depth: int = 0) -> Optional[ShadowNode]:
    """Creates a new virtual ShadowNode containing only the Maximum Common Subtree intersection."""
    tag1, tag2 = tree1.tag.lower(), tree2.tag.lower()
    if tag1 in SKIP_TAGS or tag1.startswith('#') or tag1 != tag2: return None
    
    skeleton_node = ShadowNode(tag=tag1, attributes=tree1.attributes)
    if _depth >= max_depth: return skeleton_node
    
    children1 = _mcs_get_structural_children(tree1)
    children2 = _mcs_get_structural_children(tree2)
    if not children1 or not children2: return skeleton_node

    # Build matching matrix
    try:
        from scipy.optimize import linear_sum_assignment
        import numpy as np
        cost = np.array([[-mcs_bipartite(c1, c2, max_depth, _depth + 1) for c2 in children2] for c1 in children1])
        row_ind, col_ind = linear_sum_assignment(cost)
        
        for r, c in zip(row_ind, col_ind):
            if r < len(children1) and c < len(children2) and cost[r][c] < 0: # If there is a match
                child_skeleton = _extract_mcs_skeleton(children1[r], children2[c], max_depth, _depth + 1)
                if child_skeleton:
                    skeleton_node.children.append(child_skeleton)
    except ImportError:
        pass # Fallback to greedy if scipy missing
    return skeleton_node

def mcs_similarity(
    tree1: ShadowNode, tree2: ShadowNode,
    max_depth: int = MCS_MAX_DEPTH,
) -> float:
    """MCS similarity: MCS_size / min(|T1|, |T2|)."""
    n1 = _mcs_count_nodes(tree1, max_depth)
    n2 = _mcs_count_nodes(tree2, max_depth)
    if n1 == 0 or n2 == 0:
        return 0.0
    return mcs_bipartite(tree1, tree2, max_depth) / min(n1, n2)


class MCSGroupMerger:
    """Merge TemplateGroups with near-isomorphic subtree structures.

    Uses MCS + Hungarian matching to find groups that should be merged
    despite having different WL template_hashes (e.g., due to injected
    tracking spans or optional metadata elements).
    """

    def __init__(self, verbose: bool = False):
        self._log = print if verbose else lambda *a, **k: None

    def merge(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        if len(groups) < 2:
            return groups

        by_tag: Dict[str, List[int]] = defaultdict(list)
        for idx, g in enumerate(groups):
            by_tag[g.color.tag].append(idx)

        parent_uf = list(range(len(groups)))

        def find(x):
            while parent_uf[x] != x:
                parent_uf[x] = parent_uf[parent_uf[x]]
                x = parent_uf[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent_uf[rb] = ra

        merge_count = 0
        for tag, indices in by_tag.items():
            if len(indices) < 2:
                continue
            valid = [i for i in indices
                     if groups[i].color.height >= 1
                     and groups[i].instances
                     and _mcs_count_nodes(groups[i].instances[0].node,
                                          MCS_MAX_DEPTH) >= MCS_MIN_NODES]
            if len(valid) < 2:
                continue

            for ai in range(len(valid)):
                for bi in range(ai + 1, len(valid)):
                    i, j = valid[ai], valid[bi]
                    if find(i) == find(j):
                        continue
                    gi, gj = groups[i], groups[j]
                    if abs(gi.color.height - gj.color.height) > 1:
                        continue
                    sim = mcs_similarity(gi.instances[0].node,
                                         gj.instances[0].node, MCS_MAX_DEPTH)
                    if sim >= MCS_MERGE_THRESHOLD:
                        union(i, j)
                        merge_count += 1
                        self._log(f"[MCS] Merge gid={gi.group_id} ↔ gid={gj.group_id} "
                                  f"(tag={tag}, sim={sim:.2f})")

        if merge_count == 0:
            return groups

        components: Dict[int, List[int]] = defaultdict(list)
        for idx in range(len(groups)):
            components[find(idx)].append(idx)

        merged: List[TemplateGroup] = []
        for root_idx, member_indices in components.items():
            if len(member_indices) == 1:
                merged.append(groups[member_indices[0]])
            else:
                member_groups = [groups[i] for i in member_indices]
                base = max(member_groups, key=lambda g: (g.color.height, g.frequency))
                all_instances = []
                seen_ids: Set[int] = set()
                for g in member_groups:
                    for inst in g.instances:
                        nid = id(inst.node)
                        if nid not in seen_ids:
                            seen_ids.add(nid)
                            all_instances.append(inst)
                base.instances = all_instances
                
                # Extract the canonical intersection skeleton from the two most representative members
                if len(member_groups) >= 2:
                    base.canonical_template = _extract_mcs_skeleton(member_groups[0].instances[0].node, member_groups[1].instances[0].node)
                    
                # Phase 5: Induce PQ-Tree for the merged group
                base.pq_tree = induce_pq_tree(
                    [inst.node for inst in all_instances[:10]],
                    max_depth=MCS_MAX_DEPTH,
                )
                merged.append(base)
                self._log(f"[MCS] Consolidated {len(member_indices)} groups → "
                          f"gid={base.group_id} (freq={len(all_instances)}, "
                          f"pq={base.pq_signature[:60]})")

        self._log(f"[MCS] {len(groups)} groups → {len(merged)} after MCS merge")
        return merged


# ═══════════════════════════════════════════════════════════════════════════
# SUBSUMPTION FILTER (with container exemption)
# ═══════════════════════════════════════════════════════════════════════════

class SubsumptionFilter:
    def __init__(
        self,
        groups: List[TemplateGroup],
        dag: ContainmentDAG,
        colored_nodes: Dict[int, ColoredNode],
        verbose: bool = False,
    ):
        self.groups = groups
        self.dag = dag
        self.colored_nodes = colored_nodes
        self._log = print if verbose else lambda *a, **k: None
        self._gid_to_group: Dict[int, TemplateGroup] = {
            g.group_id: g for g in groups
        }

    def _is_container(self, g: TemplateGroup) -> bool:
        """Check if group has a container class token."""
        for inst in g.instances[:3]:
            cls = inst.node.get_attr('class', '')
            if cls and any(token in cls for token in CONTAINER_CLASS_TOKENS):
                return True
        return False

    def filter(self) -> List[TemplateGroup]:
        top_gids = self._detect_top_elements()
        for gid in top_gids:
            self._gid_to_group[gid].suppressed = True
        self._log(f"[SUB] ⊤ elements: {sorted(top_gids)} ({len(top_gids)} suppressed)")

        sub_gids = self._geometric_subsume(top_gids)
        self._log(f"[SUB] Sub-components: {sorted(sub_gids)} ({len(sub_gids)} suppressed)")

        all_suppressed = top_gids | sub_gids
        abs_gids = self._geometric_orphan_absorption(all_suppressed)
        self._log(f"[SUB] Orphans absorbed: {sorted(abs_gids)} ({len(abs_gids)} suppressed)")

        leaf_gids = self._absorb_leaves(all_suppressed | abs_gids)
        self._log(f"[SUB] Leaf fragments: {sorted(leaf_gids)} ({len(leaf_gids)} suppressed)")

        all_suppressed |= abs_gids | leaf_gids
        triv_gids = self._suppress_trivial_leaves(all_suppressed)
        self._log(f"[SUB] Trivial leaves: {sorted(triv_gids)} ({len(triv_gids)} suppressed)")

        all_suppressed |= triv_gids
        surviving = [g for g in self.groups if g.group_id not in all_suppressed]
        self._log(f"[SUB] Surviving: {len(surviving)}/{len(self.groups)} groups (pre-antichain)")

        ac_gids = self._antichain_prune(surviving)
        self._log(f"[SUB] Antichain pruned: {sorted(ac_gids)} ({len(ac_gids)} suppressed)")

        all_suppressed |= ac_gids
        surviving = [g for g in self.groups if g.group_id not in all_suppressed]
        self._log(f"[SUB] Final: {len(surviving)}/{len(self.groups)} groups")
        return surviving

    def _detect_top_elements(self) -> Set[int]:
        total_content = sum(
            1 for cn in self.colored_nodes.values()
            if cn.is_content_bearing
        )
        if total_content == 0:
            return set()

        top_gids: Set[int] = set()
        memo_depth: Dict[int, int] = {}
        visiting_depth: Set[int] = set()
        for g in self.groups:
            if self._is_container(g):
                continue  # containers are never ⊤
            if g.frequency > TOP_MAX_FREQ:
                continue
            # Skip groups deep in the DAG — they're sub-components,
            # not page-level ⊤ elements (replaces Poincaré busemann check)
            dag_d = self.dag.depth(g.group_id, memo_depth, visiting_depth)
            if dag_d >= 2:
                continue
            counts = sorted(cn.subtree_content_count for cn in g.instances)
            median_content = counts[len(counts) // 2]
            ratio = median_content / total_content
            if ratio > TOP_CONTENT_RATIO:
                top_gids.add(g.group_id)
                self._log(f"[SUB] ⊤ gid={g.group_id} (f={g.frequency}, h={g.color.height}, content={median_content}/{total_content} = {ratio:.0%})")
        return top_gids

    def _geometric_subsume(self, top_gids: Set[int]) -> Set[int]:
        """TED-based structural subsumption.

        For each group (deepest-first), check DAG ancestors. If the
        structural distance between the group's representative instance
        and an ancestor's representative is small (TED ≤ MAX_SUBSUME_TED),
        the group is a redundant sub-component — suppress it.

        Falls back to physical DOM containment for groups where TED
        computation is ambiguous (e.g., very different heights).
        """
        suppressed: Set[int] = set()
        group_node_ids: Dict[int, Set[int]] = {}
        for g in self.groups:
            group_node_ids[g.group_id] = {id(inst.node) for inst in g.instances}

        memo: Dict[int, int] = {}
        visiting: Set[int] = set()
        depth_ordered = sorted(
            self.groups,
            key=lambda g: self.dag.depth(g.group_id, memo, visiting),
            reverse=True,
        )

        for g in depth_ordered:
            gid = g.group_id
            if gid in top_gids or gid in suppressed:
                continue

            ancestors = self._collect_dag_ancestors(gid, top_gids)

            for anc_gid in ancestors:
                anc_g = self._gid_to_group.get(anc_gid)
                if not anc_g or anc_gid in top_gids:
                    continue

                anc_children = self.dag.edges.get(anc_gid, set())
                if len(anc_children) < SUBSUME_MIN_CHILDREN:
                    continue

                # ── TED-based structural redundancy check ──
                ted = self._structural_ted(g, anc_g)
                structurally_subsumed = (ted <= MAX_SUBSUME_TED)

                # ── Fallback: physical DOM containment ──
                if not structurally_subsumed:
                    ratio = self._containment_ratio(
                        g, group_node_ids.get(anc_gid, set())
                    )
                    if ratio >= SUBSUME_RATIO:
                        structurally_subsumed = True

                if structurally_subsumed:
                    if self._is_container(g):
                        continue
                    g.suppressed = True
                    g.suppressed_by = anc_gid
                    suppressed.add(gid)
                    self._log(
                        f"[SUB] gid={gid:3d}(f={g.frequency:4d},h={g.color.height}) "
                        f"⊂ gid={anc_gid:3d}(f={anc_g.frequency:4d},h={anc_g.color.height}) "
                        f"TED={ted}"
                    )
                    break

            if gid not in suppressed:
                direct_parents = [
                    pid for pid in self.dag.reverse.get(gid, set())
                    if pid not in top_gids
                ]
                if len(direct_parents) >= 2:
                    union_ids: Set[int] = set()
                    for pid in direct_parents:
                        union_ids |= group_node_ids.get(pid, set())
                    ratio = self._containment_ratio(g, union_ids)
                    if ratio >= SUBSUME_RATIO:
                        live = [p for p in direct_parents if p not in suppressed]
                        pool = live if live else direct_parents
                        best = max(
                            pool,
                            key=lambda p: self._gid_to_group[p].frequency
                            if p in self._gid_to_group else 0,
                        )
                        g.suppressed = True
                        g.suppressed_by = best
                        suppressed.add(gid)
                        self._log(
                            f"[SUB] gid={gid:3d}(f={g.frequency:4d},h={g.color.height}) "
                            f"⊂ union({','.join(str(p) for p in sorted(direct_parents))}) "
                            f"at {ratio:.0%}"
                        )

        return suppressed

    def _geometric_orphan_absorption(self, already_suppressed: Set[int]) -> Set[int]:
        absorbed: Set[int] = set()
        total_content = sum(
            1 for cn in self.colored_nodes.values()
            if cn.is_content_bearing
        )

        orphans = [
            g for g in self.groups
            if g.group_id not in already_suppressed
            and not self.dag.reverse.get(g.group_id)
            and not self.dag.edges.get(g.group_id)
        ]
        if not orphans:
            return absorbed

        for o in orphans:
            if o.frequency <= TOP_MAX_FREQ and not self._is_container(o):
                counts = sorted(cn.subtree_content_count for cn in o.instances)
                median = counts[len(counts) // 2]
                if total_content > 0 and median / total_content > TOP_CONTENT_RATIO:
                    o.suppressed = True
                    o.suppressed_by = -1
                    absorbed.add(o.group_id)
                    self._log(f"[SUB] Orphan ⊤ gid={o.group_id} (content={median}/{total_content})")

        orphan_ids = {o.group_id for o in orphans}
        parents = [
            g for g in self.groups
            if g.group_id not in already_suppressed
            and g.group_id not in absorbed
            and g.group_id not in orphan_ids
        ]

        surviving_node_ids: Dict[int, Set[int]] = {}
        for sg in parents:
            surviving_node_ids[sg.group_id] = {
                id(inst.node) for inst in sg.instances
            }

        for o in orphans:
            if o.group_id in absorbed:
                continue

            dom_absorbed = False
            for sg in parents:
                ratio = self._containment_ratio(
                    o, surviving_node_ids.get(sg.group_id, set())
                )
                if ratio >= SUBSUME_RATIO:
                    o.suppressed = True
                    o.suppressed_by = sg.group_id
                    absorbed.add(o.group_id)
                    self._log(f"[SUB] Orphan gid={o.group_id:3d} absorbed into gid={sg.group_id:3d} at {ratio:.0%}")
                    dom_absorbed = True
                    break

            if not dom_absorbed:
                # TED-based nearest structural match (replaces Poincaré distance)
                best_gid = None
                best_ted = float('inf')
                for p in parents:
                    if p.color.height <= o.color.height:
                        continue  # parent must be structurally richer
                    ted = self._structural_ted(o, p)
                    if ted < best_ted:
                        best_ted = ted
                        best_gid = p.group_id
                if best_gid is not None and best_ted <= MAX_SUBSUME_TED:
                    o.suppressed = True
                    o.suppressed_by = best_gid
                    absorbed.add(o.group_id)
                    self._log(f"[SUB] Orphan gid={o.group_id:3d} absorbed by gid={best_gid:3d} (TED={best_ted})")

        return absorbed

    def _absorb_leaves(self, already_suppressed: Set[int]) -> Set[int]:
        absorbed: Set[int] = set()
        surviving_node_ids: Dict[int, Set[int]] = {}
        for g in self.groups:
            if g.group_id not in already_suppressed:
                surviving_node_ids[g.group_id] = {
                    id(inst.node) for inst in g.instances
                }

        for g in self.groups:
            gid = g.group_id
            if gid in already_suppressed:
                continue
            if g.color.height > 1:
                continue
            dag_children = self.dag.edges.get(gid, set())
            if dag_children:
                continue

            all_ancestors = self._collect_dag_ancestors(
                gid, already_suppressed | absorbed, max_depth=15
            )
            live_parents = [
                pid for pid in all_ancestors
                if pid not in already_suppressed and pid not in absorbed
            ]
            if not live_parents:
                continue

            union_parent_ids: Set[int] = set()
            for pid in live_parents:
                union_parent_ids |= surviving_node_ids.get(pid, set())

            if not union_parent_ids:
                continue

            inside = 0
            for inst in g.instances:
                cursor = inst.node.parent
                while cursor is not None:
                    if id(cursor) in union_parent_ids:
                        inside += 1
                        break
                    cursor = cursor.parent
            ratio = inside / len(g.instances)

            if ratio >= SUBSUME_RATIO:
                best_parent = max(
                    live_parents,
                    key=lambda pid: self._gid_to_group[pid].frequency
                    if pid in self._gid_to_group else 0,
                )
                g.suppressed = True
                g.suppressed_by = best_parent
                absorbed.add(gid)
                self._log(
                    f"[SUB] Leaf gid={gid:3d}(f={g.frequency:4d},h={g.color.height}) "
                    f"⊂ union({','.join(str(p) for p in live_parents)}) "
                    f"at {ratio:.0%}"
                )

        return absorbed

    def _suppress_trivial_leaves(self, already_suppressed: Set[int]) -> Set[int]:
        trivial: Set[int] = set()
        for g in self.groups:
            gid = g.group_id
            if gid in already_suppressed:
                continue
            if g.color.height > 1:
                continue
            if g.frequency < TRIVIAL_MIN_FREQ:
                continue
            dag_children = self.dag.edges.get(gid, set())
            if dag_children:
                continue

            hashes: Set[int] = set()
            texts: List[int] = []
            for inst in g.instances:
                h = hash(inst.subtree_text_len)
                for desc in inst.node.iter_all():
                    if desc.tag.lower() in ('img', 'source'):
                        src = desc.get_attr('src') or desc.get_attr('data-src')
                        if src:
                            h ^= hash(src)
                hashes.add(h)
                texts.append(inst.subtree_text_len)

            if not texts:
                continue

            uniqueness = len(hashes) / len(texts)
            avg_len = sum(texts) / len(texts)

            if uniqueness < UNIQUENESS_THRESHOLD and avg_len < 15:
                g.suppressed = True
                g.suppressed_by = -2
                trivial.add(gid)
                self._log(
                    f"[SUB] Trivial gid={gid:3d}(f={g.frequency:4d},h={g.color.height}) "
                    f"avg_text={avg_len:.0f}ch uniqueness={uniqueness:.2f} "
                    f"unique={len(hashes)}/{len(texts)}"
                )

        return trivial

    def _antichain_prune(self, surviving: List[TemplateGroup]) -> Set[int]:
        surv_gids = {g.group_id for g in surviving}
        if not surviving:
            return set()

        comparable = 0
        for g in surviving:
            children = self.dag.edges.get(g.group_id, set()) & surv_gids
            comparable += len(children)
        if comparable == 0:
            return set()

        def _info_score(g: TemplateGroup) -> float:
            if g.tier in (ContentTier.SINGLETON, ContentTier.ORPHAN):
                return float('inf')
            all_ct: Set[ContentCategory] = set()
            for inst in g.instances:
                all_ct.update(inst.content_types)
            num_types = max(1, len(all_ct))
            texts = [inst.subtree_text_len for inst in g.instances]
            avg = sum(texts) / max(1, len(texts))
            var = sum((t - avg) ** 2 for t in texts) / max(1, len(texts))
            H = math.log1p(var) if var > 0 else 0.0
            content_count = max(1, g.instances[0].subtree_content_count)
            return (g.frequency * num_types * (1 + H)
                    / (1 + math.log2(content_count)))

        scores: Dict[int, float] = {g.group_id: _info_score(g) for g in surviving}

        selected: Set[int] = set()
        shadowed: Set[int] = set()
        pruned: Set[int] = set()

        for g in sorted(surviving, key=lambda g: scores.get(g.group_id, 0),
                        reverse=True):
            gid = g.group_id
            if gid in shadowed:
                g.suppressed = True
                g.suppressed_by = -3
                pruned.add(gid)
                continue

            selected.add(gid)

            frontier = list(self.dag.reverse.get(gid, set()) & surv_gids)
            while frontier:
                nxt = []
                for pid in frontier:
                    if pid not in shadowed and pid not in selected:
                        shadowed.add(pid)
                        nxt.extend(self.dag.reverse.get(pid, set()) & surv_gids)
                frontier = nxt

            frontier = list(self.dag.edges.get(gid, set()) & surv_gids)
            while frontier:
                nxt = []
                for cid in frontier:
                    if cid not in shadowed and cid not in selected:
                        shadowed.add(cid)
                        nxt.extend(self.dag.edges.get(cid, set()) & surv_gids)
                frontier = nxt

        if pruned:
            self._log(f"[SUB] Antichain: selected {len(selected)}, pruned {len(pruned)} comparable groups")

        return pruned

    def _collect_dag_ancestors(
        self, gid: int, exclude: Set[int], max_depth: int = 10,
    ) -> List[int]:
        ancestors: List[int] = []
        visited: Set[int] = {gid}
        frontier = list(self.dag.reverse.get(gid, set()))
        depth = 0
        while frontier and depth < max_depth:
            next_frontier: List[int] = []
            for parent in frontier:
                if parent in visited or parent in exclude:
                    continue
                visited.add(parent)
                ancestors.append(parent)
                next_frontier.extend(self.dag.reverse.get(parent, set()))
            frontier = next_frontier
            depth += 1
        return ancestors

    def _structural_ted(
        self, child_group: TemplateGroup, parent_group: TemplateGroup,
    ) -> int:
        """Compute Zhang-Shasha TED between representative instances.

        Uses the first instance of each group as the canonical
        representative. TED is computed on depth-truncated subtrees
        (TED_MAX_DEPTH=4) for performance.

        Returns:
            Integer edit distance. Low values (≤ MAX_SUBSUME_TED)
            indicate the parent is a thin structural wrapper around
            the child with negligible added semantic value.
        """
        if not child_group.instances or not parent_group.instances:
            return 999
        child_rep = child_group.instances[0].node
        parent_rep = parent_group.instances[0].node
        return zhang_shasha_ted(parent_rep, child_rep, max_depth=TED_MAX_DEPTH)

    def _containment_ratio(
        self, child_group: TemplateGroup, parent_node_ids: Set[int],
    ) -> float:
        if not parent_node_ids or not child_group.instances:
            return 0.0
        inside = 0
        for inst in child_group.instances:
            cursor = inst.node.parent
            while cursor is not None:
                if id(cursor) in parent_node_ids:
                    inside += 1
                    break
                cursor = cursor.parent
        return inside / len(child_group.instances)


# ═══════════════════════════════════════════════════════════════════════════
# SELECTOR GENERATION + CHUNKGROUP BRIDGE
# ═══════════════════════════════════════════════════════════════════════════

class WLSelectorGenerator:
    @classmethod
    def generate(cls, groups: List[TemplateGroup]) -> Dict[int, str]:
        gt: Dict[Tuple[str,str], Set[int]] = defaultdict(set)
        grp_t: Dict[int, FrozenSet[Tuple[str,str]]] = {}
        for g in groups:
            grp_t[g.group_id] = g.color.attr_fingerprint
            for t in g.color.attr_fingerprint:
                gt[t].add(g.group_id)
        n = max(len(groups), 1)
        sels: Dict[int, str] = {}
        for g in groups:
            tag = g.color.tag
            ranked = sorted(grp_t.get(g.group_id, frozenset()),
                           key=lambda t: (len(gt[t]), t))
            preds = [f"contains(@{k},'{v}')" for k, v in ranked[:3]
                     if len(gt[(k,v)]) <= n * 0.4]
            sels[g.group_id] = f"//{tag}[{']['.join(preds)}]" if preds else f"//{tag}"
        return sels


def _to_chunk(tg: TemplateGroup, sel: str = "", dom=None) -> ChunkGroup:
    paths = [cn.xpath for cn in tg.instances]
    nodes = [cn.node for cn in tg.instances]

    tag = tg.color.tag
    fp = sorted(tg.color.attr_fingerprint)[:2]
    sig = f"{tag}.{'.'.join(t[1] for t in fp)}" if fp else tag
    sub = paths[0] if paths else ""
    for p in paths[1:]:
        pa, pb = sub.split('/'), p.split('/')
        c = []
        for a, b in zip(pa, pb):
            if a == b: c.append(a)
            else: break
        sub = '/'.join(c)
    all_t: Set[ContentCategory] = set()
    for cn in tg.instances:
        all_t.update(cn.content_types)

    # Phase 5: Use PQ-Tree canonical signature for _structural_sig.
    # Falls back to template_hash string if no PQ-Tree was induced.
    structural_sig = tg.pq_signature

    return ChunkGroup(
        chunk_id=tg.group_id, selectors=[sel] if sel else [],
        trie_paths=paths, frequency=len(paths),
        content_types=all_t, subtree_root=sub, signature=sig,
        _instance_nodes=nodes,
        _structural_sig=structural_sig,
        _parent_chunk_id=getattr(tg, '_parent_chunk_id', -1),
    )


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL DISTILLER with all integrated refinements
# ═══════════════════════════════════════════════════════════════════════════

class WLDistiller:
    def __init__(self, html: str):
        self.html = html
        self.dom = ShadowDOM(html)
        self.chunks: List[ChunkGroup] = []
        self.template_groups: List[TemplateGroup] = []
        self.containment_dag: Optional[ContainmentDAG] = None
        self.sampler: Optional[ChunkSampler] = None

    # -----------------------------------------------------------------------
    # Helper methods (fingerprinting, canonical href, text boundaries)
    # -----------------------------------------------------------------------

    def _content_fingerprint(self, node: ShadowNode) -> str:
        text = node.get_text().strip()
        text_norm = ' '.join(text.split()).lower()[:CONTENT_FINGERPRINT_MAX_LEN]
        resources = []
        for desc in node.iter_descendants():
            for url in AgnosticAttr.urls_from_node(desc):
                if url and not url.startswith(('#', 'javascript:')):
                    resources.append(url[:200])
        resource_str = '|'.join(sorted(set(resources)))
        return f"{text_norm}||{resource_str}"

    def _canonical_href(self, url: str) -> str:
        if not url:
            return ""
        h = url.strip()
        if len(h) > 1 and h.endswith('/'):
            h = h.rstrip('/')
        if '?' in h:
            path, query = h.split('?', 1)
            h = path.lower() + '?' + query
        else:
            h = h.lower()
        return h

    def _extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from adafruit.com/product/XXXX URLs."""
        match = re.search(r'/product/(\d+)', url)
        if match:
            return match.group(1)
        return None

    def _fix_text_boundaries(self, text: str) -> str:
        """Insert spaces between letters and digits."""
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
        return text

    # ── Media deduplication mask (new) ─────────────────────────────────

    def _build_dedup_mask(self, node: ShadowNode) -> Set[int]:
        """Build a semantic deduplication mask for an instance node."""
        masked = set()

        # Phase 0: mask fallback-copy elements
        for desc in node.iter_descendants():
            if AgnosticAttr.is_fallback_copy(desc):
                masked.add(id(desc))
                for nd in desc.iter_descendants():
                    masked.add(id(nd))

        # Helper: canonical image key
        def _img_key(n: ShadowNode) -> str:
            urls = AgnosticAttr.media_urls(n)
            if not urls:
                return ""
            # Normalise: strip query params and size suffixes
            norm = re.sub(r'[?#].*$', '', urls[0])
            norm = re.sub(r'-\d+x\d+', '', norm)
            return norm

        # Phase 1: detect duplicate picture blocks
        stack = deque([node])
        while stack:
            parent = stack.popleft()
            if id(parent) in masked:
                continue
            children = [c for c in parent.get_children()
                        if not c.tag.startswith('#')
                        and id(c) not in masked]
            if len(children) < 2:
                for c in children:
                    stack.append(c)
                continue

            # Fingerprint each child: combine text and image keys
            fps = {}
            for c in children:
                text = (c.get_text() or '').strip().lower()[:100]
                img_key = _img_key(c)
                # Also consider child's own children for picture containers
                if AgnosticAttr.is_media_container(c):
                    for gc in c.iter_descendants():
                        if gc.tag.lower() in ('img', 'source'):
                            img_key += _img_key(gc)
                fp = (text, img_key)
                fps[id(c)] = (fp, c)

            # Group by fingerprint
            fp_groups = defaultdict(list)
            for nid, (fp, c) in fps.items():
                fp_groups[fp].append(c)

            for fp, members in fp_groups.items():
                if len(members) < 2:
                    for c in members:
                        stack.append(c)
                    continue

                if DEBUG:
                    print(f"[DEBUG DEDUP] Found {len(members)} duplicate siblings at parent {parent.tag}:")
                    for m in members:
                        print(f"    {m.tag} – text: {m.get_text()[:30]}, img_key: {_img_key(m)}")

                # Keep the richest (largest subtree)
                members.sort(key=lambda c: sum(1 for _ in c.iter_descendants()), reverse=True)
                stack.append(members[0])
                for dup in members[1:]:
                    masked.add(id(dup))
                    for d in dup.iter_descendants():
                        masked.add(id(d))

            # Walk children not fingerprinted (too small)
            fps_ids = set(fps.keys())
            for c in children:
                if id(c) not in fps_ids:
                    stack.append(c)

        return masked

    # -----------------------------------------------------------------------
    # Post‑processing phases (from frequency miner)
    # -----------------------------------------------------------------------

    def _deduplicate_content_within_groups(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        result = []
        for g in groups:
            if not g.instances:
                continue
            seen_fp = set()
            unique_instances = []
            for cn in g.instances:
                fp = self._content_fingerprint(cn.node)
                if len(fp.split('||')[0]) < MIN_CONTENT_TEXT_LEN and '||' in fp and not fp.split('||')[1]:
                    continue
                if fp not in seen_fp:
                    seen_fp.add(fp)
                    unique_instances.append(cn)

            if len(unique_instances) < MIN_TEMPLATE_FREQ:
                if DEBUG:
                    print(f"[DEBUG] Dropped group {g.group_id} due to content dedup: freq {g.frequency} -> {len(unique_instances)} < {MIN_TEMPLATE_FREQ}")
                continue

            if len(unique_instances) < g.frequency:
                if DEBUG:
                    print(f"[DEBUG] Content dedup in group {g.group_id}: {g.frequency} → {len(unique_instances)} instances")
                g.instances = unique_instances
            result.append(g)
        return result

    def _is_anchor_interior(self, node: ShadowNode) -> bool:
        if _node_has_nav_url(node):
            return False
        anc = node.parent
        while anc:
            if _node_has_nav_url(anc):
                return True
            if anc.tag.lower() in ('#document', 'html', 'body'):
                return False
            anc = anc.parent
        return False

    def _promote_to_anchor_root(self, nodes: List[ShadowNode]) -> List[ShadowNode]:
        promoted = []
        seen_ids = set()
        for node in nodes:
            anc = node.parent
            while anc:
                if _node_has_nav_url(anc):
                    if id(anc) not in seen_ids:
                        seen_ids.add(id(anc))
                        promoted.append(anc)
                    break
                if anc.tag.lower() in ('#document', 'html', 'body'):
                    break
                anc = anc.parent
        return promoted

    def _split_anchor_interior_groups(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        result = []
        for g in groups:
            if not g.instances:
                continue
            exterior = []
            interior_count = 0
            for cn in g.instances:
                if self._is_anchor_interior(cn.node):
                    interior_count += 1
                else:
                    exterior.append(cn)

            if interior_count == 0:
                result.append(g)
                continue

            if len(exterior) < MIN_TEMPLATE_FREQ:
                promoted_nodes = self._promote_to_anchor_root([cn.node for cn in g.instances])
                if len(promoted_nodes) >= MIN_ANCHOR_PROMOTION_FREQ:
                    synthetic_instances = []
                    for pnode in promoted_nodes:
                        syn = ColoredNode(
                            node=pnode,
                            color=g.color,
                            xpath=cached_xpath(pnode),
                            depth=0,
                            is_content_bearing=True,
                            is_structural_hub=False,
                            is_anchor_descendant=False,
                            content_types=frozenset(),
                            subtree_text_len=len(pnode.get_text().strip()),
                            subtree_content_count=1,
                            subtree_link_count=len(URLExtractor.extract_from_node(pnode)),
                        )
                        synthetic_instances.append(syn)
                    g.instances = synthetic_instances
                    if DEBUG:
                        print(f"[DEBUG] Anchor promotion in group {g.group_id}: all interior → {len(synthetic_instances)} instances")
                    result.append(g)
                else:
                    if DEBUG:
                        print(f"[DEBUG] Dropped group {g.group_id} (all interior, promotion insufficient)")
                continue

            if DEBUG:
                print(f"[DEBUG] Anchor split in group {g.group_id}: {g.frequency} → {len(exterior)} instances (removed {interior_count} interior)")
            g.instances = exterior
            result.append(g)
        return result

    def _precontraction_root(self, node: ShadowNode) -> ShadowNode:
        current = node
        while current.parent:
            parent = current.parent
            element_children = 0
            for c in parent.get_children(include_shadow=True):
                t = c.tag.lower()
                if t.startswith('#') and t != '#shadow-root':
                    continue
                if t in SKIP_TAGS:
                    continue
                element_children += 1
                if element_children >= 2:
                    break
            if element_children == 1:
                current = parent
            else:
                break
        return current

    def _refine_homogeneity(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        """
        Split groups whose instances have different ordered subtree signatures,
        but merge all instances into the largest variant to avoid data loss.
        """
        refined = []
        for g in groups:
            if not g.instances:
                continue
            sig_groups = defaultdict(list)
            for cn in g.instances:
                root = self._precontraction_root(cn.node)
                sig = get_ordered_subtree_signature(root, max_depth=ORDERED_SIG_DEPTH)
                sig_groups[sig].append(cn)

            if len(sig_groups) == 1:
                # All instances have identical ordered structure
                # Induce PQ-Tree (will be a Q-node since order is consistent)
                g.pq_tree = induce_pq_tree(
                    [cn.node for cn in g.instances[:5]],
                    max_depth=ORDERED_SIG_DEPTH,
                )
                refined.append(g)
                continue

            if DEBUG:
                print(f"[DEBUG HOMOGENEITY] Group {g.group_id} has {len(sig_groups)} variants, merging into largest")

            # Find the largest variant
            largest_sig = max(sig_groups, key=lambda s: len(sig_groups[s]))
            largest_instances = sig_groups[largest_sig]
            # Merge all other variants into the largest
            for sig, members in sig_groups.items():
                if sig == largest_sig:
                    continue
                largest_instances.extend(members)

            # Create a new group with all instances
            new_g = TemplateGroup(
                group_id=-1,
                color=largest_instances[0].color,
                instances=largest_instances,
                tier=g.tier,
                parent_group_ids=set(),
                child_group_ids=set(),
                suppressed=False,
                _parent_chunk_id=getattr(g, '_parent_chunk_id', -1),
            )
            # Phase 5: Induce PQ-Tree from merged instances.
            # Since variants have different child orderings, the PQ-Tree
            # will contain P-nodes for permutable positions.
            new_g.pq_tree = induce_pq_tree(
                [cn.node for cn in largest_instances[:10]],
                max_depth=ORDERED_SIG_DEPTH,
            )
            refined.append(new_g)
            if DEBUG:
                pqs = new_g.pq_signature
                print(f"[DEBUG] Homogeneity: merged {len(sig_groups)} variants, "
                      f"PQ-sig={pqs[:80]}")

        return refined

    def _merge_resource_affinity(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        """Merge chunks that share the same primary href (decoupled columns)."""
        href_map = defaultdict(list)
        for g in groups:
            href = None
            for inst in g.instances[:3]:
                u = AgnosticAttr.primary_url(inst.node)
                if u:
                    href = self._canonical_href(u)
                    break
            if href:
                href_map[href].append(g)
            else:
                href_map[None].append(g)

        merged = []
        for href, grps in href_map.items():
            if href is None or len(grps) == 1:
                merged.extend(grps)
            else:
                base = max(grps, key=lambda g: g.color.height)
                all_instances = []
                for g in grps:
                    all_instances.extend(g.instances)
                base.instances = all_instances
                merged.append(base)
                if DEBUG:
                    print(f"[DEBUG MERGE] Merged {len(grps)} groups with same href: {href}")
        return merged

    def _merge_adjacent_siblings(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        """
        Merge groups whose instances are siblings under the same parent.
        This helps combine decoupled image/text columns (e.g., crystal cards).
        """
        parent_to_groups = defaultdict(list)
        for g in groups:
            if not g.instances:
                continue
            parent = g.instances[0].node.parent
            if parent:
                parent_to_groups[id(parent)].append(g)

        merged = []
        for pid, grps in parent_to_groups.items():
            if len(grps) < 2:
                merged.extend(grps)
            else:
                if DEBUG:
                    print(f"[DEBUG MERGE] Merging {len(grps)} groups under parent {pid}:")
                    for grp in grps:
                        print(f"    group {grp.group_id} (tag {grp.color.tag}, freq {grp.frequency})")
                base = max(grps, key=lambda g: g.color.height)
                all_instances = []
                for g in grps:
                    all_instances.extend(g.instances)
                base.instances = all_instances
                merged.append(base)

        # Add groups that were not merged (their parent had only one group)
        merged_ids = {id(g) for g in merged}
        for g in groups:
            if id(g) not in merged_ids:
                merged.append(g)

        return merged

    # ── CIST Mining (Cross‑Instance Sub‑Template) ──────────────────────

    def _get_original_element_children(self, node: ShadowNode) -> List[ShadowNode]:
        """Return direct element children (no contraction)."""
        children = []
        for child in node.get_children(include_shadow=True):
            tag = child.tag.lower()
            if tag.startswith('#') and tag != '#shadow-root':
                continue
            if tag in SKIP_TAGS:
                continue
            children.append(child)
        return children

    def _is_chunk_composite(self, chunk: TemplateGroup) -> bool:
        """
        Check if chunk is composite: either has ≥2 distinct navigable URLs,
        or has ≥3 direct element children (structural complexity).
        """
        # Check hrefs first
        for node in chunk.instances[:5]:
            urls = set(AgnosticAttr.navigable_urls(node.node))
            if len(urls) >= 2:
                if DEBUG:
                    print(f"[DEBUG CIST] {chunk.group_id} is composite: {len(urls)} URLs")
                return True
        # Fallback: if any instance has ≥3 direct element children that are not skip tags
        for node in chunk.instances[:5]:
            children = [c for c in node.node.get_children()
                        if not c.tag.startswith('#') and c.tag.lower() not in SKIP_TAGS]
            if len(children) >= 3:
                if DEBUG:
                    print(f"[DEBUG CIST] {chunk.group_id} is composite: {len(children)} direct children")
                return True
        if DEBUG:
            print(f"[DEBUG CIST] {chunk.group_id} is NOT composite")
        return False

    def _mine_cross_instance_subtemplates(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        """
        CIST: for each composite chunk, pool descendant cohorts from original tree,
        group by structural signature, and emit as new sub‑templates.
        """
        new_groups: List[TemplateGroup] = []
        existing_node_ids: Set[int] = set()
        for g in groups:
            for inst in g.instances:
                existing_node_ids.add(id(inst.node))

        nodes_containing_existing: Set[int] = set()
        for g in groups:
            for inst in g.instances:
                ancestor = inst.node.parent
                depth = 30
                while ancestor and depth > 0:
                    nodes_containing_existing.add(id(ancestor))
                    ancestor = ancestor.parent
                    depth -= 1

        for g in groups:
            if not self._is_chunk_composite(g):
                continue
            if DEBUG:
                print(f"[DEBUG CIST] Processing composite group {g.group_id} with freq {g.frequency}")

            sig_pool: defaultdict[str, List[ShadowNode]] = defaultdict(list)

            for instance_node in g.instances:
                queue = deque([instance_node.node])
                while queue:
                    node = queue.popleft()
                    children = self._get_original_element_children(node)

                    if len(children) >= 2:
                        for child in children:
                            if id(child) in existing_node_ids:
                                continue
                            if id(child) in nodes_containing_existing:
                                continue
                            sig = cached_signature(child, max_depth=6)
                            sig_pool[sig].append(child)

                    for child in children:
                        if (id(child) not in existing_node_ids
                                and id(child) not in nodes_containing_existing):
                            queue.append(child)

            min_sub_freq = max(MIN_TEMPLATE_FREQ, g.frequency)

            for sig, members in sig_pool.items():
                if len(members) < min_sub_freq:
                    if DEBUG:
                        print(f"[DEBUG CIST] Skipping sig {sig[:40]}: {len(members)} < {min_sub_freq}")
                    continue
                h = signature_height(sig)
                if h < CIST_MIN_HEIGHT:
                    continue
                root_tag = sig.split('(')[0] if '(' in sig else sig
                if root_tag in PRESENTATIONAL_ROOTS:
                    continue

                has_value = any(
                    AgnosticAttr.primary_url(m) for m in members[:10]
                )
                if not has_value:
                    continue

                unique_members = [m for m in members if id(m) not in existing_node_ids]
                if len(unique_members) < min_sub_freq:
                    continue

                # Build synthetic color (use first member's color as base)
                first = unique_members[0]
                fake_color = WLColor(
                    exact_hash=hash(sig),
                    template_hash=hash(sig),
                    tag=first.tag.lower() if hasattr(first, 'tag') else 'unknown',
                    height=h,
                    child_tag_bag=(),
                    attr_fingerprint=frozenset()
                )
                colored_instances = []
                for node in unique_members:
                    cn = ColoredNode(
                        node=node,
                        color=fake_color,
                        xpath=cached_xpath(node),
                        depth=0,
                        is_content_bearing=True,
                        is_structural_hub=False,
                        is_anchor_descendant=False,
                        content_types=frozenset(),
                        subtree_text_len=len(node.get_text()),
                        subtree_content_count=1,
                        subtree_link_count=len(URLExtractor.extract_from_node(node)),
                    )
                    colored_instances.append(cn)

                sub_chunk = TemplateGroup(
                    group_id=-1,
                    color=fake_color,
                    instances=colored_instances,
                    tier=ContentTier.TEMPLATE,
                    parent_group_ids=set(),
                    child_group_ids=set(),
                    _parent_chunk_id=g.group_id,
                )
                new_groups.append(sub_chunk)
                if DEBUG:
                    print(
                        f"[DEBUG CIST] Created sub‑template from group {g.group_id}: "
                        f"freq={len(unique_members)} height={h} sig={sig[:60]}"
                    )

        return groups + new_groups

    # ── Cross‑chunk deduplication ─────────────────────────────────────

    def _cross_chunk_deduplicate_text(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        if len(groups) < 2:
            return groups

        fp_to_instances = defaultdict(list)
        for gi, g in enumerate(groups):
            for ii, cn in enumerate(g.instances):
                fp = self._content_fingerprint(cn.node)
                if len(fp.split('||')[0]) < CROSS_DEDUP_TEXT_MIN_LEN:
                    continue
                fp_to_instances[fp].append((gi, ii, g, cn))

        def specificity(g: TemplateGroup, cn: ColoredNode) -> tuple:
            tier_score = {'SINGLETON': 2, 'ORPHAN': 1, 'TEMPLATE': 0}[g.tier.name]
            return (tier_score, -cn.subtree_content_count, g.frequency)

        to_remove = defaultdict(set)

        for fp, locations in fp_to_instances.items():
            if len(locations) < 2:
                continue
            best = max(locations, key=lambda loc: specificity(loc[2], loc[3]))
            best_gi, best_ii, best_g, best_cn = best
            for gi, ii, g, cn in locations:
                if (gi, ii) != (best_gi, best_ii):
                    to_remove[gi].add(ii)

        new_groups = []
        for gi, g in enumerate(groups):
            if gi not in to_remove:
                new_groups.append(g)
                continue
            surviving = [cn for ii, cn in enumerate(g.instances) if ii not in to_remove[gi]]
            if len(surviving) < MIN_TEMPLATE_FREQ:
                if DEBUG:
                    print(f"[DEBUG] Cross‑chunk text dedup dropped group {g.group_id} (freq fell to {len(surviving)})")
                continue
            g.instances = surviving
            new_groups.append(g)

        return new_groups

    def _cross_chunk_deduplicate_urls(self, groups: List[TemplateGroup]) -> List[TemplateGroup]:
        if len(groups) < 2:
            return groups

        # Compute product ID sets per group (for Adafruit)
        group_pids = []
        for g in groups:
            pids = set()
            for inst in g.instances[:10]:
                for url in AgnosticAttr.navigable_urls(inst.node):
                    pid = self._extract_product_id(url)
                    if pid:
                        pids.add(pid)
            group_pids.append(pids)

        # Also compute full URL sets for non‑product sites
        group_urls = []
        for g in groups:
            urls = set()
            for inst in g.instances[:10]:
                urls.update(AgnosticAttr.navigable_urls(inst.node))
            group_urls.append(urls)

        def specificity(g: TemplateGroup) -> tuple:
            tier_score = {'SINGLETON': 2, 'ORPHAN': 1, 'TEMPLATE': 0}[g.tier.name]
            avg_size = sum(inst.subtree_content_count for inst in g.instances) / len(g.instances)
            return (tier_score, -avg_size, g.frequency)

        dropped = set()
        for i in range(len(groups)):
            if i in dropped:
                continue
            for j in range(i+1, len(groups)):
                if j in dropped:
                    continue
                pi = group_pids[i]
                pj = group_pids[j]
                ui = group_urls[i]
                uj = group_urls[j]

                # Use product IDs if available (more precise)
                if pi and pj:
                    overlap = pi & pj
                    if len(overlap) / len(pi) > 0.8 or len(overlap) / len(pj) > 0.8:
                        if DEBUG:
                            print(f"[DEBUG URL DEDUP] Groups {i} and {j} product overlap {len(overlap)}/{len(pi)} and {len(overlap)}/{len(pj)}")
                        if specificity(groups[i]) < specificity(groups[j]):
                            dropped.add(i)
                        else:
                            dropped.add(j)
                # Otherwise fall back to full URLs
                elif ui and uj:
                    overlap = ui & uj
                    if len(overlap) / len(ui) > 0.8 or len(overlap) / len(uj) > 0.8:
                        if DEBUG:
                            print(f"[DEBUG URL DEDUP] Groups {i} and {j} URL overlap {len(overlap)}/{len(ui)} and {len(overlap)}/{len(uj)}")
                        if specificity(groups[i]) < specificity(groups[j]):
                            dropped.add(i)
                        else:
                            dropped.add(j)

        if DEBUG and dropped:
            print(f"[DEBUG] URL dedup dropped {len(dropped)} groups")
        return [g for idx, g in enumerate(groups) if idx not in dropped]

    # -----------------------------------------------------------------------
    # Main processing pipeline
    # -----------------------------------------------------------------------

    def process(self, verbose: bool = False) -> List[ChunkGroup]:
        log = print if verbose else lambda *a, **k: None
        self._log = log
        global DEBUG
        DEBUG = verbose  # enable debug prints if verbose

        log("[WL] Coloring...")
        engine = WLColorEngine(self.dom, verbose=verbose)
        colored = engine.color()
        if not colored:
            return []

        log("[WL] Grouping...")
        grouper = TemplateGrouper(colored, self.dom, verbose=verbose)
        self.template_groups = grouper.group()

        # ── Phase 4a: MCS near-isomorphic merge ──
        mcs_merger = MCSGroupMerger(verbose=verbose)
        self.template_groups = mcs_merger.merge(self.template_groups)
        log(f"[WL] After MCS merge: {len(self.template_groups)} groups")

        self.containment_dag = ContainmentDAG()
        self.containment_dag.build(self.template_groups, engine.colored_nodes,
                                   engine.containment_edges)
        log(f"[WL] DAG: {len(self.containment_dag.roots)} roots, "
            f"{sum(len(ch) for ch in self.containment_dag.edges.values())} edges")

        # ── Subsumption filter (Phase 3: Zhang-Shasha TED) ──
        sf = SubsumptionFilter(
            self.template_groups, self.containment_dag,
            engine.colored_nodes, verbose=verbose,
        )
        surviving = sf.filter()
        log(f"[WL] Subsumption: {len(self.template_groups)} → {len(surviving)} groups")

        # ── New post‑processing phases (in order) ─────────────────────
        surviving = self._deduplicate_content_within_groups(surviving)
        surviving = self._split_anchor_interior_groups(surviving)
        surviving = self._refine_homogeneity(surviving)
        surviving = self._merge_resource_affinity(surviving)
        surviving = self._merge_adjacent_siblings(surviving)
        surviving = self._mine_cross_instance_subtemplates(surviving)
        surviving = self._cross_chunk_deduplicate_text(surviving)
        surviving = self._cross_chunk_deduplicate_urls(surviving)

        # Re‑number groups
        for new_id, g in enumerate(surviving):
            g.group_id = new_id
        self.template_groups = surviving

        # ── Convert to ChunkGroup ──
        sels = WLSelectorGenerator.generate(surviving)
        self.chunks = [_to_chunk(tg, sels.get(tg.group_id, ""), dom=self.dom) for tg in surviving]

        # ── Collect search inputs, pagination, and text/nav chunks ──
        search = SearchInputCollector().collect(self.dom)
        if search:
            search.chunk_id = len(self.chunks)
            self.chunks.append(search)
            log(f"[WL] Search inputs: {search.frequency}")

        pagination = PaginationCollector().collect(self.dom, self.chunks)
        if pagination:
            pagination.chunk_id = len(self.chunks)
            self.chunks.append(pagination)
            log(f"[WL] Pagination: {pagination.frequency}")

        text_collector = TextContentCollector()
        text_chunks = text_collector.collect(self.dom, self.chunks)
        for tc in text_chunks:
            tc.chunk_id = len(self.chunks)
            self.chunks.append(tc)
            log(f"[WL] Text/nav chunk: {tc.frequency} elements ({tc.signature})")

        if self.chunks:
            self.sampler = ChunkSampler(self.dom, self.chunks)
            sd = self.sampler.sample_all_chunks(max_samples=3)
            log(f"[WL] Sampled {sum(len(x['samples']) for x in sd)}")
            cs = TokenizedXPathSelector.compute_all(self.chunks, dom=self.dom)
            log(f"[WL] {len(cs)} tokenized selectors")

        # ── Phase 6: BUTA primary extraction ──
        # The Bottom-Up Tree Automaton evaluates ALL structural templates
        # in a single O(N) post-order traversal. It is now the authoritative
        # source for structural chunk instance nodes. Selectors are still
        # generated from the XPath pipeline for cross-page portability.
        structural_chunks = [ch for ch in self.chunks if ch._structural_sig]
        if structural_chunks:
            buta = BottomUpTreeAutomaton(verbose=verbose)
            n_compiled = buta.compile(structural_chunks, self.template_groups)
            if n_compiled > 0:
                buta_matches = buta.execute(self.dom)
                # Populate _instance_nodes from BUTA results
                for ch in structural_chunks:
                    buta_nodes = buta_matches.get(ch.chunk_id, [])
                    if buta_nodes:
                        ch._instance_nodes = buta_nodes
                log(f"[BUTA] Primary extraction: {n_compiled} patterns, "
                    f"{sum(len(v) for v in buta_matches.values())} nodes")

        log(f"[WL] Done. {len(self.chunks)} chunks.")
        return self.chunks

    def get_template_groups(self): return self.template_groups
    def get_containment_dag(self): return self.containment_dag

    def serialize_for_llm(self, max_samples: int = 5) -> List[Dict[str, Any]]:
        """
        Serialize surviving chunks into the dict format expected by
        fibre_llm.py's collect_input_selectors_from_chunks(),
        collect_button_selectors_from_chunks(), and
        build_chunk_selection_prompt().

        Each chunk dict contains:
          - chunk_id, frequency, subtree, content_types, signature
          - selectors: list of XPath strings
          - samples: list of selector_sample groups, each containing:
            - selector: XPath string
            - samples: list of node-level dicts with tag, text,
              input_attrs, button_info, aria_label, links

        This is the integration bridge between the WL structural coloring
        engine and the Fibre cognitive loop.
        """
        from .web_distiller_freq import ContentCategory, URLExtractor

        result: List[Dict[str, Any]] = []
        seen_texts: set = set()

        for chunk in self.chunks:
            paths = chunk.trie_paths
            if not paths:
                continue

            # Sample evenly across instances
            count = len(paths)
            if count <= max_samples:
                indices = list(range(count))
            else:
                step = (count - 1) / (max_samples - 1)
                indices = sorted(set(int(round(i * step)) for i in range(max_samples)))

            node_samples: List[Dict[str, Any]] = []
            for idx in indices:
                if idx >= count:
                    continue
                node = self.dom.xpath_one(paths[idx])
                if not node:
                    continue

                # Extract text with boundaries dynamically fixed
                text_raw = (node.get_text() or '')[:300]
                text_raw = self._fix_text_boundaries(text_raw)
                text_key = ' '.join(text_raw.split()).lower()[:100]
                if text_key in seen_texts and len(text_key) >= 20:
                    continue
                if len(text_key) >= 20:
                    seen_texts.add(text_key)

                # Extract tag-level attributes
                tag = (node.tag or '').lower()
                input_attrs = {}
                if tag in ('input', 'textarea', 'select'):
                    for k in ('type', 'name', 'placeholder', 'value', 'id'):
                        v = node.get_attr(k)
                        if v:
                            input_attrs[k] = v

                button_info = {}
                is_btn = tag == 'button' or node.get_attr('role') == 'button'
                if tag == 'input' and node.get_attr('type', '').lower() in (
                    'button', 'submit', 'reset', 'image'
                ):
                    is_btn = True
                if is_btn:
                    button_info['text'] = text_raw[:100]
                    al = node.get_attr('aria-label')
                    if al:
                        button_info['aria_label'] = al

                # Extract links from subtree
                links: List[str] = []
                stack = [node]
                while stack:
                    n = stack.pop()
                    for attr in ('href', 'src', 'data-src', 'action'):
                        url = n.get_attr(attr)
                        if url and not url.startswith(('javascript:', 'data:', '#')):
                            links.append(url[:200])
                    for c in n.get_children(include_shadow=True):
                        stack.append(c)

                aria_label = node.get_attr('aria-label') or ''

                node_samples.append({
                    'tag': tag,
                    'text': text_raw,
                    'xpath': paths[idx],
                    'input_attrs': input_attrs,
                    'button_info': button_info,
                    'aria_label': aria_label,
                    'links': links[:10],
                })

            if not node_samples:
                continue

            # Build selector_samples groups (one per selector)
            sel_list = chunk.selectors or [chunk.subtree_root]
            selector_samples = []
            for sel in sel_list:
                selector_samples.append({
                    'selector': sel,
                    'samples': node_samples,
                })

            result.append({
                'chunk_id': chunk.chunk_id,
                'frequency': chunk.frequency,
                'subtree': chunk.subtree_root,
                'content_types': [c.value for c in chunk.content_types],
                'signature': chunk.signature[:80],
                'selectors': sel_list,
                'samples': selector_samples,
            })

        return result