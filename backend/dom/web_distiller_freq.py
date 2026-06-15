"""
Web Distiller v13 – Resource-Bounded Sibling-Cohort Spectral Template Miner
=============================================================================
Refines v12 with principled additions (see THEORY_v13.md–THEORY_v16.md):

  1. Minimum Merge Depth (Phase 3): The adaptive depth algorithm finds
     the shallowest depth where a cohort's partition stabilizes. When this
     returns depth 0 (bare tag), the merge key captures zero structural
     information — it conflates all elements with the same tag regardless
     of subtree structure. Enforcing minimum merge depth of 1 ensures
     at least first-order branching structure (children tag sequence) in
     every merge key. This is the structural minimum for cross-cohort
     template discrimination.

  2. Content-Based Instance Deduplication (Phase 5): Many pages render
     the same DOM subtree in multiple locations (responsive layouts,
     sidebar mirrors). After structural mining, instances within each
     group are deduplicated by content fingerprint (hash of normalized
     text + resource URLs). This contracts the instance set to its
     content-unique quotient without affecting structural analysis.

  3. Anchor-Interior Splitting (Phase 6): Template instances that are
     descendants of an <a href="..."> tag (but are not <a> tags
     themselves) are resource-orphan fragments. They inherit navigability
     context from an external ancestor and are not independently
     navigable content units. Split out of their groups.

  4. Purity-Dominance Redundancy Filter (Phase 8): Eliminates template
     groups whose instances are self-duplicated rendering artifacts of
     content already covered cleanly by another group. Uses href-set
     coverage (H_i ⊆ H_j) with mean purity comparison to detect groups
     that are structurally bloated shadows of cleaner groups (e.g.,
     DDG renders each search result in both a compact and expanded DOM
     variant — the expanded one has 2× buttons, menus, headings).

  5. Content Coagulation Map (post-pipeline, ContentCoagulator class):
     Deduplicates template instances by content identity (canonical href),
     extracts atomic content items from composite sections, builds
     containment graph, and produces graph-ready records. Selects the
     structurally richest clean instance as canonical using effective_size
     = subtree_size × purity. Generates relative xpaths for re-extraction.

  6. Intra-Instance Semantic Deduplication Mask (v16): Identifies
     semantically equivalent sibling subtrees within each instance
     (same text + same resources) and masks the duplicates. The mask
     is used by text extraction, HTML rendering, and fingerprinting
     to produce clean output free of rendering-artifact duplication.
     Eliminates 75% of text duplication across test pages.

Retained from v12:
  - Signature tree height filter (h >= 2, removes flat star-topology noise)
  - Post-spectral signature purification (structural homogeneity)
  - Hierarchical subsumption resolution (maximal templates only)
  - Adaptive depth within cohorts (variation tolerance)
  - Sibling cohort spectral analysis (Cheeger stopping)
  - Full-depth structural signatures (accurate complexity measurement)
"""

from __future__ import annotations
import re
import math
from typing import Optional, Iterator, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

import numpy as np
import networkx as nx
from scipy import sparse
from scipy.sparse.linalg import eigsh

from .shadow_html_parser import ShadowDOM, ShadowNode, get_absolute_xpath


# =============================================================================
# PER-SESSION COMPUTATION CACHES
# =============================================================================
# These module-level dicts eliminate redundant tree walks across phases.
# Cleared at the start of each WebDistiller.process() call.
# Within a single process() session, node identity (id()) is stable since
# no nodes are garbage-collected mid-pipeline.

_XPATH_CACHE: dict[int, str] = {}
_SIG_CACHE: dict[tuple[int, int], str] = {}


def _clear_caches() -> None:
    """Clear all per-session computation caches."""
    _XPATH_CACHE.clear()
    _SIG_CACHE.clear()


def cached_xpath(node: ShadowNode) -> str:
    """get_absolute_xpath with per-session memoization."""
    nid = id(node)
    if nid not in _XPATH_CACHE:
        _XPATH_CACHE[nid] = get_absolute_xpath(node)
    return _XPATH_CACHE[nid]


def cached_signature(node: ShadowNode, max_depth: int = -1) -> str:
    """get_subtree_signature with per-session memoization."""
    key = (id(node), max_depth)
    if key not in _SIG_CACHE:
        _SIG_CACHE[key] = get_subtree_signature(node, max_depth=max_depth)
    return _SIG_CACHE[key]


# =============================================================================
# CONSTANTS (unchanged from v10)
# =============================================================================
class ContentCategory(Enum):
    INPUT = "input"
    BUTTON = "button"
    TEXT = "text"
    LINK = "link"
    STRUCTURE = "structure"
    NAVIGATION = "navigation"

URL_PATTERN = re.compile(
    r'(?:(?:https?://)[^\s<>"\'`\)]+|//[^\s<>"\'`\)]+|'
    r'/[a-zA-Z0-9_\-]+(?:/[a-zA-Z0-9_\-\.%]+)+(?:\?[^\s<>"\'`\)]*)?)',
    re.IGNORECASE,
)
CSS_URL_PATTERN = re.compile(
    r'''url\s*\(\s*['"]?([^'"\)]+)['"]?\s*\)''', re.IGNORECASE
)

SCRIPT_EXTENSIONS = frozenset({'.js', '.jsx', '.ts', '.php', '.py'})
BUTTON_INPUT_TYPES = frozenset({'button', 'submit', 'reset', 'image'})

SKIP_TAGS = frozenset({
    'script', 'style', 'noscript', 'meta', 'link', 'head',
    '#comment', '#declaration', '#text', '#document',
})
DOCUMENT_TAGS = frozenset({'html', 'body', 'head', 'document', '#document'})

# ── Agnostic Tag-Role Constants ──────────────────────────────────────
# HTML defines semantic roles via tag names. These are structural
# categories from the spec, NOT arbitrary assumptions. They are used
# only as fallback classifications when attribute-based detection
# (via AgnosticAttr) cannot determine the node's role.
FORM_INPUT_TAGS = frozenset({'input', 'textarea', 'select'})
HEADING_TAGS = frozenset({'h1', 'h2', 'h3', 'h4', 'h5', 'h6'})
MEDIA_TAGS = frozenset({'img', 'video', 'source', 'picture', 'audio'})
MEDIA_CONTAINER_TAGS = frozenset({'picture', 'video', 'audio'})
FALLBACK_COPY_TAGS = frozenset({'noscript', 'template'})


# =============================================================================
# UTILITY CLASSES (unchanged from v10)
# =============================================================================
class URLExtractor:
    @staticmethod
    def is_excluded_url(url: str) -> bool:
        if not url:
            return True
        u = url.lower().strip()
        if u.startswith('data:') or u.startswith('javascript:'):
            return True
        return any(u.endswith(ext) for ext in SCRIPT_EXTENSIONS)

    @staticmethod
    def extract_from_node(node: ShadowNode) -> list[str]:
        """
        Agnostic URL extraction: inspects ALL attribute values for
        URL-like patterns rather than filtering by a hardcoded key
        allowlist.  Delegates to AgnosticAttr.urls_from_node and
        applies the same exclusion filter.
        """
        urls = []
        for url in AgnosticAttr.urls_from_node(node):
            if not URLExtractor.is_excluded_url(url):
                urls.append(url)
        return list(dict.fromkeys(urls))


class AttributeTokenizer:
    @staticmethod
    def tokenize(value: str) -> list[str]:
        if not value:
            return []
        tokens = re.split(r'[\s\-_]+', value)
        final = []
        for t in tokens:
            parts = re.findall(
                r'([A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$|\d)|\d+)', t
            )
            final.extend(parts if parts else [t])
        return [f.lower() for f in final if len(f) > 1 and not f.isdigit()]


class AgnosticAttr:
    """
    Agnostic attribute inspection — no hardcoded attribute keys.

    Every method inspects ALL attributes on a node or subtree,
    discovering URLs, link text, and media sources by value heuristics
    rather than key assumptions.  This mirrors the tokenized-XPath
    predicate approach used by SiblingCohortMiner's spectral graph:
    attribute *keys* are metadata, attribute *values* carry the signal.

    URL heuristic:  a value is URL-like if it starts with ``/``,
    ``http://``, ``https://``, ``data:``, or ``//``, OR if it contains
    both ``/`` and ``.`` (path-like).  Inline CSS ``url(...)`` is also
    extracted.

    This replaces ~44 hardcoded ``get_attr('href'...)``,
    ``get_attr('src'...)``, ``get_attr('class'...)`` calls scattered
    throughout the pipeline with a single discoverable interface.
    """

    _URL_RE = re.compile(
        r'^(?:https?://|//|/|data:image/)',
        re.IGNORECASE,
    )
    _CSS_URL_RE = re.compile(r"url\(['\"]?([^'\")\s]+)['\"]?\)")

    # Attributes whose values are NEVER URLs (prevent false positives
    # from long class strings or JS event handlers).  Discovered
    # empirically, not assumed — keep minimal.
    _ATTR_DENYLIST = frozenset({
        'style', 'onclick', 'onload', 'onerror', 'onmouseover',
    })

    @classmethod
    def is_url(cls, value: str) -> bool:
        """Heuristic: does this string look like a URL?"""
        if not value:
            return False
        v = value.strip()
        if not v:
            return False
        # Accept bare root path '/'
        if v == '/':
            return True
        if len(v) < 2:
            return False
        if cls._URL_RE.match(v):
            return True
        # Path-like: has both / and . but isn't a sentence
        if '/' in v and '.' in v and ' ' not in v and len(v) < 500:
            return True
        return False

    @classmethod
    def urls_from_node(cls, node: ShadowNode) -> list[str]:
        """Extract all URL-like values from ALL attributes of a single node."""
        urls: list[str] = []
        for key, val in node.get_all_attrs().items():
            if key.lower() in cls._ATTR_DENYLIST:
                # But still check style for url()
                if key.lower() == 'style' and val and 'url(' in val:
                    for m in cls._CSS_URL_RE.finditer(val):
                        u = m.group(1).strip()
                        if u and not u.startswith('data:') or u.startswith('data:image/'):
                            urls.append(u)
                continue
            if not val or not isinstance(val, str):
                continue
            v = val.strip()
            if cls.is_url(v):
                urls.append(v)
            # Handle multi-value attrs like srcset: "img1.jpg 1x, img2.jpg 2x"
            elif ',' in v and '/' in v:
                for part in v.split(','):
                    candidate = part.strip().split()[0] if part.strip() else ''
                    if cls.is_url(candidate):
                        urls.append(candidate)
        return urls

    @classmethod
    def all_urls(cls, node: ShadowNode) -> list[str]:
        """Extract all URL-like values from a subtree (recursive)."""
        urls: list[str] = []
        for desc in node.iter_all():
            urls.extend(cls.urls_from_node(desc))
        return urls

    @classmethod
    def unique_urls(cls, node: ShadowNode) -> set[str]:
        """Deduplicated URL set from a subtree."""
        return set(cls.all_urls(node))

    @classmethod
    def primary_url(cls, node: ShadowNode) -> Optional[str]:
        """
        Extract the primary navigable URL from a node.

        Inspects all attributes agnostically; returns the first URL found
        on the node itself, or the first URL found on any descendant.
        Skips fragment-only (#) and javascript: pseudo-URLs.
        """
        def _valid(u: str) -> bool:
            return (u and not u.startswith('#')
                    and not u.startswith('javascript'))

        # Check node itself first
        for u in cls.urls_from_node(node):
            if _valid(u):
                return u
        # Then descendants
        for desc in node.iter_descendants():
            for u in cls.urls_from_node(desc):
                if _valid(u):
                    return u
        return None

    @classmethod
    def has_url_descendant(cls, node: ShadowNode) -> bool:
        """True if any descendant carries a URL-bearing attribute."""
        for desc in node.iter_descendants():
            if cls.urls_from_node(desc):
                return True
        return False

    @classmethod
    def node_has_url(cls, node: ShadowNode) -> bool:
        """True if this specific node has any URL-bearing attribute."""
        return bool(cls.urls_from_node(node))

    @classmethod
    def media_urls(cls, node: ShadowNode) -> list[str]:
        """Extract media-specific URLs (images, video, audio) from subtree.

        Uses the agnostic URL extractor but filters to common media
        extensions and data URIs.  No hardcoded attribute keys.
        """
        media_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
                      '.mp4', '.webm', '.ogg', '.mp3', '.wav')
        result = []
        for url in cls.all_urls(node):
            u_lower = url.lower().split('?')[0]
            if (any(u_lower.endswith(ext) for ext in media_exts)
                    or 'image' in u_lower
                    or url.startswith('data:image/')):
                result.append(url)
        return result

    @classmethod
    def attr_token_vector(cls, node: ShadowNode) -> set[str]:
        """
        Build the tokenized XPath predicate vector for a node.

        Returns a set of strings in XPath predicate notation:
            ``@{key}:{token}``
        Identical to the spectral miner's feature extraction,
        ensuring consistency between mining and matching phases.
        """
        tokens: set[str] = set()
        tokens.add(f"tag:{node.tag.lower()}")
        for key, val in node.get_all_attrs().items():
            key_lower = key.lower()
            tokens.add(f"@{key_lower}")
            val_str = str(val or '')[:300]
            if val_str:
                for tok in AttributeTokenizer.tokenize(val_str):
                    tokens.add(f"@{key_lower}:{tok}")
        return tokens

    @classmethod
    def attr_has_token(cls, node: ShadowNode, token: str) -> bool:
        """Check if any attribute value on node contains a specific token."""
        token_lower = token.lower()
        for _key, val in node.get_all_attrs().items():
            if not val:
                continue
            for tok in AttributeTokenizer.tokenize(str(val)[:300]):
                if tok == token_lower:
                    return True
        return False

    @classmethod
    def is_button_like(cls, node: ShadowNode) -> bool:
        """
        Agnostic button detection.

        An element is button-like if:
        - Its tag is 'button' (structural HTML)
        - Any attribute value tokenizes to a button-type token
          (submit, button, reset, image) — catches ``<input type=submit>``,
          ``<div data-action=submit>``, ``<custom role=button>``, etc.

        Replaces hardcoded ``get_attr('type') in BUTTON_INPUT_TYPES``
        with agnostic attribute-value tokenization.
        """
        if node.tag.lower() == 'button':
            return True
        for _key, val in node.get_all_attrs().items():
            if not val:
                continue
            val_lower = str(val).lower().strip()
            if val_lower in BUTTON_INPUT_TYPES:
                return True
        return False

    @classmethod
    def is_input_like(cls, node: ShadowNode) -> bool:
        """
        Agnostic form-input detection.

        An element is input-like if:
        - Its tag is in FORM_INPUT_TAGS (input, textarea, select)
        - OR any attribute value tokenizes to an input-role token
          (textbox, searchbox, combobox, listbox, spinbutton)
        - OR it has contenteditable="true"

        This catches ``<div role="searchbox">``,
        ``<custom-input contenteditable="true">``, etc.
        """
        if node.tag.lower() in FORM_INPUT_TAGS:
            return True
        _INPUT_ROLE_TOKENS = frozenset({
            'textbox', 'searchbox', 'combobox', 'listbox', 'spinbutton',
        })
        for _key, val in node.get_all_attrs().items():
            if not val:
                continue
            val_lower = str(val).lower().strip()
            if val_lower in _INPUT_ROLE_TOKENS:
                return True
            if val_lower == 'true' and _key.lower() == 'contenteditable':
                return True
        return False

    @classmethod
    def is_heading_like(cls, node: ShadowNode) -> bool:
        """
        Agnostic heading detection.

        An element is heading-like if:
        - Its tag is in HEADING_TAGS (h1-h6)
        - OR any attribute value tokenizes to 'heading'
          (catches ``<div role="heading" aria-level="2">``)
        """
        if node.tag.lower() in HEADING_TAGS:
            return True
        for _key, val in node.get_all_attrs().items():
            if not val:
                continue
            if str(val).lower().strip() == 'heading':
                return True
        return False

    @classmethod
    def is_fallback_copy(cls, node: ShadowNode) -> bool:
        """
        Agnostic fallback-copy detection.

        Identifies elements whose content is a browser-fallback copy
        of richer content (noscript, template).  These should be masked
        in dedup to avoid double-counting.
        """
        return node.tag.lower() in FALLBACK_COPY_TAGS

    @classmethod
    def is_container_of_links(cls, node: ShadowNode) -> bool:
        """
        Agnostic container-of-links detection.

        True if this element has >=2 direct children that carry URLs.
        Used for molecule splitting: instead of hardcoding tag names
        like (ul, ol, nav, div), we test if the element structurally
        wraps multiple link atoms.
        """
        url_children = 0
        for child in node.get_children(include_shadow=True):
            if cls.node_has_url(child) or cls.has_url_descendant(child):
                url_children += 1
                if url_children >= 2:
                    return True
        return False

    @classmethod
    def is_media_container(cls, node: ShadowNode) -> bool:
        """
        Agnostic media-container detection.

        True if this element is a container that wraps media sources
        (picture, video, audio) or has ARIA/attribute indicating media.
        """
        if node.tag.lower() in MEDIA_CONTAINER_TAGS:
            return True
        for _key, val in node.get_all_attrs().items():
            if not val:
                continue
            val_lower = str(val).lower().strip()
            if val_lower in ('img', 'image', 'video', 'figure'):
                return True
        return False

    @classmethod
    def primary_media_key(cls, node: ShadowNode) -> str:
        """
        Extract a single dedup key for media elements (img, picture, video).

        Inspects ALL attributes agnostically.  Prefers non-placeholder URLs
        (skipping data: URIs) to handle lazy-load patterns where the real
        source lives in ``data-src``, ``data-lazy-src``, ``data-original``,
        or any vendor-specific attribute — without hardcoding any of them.

        Returns the first non-data-URI URL found, truncated to 120 chars.
        Falls back to empty string if no URL is discovered.
        """
        # Pass 1: find any non-data-URI URL on this node
        for _key, val in node.get_all_attrs().items():
            if not val or not isinstance(val, str):
                continue
            v = val.strip()
            if v.startswith('data:'):
                continue
            if cls.is_url(v):
                return v.split()[0][:120]
            # Handle srcset-style multi-value
            if ',' in v and '/' in v:
                for part in re.split(r',\s+', v):
                    candidate = part.strip().split()[0] if part.strip() else ''
                    if candidate and cls.is_url(candidate) and not candidate.startswith('data:'):
                        return candidate[:120]
        # Pass 2: last resort — any URL including data: images
        for _key, val in node.get_all_attrs().items():
            if not val or not isinstance(val, str):
                continue
            v = val.strip()
            if cls.is_url(v):
                return v.split()[0][:120]
        return ''

    @classmethod
    def primary_media_key_subtree(cls, node: ShadowNode) -> str:
        """
        Extract a dedup key from a container node (picture, video) by
        inspecting ALL descendants agnostically.

        Returns the first non-data-URI URL found on any descendant.
        """
        for desc in node.iter_descendants():
            key = cls.primary_media_key(desc)
            if key:
                return key
        return cls.primary_media_key(node)

    @classmethod
    def navigable_urls(cls, node: ShadowNode) -> list[str]:
        """
        Extract all navigable (non-fragment, non-javascript) URLs from subtree.

        Agnostic: inspects ALL attributes on ALL descendants.
        Filters out fragment-only (#...) and javascript: pseudo-URLs.
        """
        skip = ('#', 'javascript:', 'data:', 'about:', 'blob:')
        result: list[str] = []
        for url in cls.all_urls(node):
            if not any(url.startswith(p) for p in skip):
                result.append(url)
        return result


# =============================================================================
# DOM TRAVERSAL HELPERS (unchanged from v10)
# =============================================================================
def iter_elements(root: ShadowNode) -> Iterator[ShadowNode]:
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if not node.tag.startswith('#'):
            yield node
        if node.shadow_root:
            queue.extend(node.shadow_root.children)
        queue.extend(node.children)


def has_content_descendants(node: ShadowNode, content_ids: set) -> bool:
    queue = deque(node.get_children(include_shadow=True))
    while queue:
        child = queue.popleft()
        if id(child) in content_ids:
            return True
        queue.extend(child.get_children(include_shadow=True))
    return False


def get_subtree_signature(node: ShadowNode, max_depth: int = -1) -> str:
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
        child_sigs.append(get_subtree_signature(child, next_depth))
    if not child_sigs:
        return tag
    child_sigs.sort()
    return f"{tag}({','.join(child_sigs)})"


def get_ordered_subtree_signature(node: ShadowNode, max_depth: int = -1) -> str:
    """
    Ordered Tree Canonical Certificate — OTCH at bounded depth (§11.2).

    Identical to get_subtree_signature but children are hashed in their
    natural DOM sibling order (NOT sorted). Two subtrees with identical
    children in different order produce different signatures.

    At the miner's structural depth (max_depth=6), ordered and unordered
    signatures are empirically equivalent across all test sites, because
    the pre-contraction root recovery (§11.3) lifts instances to a level
    where sibling order is already consistent. The ordered form is used
    for theoretical correctness per §11.2.
    """
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
    # ORDERED: no sort — preserve DOM sibling order
    return f"{tag}({','.join(child_sigs)})"


def signature_height(sig: str) -> int:
    """
    Parse a structural signature string and compute its tree height.

    Height 0: leaf node (e.g., "div")
    Height 1: flat branching — star topology (e.g., "div(span,span)")
    Height 2+: genuine hierarchy (e.g., "article(div,header(a,h2))")

    The height threshold h >= 2 is the tree-theoretic minimum for
    non-trivial hierarchical structure. See THEORY_v12.md §3.1.
    """
    if '(' not in sig:
        return 0

    # Parse recursively: find max child height
    max_child_height = 0
    depth = 0
    child_start = -1

    # Find the opening paren of the root's children
    root_paren = sig.index('(')

    i = root_paren + 1
    child_start = i
    while i < len(sig):
        c = sig[i]
        if c == '(':
            depth += 1
        elif c == ')':
            if depth == 0:
                # End of root's children — process last child
                child_sig = sig[child_start:i]
                if child_sig:
                    max_child_height = max(
                        max_child_height, signature_height(child_sig)
                    )
                break
            depth -= 1
        elif c == ',' and depth == 0:
            # Separator between root's children
            child_sig = sig[child_start:i]
            if child_sig:
                max_child_height = max(
                    max_child_height, signature_height(child_sig)
                )
            child_start = i + 1
        i += 1

    return 1 + max_child_height


# =============================================================================
# DATA CLASSES (unchanged from v10)
# =============================================================================
@dataclass
class ContentNode:
    node: ShadowNode
    categories: frozenset
    links: list
    text_content: str
    xpath: str
    tag_tokens: list = field(default_factory=list)
    attr_name_tokens: list = field(default_factory=list)
    attr_value_tokens: list = field(default_factory=list)
    _resolved_selector: Optional[str] = None

    def has_category(self, cat: ContentCategory) -> bool:
        return cat in self.categories


@dataclass
class ChunkGroup:
    chunk_id: int
    selectors: list
    trie_paths: list
    frequency: int
    content_types: set
    subtree_root: str
    signature: str = ""
    samples: list = field(default_factory=list)
    # v11 additions for subsumption tracking
    _instance_nodes: list = field(default_factory=list, repr=False)
    _structural_sig: str = ""  # Tree-isomorphism signature for filtering
    _is_subsumed: bool = False
    _parent_chunk_id: int = -1
    _relative_xpath: str = ""  # Portable cross-page selector (string form)
    _tokenized_selector: dict = field(default_factory=dict, repr=False)  # Structured selector


# =============================================================================
# RELATIVE XPATH SELECTOR COMPUTATION (cross-page portability)
# =============================================================================
class TokenizedXPathSelector:
    """
    Discriminative, portable XPath selectors via inter-chunk token analysis.

    Generates ``//tag[contains(@attr, 'value')]`` selectors that achieve
    perfect precision (zero false positives from other chunks) and
    maximum recall (all instances in the chunk are retrieved).

    Algorithm:

    1. **Vocabulary extraction**: For every instance node in every chunk,
       tokenize ALL attribute values (excluding text-like attrs and URL
       values) into ``(attr_key, token)`` pairs.

    2. **Inter-chunk frequency table**: Count how many chunks each token
       appears in.  Tokens appearing in exactly ONE chunk are perfectly
       discriminative — they select that chunk and nothing else.

    3. **Discriminative token ranking**: Per chunk, rank tokens by
       exclusivity (fewer chunks) then coverage (more instances).

    4. **Base selector assembly**: Build ``//tag[contains(@k,'v')]`` from
       top-ranked discriminative tokens.

    5. **Reverse-depth accumulation**: If the base selector is ambiguous
       (matches nodes outside the chunk), iteratively climb ancestors,
       prepending ``//anc_tag[contains(@k,'v')]`` until the combined
       selector is laterally unique across all chunks.

    6. **Early stopping**: All chunks processed simultaneously; once a
       chunk's selector achieves full precision+recall, it's frozen.
    """

    # Attributes whose values are human-readable text (instance-specific,
    # useless for cross-page matching). Excluded from token vocabulary.
    _TEXT_ATTRS = frozenset({
        'aria-label', 'aria-description', 'aria-roledescription',
        'aria-placeholder', 'aria-valuetext', 'title', 'alt',
        'placeholder', 'label', 'content', 'summary',
    })

    @classmethod
    def _extract_structural_tokens(
        cls, node: ShadowNode,
    ) -> dict[tuple[str, str], int]:
        """
        Extract (attr_key, token) pairs from a single node's attributes.

        Excludes:
        - Text-like attribute values (aria-label, title, alt, ...)
        - URL-bearing values (href-like, src-like)
        - Very long values (>200 chars — likely prose or inline styles)

        Returns dict mapping (attr_key, token) → 1 (presence flag).
        """
        tokens: dict[tuple[str, str], int] = {}
        for key, val in node.get_all_attrs().items():
            key_lower = key.lower()
            if key_lower in cls._TEXT_ATTRS:
                continue
            if not val or not isinstance(val, str):
                continue
            val_str = val.strip()
            if len(val_str) > 200:
                continue
            # Skip URL-bearing values entirely
            if AgnosticAttr.is_url(val_str):
                continue
            for tok in AttributeTokenizer.tokenize(val_str):
                tokens[(key_lower, tok)] = 1
        return tokens

    @classmethod
    def _build_vocabulary(
        cls, chunks: list['ChunkGroup'],
        term_cache=None,
    ) -> tuple[
        dict[int, dict[tuple[str, str], int]],  # chunk_id → {token → instance_count}
        dict[tuple[str, str], set[int]],          # token → set of chunk_ids
    ]:
        """
        Phase 1+2: Build per-chunk token frequencies AND global cross-chunk
        frequency table in a single O(C * N * A) pass.

        If a NodeTermCache is provided, tok_pairs are derived from cached
        structural terms instead of re-scanning the DOM.

        Returns:
            chunk_tokens: mapping chunk_id → {(attr_key, token) → count}
            token_chunks: mapping (attr_key, token) → set of chunk_ids
        """
        chunk_tokens: dict[int, dict[tuple[str, str], int]] = {}
        token_chunks: dict[tuple[str, str], set[int]] = defaultdict(set)

        for ch in chunks:
            nodes = getattr(ch, '_instance_nodes', [])
            if not nodes:
                continue
            freq: dict[tuple[str, str], int] = defaultdict(int)
            for node in nodes:
                if term_cache is not None:
                    node_toks = term_cache.get_tok_pairs(node)
                else:
                    node_toks = cls._extract_structural_tokens(node)
                for tok_key in node_toks:
                    freq[tok_key] += 1
            chunk_tokens[ch.chunk_id] = dict(freq)
            for tok_key in freq:
                token_chunks[tok_key].add(ch.chunk_id)

        return chunk_tokens, dict(token_chunks)

    @classmethod
    def _select_discriminative_tokens(
        cls,
        chunk: 'ChunkGroup',
        chunk_tokens: dict[int, dict[tuple[str, str], int]],
        token_chunks: dict[tuple[str, str], set[int]],
        max_predicates: int = 5,
    ) -> list[tuple[str, str]]:
        """
        Phase 3: Select the most discriminative tokens for a chunk.

        Ranking criteria (lexicographic):
            1. Exclusivity: fewer chunks sharing this token → better
               (1 chunk = perfect precision)
            2. Coverage: higher intra-chunk frequency → better
               (N instances = perfect recall)

        Returns list of (attr_key, token) pairs, most discriminative first.
        """
        tokens = chunk_tokens.get(chunk.chunk_id, {})
        if not tokens:
            return []

        n = len(getattr(chunk, '_instance_nodes', []))
        threshold = max(1, int(n * 0.7))  # token must appear in ≥70% of instances

        candidates: list[tuple[int, int, str, str]] = []
        for (attr_key, tok), freq in tokens.items():
            if freq < threshold:
                continue  # too rare within chunk (low recall)
            n_chunks = len(token_chunks.get((attr_key, tok), set()))
            # Sort key: (exclusivity ASC, -coverage DESC)
            candidates.append((n_chunks, -freq, attr_key, tok))

        candidates.sort()
        return [(attr_key, tok) for _, _, attr_key, tok in candidates[:max_predicates]]

    @classmethod
    def _assemble_xpath(
        cls, tag: str, predicates: list[tuple[str, str]],
    ) -> str:
        """Build XPath string: //tag[contains(@k,'v')][contains(@k2,'v2')]"""
        pred_parts = []
        for attr_key, tok in predicates:
            pred_parts.append(f"[contains(@{attr_key},'{tok}')]")
        return f".//{tag}{''.join(pred_parts)}"

    @classmethod
    def _verify_selector(
        cls, xpath_str: str, chunk: 'ChunkGroup', dom: 'ShadowDOM',
    ) -> tuple[int, int]:
        """
        Verify a selector against the DOM.

        Returns (true_positives, false_positives).
        Uses node-ID matching for O(1) lookups.
        """
        instance_ids = {id(n) for n in getattr(chunk, '_instance_nodes', [])}
        tag, parsed_preds = cls._parse_selector(xpath_str)
        if not tag:
            return 0, 0

        tp = 0
        fp = 0
        for node in dom.iter_elements():
            if node.tag.lower() != tag:
                continue
            if cls._node_matches_predicates(node, parsed_preds):
                if id(node) in instance_ids:
                    tp += 1
                else:
                    fp += 1
        return tp, fp

    @staticmethod
    def _parse_selector(xpath_str: str) -> tuple[str, list[tuple[str, str]]]:
        """Parse //tag[contains(@k,'v')] into (tag, [(k, v), ...])"""
        m = re.match(r'\.?//(\w[\w-]*)', xpath_str)
        if not m:
            return '', []
        tag = m.group(1).lower()
        preds = re.findall(r"contains\(@([\w-]+),'([^']+)'\)", xpath_str)
        return tag, preds

    @staticmethod
    def _node_matches_predicates(
        node: ShadowNode, preds: list[tuple[str, str]],
    ) -> bool:
        """Check if a node matches all contains() predicates."""
        attrs = node.get_all_attrs()
        for attr_key, tok in preds:
            val = attrs.get(attr_key, '') or ''
            if isinstance(val, str) and tok in val.lower():
                continue
            # Try case-insensitive key match
            matched = False
            for k, v in attrs.items():
                if k.lower() == attr_key and isinstance(v, str) and tok in v.lower():
                    matched = True
                    break
            if not matched:
                return False
        return True

    @classmethod
    def _climb_ancestor(
        cls,
        chunk: 'ChunkGroup',
        base_tag: str,
        base_preds: list[tuple[str, str]],
        chunk_tokens: dict[int, dict[tuple[str, str], int]],
        token_chunks: dict[tuple[str, str], set[int]],
        dom: 'ShadowDOM',
        max_depth: int = 3,
        _tag_index: dict[str, list] | None = None,
    ) -> str:
        """
        Phase 5: Reverse-depth accumulation.

        If the base selector has false positives, climb ancestors to add
        structural context.  At each depth level, find the ancestor's
        discriminative tokens and prepend them.

        Uses pre-built tag→nodes index for O(T) verification instead
        of O(N) full DOM scans.
        """
        nodes = getattr(chunk, '_instance_nodes', [])
        if not nodes:
            return cls._assemble_xpath(base_tag, base_preds)

        # Collect ancestor tokens at each depth level
        for depth in range(1, max_depth + 1):
            # Get ancestors at this depth for all instances
            ancestor_tag_freq: dict[str, int] = defaultdict(int)
            ancestor_tok_freq: dict[tuple[str, str], int] = defaultdict(int)

            for node in nodes:
                anc = node
                for _ in range(depth):
                    if anc.parent is None:
                        break
                    anc = anc.parent
                else:
                    # Reached target depth
                    ancestor_tag_freq[anc.tag.lower()] += 1
                    for tok_key in cls._extract_structural_tokens(anc):
                        ancestor_tok_freq[tok_key] += 1

            if not ancestor_tag_freq:
                continue

            # Pick most common ancestor tag
            anc_tag = max(ancestor_tag_freq, key=ancestor_tag_freq.get)
            anc_coverage = ancestor_tag_freq[anc_tag]

            # Find discriminative ancestor tokens
            n = len(nodes)
            anc_threshold = max(1, int(n * 0.7))
            anc_preds: list[tuple[str, str]] = []

            for (attr_key, tok), freq in sorted(
                ancestor_tok_freq.items(), key=lambda x: -x[1]
            ):
                if freq < anc_threshold:
                    continue
                n_chunks_with = len(token_chunks.get((attr_key, tok), set()))
                if n_chunks_with <= 2:  # reasonably exclusive
                    anc_preds.append((attr_key, tok))
                if len(anc_preds) >= 3:
                    break

            if not anc_preds and anc_coverage < n * 0.7:
                continue  # no useful ancestor tokens at this depth

            # Build combined selector:  //anc[...] <sep> //node[...]
            sep = '/' if depth == 1 else '//'
            anc_parts = ''.join(
                f"[contains(@{k},'{v}')]" for k, v in anc_preds
            )
            node_parts = ''.join(
                f"[contains(@{k},'{v}')]" for k, v in base_preds
            )
            combined = f".//{anc_tag}{anc_parts}{sep}{base_tag}{node_parts}"

            # Quick verification using tag_index (O(T) instead of O(N))
            instance_ids = {id(n) for n in nodes}
            sample_fp = 0
            sample_tp = 0
            anc_tag_lower = anc_tag.lower()
            node_tag_lower = base_tag.lower()
            # Use tag index for candidate lookup
            candidates = (_tag_index or {}).get(node_tag_lower, [])
            if not candidates:
                candidates = [nd for nd in dom.iter_elements()
                              if nd.tag.lower() == node_tag_lower]
            for test_node in candidates:
                if not cls._node_matches_predicates(test_node, base_preds):
                    continue
                # Check ancestor constraint
                if depth == 1:
                    anc_node = test_node.parent
                    if not anc_node or anc_node.tag.lower() != anc_tag_lower:
                        continue
                    if not cls._node_matches_predicates(anc_node, anc_preds):
                        continue
                else:
                    # For depth > 1, walk up
                    found = False
                    a = test_node.parent
                    for _ in range(depth + 2):  # allow some slack
                        if a is None:
                            break
                        if a.tag.lower() == anc_tag_lower and \
                           cls._node_matches_predicates(a, anc_preds):
                            found = True
                            break
                        a = a.parent
                    if not found:
                        continue

                if id(test_node) in instance_ids:
                    sample_tp += 1
                else:
                    sample_fp += 1

            if sample_fp == 0 and sample_tp > 0:
                return combined  # perfect precision achieved
            # If still has FP but fewer than base, keep going deeper

        # Fallback: return base selector
        return cls._assemble_xpath(base_tag, base_preds)

    @classmethod
    def compute(cls, chunk: 'ChunkGroup',
                chunk_tokens: dict[int, dict[tuple[str, str], int]] | None = None,
                token_chunks: dict[tuple[str, str], set[int]] | None = None,
                dom: 'ShadowDOM | None' = None,
                _tag_index: dict[str, list] | None = None) -> dict:
        """
        Compute a discriminative tokenized XPath selector for a chunk.

        If vocabulary tables are provided (from compute_all), uses them
        for inter-chunk discrimination.  Otherwise falls back to
        intra-chunk-only analysis.

        Returns structured dict:
            tag:          common root tag
            predicates:   list of (attr_key, token) pairs
            xpath:        assembled ``//tag[contains(@k,'v')]`` string
            frequency:    instance count
            signature:    structural signature
            exclusivity:  avg chunk-exclusivity score of predicates
        """
        nodes = getattr(chunk, '_instance_nodes', [])
        if not nodes:
            return {'tag': '', 'predicates': [], 'xpath': '',
                    'frequency': 0, 'signature': '', 'exclusivity': 0}

        n = len(nodes)

        # ── Common root tag ──
        tag_freq: dict[str, int] = defaultdict(int)
        for node in nodes:
            tag_freq[node.tag.lower()] += 1
        common_tag = max(tag_freq, key=tag_freq.get)

        # ── Discriminative tokens ──
        if chunk_tokens is not None and token_chunks is not None:
            disc_tokens = cls._select_discriminative_tokens(
                chunk, chunk_tokens, token_chunks)
        else:
            # Fallback: intra-chunk only (single-chunk mode)
            local_tokens: dict[tuple[str, str], int] = defaultdict(int)
            for node in nodes:
                for tok_key in cls._extract_structural_tokens(node):
                    local_tokens[tok_key] += 1
            threshold = max(1, int(n * 0.7))
            disc_tokens = [
                (k, t) for (k, t), freq in
                sorted(local_tokens.items(), key=lambda x: -x[1])
                if freq >= threshold
            ][:5]

        # ── Base selector ──
        base_xpath = cls._assemble_xpath(common_tag, disc_tokens)

        # ── Exclusivity score (compute BEFORE DOM verification) ──
        if token_chunks and disc_tokens:
            excl_scores = [
                1.0 / len(token_chunks.get(t, {chunk.chunk_id}))
                for t in disc_tokens
            ]
            avg_excl = sum(excl_scores) / len(excl_scores)
        else:
            avg_excl = 0.0

        # ── Reverse-depth accumulation (if DOM available) ──
        # EARLY SKIP: if all predicates are exclusive to this chunk
        # (exclusivity=1.0), the selector is guaranteed unique — no
        # DOM verification needed.  This is the O(1) fast path.
        final_xpath = base_xpath
        needs_verification = (
            dom is not None
            and chunk_tokens is not None
            and token_chunks is not None
            and disc_tokens  # has predicates
            and avg_excl < 1.0  # NOT all tokens exclusive
        )
        if needs_verification:
            # Quick check: does base selector have false positives?
            # Uses pre-built tag→nodes index for O(T) lookup instead
            # of O(N) full DOM scan.
            instance_ids = {id(nd) for nd in nodes}
            common_tag_lower = common_tag.lower()
            fp_found = False
            candidates = (_tag_index or {}).get(common_tag_lower, [])
            if not candidates and dom is not None:
                # Fallback: full scan if no index
                candidates = [n for n in dom.iter_elements()
                              if n.tag.lower() == common_tag_lower]
            for test_node in candidates:
                if id(test_node) not in instance_ids:
                    if cls._node_matches_predicates(test_node,
                                                     disc_tokens):
                        fp_found = True
                        break

            if fp_found:
                final_xpath = cls._climb_ancestor(
                    chunk, common_tag, disc_tokens,
                    chunk_tokens, token_chunks, dom,
                    _tag_index=_tag_index)

        return {
            'tag': common_tag,
            'predicates': [f"@{k}:'{t}'" for k, t in disc_tokens],
            'contains_predicates': disc_tokens,
            'xpath': final_xpath,
            'frequency': n,
            'signature': getattr(chunk, '_structural_sig', ''),
            'exclusivity': round(avg_excl, 3),
        }

    @classmethod
    def match(cls, selector: dict, dom: 'ShadowDOM',
              min_score: float = 0.6) -> list['ShadowNode']:
        """
        Match a tokenized XPath selector against a new DOM.

        For each element with the correct tag, compute token overlap
        score against the selector's contains_predicates.  Return all
        elements scoring above ``min_score``.

        This is the cross-page extraction entry point.
        """
        preds = selector.get('contains_predicates', [])
        if not preds:
            return []

        target_tag = selector['tag']
        n_preds = len(preds)

        matches: list[tuple[float, 'ShadowNode']] = []
        for node in dom.iter_elements():
            if node.tag.lower() != target_tag:
                continue

            matched = 0
            attrs = node.get_all_attrs()
            for attr_key, tok in preds:
                for k, v in attrs.items():
                    if k.lower() == attr_key and isinstance(v, str) \
                       and tok in v.lower():
                        matched += 1
                        break

            score = matched / n_preds
            if score >= min_score:
                matches.append((score, node))

        matches.sort(key=lambda x: -x[0])
        return [node for _, node in matches]

    @classmethod
    def compute_all(cls, chunks: list['ChunkGroup'],
                    dom: 'ShadowDOM | None' = None,
                    term_cache=None) -> dict[int, dict]:
        """
        Compute discriminative XPath selectors for ALL chunks.

        Performs the full inter-chunk analysis:
        1. Build global vocabulary (O(C * N * A)) — uses NodeTermCache
        2. Compute discriminative tokens per chunk (O(C * T))
        3. Assemble + verify selectors with reverse-depth (O(C * E))
        4. Early stopping: chunks with exclusive tokens skip depth climb

        Args:
            chunks: all chunks to generate selectors for
            dom: ShadowDOM for verification (optional)
            term_cache: NodeTermCache for cached tok_pairs (optional)

        Returns dict mapping chunk_id → selector dict.
        """
        # ── Phase 1+2: Build vocabulary across ALL chunks ──
        chunk_tokens, token_chunks = cls._build_vocabulary(
            chunks, term_cache=term_cache)

        # ── Pre-build tag→nodes index for O(1) verification ──
        tag_index: dict[str, list] = defaultdict(list)
        if dom is not None:
            for node in dom.iter_elements():
                tag_index[node.tag.lower()].append(node)

        result = {}
        for ch in chunks:
            if not getattr(ch, '_instance_nodes', None):
                continue
            selector = cls.compute(
                ch, chunk_tokens, token_chunks, dom,
                _tag_index=tag_index)
            ch._relative_xpath = selector.get('xpath', '')
            ch._tokenized_selector = selector
            result[ch.chunk_id] = selector

        return result


# Backward compatibility alias
RelativeXPathComputer = TokenizedXPathSelector


# =============================================================================
# CONTENT SCANNER (unchanged from v10)
# =============================================================================
class ContentScanner:
    def __init__(self, dom: ShadowDOM):
        self.dom = dom
        self.content_nodes: dict[int, ContentNode] = {}
        self._content_ids: set = set()

    def scan(self) -> dict[int, ContentNode]:
        self.content_nodes.clear()
        self._content_ids.clear()
        stack = [(self.dom.root, [], [], [])]

        while stack:
            node, tag_acc, name_acc, val_acc = stack.pop()

            tag = node.tag.lower()
            if not tag.startswith('#') or tag == '#shadow-root':
                new_tag_acc = tag_acc + [tag]
            else:
                new_tag_acc = tag_acc

            new_name_acc = name_acc[:]
            new_val_acc = val_acc[:]
            for k, v in node.get_all_attrs().items():
                new_name_acc.append(k.lower())
                if isinstance(v, str):
                    new_val_acc.extend(AttributeTokenizer.tokenize(v))

            if (not tag.startswith('#')
                    and tag not in SKIP_TAGS
                    and tag not in DOCUMENT_TAGS):
                cats = set()
                links = URLExtractor.extract_from_node(node)
                text = (node.text or "").strip() + " " + (node.tail or "").strip()
                if AgnosticAttr.is_input_like(node):
                    cats.add(ContentCategory.INPUT)
                if AgnosticAttr.is_button_like(node):
                    cats.add(ContentCategory.BUTTON)
                if links:
                    cats.add(ContentCategory.LINK)
                if len(text.strip()) > 2:
                    cats.add(ContentCategory.TEXT)

                if cats:
                    xpath = cached_xpath(node)
                    cn = ContentNode(
                        node=node,
                        categories=frozenset(cats),
                        links=links,
                        text_content=text.strip(),
                        xpath=xpath,
                        tag_tokens=new_tag_acc,
                        attr_name_tokens=new_name_acc,
                        attr_value_tokens=new_val_acc,
                    )
                    self.content_nodes[id(node)] = cn
                    self._content_ids.add(id(node))

            children = node.get_children_with_shadow_boundary()
            for child in reversed(children):
                stack.append((child, new_tag_acc, new_name_acc, new_val_acc))

        all_elements = list(iter_elements(self.dom.root))
        for node in all_elements:
            nid = id(node)
            if nid in self.content_nodes:
                continue
            tag = node.tag.lower()
            if tag in SKIP_TAGS or tag in DOCUMENT_TAGS:
                continue
            content_child_count = 0
            for child in node.get_children(include_shadow=True):
                if id(child) in self._content_ids:
                    content_child_count += 1
                elif has_content_descendants(child, self._content_ids):
                    content_child_count += 1
                if content_child_count >= 2:
                    break
            if content_child_count >= 2:
                xpath = cached_xpath(node)
                self.content_nodes[nid] = ContentNode(
                    node=node,
                    categories=frozenset({ContentCategory.STRUCTURE}),
                    links=[],
                    text_content="",
                    xpath=xpath,
                )

        return self.content_nodes


def _classify_subtree(node: ShadowNode) -> set[ContentCategory]:
    cats = set()
    for desc in node.iter_all(include_shadow=True):
        tag = desc.tag.lower()
        if tag.startswith('#') or tag in SKIP_TAGS:
            continue
        links = URLExtractor.extract_from_node(desc)
        text = (desc.text or "").strip() + " " + (desc.tail or "").strip()
        if AgnosticAttr.is_input_like(desc):
            cats.add(ContentCategory.INPUT)
        if AgnosticAttr.is_button_like(desc):
            cats.add(ContentCategory.BUTTON)
        if links:
            cats.add(ContentCategory.LINK)
        if len(text.strip()) > 2:
            cats.add(ContentCategory.TEXT)
    return cats


def _agnostic_display_signature(members: list[ShadowNode]) -> str:
    """
    Build a human-readable display signature from tokenized attributes.
    
    No hardcoded attribute keys — uses the same AttributeTokenizer
    approach as spectral partitioning for consistency. Inspects ALL
    attributes on ALL elements, selecting the most frequent tag+token
    combination as the display label.
    
    Returns e.g. 'div.card.product' or 'a.nav.link' or bare 'li'.
    """
    tag_attr_counts: defaultdict[str, int] = defaultdict(int)
    for m in members:
        tokens = []
        for key, val in m.get_all_attrs().items():
            val_str = str(val or '')[:300]
            if val_str:
                for tok in AttributeTokenizer.tokenize(val_str):
                    tokens.append(tok)
        top_tokens = '.'.join(sorted(set(tokens))[:2]) if tokens else ''
        sig = f"{m.tag}.{top_tokens}" if top_tokens else m.tag
        tag_attr_counts[sig] += 1
    return max(tag_attr_counts, key=tag_attr_counts.get)


# =============================================================================
# SIBLING-COHORT SPECTRAL TEMPLATE MINER  (v11)
# =============================================================================

# Navigation URL attributes — only these create navigable contexts.
# Excludes Schema.org microdata (itemtype), RDFa, and metadata URLs.
_NAV_URL_ATTRS = frozenset({
    'href', 'action', 'formaction',
    'data-href', 'data-url', 'data-link',
})


def _node_has_nav_url(node: ShadowNode) -> bool:
    """
    True if node has a navigation-bearing attribute (href, action, etc.).

    Unlike AgnosticAttr.node_has_url(), this only checks attributes that
    create actual user navigation contexts.  Schema.org itemtype,
    itemscope, xmlns, and other metadata URLs are excluded.
    """
    tag = node.tag.lower()
    # <a>, <area>, <link> with href are always navigable
    if tag in ('a', 'area') and 'href' in (node.attributes or {}):
        return True
    attrs = node.get_all_attrs() if hasattr(node, 'get_all_attrs') else (node.attributes or {})
    for key in attrs:
        if key.lower() in _NAV_URL_ATTRS:
            val = str(attrs[key] or '')
            # Must look URL-like (not empty, not just '#')
            if val and val != '#' and len(val) > 1:
                return True
    return False


class SiblingCohortMiner:
    """
    Spectral template miner with v11 refinements + v20 agnostic attributes:
      1. Post-spectral signature purification
      2. Subtree cardinality (leaf) filter
      3. Hierarchical subsumption resolution

    Attribute tokenization is fully agnostic: ALL attributes on every
    element are enumerated, tokenized via AttributeTokenizer, and emitted
    as XPath-predicate-style tokens (``@{key}:{value_token}``).  The
    spectral graph's frequency filter (2 ≤ freq ≤ m/2) acts as an
    information-theoretic feature selector, automatically discarding:
      - Unique attributes (freq = 1): element IDs, session tokens, URLs
      - Universal attributes (freq = m): no discriminative power
    Only structurally discriminative attribute tokens survive, exactly
    as a tokenized-XPath predicate search would select them.

    No hard-coded attribute keys — the same tokenized-XPath approach used
    for spectral comparison is also used for relative selector generation,
    ensuring consistency between mining and cross-page matching.
    """

    # ─── Attribute agnosticism (XPath predicate tokenization) ──────
    # NO hard-coded attribute keys. ALL attributes on every element are
    # enumerated, tokenized via AttributeTokenizer, and emitted as
    # XPath-predicate-style tokens:
    #   presence:  ``@{key}``      ≡ XPath ``[@key]``
    #   value:     ``@{key}:{tok}`` ≡ XPath ``[contains(@key,'tok')]``
    #
    # The spectral graph's frequency filter (2 ≤ freq ≤ m/2) acts as
    # an information-theoretic feature selector, automatically discarding:
    #   - Unique tokens (freq=1): element IDs, session tokens, unique URLs
    #   - Universal tokens (freq=m): no discriminative power
    # Only structurally discriminative tokens survive — exactly the tokens
    # that would form effective XPath predicates for cross-page matching.
    _MAX_ATTR_VALUE_LEN = 300  # cap tokenisation of very long values

    MAX_CONDUCTANCE = 0.50
    LAMBDA2_CEILING = 0.80
    MIN_CHUNK_FREQ  = 2
    MAX_SIG_DEPTH   = 6

    # Large cohort threshold: above this, signature grouping alone is
    # sufficient and spectral analysis (O(m²)) is unnecessary.
    SPECTRAL_COHORT_LIMIT = 200

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._log = print if verbose else lambda *a, **k: None
        self._sig_cache: dict[int, dict[int, str]] = {}
        # Per-document term cache: extract once, reuse in partition,
        # cross-cohort merge, and selector generation.
        from .tfidf_cheeger_miner import NodeTermCache
        self._term_cache = NodeTermCache()

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def mine(self, dom: ShadowDOM) -> list[ChunkGroup]:
        self._log("[v13] Phase 1: Enumerating sibling cohorts...")
        cohorts = self._enumerate_cohorts(dom)
        self._log(f"[v13] Found {len(cohorts)} branching points")

        self._log("[v22] Phase 2: TF-IDF Cheeger partitioning...")
        raw_groups: list[tuple[list[ShadowNode], ShadowNode]] = []

        for parent, siblings in cohorts:
            groups = self._partition_cohort(parent, siblings)
            for _sig, members in groups:
                if len(members) >= self.MIN_CHUNK_FREQ:
                    raw_groups.append((members, parent))

        self._log(
            f"[v22] {len(raw_groups)} raw template groups (after freq filter)"
        )

        self._log("[v22] Phase 3: TF-IDF cross-cohort merge...")
        chunks = self._tfidf_merge_and_emit(raw_groups)
        self._log(f"[v22] {len(chunks)} chunks after TF-IDF merge")

        self._log("[v13] Phase 4: Signature height filter...")
        before_leaf = len(chunks)
        chunks = self._filter_leaf_groups(chunks)
        self._log(
            f"[v13] {before_leaf} → {len(chunks)} after height filter"
        )

        self._log("[v13] Phase 5: Content-based deduplication...")
        before_dedup = sum(c.frequency for c in chunks)
        chunks = self._deduplicate_by_content(chunks)
        after_dedup = sum(c.frequency for c in chunks)
        self._log(
            f"[v13] {before_dedup} → {after_dedup} instances "
            f"({len(chunks)} groups) after dedup"
        )

        self._log("[v13] Phase 6: Anchor-interior splitting...")
        before_anchor = len(chunks)
        chunks = self._split_anchor_interior(chunks)
        self._log(
            f"[v13] {before_anchor} → {len(chunks)} after anchor splitting"
        )

        self._log("[v13] Phase 7: Hierarchical subsumption...")
        before_sub = len(chunks)
        chunks = self._resolve_subsumption(chunks)
        self._log(
            f"[v13] {before_sub} → {len(chunks)} after subsumption"
        )

        self._log("[v17] Phase 8: Cross-instance sub-template mining...")
        before_cist = len(chunks)
        chunks = self._mine_cross_instance_subtemplates(chunks)
        new_sub = len(chunks) - before_cist
        self._log(
            f"[v17] {before_cist} + {new_sub} sub-templates = {len(chunks)} total"
        )

        self._log("[v14] Phase 9: Purity-dominance redundancy filter...")
        before_purity = len(chunks)
        chunks = self._filter_purity_dominated(chunks)
        self._log(
            f"[v14] {before_purity} → {len(chunks)} after purity filter"
        )

        # Phase 9.5: CIST structural deduplication.
        # Instead of eliminating all CIST children whose parent survives
        # (which destroys valuable atomic sub-templates), we:
        #   (a) Merge CIST chunks sharing the same structural signature
        #       (multiple composites often mine identical patterns)
        #   (b) Apply intra-CIST subsumption: if CIST chunk A's instances
        #       are all descendants of CIST chunk B's instances, A is
        #       redundant
        # This preserves atomic card-level granularity while eliminating
        # the signature-duplicate explosion seen on multi-composite pages.
        cist_chunks = [ch for ch in chunks if getattr(ch, '_parent_chunk_id', -1) >= 0]
        non_cist = [ch for ch in chunks if getattr(ch, '_parent_chunk_id', -1) < 0]

        if cist_chunks:
            # (a) Merge by structural signature: keep one chunk per sig,
            #     union instance nodes, deduplicate by node identity
            from collections import defaultdict as _dd
            sig_groups: dict[str, list[ChunkGroup]] = _dd(list)
            for ch in cist_chunks:
                sig_groups[ch._structural_sig].append(ch)

            merged_cist: list[ChunkGroup] = []
            merge_count = 0
            for sig, group in sig_groups.items():
                if len(group) == 1:
                    merged_cist.append(group[0])
                    continue

                # Merge: union all instance nodes, deduplicate by id
                seen_ids: set[int] = set()
                merged_nodes: list = []
                merged_xpaths: list[str] = []
                # Pick the chunk with the richest metadata as base
                base = max(group, key=lambda c: c.frequency)
                for ch in group:
                    for i, node in enumerate(ch._instance_nodes):
                        if id(node) not in seen_ids:
                            seen_ids.add(id(node))
                            merged_nodes.append(node)
                            if i < len(ch.trie_paths):
                                merged_xpaths.append(ch.trie_paths[i])

                base._instance_nodes = merged_nodes
                base.trie_paths = merged_xpaths
                base.frequency = len(merged_nodes)
                base.selectors = sorted(set(merged_xpaths))
                merged_cist.append(base)
                merge_count += len(group) - 1

            if merge_count:
                self._log(
                    f"[v19] Merged {merge_count} duplicate-sig CIST "
                    f"sub-templates ({len(cist_chunks)} → {len(merged_cist)})"
                )

            # (b) Intra-CIST subsumption: remove CIST chunks whose
            #     instances are all inside another CIST chunk's instances
            cist_node_ids = []
            for ch in merged_cist:
                cist_node_ids.append({id(n) for n in ch._instance_nodes})

            subsumed = set()
            for i, ch_i in enumerate(merged_cist):
                if i in subsumed:
                    continue
                for j, ch_j in enumerate(merged_cist):
                    if i == j or j in subsumed:
                        continue
                    # Check: is j's every instance a descendant of i's instances?
                    all_inside = True
                    for node in ch_j._instance_nodes:
                        found = False
                        ancestor = node.parent
                        depth_limit = 30
                        while ancestor and depth_limit > 0:
                            if id(ancestor) in cist_node_ids[i]:
                                found = True
                                break
                            ancestor = ancestor.parent
                            depth_limit -= 1
                        if not found:
                            all_inside = False
                            break
                    if all_inside:
                        subsumed.add(j)

            if subsumed:
                self._log(
                    f"[v19] Intra-CIST subsumption: removed "
                    f"{len(subsumed)} nested sub-templates"
                )

            final_cist = [
                ch for i, ch in enumerate(merged_cist) if i not in subsumed
            ]
            chunks = non_cist + final_cist
            self._log(
                f"[v19] Phase 9.5: {len(cist_chunks)} CIST → "
                f"{len(final_cist)} after dedup+subsumption"
            )
        else:
            self._log("[v19] Phase 9.5: no CIST sub-templates to process")

        self._log("[v18] Phase 10: Structural homogeneity refinement...")
        before_refine = len(chunks)
        chunks = self._refine_structural_homogeneity(chunks)
        self._log(
            f"[v18] {before_refine} → {len(chunks)} after homogeneity refinement"
        )

        self._log("[v19] Phase 11: Cross-chunk content deduplication...")
        before_xdedup = sum(c.frequency for c in chunks)
        chunks = self._deduplicate_cross_chunk(chunks)
        after_xdedup = sum(c.frequency for c in chunks)
        self._log(
            f"[v19] {before_xdedup} → {after_xdedup} instances "
            f"({len(chunks)} groups) after cross-chunk dedup"
        )

        self._log("[v21] Phase 11b: URL-based cross-chunk dedup...")
        before_url_dedup = len(chunks)
        chunks = self._deduplicate_cross_chunk_urls(chunks)
        self._log(
            f"[v21] {before_url_dedup} → {len(chunks)} after URL dedup"
        )

        # Re-number
        for i, ch in enumerate(chunks):
            ch.chunk_id = i

        # Note: XPath selector computation deferred to WebDistiller.process()
        # which runs AFTER all chunk types (structural, text/nav, search,
        # pagination) are assembled.  This enables inter-chunk discrimination
        # across the full chunk set, not just structural chunks.

        return chunks

    # =================================================================
    # PHASE 1: COHORT ENUMERATION (Tree Contraction)
    # =================================================================

    def _enumerate_cohorts(
        self, dom: ShadowDOM
    ) -> list[tuple[ShadowNode, list[ShadowNode]]]:
        cohorts = []
        visited = set()

        queue = deque([dom.root])
        while queue:
            node = queue.popleft()
            nid = id(node)
            if nid in visited:
                continue
            visited.add(nid)

            children = self._get_effective_children(node)

            if len(children) >= 2:
                cohorts.append((node, children))

            for child in children:
                if id(child) not in visited:
                    queue.append(child)

        return cohorts

    def _get_effective_children(self, node: ShadowNode) -> list[ShadowNode]:
        raw_children = []
        for child in node.get_children(include_shadow=True):
            tag = child.tag.lower()
            if tag.startswith('#') and tag != '#shadow-root':
                continue
            if tag in SKIP_TAGS:
                continue
            raw_children.append(child)

        effective = []
        for child in raw_children:
            current = child
            while True:
                sub_children = []
                for sc in current.get_children(include_shadow=True):
                    t = sc.tag.lower()
                    if t.startswith('#') and t != '#shadow-root':
                        continue
                    if t in SKIP_TAGS:
                        continue
                    sub_children.append(sc)
                if len(sub_children) == 1:
                    current = sub_children[0]
                else:
                    break
            effective.append(current)

        return effective

    # =================================================================
    # PHASE 2: PER-COHORT SPECTRAL PARTITIONING + PURIFICATION
    # =================================================================

    def _partition_cohort(
        self,
        parent: ShadowNode,
        siblings: list[ShadowNode],
    ) -> list[tuple[str, list[ShadowNode]]]:
        """
        Partition siblings via TF-IDF Cheeger cuts.

        For cohorts of 4+ siblings: TF-IDF vectorisation of structural
        attributes (excluding text and URLs) → cosine similarity affinity
        matrix → recursive Cheeger cuts with local IDF re-weighting.

        For tiny (<4) cohorts: direct signature grouping (spectral
        analysis is unnecessary — just group by subtree shape).

        Returns list of (label, cluster_nodes) tuples.  The label is
        an empty string for TF-IDF clusters (cross-cohort merge uses
        TF-IDF centroids instead of signature strings).
        """
        m = len(siblings)

        if m < 4:
            # Tiny cohort: direct signature grouping (cheap)
            sig_groups: defaultdict[str, list[ShadowNode]] = defaultdict(list)
            for s in siblings:
                sig = cached_signature(s, max_depth=3)
                sig_groups[sig].append(s)
            return [('', members) for members in sig_groups.values()]

        # ── TF-IDF Cheeger partition (cached terms) ───────────────
        from .tfidf_cheeger_miner import TfIdfCheegerMiner
        cheeger = TfIdfCheegerMiner(verbose=False, cache=self._term_cache)
        clusters = cheeger.partition_cohort(siblings)

        # Return clusters with empty label — the TF-IDF cross-cohort
        # merge (Phase 3) uses centroid cosine similarity instead of
        # signature-string matching.
        return [('', cluster) for cluster in clusters
                if len(cluster) >= self.MIN_CHUNK_FREQ]

    def _adaptive_signature(
        self, node: ShadowNode, cohort: list[ShadowNode]
    ) -> str:
        """
        Compute H_d at the shallowest depth where the cohort grouping
        has stabilized. This tolerates minor deep-level variations
        (e.g., optional badge elements) while still separating truly
        different structures.
        """
        nid = id(node)
        if nid not in self._sig_cache:
            sigs = {}
            for d in range(self.MAX_SIG_DEPTH + 1):
                sigs[d] = cached_signature(node, max_depth=d)
            self._sig_cache[nid] = sigs

        # Return the stabilized signature (deepest computed)
        # Adaptive depth selection happens at the cohort level in
        # _group_by_signature and _spectral_partition_purified
        cached = self._sig_cache[nid]
        return cached[self.MAX_SIG_DEPTH]

    def _select_adaptive_depth(
        self, siblings: list[ShadowNode]
    ) -> int:
        """
        Find the shallowest depth d where the partition of the cohort
        by H_d is identical to the partition by H_{d+1}.

        This is the stabilization point: going deeper doesn't refine
        the grouping further. It naturally tolerates optional deep-level
        elements while capturing the essential structure.

        MINIMUM DEPTH = 1: Depth 0 produces bare-tag merge keys (e.g. 'a',
        'div') which capture zero structural information about the subtree.
        When used as cross-cohort merge keys, depth-0 signatures conflate
        elements with the same tag but entirely different structures
        (e.g., navigation cards merge with footer links). Depth 1 is the
        structural minimum: it includes the first-order branching pattern
        (children tag sequence), providing meaningful discrimination.
        """
        m = len(siblings)
        if m < 2:
            return 1  # Minimum useful depth

        prev_partition = None
        for d in range(self.MAX_SIG_DEPTH + 1):
            # Build partition at depth d
            groups: dict[str, list[int]] = defaultdict(list)
            for i, s in enumerate(siblings):
                cached = self._sig_cache.get(id(s), {})
                sig = cached.get(d, cached_signature(s, max_depth=d))
                groups[sig].append(i)

            # Convert to canonical partition representation
            partition = frozenset(
                frozenset(indices) for indices in groups.values()
            )

            if prev_partition is not None and partition == prev_partition:
                return max(1, d - 1)  # Minimum depth = 1

            prev_partition = partition

        return self.MAX_SIG_DEPTH

    def _group_by_signature(
        self,
        siblings: list[ShadowNode],
        sig_map: dict[int, str],
    ) -> list[tuple[str, list[ShadowNode]]]:
        """Group siblings by exact stabilized signature."""
        # Use adaptive depth for this cohort
        depth = self._select_adaptive_depth(siblings)

        groups: defaultdict[str, list[ShadowNode]] = defaultdict(list)
        for s in siblings:
            cached = self._sig_cache.get(id(s), {})
            sig = cached.get(depth, sig_map[id(s)])
            groups[sig].append(s)

        return [(sig, members) for sig, members in groups.items()]

    def _spectral_partition_purified(
        self,
        siblings: list[ShadowNode],
        sig_map: dict[int, str],
    ) -> list[tuple[str, list[ShadowNode]]]:
        """
        Build local augmented graph, spectral bisect, then PURIFY
        each spectral group by sub-partitioning on exact signature.

        This is the key v11 refinement: spectral clustering proposes
        broad separation, signature matching enforces structural purity.
        """
        m = len(siblings)

        # Select adaptive depth for this cohort
        adaptive_depth = self._select_adaptive_depth(siblings)

        # ── Collect tokens per sibling ─────────────────────────────
        # Fully agnostic: every attribute on every element is enumerated
        # and tokenized as XPath predicate notation. The frequency filter
        # below (2 ≤ freq ≤ m/2) performs automatic information-theoretic
        # feature selection — no need to hard-code which attributes matter.
        sibling_tokens: list[set[str]] = []
        token_freq: defaultdict[str, int] = defaultdict(int)

        for node in siblings:
            tokens = set()

            # ── Tag token (XPath element selector) ────────────
            tokens.add(f"tag:{node.tag.lower()}")

            # ── Attribute tokens (XPath predicate selectors) ──
            # Agnostic: iterate ALL attributes, tokenize ALL values.
            for key, val in node.get_all_attrs().items():
                key_lower = key.lower()
                # Presence token: equivalent to XPath [@key]
                tokens.add(f"@{key_lower}")
                # Value tokens: equivalent to XPath [contains(@key,'tok')]
                val_str = str(val or '')[:self._MAX_ATTR_VALUE_LEN]
                if val_str:
                    subtokens = AttributeTokenizer.tokenize(val_str)
                    tokens.update(
                        f"@{key_lower}:{t}" for t in subtokens
                    )

            # ── Subtree signature tokens at multiple depths ───
            cached = self._sig_cache.get(id(node), {})
            for d in range(1, self.MAX_SIG_DEPTH + 1):
                if d in cached:
                    tokens.add(f"sig_d{d}:{cached[d]}")

            sibling_tokens.append(tokens)
            for t in tokens:
                token_freq[t] += 1

        # ── Filter tokens: 2 <= freq <= m/2 ───────────────────────
        half_m = m / 2
        valid_tokens = {
            t for t, f in token_freq.items() if 2 <= f <= half_m
        }

        if not valid_tokens:
            return self._group_by_signature(siblings, sig_map)

        # ── Build augmented graph with local IDF ───────────────────
        idf = {t: math.log(m / token_freq[t]) for t in valid_tokens}

        G = nx.Graph()
        for i in range(m):
            G.add_node(i)
        for i, tokens in enumerate(sibling_tokens):
            for t in tokens:
                if t in valid_tokens:
                    G.add_edge(i, t, weight=idf[t])

        # ── Recursive spectral bisection ───────────────────────────
        all_nodes = list(G.nodes())
        final_partitions: list[list[int]] = []
        bfs_queue = [(all_nodes, 0)]

        while bfs_queue:
            nodes, depth = bfs_queue.pop(0)
            elem_nodes = [n for n in nodes if isinstance(n, int)]

            if len(elem_nodes) < 2:
                if elem_nodes:
                    final_partitions.append(elem_nodes)
                continue

            if len(elem_nodes) < 4 or depth > 12:
                final_partitions.append(elem_nodes)
                continue

            left, right, phi_star, lambda2 = self._spectral_bisect(G, nodes)

            left_elems = [n for n in left if isinstance(n, int)]
            right_elems = [n for n in right if isinstance(n, int)]

            accept = (
                phi_star < self.MAX_CONDUCTANCE
                and lambda2 < self.LAMBDA2_CEILING
                and len(left_elems) >= 2
                and len(right_elems) >= 2
                and depth < 12
            )

            if accept:
                bfs_queue.append((left, depth + 1))
                bfs_queue.append((right, depth + 1))
            else:
                final_partitions.append(elem_nodes)

        # ── PURIFICATION: sub-partition each spectral group by ─────
        # ── exact signature at adaptive depth                   ─────
        results: list[tuple[str, list[ShadowNode]]] = []

        for partition in final_partitions:
            # Sub-group by exact signature at adaptive depth
            sub_groups: defaultdict[str, list[ShadowNode]] = defaultdict(list)
            for idx in partition:
                node = siblings[idx]
                cached = self._sig_cache.get(id(node), {})
                sig = cached.get(adaptive_depth, sig_map[id(node)])
                sub_groups[sig].append(node)

            # Emit each pure sub-group
            for sig, members in sub_groups.items():
                if len(members) >= self.MIN_CHUNK_FREQ:
                    results.append((sig, members))

        return results

    # =================================================================
    # SPECTRAL BISECTION (unchanged from v10)
    # =================================================================

    def _spectral_bisect(self, G_full: nx.Graph, nodes: list):
        H = G_full.subgraph(nodes)

        if not nx.is_connected(H):
            comps = list(nx.connected_components(H))
            if len(comps) >= 2:
                biggest = max(comps, key=len)
                rest = [n for c in comps for n in c if c is not biggest]
                return list(biggest), rest, 0.0, 0.0
            return [], [], 1.0, 2.0

        n = len(H)
        if n < 4:
            return [], [], 1.0, 2.0

        node_list = list(H.nodes())
        adj = nx.to_scipy_sparse_array(H, weight='weight', format='csr')
        degrees = np.array(adj.sum(axis=1)).flatten()

        if np.any(degrees <= 0):
            return [], [], 1.0, 2.0

        D_inv_sqrt = sparse.diags(1.0 / np.sqrt(degrees))
        L_norm = sparse.eye(n) - D_inv_sqrt @ adj @ D_inv_sqrt

        try:
            k = min(n - 1, 3)
            if k < 2:
                return [], [], 1.0, 2.0
            vals, vecs = eigsh(L_norm, k=k, which='SM', tol=1e-4)
            lambda2 = float(vals[1])
            fiedler = vecs[:, 1]
        except Exception:
            return [], [], 1.0, 2.0

        # Full level-set sweep
        sorted_indices = np.argsort(fiedler)
        sorted_nodes = [node_list[i] for i in sorted_indices]
        sorted_degrees = degrees[sorted_indices]
        total_vol = float(degrees.sum())

        in_left = set()
        vol_left = 0.0
        cut_val = 0.0
        best_cond = float('inf')
        best_split = -1

        adj_dict = {}
        for nd in node_list:
            adj_dict[nd] = {}
            for nb in H.neighbors(nd):
                adj_dict[nd][nb] = H[nd][nb].get('weight', 1.0)

        for split_i in range(n - 1):
            u = sorted_nodes[split_i]
            u_deg = sorted_degrees[split_i]

            for nb, w in adj_dict[u].items():
                if nb in in_left:
                    cut_val -= w
                else:
                    cut_val += w

            vol_left += u_deg
            in_left.add(u)

            vol_right = total_vol - vol_left
            denom = min(vol_left, vol_right)
            if denom <= 1e-10:
                continue

            cond = cut_val / denom
            if cond < best_cond:
                best_cond = cond
                best_split = split_i + 1

        if best_split <= 0 or best_split >= n:
            return [], [], 1.0, lambda2

        return (
            sorted_nodes[:best_split],
            sorted_nodes[best_split:],
            best_cond,
            lambda2,
        )

    # =================================================================
    # PHASE 3: CROSS-COHORT MERGING AND CHUNK EMISSION
    # =================================================================

    def _merge_and_emit(
        self,
        raw_groups: list[tuple[str, list[ShadowNode], ShadowNode]],
    ) -> list[ChunkGroup]:
        by_sig: defaultdict[str, list[tuple[list[ShadowNode], ShadowNode]]] = (
            defaultdict(list)
        )
        for sig, members, parent in raw_groups:
            by_sig[sig].append((members, parent))

        chunks: list[ChunkGroup] = []
        seen_nodes: set[int] = set()

        for structural_sig, entries in by_sig.items():
            all_members: list[ShadowNode] = []
            parents: list[ShadowNode] = []
            for members, parent in entries:
                for m in members:
                    if id(m) not in seen_nodes:
                        all_members.append(m)
                        seen_nodes.add(id(m))
                parents.append(parent)

            if len(all_members) < self.MIN_CHUNK_FREQ:
                continue

            xpaths = [cached_xpath(m) for m in all_members]

            content_types: set[ContentCategory] = set()
            for m in all_members[:5]:
                content_types.update(_classify_subtree(m))

            if len(parents) == 1:
                container = parents[0]
            else:
                container = self._find_lca_nodes(parents)

            container_xpath = (
                cached_xpath(container) if container else "/html/body"
            )

            primary_tag_sig = _agnostic_display_signature(all_members)

            # Compute TRUE structural signature from instance structure,
            # not from the grouping key (which may be at adaptive depth).
            # v12: use MAX_SIG_DEPTH to capture full hierarchical structure
            # for accurate height-based filtering.
            if all_members:
                true_structural_sig = cached_signature(
                    all_members[0], max_depth=6
                )
            else:
                true_structural_sig = structural_sig

            chunk = ChunkGroup(
                chunk_id=len(chunks),
                selectors=sorted(set(xpaths)),
                trie_paths=xpaths,
                frequency=len(all_members),
                content_types=content_types,
                subtree_root=container_xpath,
                # Display signature: tag.class for human readability
                signature=f"{primary_tag_sig}",
                samples=[],
                _instance_nodes=all_members,
                # Store structural signature for tree-theoretic filtering
                _structural_sig=true_structural_sig,
            )
            chunks.append(chunk)

        chunks.sort(key=lambda c: c.frequency, reverse=True)
        for i, ch in enumerate(chunks):
            ch.chunk_id = i

        return chunks

    def _tfidf_merge_and_emit(
        self,
        raw_groups: list[tuple[list[ShadowNode], ShadowNode]],
    ) -> list[ChunkGroup]:
        """
        TF-IDF cosine-similarity cross-cohort merge (replaces signature merge).

        Uses the dual-space tokenization:
        - Source A+B+C+E (lateral): structural identity features
        - Source D (vertical): xpath-path tokens encoding graph distance

        Two clusters from different cohorts merge when their mean TF-IDF
        centroids (including path tokens) have cosine similarity > threshold.

        This replaces _merge_and_emit's signature-string grouping with
        continuous feature-space similarity, absorbing the adaptive-depth
        signature stabilization into the IDF weighting.
        """
        from .tfidf_cheeger_miner import CrossCohortMerger

        merger = CrossCohortMerger(
            verbose=self.verbose, cache=self._term_cache)
        merged = merger.merge(raw_groups)

        chunks: list[ChunkGroup] = []
        for all_members, tfidf_selector, centroid in merged:
            if len(all_members) < self.MIN_CHUNK_FREQ:
                continue

            xpaths = [cached_xpath(m) for m in all_members]

            content_types: set[ContentCategory] = set()
            for m in all_members[:5]:
                content_types.update(_classify_subtree(m))

            # LCA for container xpath
            parents = list({id(m.parent): m.parent for m in all_members
                           if m.parent}.values())
            if len(parents) == 1:
                container = parents[0]
            elif parents:
                container = self._find_lca_nodes(parents)
            else:
                container = None

            container_xpath = (
                cached_xpath(container) if container else "/html/body"
            )

            # Display signature from agnostic tag+token analysis
            primary_tag_sig = _agnostic_display_signature(all_members)

            # Structural signature for height filter (from first instance)
            true_structural_sig = cached_signature(
                all_members[0], max_depth=6
            ) if all_members else ''

            chunk = ChunkGroup(
                chunk_id=len(chunks),
                selectors=sorted(set(xpaths)),
                trie_paths=xpaths,
                frequency=len(all_members),
                content_types=content_types,
                subtree_root=container_xpath,
                signature=f"{primary_tag_sig}",
                samples=[],
                _instance_nodes=all_members,
                _structural_sig=true_structural_sig,
            )
            chunks.append(chunk)

        chunks.sort(key=lambda c: c.frequency, reverse=True)
        for i, ch in enumerate(chunks):
            ch.chunk_id = i

        return chunks

    # =================================================================
    # PHASE 4: LEAF FILTER (Subtree Cardinality)
    # =================================================================

    def _filter_leaf_groups(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Remove template groups whose structural signature has tree height < 2.

        Height 0: bare tag (e.g., "div") — degenerate, no structure
        Height 1: flat branching / star topology (e.g., "div(span,span)",
                  "svg(path,path)", "li(div,div)") — no hierarchy
        Height 2+: genuine hierarchical nesting (e.g., "article(div,
                  footer,header(a,h2))") — multi-level structure

        The threshold h >= 2 is NOT a tunable parameter — it is the
        tree-theoretic minimum for non-trivial hierarchy. A tree of
        height 1 is a star graph K_{1,k} with no internal structure
        beyond the root. Height 2 is the minimum for encoding parent →
        intermediate → descendant relationships.

        See THEORY_v12.md §3.1 for full justification.
        """
        filtered = []
        for chunk in chunks:
            structural_sig = getattr(chunk, '_structural_sig', '')

            if not structural_sig:
                # Non-cohort chunks (search inputs, pagination) — keep
                filtered.append(chunk)
                continue

            h = signature_height(structural_sig)
            if h >= 2:
                filtered.append(chunk)
            else:
                self._log(
                    f"  [height filter] Removed: freq={chunk.frequency} "
                    f"height={h} structural_sig={structural_sig[:60]} "
                    f"display={chunk.signature[:40]}"
                )

        return filtered

    # =================================================================
    # PHASE 5: CONTENT-BASED DEDUPLICATION
    # =================================================================

    @staticmethod
    def _content_fingerprint(node: ShadowNode) -> str:
        """
        Compute a content fingerprint for an instance node.

        The fingerprint captures the semantic content of the subtree:
        normalized text + sorted resource URLs. Two instances with the
        same fingerprint represent the same information, even if they
        appear at different DOM locations.

        Agnostic URL extraction: ALL attributes on every descendant are
        inspected for URL-like values (starting with '/', 'http', or
        containing '.'). No hardcoded attribute keys — this mirrors the
        tokenized-XPath predicate approach used throughout the pipeline.
        """
        text = node.get_text().strip()

        # Agnostic: extract URL-like values from ALL attributes
        resources = []
        for desc in node.iter_descendants():
            for key, val in desc.get_all_attrs().items():
                if not val or not isinstance(val, str):
                    continue
                v = val.strip()
                # Heuristic: looks like a URL (starts with /, http, or has
                # path-like structure). Covers href, src, data-src, action,
                # poster, srcset, background-image:url(), etc.
                if (v.startswith(('/', 'http://', 'https://'))
                        or ('.' in v and '/' in v)):
                    resources.append(v[:200])

        resource_str = '|'.join(sorted(set(resources)))
        return f"{text[:500]}||{resource_str[:500]}"

    def _deduplicate_by_content(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Remove content-duplicate instances within each template group.

        Many websites render the same DOM subtree in multiple locations
        for responsive design (desktop + mobile layouts, sidebar mirrors).
        These are structurally identical AND content-identical nodes at
        different xpaths. The structural miner correctly identifies them
        as instances of the same template, but the user wants unique
        content, not duplicate DOM nodes.

        Algorithm: For each group, compute per-instance content
        fingerprints. Keep only one representative per fingerprint
        (the first encountered). This is a quotient of the instance
        set by content equivalence.

        This phase operates AFTER structural mining to preserve correct
        frequency counts during spectral analysis (where duplicate
        structures legitimately participate in cohort statistics).
        """
        result = []
        for chunk in chunks:
            if not chunk._instance_nodes:
                result.append(chunk)
                continue

            # Compute fingerprints and keep unique instances
            seen_fp: set[str] = set()
            unique_nodes: list[ShadowNode] = []

            for node in chunk._instance_nodes:
                fp = self._content_fingerprint(node)
                if fp not in seen_fp:
                    seen_fp.add(fp)
                    unique_nodes.append(node)

            removed = len(chunk._instance_nodes) - len(unique_nodes)
            if removed > 0:
                self._log(
                    f"  [dedup] {chunk.frequency}→{len(unique_nodes)} "
                    f"({removed} content duplicates) "
                    f"sig={chunk.signature[:50]}"
                )

                if len(unique_nodes) < self.MIN_CHUNK_FREQ:
                    # Too few unique instances — remove group
                    self._log(
                        f"  [dedup] Removed group (< {self.MIN_CHUNK_FREQ} "
                        f"unique instances)"
                    )
                    continue

                # Update group with deduplicated instances
                chunk._instance_nodes = unique_nodes
                chunk.frequency = len(unique_nodes)
                chunk.selectors = sorted(set(
                    cached_xpath(n) for n in unique_nodes
                ))
                chunk.trie_paths = [
                    cached_xpath(n) for n in unique_nodes
                ]
                # Recompute content types
                content_types: set[ContentCategory] = set()
                for m in unique_nodes[:5]:
                    content_types.update(_classify_subtree(m))
                chunk.content_types = content_types
                chunk.samples = []

            result.append(chunk)

        return result

    # =================================================================
    # PHASE 6: ANCHOR-INTERIOR SPLITTING
    # =================================================================

    @staticmethod
    def _is_anchor_interior(node: ShadowNode) -> bool:
        """
        Check if node is a descendant of a **navigation-bearing** element
        but is not a navigation-bearing element itself.

        Only checks attributes that create actual user navigation:
        href, action, data-href, data-url, formaction.  Excludes
        Schema.org microdata (itemtype), RDFa, and other metadata
        URLs that don't create navigable contexts.

        Nodes inside a navigation-bearing ancestor inherit navigability
        context and are not independently navigable content units.
        """
        if _node_has_nav_url(node):
            return False  # IS the navigable boundary
        ancestor = node.parent
        while ancestor:
            tag = ancestor.tag.lower()
            if _node_has_nav_url(ancestor):
                return True
            if tag in ('#document', 'html', 'body'):
                return False
            ancestor = ancestor.parent
        return False

    @staticmethod
    def _promote_to_anchor_root(
        nodes: list[ShadowNode],
    ) -> list[ShadowNode]:
        """
        Promote anchor-interior instances to their nearest navigation-
        bearing ancestor.  Deduplicates by ancestor identity.
        """
        promoted: list[ShadowNode] = []
        seen_ids: set[int] = set()
        for node in nodes:
            anc = node.parent
            while anc:
                if _node_has_nav_url(anc):
                    nid = id(anc)
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        promoted.append(anc)
                    break
                if anc.tag.lower() in ('#document', 'html', 'body'):
                    break
                anc = anc.parent
        return promoted

    def _split_anchor_interior(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Split anchor-interior instances out of template groups.

        For each group, partition instances into:
          - anchor-exterior (self-contained): keep
          - anchor-interior (fragments inside <a>): discard

        This is embedded in the extraction pipeline, not post-hoc
        deduplication. It enforces a resource containment constraint:
        every emitted instance must self-contain its navigability
        context (either it IS an <a> tag, or it has <a> descendants,
        or it operates independently of any link).

        Groups where all instances are anchor-interior are removed
        entirely. Groups with mixed instances are reduced to their
        anchor-exterior subset.
        """
        result = []
        for chunk in chunks:
            if not chunk._instance_nodes:
                # Non-cohort chunks (search inputs, pagination) — keep
                result.append(chunk)
                continue

            # Partition instances by anchor-interior status
            exterior = []
            interior_count = 0
            for node in chunk._instance_nodes:
                if self._is_anchor_interior(node):
                    interior_count += 1
                else:
                    exterior.append(node)

            if interior_count == 0:
                # All instances are self-contained — keep unchanged
                result.append(chunk)
                continue

            if len(exterior) < self.MIN_CHUNK_FREQ:
                # All/most instances are anchor-interior.
                # Instead of eliminating, try PROMOTING each instance
                # to its nearest URL-bearing ancestor.  This preserves
                # card content that is wrapped entirely in <a> tags
                # (e.g. crystalvaults crystal guide cards).
                promoted = self._promote_to_anchor_root(
                    chunk._instance_nodes)
                if len(promoted) >= self.MIN_CHUNK_FREQ:
                    self._log(
                        f"  [anchor split] Promoted: freq={chunk.frequency}"
                        f"→{len(promoted)} (anchor-wrapped cards) "
                        f"sig={chunk.signature[:50]}"
                    )
                    xpaths = [cached_xpath(n) for n in promoted]
                    content_types: set[ContentCategory] = set()
                    for m in promoted[:5]:
                        content_types.update(_classify_subtree(m))
                    chunk._instance_nodes = promoted
                    chunk.frequency = len(promoted)
                    chunk.selectors = sorted(set(xpaths))
                    chunk.trie_paths = xpaths
                    chunk.content_types = content_types
                    chunk.samples = []
                    result.append(chunk)
                    continue

                self._log(
                    f"  [anchor split] Removed: freq={chunk.frequency} "
                    f"(all {interior_count} instances are anchor-interior) "
                    f"sig={chunk.signature[:50]}"
                )
                continue

            # Reduce group to self-contained instances only
            self._log(
                f"  [anchor split] Reduced: freq={chunk.frequency}→"
                f"{len(exterior)} ({interior_count} interior removed) "
                f"sig={chunk.signature[:50]}"
            )

            # Rebuild xpaths for remaining instances
            xpaths = [cached_xpath(n) for n in exterior]

            # Recompute content types from surviving instances
            content_types: set[ContentCategory] = set()
            for m in exterior[:5]:
                content_types.update(_classify_subtree(m))

            chunk._instance_nodes = exterior
            chunk.frequency = len(exterior)
            chunk.selectors = sorted(set(xpaths))
            chunk.trie_paths = xpaths
            chunk.content_types = content_types
            chunk.samples = []  # Will be re-sampled
            result.append(chunk)

        return result

    # =================================================================
    # PHASE 7: HIERARCHICAL SUBSUMPTION
    # =================================================================

    def _resolve_subsumption(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        If every instance of chunk G_i is a descendant of some instance
        of chunk G_j, then G_i is subsumed by G_j. Remove subsumed chunks.

        This eliminates redundant sub-template enumeration: images inside
        article cards are not listed as a separate template.
        """
        if len(chunks) < 2:
            return chunks

        # Build node-id → chunk mapping for efficient lookup
        # For each chunk, store the set of instance node ids
        chunk_node_ids: list[set[int]] = []
        for chunk in chunks:
            chunk_node_ids.append({id(n) for n in chunk._instance_nodes})

        # For subsumption check: for each instance root of G_i, walk
        # ancestors up to bounded depth looking for a G_j instance root
        # Build global ancestor index: node_id → set of chunk indices
        # that have this node as an instance root
        node_to_chunks: dict[int, set[int]] = defaultdict(set)
        for ci, chunk in enumerate(chunks):
            for node in chunk._instance_nodes:
                node_to_chunks[id(node)].add(ci)

        # Check subsumption: G_i ≺ G_j iff every instance of G_i has
        # an ancestor that is an instance of G_j
        subsumed_by: dict[int, set[int]] = defaultdict(set)  # i → {j, ...}

        for ci, chunk_i in enumerate(chunks):
            if not chunk_i._instance_nodes:
                continue

            # For each other chunk, check if chunk_i is subsumed
            for cj in range(len(chunks)):
                if ci == cj:
                    continue
                if len(chunks[cj]._instance_nodes) < 2:
                    continue

                # Check: every instance of ci has an ancestor in cj's instances
                cj_ids = chunk_node_ids[cj]
                all_subsumed = True

                for node in chunk_i._instance_nodes:
                    found_ancestor = False
                    ancestor = node.parent
                    depth_limit = 50
                    while ancestor and depth_limit > 0:
                        if id(ancestor) in cj_ids:
                            found_ancestor = True
                            break
                        ancestor = ancestor.parent
                        depth_limit -= 1

                    if not found_ancestor:
                        all_subsumed = False
                        break

                if all_subsumed:
                    subsumed_by[ci].add(cj)

        # Find maximal chunks: those not subsumed by any other.
        #
        # Composite-parent exemption: if the ONLY parents of G_i are
        # composite (contain ≥2 distinct hrefs), G_i is the natural
        # atomic sub-template and should NOT be subsumed. This preserves
        # gallery cards inside sections, article items inside grids, etc.
        # The coagulator will use these sub-templates for precise atom
        # extraction instead of ad-hoc href-walking.
        def _parent_is_composite(cj: int) -> bool:
            """Check if parent chunk instances are composite (multi-URL)."""
            sample = chunks[cj]._instance_nodes[:5]
            for node in sample:
                urls = AgnosticAttr.navigable_urls(node)
                if len(set(urls)) >= 2:
                    return True
            return False

        subsumed_indices = set()
        for ci, parents in subsumed_by.items():
            if not parents:
                continue

            all_parents_composite = all(
                _parent_is_composite(cj) for cj in parents
            )

            if all_parents_composite:
                max_parent_freq = max(
                    chunks[cj].frequency for cj in parents
                )
                if chunks[ci].frequency >= max_parent_freq:
                    # Verify child has content value — agnostic URL check
                    has_content = any(
                        AgnosticAttr.primary_url(sample_node)
                        for sample_node in chunks[ci]._instance_nodes[:5]
                    )
                    
                    if has_content:
                        self._log(
                            f"  [subsumption] KEPT freq={chunks[ci].frequency} "
                            f"sig={chunks[ci].signature[:50]} "
                            f"(parent freq={max_parent_freq} is composite)"
                        )
                        continue

            subsumed_indices.add(ci)
            self._log(
                f"  [subsumption] Chunk freq={chunks[ci].frequency} "
                f"sig={chunks[ci].signature[:50]} subsumed by "
                f"freq={chunks[list(parents)[0]].frequency}"
            )

        result = [
            ch for ci, ch in enumerate(chunks)
            if ci not in subsumed_indices
        ]

        return result

    # =================================================================
    # UTILITY
    # =================================================================

    @staticmethod
    def _find_lca_nodes(nodes: list[ShadowNode]) -> Optional[ShadowNode]:
        if not nodes:
            return None
        if len(nodes) == 1:
            return nodes[0]

        paths = []
        for n in nodes:
            anc = list(n.get_ancestors())
            anc.reverse()
            anc.append(n)
            paths.append(anc)

        shortest = min(paths, key=len)
        lca = None
        for i, node in enumerate(shortest):
            if all(len(p) > i and p[i] is node for p in paths):
                lca = node
            else:
                break
        return lca

    # =================================================================
    # PHASE 8: PURITY-DOMINANCE REDUNDANCY FILTER
    # =================================================================

    @staticmethod
    def _instance_purity(node: ShadowNode) -> float:
        """
        Multi-channel self-duplication purity for a single instance.
        
        Checks three channels for internal duplication within a node's
        subtree. Each channel measures unique/total for its element type.
        Channels with fewer than 2 elements return 1.0.
        
        All URL/media extraction is agnostic — uses AgnosticAttr to
        inspect ALL attributes by value heuristics, not hardcoded keys.
        
        Returns min(channel_purities):
          1.0 = no detectable duplication
          0.5 = every element appears exactly twice (2× rendering)
          <0.5 = severe duplication
        """
        channels = []
        
        # Skip descendants inside fallback-copy elements (duplicates)
        noscript_ids = set()
        for desc in node.iter_descendants():
            if AgnosticAttr.is_fallback_copy(desc):
                noscript_ids.add(id(desc))
                for nd in desc.iter_descendants():
                    noscript_ids.add(id(nd))
        
        def _visible_descendants():
            """Yield descendants not inside noscript/template."""
            for desc in node.iter_descendants():
                if id(desc) not in noscript_ids:
                    yield desc
        
        # ── Heading channel (agnostic: catches role="heading" too) ──
        heading_texts = []
        for desc in _visible_descendants():
            if AgnosticAttr.is_heading_like(desc):
                t = desc.get_text().strip()
                if t:
                    heading_texts.append(t)
        if len(heading_texts) >= 2:
            channels.append(len(set(heading_texts)) / len(heading_texts))
        
        # ── Media channel (agnostic URL extraction) ──
        # Combines image/video/source — inspects ALL attributes per element
        media_keys = []
        for desc in _visible_descendants():
            key = AgnosticAttr.primary_media_key(desc)
            if key:
                media_keys.append(key)
        if len(media_keys) >= 2:
            channels.append(len(set(media_keys)) / len(media_keys))
        
        # ── URL channel (agnostic navigable URL extraction) ──
        # Note: require ≥3 URLs. Two identical is the baseline
        # image+title-link-to-same-page pattern and is NOT duplication.
        urls = AgnosticAttr.navigable_urls(node)
        if len(urls) >= 3:
            channels.append(len(set(urls)) / len(urls))
        
        if not channels:
            return 1.0
        return min(channels)

    @staticmethod
    def _instance_primary_href(node: ShadowNode) -> Optional[str]:
        """Extract primary navigable URL from a node (agnostic)."""
        url = AgnosticAttr.primary_url(node)
        return url.strip().rstrip('/').lower() if url else None

    def _filter_purity_dominated(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Eliminate template groups that are self-duplicated rendering
        artifacts of content already covered cleanly by another group.
        
        A group G_i is purity-dominated if:
          1. G_i's content (href set) is fully covered by some G_j
             (i.e. H_i ⊆ H_j), AND
          2. G_i has strictly lower mean purity than G_j.
        
        This catches patterns like DuckDuckGo's dual-rendered search
        results where the same article element appears in two template
        variants — one clean (1 button, 1 title, 1 snippet) and one
        bloated (2× of each internal structure, identical content).
        """
        if len(chunks) < 2:
            return chunks

        # Compute href set and mean purity for each group
        group_info = []
        for chunk in chunks:
            href_set = set()
            purities = []
            for node in chunk._instance_nodes:
                href = self._instance_primary_href(node)
                if href:
                    href_set.add(href)
                purities.append(self._instance_purity(node))
            mean_purity = sum(purities) / len(purities) if purities else 1.0
            group_info.append((href_set, mean_purity))

        # Build ancestry map: for each chunk, collect all ancestor chunk_ids
        # so that no composite can be eliminated by any of its CIST descendants
        ancestor_ids = {}  # chunk index → set of ancestor chunk_ids
        id_to_idx = {ch.chunk_id: idx for idx, ch in enumerate(chunks)}
        for idx, ch in enumerate(chunks):
            ancestors = set()
            cur_parent = getattr(ch, '_parent_chunk_id', -1)
            visited = set()
            while cur_parent >= 0 and cur_parent not in visited:
                ancestors.add(cur_parent)
                visited.add(cur_parent)
                if cur_parent in id_to_idx:
                    cur_parent = getattr(
                        chunks[id_to_idx[cur_parent]],
                        '_parent_chunk_id', -1)
                else:
                    break
            ancestor_ids[idx] = ancestors

        dominated = set()
        for i in range(len(chunks)):
            h_i, p_i = group_info[i]
            if not h_i:
                continue  # No hrefs — can't check coverage
            for j in range(len(chunks)):
                if i == j or j in dominated:
                    continue
                h_j, p_j = group_info[j]
                if not h_j:
                    continue
                # A composite must never be eliminated by its own CIST
                # sub-templates (direct or transitive): the parent IS the
                # content card, the children are internal structural parts.
                # Allowing children to dominate the parent fragments the
                # card into disconnected pieces.
                if chunks[i].chunk_id in ancestor_ids.get(j, set()):
                    continue
                # Check: is i's content fully covered by j with higher purity?
                if h_i <= h_j and p_i < p_j:
                    dominated.add(i)
                    break

        result = [ch for idx, ch in enumerate(chunks) if idx not in dominated]
        if dominated:
            for idx in sorted(dominated):
                ch = chunks[idx]
                _, p = group_info[idx]
                self._log(
                    f"[v14] Eliminated purity-dominated group: "
                    f"freq={ch.frequency} purity={p:.2f} "
                    f"{ch.signature[:50]}"
                )
        return result

    # =================================================================
    # PHASE 9: CROSS-INSTANCE SUB-TEMPLATE MINING (CIST)
    # =================================================================

    @staticmethod
    def _get_original_element_children(node: ShadowNode) -> list[ShadowNode]:
        """
        Return direct element children of a node on the ORIGINAL tree
        (no single-child chain contraction).

        This preserves nodes like li(div(a(div(span)))) that tree
        contraction would collapse to bare 'span'.
        """
        children = []
        for child in node.get_children(include_shadow=True):
            tag = child.tag.lower()
            if tag.startswith('#') and tag != '#shadow-root':
                continue
            if tag in SKIP_TAGS:
                continue
            children.append(child)
        return children

    def _is_chunk_composite(self, chunk: ChunkGroup) -> bool:
        """Check if a chunk's instances are composite (≥2 distinct navigable URLs)."""
        for node in chunk._instance_nodes[:5]:
            urls = set(AgnosticAttr.navigable_urls(node))
            if len(urls) >= 2:
                return True
        return False

    def _mine_cross_instance_subtemplates(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Cross-Instance Sub-Template Mining (CIST).

        For each composite chunk, pool descendant cohorts from the ORIGINAL
        tree (no contraction) across all instances, discovering sub-templates
        that per-cohort mining on the contracted tree cannot see.

        This solves two classes of invisible patterns:
        1. Single-child chain items (li→div→a→div→span) that contract to
           height-0 and are filtered (PosthumanArt submenu items)
        2. Periodic column patterns where alternating types (img-col, txt-col)
           are not individually recognized as templates

        Algorithm:
        - For each composite chunk C, walk each instance's original subtree
        - At each branching point, collect original element children
        - Pool children across all instances by structural signature
        - Emit groups meeting MIN_CHUNK_FREQ as new sub-template chunks

        The spectral interpretation: pooling creates the affinity graph G_P
        where connected components (by exact signature) are the sub-template
        types. The eigengap at position k (number of distinct signatures)
        perfectly separates them. See THEORY_v17.md §3.
        """
        new_chunks: list[ChunkGroup] = []
        existing_node_ids: set[int] = set()
        for ch in chunks:
            for node in ch._instance_nodes:
                existing_node_ids.add(id(node))

        # Also build ancestor lookup: for each existing instance node,
        # mark all its ancestors. This allows CIST to skip pooled children
        # that CONTAIN existing chunk instances (not just ARE them).
        # E.g., a fl-col wrapper containing a contracted text-column endpoint.
        nodes_containing_existing: set[int] = set()
        for ch in chunks:
            for node in ch._instance_nodes:
                ancestor = node.parent
                depth_limit = 30
                while ancestor and depth_limit > 0:
                    nodes_containing_existing.add(id(ancestor))
                    ancestor = ancestor.parent
                    depth_limit -= 1

        for chunk in chunks:
            if not self._is_chunk_composite(chunk):
                continue

            # Pool children from all branching points inside all instances
            # Key: structural signature → list of child nodes
            sig_pool: defaultdict[str, list[ShadowNode]] = defaultdict(list)

            for instance_node in chunk._instance_nodes:
                # BFS over the ORIGINAL subtree (no contraction)
                # STOP descending into nodes that belong to existing chunks
                # — their internal structure is already mined
                queue = deque([instance_node])
                while queue:
                    node = queue.popleft()
                    children = self._get_original_element_children(node)

                    if len(children) >= 2:
                        # This is a branching point — pool its children
                        for child in children:
                            # Skip children that are already top-level template instances
                            if id(child) in existing_node_ids:
                                continue
                            # Skip children that CONTAIN existing template instances
                            # (e.g., fl-col wrapper around a contracted text-column)
                            if id(child) in nodes_containing_existing:
                                continue
                            # Compute signature on ORIGINAL tree (preserves chains)
                            sig = cached_signature(child, max_depth=6)
                            sig_pool[sig].append(child)

                    # Continue traversal — but DON'T descend into existing chunks
                    # or nodes that are ancestors of existing chunk instances
                    for child in children:
                        if (id(child) not in existing_node_ids
                                and id(child) not in nodes_containing_existing):
                            queue.append(child)

            # Emit sub-template groups that meet frequency threshold
            # Require freq >= parent chunk frequency to avoid one-off deep structures
            min_sub_freq = max(self.MIN_CHUNK_FREQ, chunk.frequency)

            for sig, members in sig_pool.items():
                if len(members) < min_sub_freq:
                    continue

                # Height filter: require at least height 2 for sub-templates
                # (same as top-level: we want genuine hierarchical structure,
                # not bare a(span,span) or defs(style))
                h = signature_height(sig)
                if h < 2:
                    continue

                # Exclude presentational-root sub-templates: SVG internals,
                # canvas wrappers, and video player chrome are never content
                root_tag = sig.split('(')[0] if '(' in sig else sig
                PRESENTATIONAL_ROOTS = {
                    'svg', 'canvas', 'video', 'audio', 'defs', 'g',
                    'filter', 'fecolormatrix', 'fegaussianblur',
                    'femerge', 'feoffset', 'fecomponenttransfer',
                    'style', 'noscript', 'template',
                }
                if root_tag in PRESENTATIONAL_ROOTS:
                    continue

                # Content value check: sub-templates must have navigable
                # content (at least SOME instances with <a href>).
                # Text-only or SVG-only structures inside composites are
                # formatting wrappers, not content items.
                has_value = any(
                    AgnosticAttr.primary_url(sample)
                    for sample in members[:10]
                )

                if not has_value:
                    continue

                # Deduplicate: don't re-emit if these nodes overlap with
                # existing chunks
                unique_members = [m for m in members if id(m) not in existing_node_ids]
                if len(unique_members) < min_sub_freq:
                    continue

                # Build the sub-template chunk
                xpaths = [cached_xpath(m) for m in unique_members]
                content_types: set[ContentCategory] = set()
                for m in unique_members[:5]:
                    content_types.update(_classify_subtree(m))

                container_xpath = chunk.subtree_root

                primary_tag_sig = _agnostic_display_signature(unique_members)

                sub_chunk = ChunkGroup(
                    chunk_id=len(chunks) + len(new_chunks),
                    selectors=sorted(set(xpaths)),
                    trie_paths=xpaths,
                    frequency=len(unique_members),
                    content_types=content_types,
                    subtree_root=container_xpath,
                    signature=f"{primary_tag_sig}",
                    samples=[],
                    _instance_nodes=unique_members,
                    _structural_sig=sig,
                    _parent_chunk_id=chunk.chunk_id,
                )
                new_chunks.append(sub_chunk)

                self._log(
                    f"  [CIST] Sub-template: freq={len(unique_members)} "
                    f"height={h} sig={sig[:60]} "
                    f"(from composite freq={chunk.frequency})"
                )

        return chunks + new_chunks

    # =================================================================
    # PHASE 10: STRUCTURAL HOMOGENEITY REFINEMENT (§11)
    # =================================================================

    @staticmethod
    def _precontraction_root(node: ShadowNode) -> ShadowNode:
        """
        Recover the pre-contraction root of a contracted endpoint (§11.3).

        Walks UP from node through ancestors that have exactly one
        element child, stopping when the parent branches (≥2 element
        children) or when we reach the tree root. The result is the
        original direct child of the cohort parent that contraction
        collapsed into this endpoint.
        """
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

    @staticmethod
    def _ordered_tree_hash(node: ShadowNode) -> int:
        """
        Ordered Tree Canonical Hash — OTCH (§11.2).

        Computes a hash certificate for ordered labeled tree isomorphism
        on the ORIGINAL (uncontracted) subtree. Children are hashed in
        their natural DOM sibling order (NOT sorted), so two subtrees
        with identical children in different order produce different
        hashes. No depth limit — the full subtree is captured.

        OTCH(leaf with tag t) = hash(t)
        OTCH(node with tag t, ordered children c₁...cₖ)
            = hash(t, OTCH(c₁), ..., OTCH(cₖ))

        Complexity: O(|T|) time, O(depth) stack space.
        """
        def _hash(n: ShadowNode) -> int:
            tag = n.tag.lower()
            child_hashes: list[int] = []
            for child in n.get_children(include_shadow=True):
                ctag = child.tag.lower()
                if ctag.startswith('#') and ctag != '#shadow-root':
                    continue
                if ctag in SKIP_TAGS:
                    continue
                child_hashes.append(_hash(child))
            if not child_hashes:
                return hash(tag)
            return hash((tag, tuple(child_hashes)))
        return _hash(node)

    def _refine_structural_homogeneity(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Phase 10: Split chunks with structurally heterogeneous instances.

        For each chunk, finds the pre-contraction root of every instance
        (§11.3) and computes the Ordered Tree Canonical Certificate
        (§11.2) at the miner's structural depth. Instances whose
        pre-contraction subtrees have different ordered signatures go
        into separate refined chunks.

        Uses get_ordered_subtree_signature (preserves sibling order)
        from the pre-contraction root, at the same depth bound as the
        miner's structural signature (max_depth=6). This provides the
        finest partition consistent with the pipeline's structural
        resolution. See THEORY_v18 §11.
        """
        refined: list[ChunkGroup] = []

        for chunk in chunks:
            if not getattr(chunk, '_structural_sig', ''):
                refined.append(chunk)
                continue

            nodes = getattr(chunk, '_instance_nodes', [])
            if len(nodes) < 2:
                refined.append(chunk)
                continue

            # Compute ORDERED signature from pre-contraction root (§11.2-§11.3)
            sig_groups: defaultdict[str, list[ShadowNode]] = defaultdict(list)
            for node in nodes:
                root = self._precontraction_root(node)
                sig = get_ordered_subtree_signature(root, max_depth=6)
                sig_groups[sig].append(node)

            if len(sig_groups) == 1:
                refined.append(chunk)
                continue

            groups_sorted = sorted(
                sig_groups.items(), key=lambda x: -len(x[1])
            )
            kept = 0
            dropped = 0
            for sig, members in groups_sorted:
                if len(members) < self.MIN_CHUNK_FREQ:
                    dropped += len(members)
                    continue

                xpaths = [cached_xpath(m) for m in members]
                content_types: set[ContentCategory] = set()
                for m in members[:5]:
                    content_types.update(_classify_subtree(m))

                primary_tag_sig = _agnostic_display_signature(members)

                new_chunk = ChunkGroup(
                    chunk_id=-1,
                    selectors=sorted(set(xpaths)),
                    trie_paths=xpaths,
                    frequency=len(members),
                    content_types=content_types,
                    subtree_root=chunk.subtree_root,
                    signature=primary_tag_sig,
                    samples=[],
                    _instance_nodes=members,
                    _structural_sig=sig,
                    _parent_chunk_id=getattr(chunk, '_parent_chunk_id', -1),
                )
                refined.append(new_chunk)
                kept += 1

            self._log(
                f"  [homogeneity] Split chunk freq={chunk.frequency} "
                f"sig={chunk._structural_sig[:40]} → "
                f"{len(sig_groups)} variants, {kept} kept, "
                f"{dropped} instances dropped"
            )

        return refined

    def _deduplicate_cross_chunk(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Phase 11: Cross-Chunk Content Deduplication.

        After Phase 10 (homogeneity refinement) and Phase 9.5 (CIST
        processing), content-duplicate instances can appear in multiple
        chunks via two mechanisms:

        1. Homogeneity variant overlap: Phase 10 splits a chunk into
           structural variants. If the same content has two different
           DOM renderings (responsive layout), the same text appears
           in two variant chunks.

        2. CIST parent-child overlap: A CIST sub-template extracts
           atomic items from a composite parent. Both parent and child
           chunks contain the same text for overlapping instances.

        Algorithm:
        - Compute content fingerprints for all instances across all
          structural chunks
        - When the same fingerprint appears in multiple chunks, keep
          it in the most specific chunk (prefer CIST sub-templates
          over parents, and smaller subtree size)
        - Remove duplicate instances from less-specific chunks
        - Drop chunks that fall below MIN_CHUNK_FREQ

        Specificity ordering (higher = more specific, preferred):
        - CIST sub-templates (_parent_chunk_id >= 0) over top-level
        - Smaller average subtree size over larger
        - Higher frequency (more representative) as tiebreaker
        """
        structural = [ch for ch in chunks if ch._structural_sig]
        non_structural = [ch for ch in chunks if not ch._structural_sig]

        if len(structural) < 2:
            return chunks

        # Compute specificity score for each chunk:
        #   CIST children are more specific than parents
        #   Smaller subtrees are more specific
        def _avg_subtree_size(ch: ChunkGroup) -> float:
            if not ch._instance_nodes:
                return 0.0
            total = 0
            for node in ch._instance_nodes[:10]:
                total += sum(1 for _ in node.iter_descendants())
            return total / min(len(ch._instance_nodes), 10)

        def _specificity(ch: ChunkGroup) -> tuple:
            """Higher tuple = more specific (preferred to keep)."""
            is_cist = 1 if getattr(ch, '_parent_chunk_id', -1) >= 0 else 0
            avg_size = _avg_subtree_size(ch)
            # Prefer: CIST sub-templates, smaller subtrees, higher freq
            return (is_cist, -avg_size, ch.frequency)

        chunk_specificity = {id(ch): _specificity(ch) for ch in structural}

        # Build fingerprint → [(chunk_idx, instance_idx, node)] map
        # Use TEXT-ONLY fingerprint for cross-chunk dedup: content from
        # parent composites and child sub-templates shares the same text
        # but has different resource URLs (parent includes more). Text
        # identity is the correct content-equivalence for dedup.
        fp_map: dict[str, list[tuple[int, int, 'ShadowNode']]] = defaultdict(list)
        for ci, ch in enumerate(structural):
            for ni, node in enumerate(ch._instance_nodes):
                text = node.get_text().strip()[:500]
                # Normalize: lowercase, collapse whitespace
                text_norm = re.sub(r'\s+', ' ', text.lower()).strip()
                if len(text_norm) < 20:
                    continue  # Skip near-empty instances
                fp = text_norm
                fp_map[fp].append((ci, ni, node))

        # Identify cross-chunk duplicates
        # For each fingerprint present in >1 chunk, keep in most specific
        remove_from: dict[int, set[int]] = defaultdict(set)  # chunk_idx → {instance_indices}

        for fp, locations in fp_map.items():
            # Group by chunk index
            by_chunk: dict[int, list[tuple[int, int]]] = defaultdict(list)
            for ci, ni, _node in locations:
                by_chunk[ci].append((ci, ni))

            if len(by_chunk) < 2:
                continue  # Only in one chunk — no cross-chunk dupe

            # Find the most specific chunk among those containing this fp
            chunk_indices = list(by_chunk.keys())
            best_ci = max(chunk_indices,
                          key=lambda ci: chunk_specificity[id(structural[ci])])

            # Remove from all other chunks
            for ci in chunk_indices:
                if ci == best_ci:
                    continue
                for _ci, ni in by_chunk[ci]:
                    remove_from[ci].add(ni)

        # Apply removals
        total_removed = 0
        result_structural = []
        for ci, ch in enumerate(structural):
            if ci not in remove_from:
                result_structural.append(ch)
                continue

            to_remove = remove_from[ci]
            total_removed += len(to_remove)
            surviving_nodes = [
                node for ni, node in enumerate(ch._instance_nodes)
                if ni not in to_remove
            ]

            if len(surviving_nodes) < self.MIN_CHUNK_FREQ:
                self._log(
                    f"  [x-dedup] Dropped chunk {ch.chunk_id} "
                    f"(freq={ch.frequency}→{len(surviving_nodes)} "
                    f"< {self.MIN_CHUNK_FREQ}) sig={ch.signature[:50]}"
                )
                total_removed += len(surviving_nodes)
                continue

            if len(surviving_nodes) < len(ch._instance_nodes):
                self._log(
                    f"  [x-dedup] {ch.frequency}→{len(surviving_nodes)} "
                    f"in chunk sig={ch.signature[:50]}"
                )

            ch._instance_nodes = surviving_nodes
            ch.frequency = len(surviving_nodes)
            ch.selectors = sorted(set(
                cached_xpath(n) for n in surviving_nodes
            ))
            ch.trie_paths = [
                cached_xpath(n) for n in surviving_nodes
            ]
            result_structural.append(ch)

        return result_structural + non_structural

    def _deduplicate_cross_chunk_urls(
        self, chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Phase 11b: URL-based cross-chunk deduplication.

        Catches duplicates that text fingerprinting misses — e.g., when
        the same set of links appears in two structural variants with
        different wrapper elements (so the root-level text differs but
        the navigable URLs are identical).

        Algorithm:
        - For each pair of structural chunks, compute agnostic URL overlap
        - If overlap > 80%, remove the less specific chunk
        """
        structural = [ch for ch in chunks if ch._structural_sig]
        non_structural = [ch for ch in chunks if not ch._structural_sig]

        if len(structural) < 2:
            return chunks

        # Precompute URL sets per chunk
        chunk_urls: list[set[str]] = []
        for ch in structural:
            urls: set[str] = set()
            for node in ch._instance_nodes:
                urls.update(AgnosticAttr.navigable_urls(node))
            chunk_urls.append(urls)

        # Compute specificity: prefer CIST sub-templates, smaller subtrees
        def _avg_size(ch: ChunkGroup) -> float:
            if not ch._instance_nodes:
                return 0.0
            total = sum(
                sum(1 for _ in n.iter_descendants())
                for n in ch._instance_nodes[:10]
            )
            return total / min(len(ch._instance_nodes), 10)

        dropped = set()

        # Pre-build instance node ID sets for fast containment checks
        chunk_nid_sets: list[set[int]] = [
            {id(n) for n in ch._instance_nodes} for ch in structural
        ]

        def _is_cist_contained_in(cist_idx: int, parent_idx: int) -> bool:
            """
            Check if a CIST sub-template's instances are physically
            nested inside another chunk's instances.  Walks up 6
            ancestor levels from sampled CIST instances looking for
            a hit in the candidate parent's instance set.

            This replaces the broken chunk_id reference check — chunk_ids
            get orphaned when homogeneity refinement splits the parent.
            """
            parent_nids = chunk_nid_sets[parent_idx]
            cist_ch = structural[cist_idx]
            sample = cist_ch._instance_nodes[:5]
            hits = 0
            for node in sample:
                anc = node.parent
                depth = 0
                while anc and depth < 6:
                    if id(anc) in parent_nids:
                        hits += 1
                        break
                    if anc.tag.lower() in ('#document', 'html', 'body'):
                        break
                    anc = anc.parent
                    depth += 1
            # Require majority of samples to match
            return hits >= max(1, len(sample) // 2)

        for i in range(len(structural)):
            if i in dropped:
                continue
            for j in range(i + 1, len(structural)):
                if j in dropped:
                    continue
                urls_i = chunk_urls[i]
                urls_j = chunk_urls[j]
                if not urls_i or not urls_j:
                    continue
                overlap = urls_i & urls_j
                # Check if j is subset of i (or vice versa)
                ratio_j = len(overlap) / len(urls_j) if urls_j else 0
                ratio_i = len(overlap) / len(urls_i) if urls_i else 0

                if ratio_j > 0.8 or ratio_i > 0.8:
                    is_cist_i = getattr(structural[i], '_parent_chunk_id', -1) >= 0
                    is_cist_j = getattr(structural[j], '_parent_chunk_id', -1) >= 0

                    # If one is a CIST sub-template, check physical DOM
                    # containment.  Skip dedup if the CIST is nested
                    # inside the other chunk (legitimate parent-child).
                    if is_cist_i and not is_cist_j:
                        if _is_cist_contained_in(i, j):
                            continue  # i is CIST nested inside j
                    elif is_cist_j and not is_cist_i:
                        if _is_cist_contained_in(j, i):
                            continue  # j is CIST nested inside i

                    # Drop the less specific (larger subtree avg)
                    size_i = _avg_size(structural[i])
                    size_j = _avg_size(structural[j])

                    if is_cist_j and not is_cist_i:
                        dropped.add(i)
                    elif is_cist_i and not is_cist_j:
                        dropped.add(j)
                    elif size_i > size_j:
                        dropped.add(i)
                    else:
                        dropped.add(j)

        if dropped:
            self._log(
                f"  [url-dedup] Dropped {len(dropped)} URL-overlapping chunks"
            )

        surviving = [ch for idx, ch in enumerate(structural) if idx not in dropped]
        return surviving + non_structural


class ChunkSampler:
    def __init__(self, dom: ShadowDOM, chunks: list[ChunkGroup]):
        self.dom = dom
        self.chunks = chunks

    def sample_all_chunks(self, max_samples: int = 3) -> list[dict]:
        results = []
        global_seen_texts: set[str] = set()
        for chunk in self.chunks:
            paths = chunk.trie_paths
            count = len(paths)
            if count == 0:
                continue

            # Sample more candidates than needed so dedup has fallbacks
            if max_samples <= 1 or count <= max_samples * 2:
                candidate_indices = list(range(count))
            else:
                step = (count - 1) / (max_samples * 2 - 1)
                candidate_indices = [
                    int(round(i * step)) for i in range(max_samples * 2)
                ]
            candidate_indices = sorted(set(candidate_indices))

            samples: list[dict] = []
            local_seen: set[str] = set()
            for idx in candidate_indices:
                if len(samples) >= max_samples:
                    break
                node = self.dom.xpath_one(paths[idx])
                if not node:
                    continue
                text_raw = node.get_text()[:200]
                text_key = ' '.join(text_raw.split()).lower()[:100]
                # Skip if this text was already used (intra or cross-chunk)
                if text_key in local_seen or (
                    len(text_key) >= 20 and text_key in global_seen_texts
                ):
                    continue
                local_seen.add(text_key)
                if len(text_key) >= 20:
                    global_seen_texts.add(text_key)
                samples.append({
                    "xpath": cached_xpath(node),
                    "html": node.to_html(indent=0)[:800],
                    "text": text_raw,
                    "signature": cached_signature(node, max_depth=2)[:100],
                })
            chunk.samples = samples

            if not samples:
                continue

            results.append({
                "chunk_id": chunk.chunk_id,
                "frequency": chunk.frequency,
                "subtree": chunk.subtree_root,
                "content_types": [c.value for c in chunk.content_types],
                "signature": chunk.signature[:80],
                "samples": samples,
            })
        return results

    def build_full_chunk_html(self, chunk: ChunkGroup) -> str:
        lines = [
            '<!DOCTYPE html>',
            '<html><head><meta charset="utf-8">',
            f'<title>Chunk {chunk.chunk_id} — {chunk.frequency} instances</title>',
            '<style>',
            '  .instance { border: 1px solid #ccc; margin: 8px; padding: 8px; }',
            '  .instance-header { font-size: 0.8em; color: #666; margin-bottom: 4px; }',
            '</style>',
            '</head><body>',
            f'<h2>Chunk {chunk.chunk_id}</h2>',
            f'<p>Signature: <code>{chunk.signature[:120]}</code></p>',
            f'<p>Container: <code>{chunk.subtree_root}</code></p>',
            f'<p>Instances: {chunk.frequency}</p>',
            '<hr>',
        ]
        for path in chunk.trie_paths:
            node = self.dom.xpath_one(path)
            if node:
                lines.append('<div class="instance">')
                lines.append(f'  <div class="instance-header">{path}</div>')
                lines.append(f'  {node.to_html(indent=1)}')
                lines.append('</div>')
        lines.append('</body></html>')
        return "\n".join(lines)

    def build_distilled_html(self, chunk: ChunkGroup) -> str:
        lines = [
            f'<div id="chunk-{chunk.chunk_id}" data-freq="{chunk.frequency}">'
        ]
        for s in chunk.samples:
            lines.append(
                f'  <div class="sample" data-xpath="{s["xpath"]}">'
            )
            lines.append(f'    {s["html"]}')
            lines.append('  </div>')
        lines.append('</div>')
        return "\n".join(lines)


# =============================================================================
# FUNCTIONAL ELEMENT COLLECTORS (unchanged from v10)
# =============================================================================

class _VocabularyScorer:
    """
    Multi-channel vocabulary scorer using tokenized matching.

    Avoids raw substring matching (which causes 'load' to match
    'uploads' in URLs). Instead:

    - Attribute name/value: tokenized via AttributeTokenizer, then
      exact-match against vocabulary tokens.
    - Text content: word-boundary regex matching to catch multi-word
      phrases ('load more') while preventing partial matches.
    """

    def __init__(self, vocabulary: frozenset[str]):
        self.vocabulary = vocabulary
        # Pre-compile word-boundary patterns for text matching
        self._text_patterns = {
            term: re.compile(r'(?<!\w)' + re.escape(term) + r'(?!\w)',
                             re.IGNORECASE)
            for term in vocabulary if len(term) > 1
        }
        # Single-char terms (>, <, etc.) use direct containment
        self._char_terms = frozenset(
            term for term in vocabulary if len(term) <= 1
        )

    def score_node(self, node: ShadowNode) -> int:
        """
        Multi-channel vocabulary scoring (§13.1).

        Scores against three channels:
          1. Attribute names (tokenized)
          2. Attribute values (tokenized)
          3. Visible text content (word-boundary regex)

        Returns total match count across all channels.
        """
        total = 0
        for attr_name, attr_val in node.get_all_attrs().items():
            # Channel 1: attribute name tokens
            name_tokens = set(AttributeTokenizer.tokenize(attr_name))
            for term in self.vocabulary:
                if term in name_tokens:
                    total += 1

            # Channel 2: attribute value tokens
            val_str = str(attr_val or '')[:300]
            if val_str:
                val_tokens = set(AttributeTokenizer.tokenize(val_str))
                for term in self.vocabulary:
                    if term in val_tokens:
                        total += 1

        # Channel 3: visible text content (word-boundary matching)
        text = (node.get_text() or '').strip()
        if text:
            text_lower = text.lower()
            for term, pattern in self._text_patterns.items():
                if pattern.search(text_lower):
                    total += 1
            for ch in self._char_terms:
                if ch in text_lower:
                    total += 1
        return total


class SearchInputCollector:
    VOCABULARY = frozenset({
        'search', 'q', 'query', 'find', 'keyword', 'lookup',
        'srch', 'buscar', 'recherche', 'suche',
    })
    # Value tokens that indicate an input is NOT a search field.
    # Applied agnostically against ALL attribute values, not just
    # 'type', 'name', or 'id'.  Discovered via frequency-filter
    # failures across multiple test sites.
    _EXCLUDED_TYPE_TOKENS = frozenset({
        'hidden', 'email', 'checkbox', 'radio', 'file',
        'image', 'color', 'date', 'range', 'password',
    })
    _EXCLUDED_NAME_RE = re.compile(
        r'(first.?name|last.?name|subbox|subscribe|signup|newsletter|'
        r'password|captcha|token|nonce|csrf|turnstile)',
        re.IGNORECASE,
    )
    def __init__(self, vocabulary: frozenset[str] | None = None):
        self.scorer = _VocabularyScorer(vocabulary or self.VOCABULARY)

    def collect(self, dom: ShadowDOM) -> ChunkGroup | None:
        scored: list[tuple[int, ShadowNode]] = []
        for node in dom.iter_elements():
            # Agnostic: catches <input>, <textarea>, <select>,
            # <div role="searchbox">, <custom-input contenteditable>, etc.
            if not AgnosticAttr.is_input_like(node):
                continue

            # Agnostic exclusion: scan ALL attribute values for
            # excluded type tokens and name patterns.
            excluded = False
            for _key, val in node.get_all_attrs().items():
                if not val:
                    continue
                val_lower = str(val).lower().strip()
                # Check for excluded type values (exact match on
                # short values — prevents 'hidden' in a long class)
                if len(val_lower) < 30 and val_lower in self._EXCLUDED_TYPE_TOKENS:
                    excluded = True
                    break
                # Check for excluded name/id patterns
                if self._EXCLUDED_NAME_RE.search(val_lower):
                    excluded = True
                    break
            if excluded:
                continue

            score = self.scorer.score_node(node)
            scored.append((score, node))
        if not scored:
            return None
        scored.sort(key=lambda x: -x[0])
        nodes = [node for _, node in scored]
        xpaths = [cached_xpath(n) for n in nodes]
        chunk = ChunkGroup(
            chunk_id=-1, selectors=xpaths, trie_paths=xpaths,
            frequency=len(nodes), content_types={ContentCategory.INPUT},
            subtree_root='/html/body', signature='[search_inputs]', samples=[],
        )
        chunk._instance_nodes = nodes
        return chunk


class PaginationCollector:
    VOCABULARY = frozenset({
        'next', 'prev', 'previous', 'page', 'pagination', 'pager',
        'load more', 'show more', 'see more', 'view more', 'read more',
        'load', 'older', 'newer', 'additional',
        '>', '<', '\u00bb', '\u00ab', '\u2192', '\u2190',
        'forward', 'back', 'last', 'first', 'paginat', 'more', 'results'
    })
    _PAGINATION_RE = re.compile(r'pagination', re.IGNORECASE)
    # Taxonomy "More" guard: matches "More X..." (1+ words after "more")
    _MORE_TAXONOMY_RE = re.compile(r'(?i)^more\s+\w')
    # Words that legitimize a "more X" phrase as pagination
    _MORE_PAGINATION_WORDS = frozenset({
        'results', 'pages', 'items', 'posts', 'stories',
        'articles', 'entries', 'comments',
    })
    # Shadow DOM widget tags to exclude
    _WIDGET_TAG_DENYLIST = frozenset({
        'slick-fab', 'slick-heartbeat', 'soso-button',
        'soso-icon-button', 'soso-icon',
    })
    # Agnostic negative attribute-value tokens: if ANY attribute on a
    # node contains one of these tokens, it's NOT a pagination element.
    # Discovered via test failures across diverse sites — media player
    # controls, cart buttons, social sharing, feed interaction widgets.
    # Uses substring matching against lowercased attribute values.
    _NEGATIVE_ATTR_TOKENS = frozenset({
        # Media player controls
        'playable', 'player', 'volume', 'mute', 'fullscreen',
        'pip', 'rewind', 'scrub', 'playback',
        # Media container signals
        'audio', 'video',
        # E-commerce interaction
        'cart', 'wishlist', 'addtocart',
        # Social feed interaction
        'reply', 'repost', 'retweet', 'bookmark',
        'dropdown', 'haspopup',
        # Content item controls
        'favorite', 'share', 'social',
    })

    def __init__(self, vocabulary: frozenset[str] | None = None):
        self.scorer = _VocabularyScorer(vocabulary or self.VOCABULARY)

    def collect(
        self,
        dom: ShadowDOM,
        structural_chunks: list | None = None,
    ) -> ChunkGroup | None:
        # Build exclusion set: all node IDs inside structural instances
        structural_node_ids: set[int] = set()
        if structural_chunks:
            for chunk in structural_chunks:
                if getattr(chunk, '_structural_sig', ''):
                    for inst_node in getattr(chunk, '_instance_nodes', []):
                        structural_node_ids.add(id(inst_node))
                        for desc in inst_node.iter_descendants():
                            structural_node_ids.add(id(desc))

        # Pre-compute widget ancestor set for O(1) denylist check.
        # Walking ancestors per-node is O(N*D); pre-building is O(N).
        _widget_deny_ids: set[int] = set()
        for node in dom.iter_elements():
            if node.tag.lower() in self._WIDGET_TAG_DENYLIST:
                _widget_deny_ids.add(id(node))
                for desc in node.iter_descendants():
                    _widget_deny_ids.add(id(desc))

        seen_ids: set[int] = set()
        scored: list[tuple[int, ShadowNode]] = []
        for node in dom.iter_elements():
            nid = id(node)
            if nid in seen_ids:
                continue

            # ── O(1) widget denylist ──
            if nid in _widget_deny_ids:
                continue

            # ── O(1) structural exclusion (moved EARLY) ──
            if structural_node_ids and nid in structural_node_ids:
                continue

            # ── Cheap O(attrs) checks: determine candidacy BEFORE scoring ──
            is_button_like = AgnosticAttr.is_button_like(node)
            has_url = AgnosticAttr.node_has_url(node)
            has_pagination_attr = False
            for attr_name, attr_val in node.get_all_attrs().items():
                combined = attr_name.lower() + ' ' + str(attr_val or '').lower()
                if self._PAGINATION_RE.search(combined):
                    has_pagination_attr = True
                    break

            # Quick reject: if not button-like, no URL, no pagination attr
            # → this node can never be included. Skip expensive scoring.
            if not is_button_like and not has_url and not has_pagination_attr:
                continue

            # ── Expensive scoring (only for candidates) ──
            score = self.scorer.score_node(node)

            # ── Zero-score gating ──
            if score == 0 and not has_pagination_attr:
                continue

            # ── Inclusion decision ──
            include = is_button_like or has_pagination_attr
            if not include and has_url and score > 0:
                include = True
            if not include:
                continue

            # ── Content-weight guard (only for included candidates) ──
            text_len = len(node.get_text().strip())
            if text_len > 200:
                continue

            # ── Agnostic negative-token exclusion ──
            # Reject nodes whose attributes (or shallow descendant attrs)
            # contain tokens indicating non-pagination roles: media
            # controls, cart widgets, social sharing, etc.
            # Depth-limited to avoid O(N*D) on deep subtrees.
            excluded_by_token = False
            _check_nodes = [node]
            for child in node.get_children(include_shadow=True):
                _check_nodes.append(child)
                for gc in child.get_children(include_shadow=True):
                    _check_nodes.append(gc)
            for cn in _check_nodes:
                if AgnosticAttr.is_media_container(cn):
                    excluded_by_token = True
                    break
                for _key, val in cn.get_all_attrs().items():
                    if not val:
                        continue
                    val_lower = str(val).lower()[:200]
                    for neg in self._NEGATIVE_ATTR_TOKENS:
                        if neg in val_lower:
                            excluded_by_token = True
                            break
                    if excluded_by_token:
                        break
                if excluded_by_token:
                    break
            if excluded_by_token:
                continue

            # ── Taxonomy "More" false-positive guard ──
            # Links like "MORE I CHING INSIGHT" or "More Eastern Wisdom"
            # are taxonomy section headers, not pagination buttons.
            # A legitimate "More" pagination button is short (1-2 words).
            # Reject if text starts with "more" followed by 2+ content
            # words that aren't pagination vocabulary.
            if text_len > 0:
                text_stripped = node.get_text().strip()
                if self._MORE_TAXONOMY_RE.match(text_stripped):
                    # Starts with "more" + multi-word content → taxonomy
                    # Exception: "more results", "more pages" are pagination
                    words_after = text_stripped.split()[1:]
                    if words_after and not any(
                        w.lower() in self._MORE_PAGINATION_WORDS
                        for w in words_after[:2]
                    ):
                        continue

            seen_ids.add(nid)
            scored.append((score, node))
        if not scored:
            return None
        scored.sort(key=lambda x: -x[0])
        nodes = [node for _, node in scored]
        xpaths = [cached_xpath(n) for n in nodes]
        chunk = ChunkGroup(
            chunk_id=-1, selectors=xpaths, trie_paths=xpaths,
            frequency=len(nodes), content_types={ContentCategory.BUTTON},
            subtree_root='/html/body', signature='[pagination_buttons]', samples=[],
        )
        chunk._instance_nodes = nodes
        return chunk


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================
class TextContentCollector:
    """
    Collects text-rich DOM elements not captured by template mining.
    
    Article pages (like Wikipedia, Stanford Encyclopedia, blog posts)
    have their main content in repeating paragraph elements (p, blockquote,
    pre) that the template miner discards because they have height=0
    (flat leaf nodes with no structural children). This collector
    finds groups of text-bearing siblings under the same parent that
    carry substantial visible text.
    
    Also collects navigation link groups (menus, nav bars) that the
    template miner misses due to tree height < 2.  These become
    ``[nav_content:…]`` chunks so that URL-text pairs are preserved.
    
    Only collects elements NOT already inside a template instance,
    avoiding double-counting. Groups must exceed a minimum total
    text length to filter trivial UI fragments.
    """

    TEXT_TAGS = frozenset({
        'p', 'blockquote', 'pre', 'code', 'dd', 'dt',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'li', 'figcaption', 'summary',
    })

    # Tags whose presence makes an element "substantial" regardless
    # of how short the text is (e.g. <p><img src="big-banner.gif"></p>).
    RESOURCE_TAGS = MEDIA_TAGS | frozenset({'iframe'})

    MIN_ELEMENT_TEXT = 30     # chars: skip short metadata fragments
    MIN_GROUP_TEXT = 150      # chars: skip trivial groups
    MIN_GROUP_SIZE = 2        # elements: need at least 2 siblings
    MIN_NAV_GROUP_SIZE = 4    # nav groups need more items to qualify

    def _has_resource_child(self, node: ShadowNode) -> bool:
        """True if *node* contains a descendant with a media/resource URL.

        Agnostic: inspects ALL attributes on every descendant for URL-like
        values.  No hardcoded ``src``/``data-src``/``poster`` keys.
        """
        for desc in node.iter_descendants():
            if desc.tag.lower() in self.RESOURCE_TAGS:
                if AgnosticAttr.urls_from_node(desc):
                    return True
        return False

    def collect(
        self, dom: ShadowDOM, template_chunks: list[ChunkGroup]
    ) -> list[ChunkGroup]:
        """
        Returns zero or more ChunkGroup objects for text content
        groups not covered by existing template chunks.
        """
        # Build set of node IDs already covered by templates
        covered_ids = set()
        for chunk in template_chunks:
            if not hasattr(chunk, '_instance_nodes'):
                continue
            for node in chunk._instance_nodes:
                covered_ids.add(id(node))
                for desc in node.iter_descendants():
                    covered_ids.add(id(desc))

        # Find text-rich elements not covered by any template
        # Group by parent node (siblings form natural text runs)
        from collections import defaultdict
        parent_groups: dict[int, list[ShadowNode]] = defaultdict(list)
        # Separate bucket for link-heavy elements (navigation)
        nav_groups: dict[int, list[ShadowNode]] = defaultdict(list)

        for node in dom.iter_elements():
            if id(node) in covered_ids:
                continue
            if node.tag.lower() not in self.TEXT_TAGS:
                continue

            text = node.get_text().strip()
            text_len = len(text)

            # Elements containing resource children (img, video, etc.)
            # are considered substantial even with short text.
            has_resource = self._has_resource_child(node)

            # Heading elements bypass MIN_ELEMENT_TEXT — titles are
            # naturally concise (e.g., <h1>www.criterion.com</h1>).
            # Agnostic: also catches <div role="heading">.
            is_heading = AgnosticAttr.is_heading_like(node)

            # Elements containing a navigable URL are potentially
            # navigation items — short text like "News" or "Crystal
            # Guides" is meaningful as a URL-text pair.  Agnostic:
            # checks ALL attributes, not just <a href>.
            has_link = AgnosticAttr.has_url_descendant(node)

            if text_len < self.MIN_ELEMENT_TEXT and not has_resource \
               and not has_link and not is_heading:
                continue

            # Classify: primarily links (navigation) vs content text.
            # Agnostic: measure text inside ANY URL-bearing element,
            # not just <a>.  Catches data-href, data-url, etc.
            link_text_len = 0
            for desc in node.iter_descendants():
                if AgnosticAttr.node_has_url(desc):
                    link_text_len += len(desc.get_text().strip())

            is_nav = text_len > 0 and link_text_len > text_len * 0.7

            parent_id = id(node.parent) if node.parent else 0
            if is_nav:
                nav_groups[parent_id].append(node)
            else:
                parent_groups[parent_id].append(node)

        # Track which node IDs were collected in the TEXT_TAGS pass
        text_pass_ids: set[int] = set()
        for nodes in list(nav_groups.values()) + list(parent_groups.values()):
            for n in nodes:
                text_pass_ids.add(id(n))

        # ── Agnostic accessibility-nav pass ──
        # Capture URL-bearing elements that have meaningful accessibility
        # text (aria-label, title) but no visible text — e.g. RNW icon-only
        # nav links, SVG buttons with labels. These are invisible to the
        # TEXT_TAGS filter but carry first-class semantic content per project
        # philosophy: "aria-label, title = high-weight semantic vectors".
        for node in dom.iter_elements():
            nid = id(node)
            if nid in covered_ids or nid in text_pass_ids:
                continue
            tag = node.tag.lower()
            if tag.startswith('#') or tag in SKIP_TAGS or tag in DOCUMENT_TAGS:
                continue
            # Must carry a URL (agnostic: checks ALL attributes)
            if not AgnosticAttr.node_has_url(node):
                continue
            # Must have accessibility text
            acc_text = ''
            for key, val in node.get_all_attrs().items():
                kl = key.lower()
                if not val or not isinstance(val, str):
                    continue
                if kl.startswith('aria-') and 'label' in kl:
                    acc_text = val.strip()
                    break
                if kl == 'title' and len(val.strip()) > 2:
                    acc_text = val.strip()
                    break
            if not acc_text:
                continue
            parent_id = id(node.parent) if node.parent else 0
            nav_groups[parent_id].append(node)
            text_pass_ids.add(nid)

        # Build ChunkGroups for qualifying parent groups
        results = []

        # Text content groups
        for parent_id, nodes in parent_groups.items():
            if len(nodes) < self.MIN_GROUP_SIZE:
                continue
            total_text = sum(len(n.get_text().strip()) for n in nodes)
            if total_text < self.MIN_GROUP_TEXT:
                continue
            
            # Determine common tag for signature
            from collections import Counter
            tag_counts = Counter(n.tag.lower() for n in nodes)
            primary_tag = tag_counts.most_common(1)[0][0]

            # ── Molecule formation ──
            # When a small group of mixed-tag siblings shares a parent
            # (e.g. h2 + p = security message), emit the PARENT as a
            # single molecule instance rather than individual children.
            # This prevents over-segmentation of semantically cohesive
            # content blocks. Only apply when:
            #   - ≤8 siblings (small cohesive group, not a long list)
            #   - tag diversity > 1 (mixed types, not homogeneous <p>s)
            #   - parent is not a top-level document node
            parent_node = nodes[0].parent if nodes[0].parent else None
            if (parent_node
                    and len(tag_counts) > 1
                    and len(nodes) <= 8
                    and parent_node.tag.lower() not in DOCUMENT_TAGS):
                # Emit parent as single molecule
                parent_xpath = cached_xpath(parent_node)
                chunk = ChunkGroup(
                    chunk_id=-1,
                    selectors=[parent_xpath],
                    trie_paths=[parent_xpath],
                    frequency=1,
                    content_types={ContentCategory.TEXT},
                    subtree_root=(
                        cached_xpath(parent_node.parent)
                        if parent_node.parent else '/html/body'
                    ),
                    signature=f'[text_content:{primary_tag}×{len(nodes)}]',
                    samples=[],
                )
                chunk._instance_nodes = [parent_node]
                chunk._structural_sig = ''
                results.append(chunk)
            else:
                # Homogeneous group: emit individual instances
                xpaths = [cached_xpath(n) for n in nodes]
                chunk = ChunkGroup(
                    chunk_id=-1,
                    selectors=xpaths,
                    trie_paths=xpaths,
                    frequency=len(nodes),
                    content_types={ContentCategory.TEXT},
                    subtree_root=(
                        cached_xpath(nodes[0].parent)
                        if nodes[0].parent else '/html/body'
                    ),
                    signature=f'[text_content:{primary_tag}×{len(nodes)}]',
                    samples=[],
                )
                # Attach instance nodes for coagulation
                chunk._instance_nodes = nodes
                chunk._structural_sig = ''  # mark as non-structural
                results.append(chunk)

        # Navigation link groups — with molecule splitting for mega-bundles.
        # Nav <li> elements containing >MAX_NAV_LINKS hrefs are split into
        # individual <a> atoms (or kept as-is if already atomic).
        MAX_NAV_LINKS = 5
        for parent_id, nodes in nav_groups.items():
            if len(nodes) < self.MIN_NAV_GROUP_SIZE:
                continue

            # ── Molecule splitting: expand mega-bundle into URL-atom nodes ──
            split_nodes: list[ShadowNode] = []
            for node in nodes:
                # Agnostic: count distinct navigable URLs in this instance
                nav_urls = set(AgnosticAttr.navigable_urls(node))

                if len(nav_urls) <= MAX_NAV_LINKS:
                    split_nodes.append(node)
                else:
                    # Mega-bundle: extract each direct URL-bearing child
                    extracted = False
                    for child in node.get_children(include_shadow=True):
                        if AgnosticAttr.node_has_url(child):
                            split_nodes.append(child)
                            extracted = True
                        elif AgnosticAttr.is_container_of_links(child):
                            for gc in child.get_children(include_shadow=True):
                                if AgnosticAttr.node_has_url(gc) or \
                                   AgnosticAttr.has_url_descendant(gc):
                                    split_nodes.append(gc)
                                    extracted = True
                    if not extracted:
                        split_nodes.append(node)

            if len(split_nodes) < self.MIN_NAV_GROUP_SIZE:
                continue

            from collections import Counter
            tag_counts = Counter(n.tag.lower() for n in split_nodes)
            primary_tag = tag_counts.most_common(1)[0][0]

            xpaths = [cached_xpath(n) for n in split_nodes]
            chunk = ChunkGroup(
                chunk_id=-1,
                selectors=xpaths,
                trie_paths=xpaths,
                frequency=len(split_nodes),
                content_types={ContentCategory.NAVIGATION},
                subtree_root=(
                    cached_xpath(nodes[0].parent)
                    if nodes[0].parent else '/html/body'
                ),
                signature=f'[nav_content:{primary_tag}×{len(split_nodes)}]',
                samples=[],
            )
            chunk._instance_nodes = split_nodes
            chunk._structural_sig = ''
            results.append(chunk)

        # ── Track which nodes were already collected into groups ──
        collected_ids: set[int] = set()
        for parent_id, nodes in parent_groups.items():
            if len(nodes) >= self.MIN_GROUP_SIZE:
                for n in nodes:
                    collected_ids.add(id(n))
        for parent_id, nodes in nav_groups.items():
            if len(nodes) >= self.MIN_NAV_GROUP_SIZE:
                for n in nodes:
                    collected_ids.add(id(n))

        # ── Heading singleton capture ──
        # Headings (h1-h6, role="heading") are structural landmarks that
        # should always be captured, even as singletons with short text.
        # They often appear alone under their parent (no sibling group).
        for node in dom.iter_elements():
            if id(node) in covered_ids or id(node) in collected_ids:
                continue
            if node.tag.lower() not in self.TEXT_TAGS:
                continue
            if not AgnosticAttr.is_heading_like(node):
                continue
            text = node.get_text().strip()
            if len(text) < 2:
                continue
            collected_ids.add(id(node))
            xpath = cached_xpath(node)
            chunk = ChunkGroup(
                chunk_id=-1,
                selectors=[xpath],
                trie_paths=[xpath],
                frequency=1,
                content_types={ContentCategory.TEXT},
                subtree_root=(
                    cached_xpath(node.parent)
                    if node.parent else '/html/body'
                ),
                signature=f'[text_content:{node.tag.lower()}×1]',
                samples=[],
            )
            chunk._instance_nodes = [node]
            chunk._structural_sig = ''
            results.append(chunk)

        # ── Fallback: singleton substantial elements ──
        # Elements with many resources (images, videos) AND significant
        # text that couldn't form a sibling group.  These are typically
        # search result containers or large content blocks that are the
        # sole child of their parent.
        MIN_SINGLETON_TEXT = 200
        for node in dom.iter_elements():
            if id(node) in covered_ids or id(node) in collected_ids:
                continue
            if node.tag.lower() not in self.TEXT_TAGS:
                continue
            text_len = len(node.get_text().strip())
            if text_len < MIN_SINGLETON_TEXT:
                continue
            if not self._has_resource_child(node):
                continue
            # This is a substantial uncovered element with resources
            xpath = cached_xpath(node)
            chunk = ChunkGroup(
                chunk_id=-1,
                selectors=[xpath],
                trie_paths=[xpath],
                frequency=1,
                content_types={ContentCategory.TEXT},
                subtree_root=(
                    cached_xpath(node.parent)
                    if node.parent else '/html/body'
                ),
                signature=f'[text_content:{node.tag.lower()}×1]',
                samples=[],
            )
            chunk._instance_nodes = [node]
            chunk._structural_sig = ''
            results.append(chunk)

        return results


class WebDistiller:
    def __init__(self, html: str):
        self.html = html
        self.dom = ShadowDOM(html)
        self.content_nodes: dict[int, ContentNode] = {}
        self.chunks: list = []
        self.sampler: Optional[ChunkSampler] = None

    def process(self, verbose: bool = False) -> list:
        log = print if verbose else lambda *a, **k: None

        # Clear per-session computation caches from any previous run.
        _clear_caches()

        scanner = ContentScanner(self.dom)
        self.content_nodes = scanner.scan()
        log(f"Content nodes: {len(self.content_nodes)}")

        log("Starting v11 sibling-cohort spectral mining...")
        miner = SiblingCohortMiner(verbose=verbose)
        self.chunks = miner.mine(self.dom)
        log(f"Template chunks: {len(self.chunks)}")

        search_collector = SearchInputCollector()
        search_chunk = search_collector.collect(self.dom)
        if search_chunk:
            search_chunk.chunk_id = len(self.chunks)
            self.chunks.append(search_chunk)
            log(f"Search input chunk: {search_chunk.frequency} inputs")

        pagination_collector = PaginationCollector()
        pagination_chunk = pagination_collector.collect(
            self.dom, structural_chunks=self.chunks)
        if pagination_chunk:
            pagination_chunk.chunk_id = len(self.chunks)
            self.chunks.append(pagination_chunk)
            log(f"Pagination/button chunk: {pagination_chunk.frequency} elements")

        # Collect text-rich content not captured by template mining
        text_collector = TextContentCollector()
        text_chunks = text_collector.collect(self.dom, self.chunks)

        # ── Phase 11b: Cross-chunk dedup (text/nav vs structural) ──
        # Remove text/nav fallback chunks whose hrefs are >80% covered
        # by structural chunks (prevents desktop-vs-mobile nav dupe,
        # fallback dragnet issues, submenu triple duplication).
        structural_hrefs: set[str] = set()
        for ch in self.chunks:
            if not getattr(ch, '_structural_sig', ''):
                continue
            for xpath in ch.trie_paths:
                node = self.dom.xpath_one(xpath)
                if not node:
                    continue
                # Agnostic: extract ALL navigable URLs from subtree
                structural_hrefs.update(AgnosticAttr.navigable_urls(node))

        deduped_text_chunks: list = []
        # Cache text fingerprints: chunk index -> frozenset of text snippets
        deduped_text_cache: list[frozenset] = []

        for tc in text_chunks:
            tc_hrefs: set[str] = set()
            tc_texts: set[str] = set()
            for xpath in tc.trie_paths:
                node = self.dom.xpath_one(xpath)
                if not node:
                    continue
                text = node.get_text().strip()[:200].lower()
                if text:
                    tc_texts.add(text)
                # Agnostic: extract ALL navigable URLs from subtree
                tc_hrefs.update(AgnosticAttr.navigable_urls(node))

            # Check href overlap with structural chunks
            if tc_hrefs:
                overlap = tc_hrefs & structural_hrefs
                ratio = len(overlap) / len(tc_hrefs)
                if ratio > 0.8:
                    continue  # drop this chunk

            # Check text overlap with other kept text chunks (responsive dupes)
            # Uses cached fingerprints — O(1) per comparison instead of O(M).
            tc_texts_frozen = frozenset(tc_texts)
            is_dupe = False
            for i, kept_texts in enumerate(deduped_text_cache):
                if kept_texts and tc_texts_frozen:
                    text_overlap = kept_texts & tc_texts_frozen
                    max_size = max(len(kept_texts), len(tc_texts_frozen))
                    if max_size > 0 and len(text_overlap) / max_size > 0.8:
                        if tc.frequency > deduped_text_chunks[i].frequency:
                            # Replace the kept chunk with this higher-freq one
                            deduped_text_chunks[i] = tc
                            deduped_text_cache[i] = tc_texts_frozen
                        else:
                            is_dupe = True
                        break
            if not is_dupe:
                deduped_text_chunks.append(tc)
                deduped_text_cache.append(tc_texts_frozen)

        for tc in deduped_text_chunks:
            tc.chunk_id = len(self.chunks)
            self.chunks.append(tc)
            log(f"Text content chunk: {tc.frequency} elements "
                f"({tc.signature})")

        # ── Phase 12: (Removed) ──
        # CheegerChunkRefiner refinement was empirically shown to have
        # zero test impact (same pass rate with/without). Its function
        # is already performed by Phase 3's TF-IDF cross-cohort merge.

        if not self.chunks:
            log("No structures found.")
            return []

        self.sampler = ChunkSampler(self.dom, self.chunks)
        sample_data = self.sampler.sample_all_chunks(max_samples=3)
        log(f"Sampled {sum(len(c['samples']) for c in sample_data)} elements.")

        # ── Final: Compute tokenized XPath selectors for ALL chunks ──
        # This runs AFTER all chunk types are assembled (structural,
        # search, pagination, text/nav) so every chunk gets a portable
        # cross-page selector using the same @key:token vocabulary as
        # the spectral miner.  Reuses NodeTermCache from Phase 2/3 to
        # avoid re-extracting structural tokens for every instance node.
        term_cache = getattr(miner, '_term_cache', None)
        all_selectors = TokenizedXPathSelector.compute_all(
            self.chunks, dom=self.dom, term_cache=term_cache)
        log(f"Computed {len(all_selectors)} tokenized XPath selectors")

        # ── Phase 6: BUTA primary extraction ──
        # The Bottom-Up Tree Automaton evaluates ALL structural templates
        # in a single O(N) post-order traversal. It is now the authoritative
        # source for structural chunk instance nodes.
        try:
            from .buta_extractor import BottomUpTreeAutomaton
            structural = [ch for ch in self.chunks if ch._structural_sig]
            if structural:
                buta = BottomUpTreeAutomaton(verbose=verbose)
                n_compiled = buta.compile(structural)
                if n_compiled > 0:
                    buta_matches = buta.execute(self.dom)
                    for ch in structural:
                        buta_nodes = buta_matches.get(ch.chunk_id, [])
                        if buta_nodes:
                            ch._instance_nodes = buta_nodes
                    log(f"[BUTA] Primary extraction: {n_compiled} patterns, "
                        f"{sum(len(v) for v in buta_matches.values())} nodes")
        except ImportError:
            pass  # buta_extractor not available — skip BUTA

        return self.chunks


# =============================================================================
# CLI
# =============================================================================
# =============================================================================
# RELATIVE XPATH COMPUTATION
# =============================================================================

def get_relative_xpath(node: ShadowNode, ancestor_xpath: str) -> str:
    """
    Compute xpath of node relative to ancestor_xpath.
    Returns the suffix after stripping the ancestor prefix.
    
    Example:
      node_xpath  = /html/body/div[2]/main/section/div/a[3]
      ancestor    = /html/body/div[2]/main/section
      result      = /div/a[3]
    """
    abs_xpath = cached_xpath(node)
    if abs_xpath.startswith(ancestor_xpath):
        rel = abs_xpath[len(ancestor_xpath):]
        return rel if rel else "/"
    return abs_xpath  # fallback: return absolute if no prefix match


# =============================================================================
# CONTENT COAGULATION MAP (see THEORY_v14.md)
# =============================================================================

@dataclass
class CoagulatedRecord:
    """
    A unique content item coagulated from one or more template instances.
    Ready for knowledge graph ingestion with text vectorization.
    """
    content_id: str                           # fingerprint hash
    canonical_xpath: str                      # absolute xpath of richest instance
    canonical_html: str                       # rendered HTML of richest
    text: str                                 # visible text content
    primary_href: Optional[str]               # main navigable link
    all_hrefs: list[str]                      # all hrefs found across instances
    image_srcs: list[str]                     # all image sources
    embedded_urls: list[str]                  # ALL URLs (§12.1): src, data-src, action, etc.
    all_xpaths: list[str]                     # every DOM position this content appears
    relative_xpaths: list[dict]               # [{xpath, template_root, chunk_id}]
    template_groups: list[dict]               # [{chunk_id, signature, frequency}]
    contained_by: list[dict]                  # [{parent_xpath, parent_chunk_id}]
    subtree_size: int                         # structural richness of canonical
    content_types: set                        # union across all instances
    is_composite: bool                        # contains multiple distinct atoms?
    child_content_ids: list[str] = field(default_factory=list)


class ContentCoagulator:
    """
    Post-processing layer that deduplicates and aggregates template
    instances by content identity, producing graph-ready records.
    
    Operates on v13 template mining output. Does NOT modify template
    groups — it produces a parallel content-indexed view.
    """

    def __init__(self, dom: ShadowDOM, chunks: list[ChunkGroup]):
        self.dom = dom
        self.chunks = chunks
        # Include structural templates, text content, and nav content
        # (text_content/nav_content chunks have _structural_sig='' but
        # signature starts with '[text_content:' or '[nav_content:')
        def _is_content_chunk(c):
            return (c._structural_sig
                    or c.signature.startswith('[text_content:')
                    or c.signature.startswith('[nav_content:'))
        self._template_chunks = [
            c for c in chunks if _is_content_chunk(c)
        ]
        self._functional_chunks = [
            c for c in chunks if not _is_content_chunk(c)
        ]

    # -----------------------------------------------------------------
    # Content Fingerprinting
    # -----------------------------------------------------------------

    @staticmethod
    def _canonical_href(href: str) -> str:
        """Normalize href for identity matching."""
        if not href:
            return ""
        h = href.strip()
        # Strip trailing slash (but not for root "/")
        if len(h) > 1 and h.endswith('/'):
            h = h.rstrip('/')
        # Lowercase path component (preserve query params case)
        if '?' in h:
            path, query = h.split('?', 1)
            h = path.lower() + '?' + query
        else:
            h = h.lower()
        return h

    @staticmethod
    def _extract_primary_href(node: ShadowNode) -> Optional[str]:
        """
        Extract the primary navigable URL from a node.

        Delegates to AgnosticAttr.primary_url — inspects ALL attributes
        on every element, not just ``<a href>``.  This catches navigable
        URLs in ``data-href``, ``data-url``, ``action``, etc.
        """
        return AgnosticAttr.primary_url(node)

    @staticmethod
    def _extract_all_hrefs(node: ShadowNode) -> list[str]:
        """Extract all substantive URLs from a subtree (agnostic)."""
        return [u for u in AgnosticAttr.all_urls(node)
                if not u.startswith('#') and not u.startswith('javascript')]

    @staticmethod
    def _extract_image_srcs(node: ShadowNode) -> list[str]:
        """Extract all image/media source URLs from a subtree (agnostic).

        Delegates to AgnosticAttr — inspects ALL attributes on every
        descendant, discovering URLs by value heuristics rather than
        hardcoded ``src``/``srcset`` key assumptions.
        """
        return list(dict.fromkeys(
            AgnosticAttr.primary_media_key(desc)
            for desc in node.iter_all()
            if AgnosticAttr.primary_media_key(desc)
        ))

    @staticmethod
    def _extract_all_embedded_urls(node: ShadowNode) -> list[str]:
        """
        Extract ALL embedded URLs from a subtree (agnostic).

        Delegates to AgnosticAttr.navigable_urls — inspects ALL
        attributes on every descendant, discovering URLs by value
        heuristics.  No hardcoded attribute key lists.
        """
        return list(dict.fromkeys(AgnosticAttr.navigable_urls(node)))

    @staticmethod
    def _text_fingerprint(text: str) -> str:
        """Hash normalized text for content identity."""
        import hashlib
        normalized = ' '.join(text.split()).lower().strip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:16]

    def _find_resource_siblings(
        self, node: ShadowNode, template_node_ids: set[int],
    ) -> list[ShadowNode]:
        """Resource-Affinity Sibling Expansion (v16).

        Detects adjacent sibling nodes that share the same primary href
        as ``node`` but are NOT themselves template instances. These are
        "orphaned" layout columns (e.g. image columns in Beaver Builder)
        that the template miner couldn't detect because their subtree
        height falls below the mining threshold.

        Algorithm (Resource-Affinity Graph over siblings):
          1. Get parent's children (the sibling cohort)
          2. Identify ``node``'s position
          3. Expand left/right while adjacent siblings:
             (a) share the same canonical href, AND
             (b) are NOT template instances (to avoid double-counting)
          4. Return the orphaned siblings

        Graph-theoretic interpretation:
          Build a bipartite graph G_R between sibling nodes and their
          navigable hrefs. Connected components of the node-projection
          partition siblings into resource-affinity groups. This method
          computes the component containing ``node`` restricted to
          non-template siblings.

        Spectral connection:
          The Fiedler vector (2nd eigenvector of G_R's normalised
          Laplacian) bipartitions siblings by resource affinity. When
          children follow a periodic pattern [img-A, txt-A, img-B,
          txt-B], the Fiedler cut separates {A-cols} from {B-cols}.
          This method achieves the same partition deterministically
          via the href equality criterion — exact when each card has
          a unique href (Cheeger constant h(G_R) → ∞ for the inter-
          card cut).
        """
        my_href = self._extract_primary_href(node)
        if not my_href:
            return []
        my_href_canon = self._canonical_href(my_href)

        parent = node.parent
        if not parent:
            return []

        siblings = [
            c for c in parent.get_children()
            if not c.tag.startswith('#')
        ]
        my_idx = None
        for i, s in enumerate(siblings):
            if s is node:
                my_idx = i
                break
        if my_idx is None:
            return []

        result = []
        for direction in (-1, 1):
            idx = my_idx + direction
            while 0 <= idx < len(siblings):
                sib = siblings[idx]
                # Skip if this sibling is a template instance
                if id(sib) in template_node_ids:
                    break
                sib_href = self._extract_primary_href(sib)
                if sib_href and self._canonical_href(sib_href) == my_href_canon:
                    result.append(sib)
                    idx += direction
                else:
                    break

        return result

    def _fingerprint(
        self, node: ShadowNode, mask: set[int] | None = None,
    ) -> tuple[str, str]:
        """
        Compute content fingerprint φ(v) = (canonical_href, text_hash).
        Uses mask-aware text extraction (v16) so that clean and self-
        duplicated instances of the same content produce the same hash.
        """
        href = self._extract_primary_href(node)
        canonical = self._canonical_href(href) if href else ""
        text = self._dedup_text(node, max_length=500, mask=mask)
        text_hash = self._text_fingerprint(text)
        return (canonical, text_hash)

    def _content_id(self, fp: tuple[str, str]) -> str:
        """Generate stable content ID from fingerprint."""
        import hashlib
        raw = f"{fp[0]}|{fp[1]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:20]

    # -----------------------------------------------------------------
    # Structural Richness
    # -----------------------------------------------------------------

    @staticmethod
    def _subtree_size(node: ShadowNode) -> int:
        """Count all descendant nodes (structural richness metric)."""
        return sum(1 for _ in node.iter_descendants())

    # -----------------------------------------------------------------
    # Composite Detection and Atom Extraction
    # -----------------------------------------------------------------

    def _is_composite(self, node: ShadowNode) -> bool:
        """
        A composite instance contains multiple distinct atomic content
        items (distinct navigable URLs) as children.  Agnostic: inspects
        ALL attributes on every descendant.
        """
        urls = set(
            self._canonical_href(u)
            for u in AgnosticAttr.navigable_urls(node)
        )
        return len(urls) >= 2

    def _extract_atoms(self, composite_node: ShadowNode) -> list[ShadowNode]:
        """
        Extract atomic content subtrees from a composite instance.
        
        Strategy: Find all elements with navigable URLs (agnostic).
        For each URL-bearing element, walk upward to find the highest
        ancestor that doesn't contain a DIFFERENT URL.
        """
        # Agnostic: find all descendants carrying navigable URLs
        anchors = []
        anchor_urls: dict[int, str] = {}  # node_id → primary URL
        for desc in composite_node.iter_descendants():
            url = AgnosticAttr.primary_url(desc)
            if url:
                # Only take the node itself if it directly has a URL
                # (not inherited from descendants)
                node_urls = [u for u in AgnosticAttr.urls_from_node(desc)
                             if u and not u.startswith('#')
                             and not u.startswith('javascript')]
                if node_urls:
                    anchors.append(desc)
                    anchor_urls[id(desc)] = node_urls[0]

        if not anchors:
            return []

        anchor_ids = {id(a) for a in anchors}

        atoms = []
        for anchor in anchors:
            anchor_url = anchor_urls[id(anchor)]
            best = anchor
            current = anchor.parent
            while current is not None and current is not composite_node:
                contains_different = False
                for desc in current.iter_descendants():
                    if id(desc) in anchor_ids and desc is not anchor:
                        other_url = anchor_urls.get(id(desc), '')
                        if other_url != anchor_url:
                            contains_different = True
                            break
                if contains_different:
                    break
                best = current
                current = current.parent
            atoms.append(best)

        seen = set()
        unique_atoms = []
        for atom in atoms:
            if id(atom) not in seen:
                seen.add(id(atom))
                unique_atoms.append(atom)

        return unique_atoms

    @staticmethod
    def _self_duplication_purity(node: ShadowNode) -> float:
        """
        Multi-channel self-duplication purity for coagulation.
        Delegates to SiblingCohortMiner._instance_purity.
        """
        return SiblingCohortMiner._instance_purity(node)

    # -----------------------------------------------------------------
    # Intra-Instance Semantic Deduplication Mask  (THEORY v16)
    # -----------------------------------------------------------------

    @staticmethod
    def _build_dedup_mask(node: ShadowNode) -> set[int]:
        """
        Build a semantic deduplication mask for an instance node.

        Identifies subtrees within the instance that are semantic
        duplicates of other sibling subtrees (same text + same
        resources). Returns the set of node IDs that should be
        excluded from text/HTML extraction.

        Complexity
        ----------
        This used to be O(N²) (or worse): each branching point re-walked
        every candidate child's entire subtree, and because every child
        has a parent, those walks piled up into a quadratic blowup on
        pages with deep DOMs. The rewrite is two passes:

        1. **Single post-order DFS** precomputes per-node
           ``(self_text, self_urls, self_img)`` in O(N) (each O(1) per
           node) and rolls them up into ``(subtree_text, subtree_urls,
           subtree_imgs, subtree_size)`` via child concatenation/union.
        2. **Branching-point walk** does an O(N) BFS where each
           comparison is just a dict lookup — no re-traversal.

        Net cost: one DFS + one BFS + per-branching-point hash keys. On
        a 5 000-node page this takes single-digit milliseconds instead
        of the multi-second stall that inspired this rewrite.

        See THEORY_v16.md §3 for formal definition.
        """
        masked: set[int] = set()

        # Phase 0: mask fallback-copy elements (always duplicate content).
        # Cheap, single pass — and we mark them before the rollup so
        # they don't contribute to ancestor fingerprints either.
        for desc in node.iter_descendants():
            if AgnosticAttr.is_fallback_copy(desc):
                masked.add(id(desc))
                for nd in desc.iter_descendants():
                    masked.add(id(nd))

        # ---- Phase 1a: post-order DFS roll-up of per-subtree stats ----
        # Per-node cached props:
        #   text:  normalized visible text of the subtree (lowercase-stripped)
        #   urls:  frozenset of navigable URLs found anywhere in the subtree
        #   imgs:  frozenset of primary media keys found in the subtree
        #   size:  count of descendant element nodes in the subtree
        #
        # Ids-of-masked (fallback-copy subtrees) are excluded entirely
        # via ``if id(c) in masked: continue`` at the rollup step.

        text_map: dict[int, str] = {}
        urls_map: dict[int, frozenset] = {}
        imgs_map: dict[int, frozenset] = {}
        size_map: dict[int, int] = {}

        # Iterative post-order traversal. We push (node, visited_flag)
        # pairs: on first pop we queue children; on second pop (visited)
        # we actually compute the rollup from already-filled child maps.
        stack: list[tuple] = [(node, False)]
        while stack:
            cur, visited = stack.pop()
            if id(cur) in masked:
                continue
            if not visited:
                stack.append((cur, True))
                for c in cur.get_children():
                    if c.tag.startswith('#') or id(c) in masked:
                        continue
                    stack.append((c, False))
                continue

            # Second visit: rollup from self + children.
            parts: list[str] = []
            urls_acc: set = set()
            imgs_acc: set = set()
            size_acc = 1

            t = cur.text
            if t:
                t = t.strip()
                if t:
                    parts.append(t)

            for u in AgnosticAttr.urls_from_node(cur):
                if u and not u.startswith('#') and not u.startswith('javascript'):
                    urls_acc.add(u.strip().lower())

            key = AgnosticAttr.primary_media_key(cur)
            if key:
                imgs_acc.add(key)

            for c in cur.get_children():
                if c.tag.startswith('#') or id(c) in masked:
                    continue
                cid = id(c)
                if cid in text_map:
                    ct = text_map[cid]
                    if ct:
                        parts.append(ct)
                    urls_acc.update(urls_map[cid])
                    imgs_acc.update(imgs_map[cid])
                    size_acc += size_map[cid]

            text_map[id(cur)] = (' '.join(parts)).lower()
            urls_map[id(cur)] = frozenset(urls_acc)
            imgs_map[id(cur)] = frozenset(imgs_acc)
            size_map[id(cur)] = size_acc

        # ---- Phase 1b: branching-point BFS using cached rollups ----
        queue = deque([node])
        while queue:
            parent = queue.popleft()
            if id(parent) in masked:
                continue
            children = [c for c in parent.get_children()
                        if not c.tag.startswith('#')
                        and id(c) not in masked]
            if len(children) < 2:
                queue.extend(children)
                continue

            # Fingerprint each child via O(1) dict lookups.
            fp_groups: dict[tuple, list] = {}
            for c in children:
                cid = id(c)
                t = text_map.get(cid, "")
                u = urls_map.get(cid, frozenset())
                i = imgs_map.get(cid, frozenset())
                if len(t) < 20 and not u and not i:
                    # Too little content to match — keep walking into it.
                    queue.append(c)
                    continue
                fp_groups.setdefault((t[:200], u, i), []).append(c)

            for members in fp_groups.values():
                if len(members) < 2:
                    queue.extend(members)
                    continue

                # Keep the richest (largest subtree) and mask the rest.
                members.sort(key=lambda c: -size_map.get(id(c), 0))
                queue.append(members[0])
                for dup in members[1:]:
                    masked.add(id(dup))
                    for d in dup.iter_descendants():
                        masked.add(id(d))

        return masked

    @staticmethod
    def _dedup_text(
        node: ShadowNode, max_length: int = 500,
        mask: set[int] | None = None,
    ) -> str:
        """Extract visible text with three-layer deduplication:

        Layer 1 (structural mask, v16): Skips entire duplicate sibling
        subtrees identified by _build_dedup_mask.

        Layer 2 (heading dedup): Tracks h1-h6 text; skips entire
        subtree on duplicate heading (heading = semantic unit).

        Layer 3 (direct-text dedup, v16): Tracks direct text fragments
        (n.text ≥ 8 chars after normalization) from ANY element. On
        duplicate, skips the text but still walks children — this
        catches repeated descriptions, metadata labels, and names in
        non-heading elements without losing unique child content.

        Also extracts text from semantic attributes (alt, aria-label,
        title, placeholder) on leaf/void elements that carry no visible
        text children, and collects tail text (text after child
        elements that belongs to the parent node).

        Normalization strips zero-width Unicode characters (ZWS, ZWNJ,
        ZWJ, BOM) which Wix and similar frameworks inject into
        otherwise-identical text copies.

        Uses n.text (text before first child), NOT get_text() (all
        descendant text), to avoid the parent-claims-children bug.
        """
        # Uses module-level HEADING_TAGS, FALLBACK_COPY_TAGS constants
        # Attributes whose values are human-readable text — discovered
        # agnostically by checking if a value has meaningful word tokens
        # and is NOT a URL.  No hardcoded attribute name list.
        # Zero-width characters commonly injected by Wix/React frameworks
        _ZW = str.maketrans('', '', '\u200b\u200c\u200d\ufeff\u00a0')
        seen_headings: set[str] = set()
        seen_fragments: set[str] = set()
        parts: list[str] = []
        _mask = mask or set()

        def _is_human_text(val: str) -> bool:
            """Heuristic: is this attribute value human-readable text?"""
            if not val or len(val) < 2:
                return False
            # Not a URL
            if AgnosticAttr.is_url(val):
                return False
            # Has word characters (not purely punctuation/numbers/hashes)
            tokens = AttributeTokenizer.tokenize(val[:200])
            return len(tokens) >= 1

        def _normalize(s: str) -> str:
            """Strip zero-width chars, collapse whitespace, lowercase."""
            return ' '.join(s.translate(_ZW).split()).lower()[:100]

        def _walk(n: ShadowNode):
            if id(n) in _mask:
                return  # masked by semantic dedup
            tag = n.tag.lower()
            if tag in SKIP_TAGS:
                return

            # Layer 2: heading dedup — skip entire subtree
            if tag in HEADING_TAGS:
                t = _normalize(n.get_text())
                if t in seen_headings:
                    return
                if t:
                    seen_headings.add(t)

            # Layer 3: direct-text dedup — skip text, walk children
            if n.text:
                raw = n.text.strip()
                norm = _normalize(raw)
                if len(norm) >= 8:
                    if norm not in seen_fragments:
                        seen_fragments.add(norm)
                        # Emit cleaned text (strip zero-width chars)
                        clean = raw.translate(_ZW).strip()
                        if clean:
                            parts.append(clean)
                    # else: skip duplicate text, still walk children
                else:
                    clean = raw.translate(_ZW).strip()
                    if clean:
                        parts.append(clean)

            # Semantic attribute text for leaf/void elements.
            # Agnostic: scan ALL attributes for human-readable text
            # (not URLs, not hashes). Catches alt, aria-label, title,
            # placeholder, and any custom attr with readable content.
            if not n.text:
                children = list(n.get_children())
                has_text_children = any(
                    (c.text and c.text.strip()) or
                    (not c.tag.startswith('#'))
                    for c in children
                )
                if not has_text_children:
                    for attr_name, attr_val in n.get_all_attrs().items():
                        val = str(attr_val or '').strip()
                        if _is_human_text(val):
                            norm = _normalize(val)
                            if len(norm) >= 8:
                                if norm not in seen_fragments:
                                    seen_fragments.add(norm)
                                    parts.append(val)
                            else:
                                parts.append(val)
                            break  # one attribute per node

            for child in n.get_children():
                _walk(child)
                # Tail text: text after child, belonging to parent
                if child.tail:
                    raw_tail = child.tail.strip()
                    if raw_tail:
                        norm_tail = _normalize(raw_tail)
                        if len(norm_tail) >= 8:
                            if norm_tail not in seen_fragments:
                                seen_fragments.add(norm_tail)
                                clean = raw_tail.translate(_ZW).strip()
                                if clean:
                                    parts.append(clean)
                        else:
                            clean = raw_tail.translate(_ZW).strip()
                            if clean:
                                parts.append(clean)

        _walk(node)
        return ' '.join(p for p in parts if p)[:max_length].strip()

    @staticmethod
    def _render_deduped_html(
        node: ShadowNode, max_length: int = 2000, indent: int = 0,
        mask: set[int] | None = None,
    ) -> str:
        """
        Render HTML from a ShadowNode while skipping internally-duplicated
        semantic elements. Uses the v16 semantic dedup mask to skip entire
        duplicate subtrees, plus element-level tracking for residual
        heading/image duplicates within non-masked subtrees.
        """
        _mask = mask or set()
        # Uses module-level HEADING_TAGS, MEDIA_TAGS constants

        seen_headings: set[str] = set()
        seen_media: set[str] = set()
        seen_text: set[str] = set()  # v16: track non-heading text leaves
        seen_hrefs: set[str] = set()  # v17: track <a> href dedup

        def _should_skip(n: ShadowNode) -> bool:
            tag = n.tag.lower()
            _ZWH = str.maketrans('', '', '\u200b\u200c\u200d\ufeff\u00a0')
            if tag in HEADING_TAGS:
                raw = n.get_text().strip()[:100]
                visible = ' '.join(raw.translate(_ZWH).split()).lower()
                if not visible:
                    return True
                if visible in seen_headings:
                    return True
                seen_headings.add(visible)
            elif tag == 'img':
                # If parent is <picture>, dedup was handled at container level
                if n.parent and AgnosticAttr.is_media_container(n.parent):
                    return False
                # Agnostic: inspect ALL attributes for media URL
                src = AgnosticAttr.primary_media_key(n)
                # Normalize CDN resize params (e.g. .jpg/v1/fill/w_300,h_200)
                if src:
                    src = re.sub(r'(\.\w{3,4})[/?].*$', r'\1', src)
                if src and src in seen_media:
                    return True
                if src:
                    seen_media.add(src)
            elif tag == 'source':
                if n.parent and AgnosticAttr.is_media_container(n.parent):
                    return False
            elif AgnosticAttr.is_media_container(n):
                # Agnostic: inspect ALL descendant attributes for media URL
                key = AgnosticAttr.primary_media_key_subtree(n)
                # Normalize CDN resize params for dedup comparison
                if key:
                    key = re.sub(r'(\.\w{3,4})[/?].*$', r'\1', key)
                if key and key in seen_media:
                    return True
                if key:
                    seen_media.add(key)
            elif tag == 'svg':
                # Agnostic SVG dedup: hash ALL attributes for identity
                all_attrs = '|'.join(
                    f"{k}={v}" for k, v in sorted(n.get_all_attrs().items())
                    if v
                )[:200]
                if all_attrs and all_attrs in seen_media:
                    return True
                if all_attrs:
                    seen_media.add(all_attrs)

            # v16: Text-leaf dedup
            _ZW = str.maketrans('', '', '\u200b\u200c\u200d\ufeff\u00a0')
            if tag not in HEADING_TAGS and tag not in MEDIA_TAGS and tag != 'svg':
                direct_text = (n.text or '').strip()
                norm = ' '.join(direct_text.translate(_ZW).split()).lower()[:100]
                if len(norm) >= 8:
                    has_text_children = any(
                        len((c.get_text() or '').strip()) >= 10
                        for c in n.get_children()
                        if not c.tag.startswith('#')
                        and c.tag.lower() not in ('noscript', 'template')
                    )
                    if not has_text_children:
                        if norm in seen_text:
                            return True
                        seen_text.add(norm)

            return False

        # Tags whose text content may contain raw HTML duplicates
        SKIP_TAGS = frozenset({'noscript', 'template'})

        # Tags that are purely structural wrappers (can be flattened)
        FLATTENABLE = frozenset({'div', 'span', 'section', 'main', 'aside',
                                 'article', 'header', 'footer', 'nav',
                                 'figure', 'figcaption', 'details'})

        # ── General URL detection ──────────────────────────────────
        # These patterns detect URLs in ANY attribute value without
        # relying on a predefined list of attribute names.
        #
        # Absolute:          https://example.com/path
        # Protocol-relative: //cdn.example.com/asset.js
        # Root-relative:     /details/folksoundomy  (starts with /\w)
        # Data URI:          data:image/svg+xml,...
        # CSS url():         url('https://...')  or  url(/path/...)
        _ABS_URL_RE = re.compile(
            r'https?://[^\s\'"<>)]+', re.I)
        _PROTO_REL_RE = re.compile(
            r'//[a-zA-Z0-9][\w.-]+\.[a-zA-Z]{2,}[^\s\'"<>)]*')
        _CSS_URL_RE = re.compile(
            r'url\([\'"]?([^\'")]+)[\'"]?\)')
        _JUNK_DOMAINS = {'w3.org', 'schema.org'}

        def _value_has_url(v: str) -> bool:
            """True if the attribute value contains any URL pattern."""
            sv = v.strip().strip("'\"")
            if sv.startswith('data:'):
                return True
            if _ABS_URL_RE.search(v):
                return not all(
                    any(j in u for j in _JUNK_DOMAINS)
                    for u in _ABS_URL_RE.findall(v))
            if _PROTO_REL_RE.search(v):
                return True
            if _CSS_URL_RE.search(v):
                return True
            # Root-relative path:  /word...  (not bare "/" or "//")
            if sv and sv[0] == '/' and len(sv) > 1 and sv[1].isalnum():
                return True
            return False

        def _node_has_url_attr(n) -> bool:
            """True if ANY attribute of *n* carries a URL."""
            for v in n.attributes.values():
                if _value_has_url(v):
                    return True
            return False

        def _render(n: ShadowNode, ind: int) -> str:
            tag = n.tag
            if tag.startswith('#'):
                return ""
            # v16: skip subtrees masked by semantic deduplication
            if id(n) in _mask:
                return ""
            # noscript/template contain fallback copies of visible content
            if tag.lower() in SKIP_TAGS:
                return ""
            if _should_skip(n):
                return ""

            # Flatten: skip pure wrapper elements (no text, 1 child)
            # to save HTML budget for deeply nested frameworks.
            # NEVER flatten if the node itself carries a URL attribute
            # (e.g. background-image in style, data-href, etc.).
            tag_lower = tag.lower()
            text_part = n.text.strip() if n.text else ""
            if (tag_lower in FLATTENABLE
                    and not text_part
                    and not _node_has_url_attr(n)):
                renderable_children = []
                for child in n.get_children():
                    if child.tag.startswith('#'):
                        continue
                    if child.tag.lower() in SKIP_TAGS:
                        continue
                    renderable_children.append(child)
                if len(renderable_children) == 1:
                    # Skip this wrapper, render the single child directly
                    return _render(renderable_children[0], ind)

            prefix = "  " * ind

            # ── Attribute filtering ────────────────────────────────
            # Agnostic: keep attributes whose values carry meaningful
            # content (tokenize to real words or contain URLs).
            # No hardcoded attribute key allowlist — discriminative
            # power is determined by value analysis.
            kept = {}

            for k, v in n.attributes.items():
                # Skip XML namespace declarations
                if k.startswith('xmlns'):
                    continue

                # ── Agnostic value analysis ──
                # 1. CSS url() in style attrs — keep if valid URL
                css_urls = _CSS_URL_RE.findall(v)
                css_urls = [u for u in css_urls
                            if not any(j in u for j in _JUNK_DOMAINS)]
                if css_urls:
                    kept[k] = v
                    continue

                # 2. Value contains a URL — keep (navigable content)
                if _value_has_url(v):
                    kept[k] = v
                    continue

                # 3. Value has meaningful tokens (words, not hashes)
                # This agnostically preserves class, alt, title,
                # aria-label, type, name, etc. without hardcoding.
                tokens = AttributeTokenizer.tokenize(str(v)[:300])
                if tokens:
                    kept[k] = v
                    continue

                # 4. Short non-empty value (likely structural: 'true',
                #    'dialog', 'button', etc.) — keep for context.
                if v and len(v) < 20:
                    kept[k] = v
                    continue

                # 5. No meaningful signal → drop (bloat reduction)

            # v17: Deduplicate <a> hrefs — when the same destination
            # appears multiple times (avatar/name/handle all → profile),
            # keep the first link, strip href from subsequent duplicates
            # so the text content is preserved but the link is not repeated.
            if tag_lower == 'a' and 'href' in kept:
                href_val = kept['href']
                if href_val in seen_hrefs:
                    del kept['href']
                else:
                    seen_hrefs.add(href_val)

            attrs = " ".join(f'{k}="{v}"' for k, v in kept.items())
            opening = f"<{tag} {attrs}>" if attrs else f"<{tag}>"

            children_html = []
            for child in n.get_children():
                child_html = _render(child, ind + 1)
                if child_html:
                    children_html.append(child_html)
                # Append tail text (text after this child, belonging to
                # parent). Include even when the child itself was skipped
                # by dedup, since the tail is parent content.
                tail = child.tail.strip() if child.tail else ""
                if tail:
                    children_html.append(f"{'  ' * (ind + 1)}{tail}")

            text_part = n.text.strip() if n.text else ""
            if not children_html and not text_part:
                return f"{prefix}{opening}</{tag}>"

            parts = [f"{prefix}{opening}"]
            if text_part:
                parts.append(f"{'  ' * (ind + 1)}{text_part}")
            parts.extend(children_html)
            parts.append(f"{prefix}</{tag}>")
            return "\n".join(parts)

        html = _render(node, indent)
        return html[:max_length]

    # -----------------------------------------------------------------
    # Main Coagulation Pipeline
    # -----------------------------------------------------------------

    def coagulate(self, max_html_length: int = 2000) -> list[CoagulatedRecord]:
        """
        Execute the full coagulation pipeline:
          1. Fingerprint all template instances
          2. Extract atoms from composite instances
          3. Group by content identity
          4. Select canonical and aggregate metadata
          5. Build containment links
        
        Returns coagulated records sorted by subtree_size descending.
        """
        # ── Step 1: Fingerprint all direct template instances ──
        # Each entry: {fp, node, chunk_idx, chunk, size, is_extracted, parent_xpath}
        # v16: compute semantic dedup mask per instance for clean fingerprinting
        # §5.3: Composite instances use text-hash-only fingerprints to
        # avoid colliding with their children's hrefs.
        all_instances = []

        for ci, chunk in enumerate(self._template_chunks):
            for node in chunk._instance_nodes:
                mask = self._build_dedup_mask(node)
                fp = self._fingerprint(node, mask=mask)
                size = self._subtree_size(node)
                purity = self._self_duplication_purity(node)

                # §5.3 Composite Fingerprint Isolation:
                # If this instance is composite (contains ≥2 distinct hrefs),
                # force it to use text-hash-only fingerprint. Otherwise the
                # section's first <a> href matches one child card's href,
                # and the section (size=2000+) wins canonical selection
                # over the card (size=80), absorbing the card.
                is_comp = self._is_composite(node)
                if is_comp and fp[0]:
                    fp = ("", fp[1])  # drop href, keep text_hash

                all_instances.append({
                    'fp': fp,
                    'node': node,
                    'chunk_idx': ci,
                    'chunk': chunk,
                    'size': size,
                    'purity': purity,
                    'mask': mask,
                    'is_extracted': False,
                    'is_composite': is_comp,
                    'parent_xpath': None,
                    'parent_chunk_idx': None,
                    'resource_siblings': [],  # v16: populated in Step 1b
                })

        # ── Step 1b: Resource-Affinity Sibling Expansion ──
        # For each non-composite template instance, find adjacent
        # non-template siblings sharing the same primary href. These
        # orphaned siblings (e.g. image columns in Beaver Builder
        # layouts) are invisible to template mining (height < 2) but
        # carry essential resources (images, supplementary text).
        template_node_ids = {id(inst['node']) for inst in all_instances}
        for inst in all_instances:
            if inst['is_composite']:
                continue
            inst['resource_siblings'] = self._find_resource_siblings(
                inst['node'], template_node_ids,
            )

        # ── Step 2: Detect composites and extract atoms ──
        composite_atoms = {}  # composite_node_id → list of atom entries

        for ci, chunk in enumerate(self._template_chunks):
            for node in chunk._instance_nodes:
                if not self._is_composite(node):
                    continue

                atoms = self._extract_atoms(node)
                parent_xpath = cached_xpath(node)
                composite_atoms[id(node)] = []

                for atom in atoms:
                    # Skip if atom IS the composite itself
                    if atom is node:
                        continue
                    # Skip if atom is already a direct template instance
                    # (already fingerprinted in step 1)
                    atom_id = id(atom)
                    already_direct = any(
                        id(inst['node']) == atom_id
                        for inst in all_instances
                        if not inst['is_extracted']
                    )
                    if already_direct:
                        # Still record containment, but don't re-add
                        atom_mask = self._build_dedup_mask(atom)
                        fp = self._fingerprint(atom, mask=atom_mask)
                        href_key = fp[0]
                        cid_fp = (href_key, "") if href_key else ("", fp[1])
                        composite_atoms[id(node)].append(self._content_id(cid_fp))
                        continue

                    atom_mask = self._build_dedup_mask(atom)
                    fp = self._fingerprint(atom, mask=atom_mask)
                    href_key = fp[0]
                    size = self._subtree_size(atom)

                    # Skip text-less tiny atoms (pure image/link wrappers).
                    # They have no content value on their own and were only
                    # extracted because they happen to contain an <a> tag.
                    atom_text = self._dedup_text(atom, 500, mask=atom_mask)
                    if not atom_text.strip() and size < 15:
                        continue

                    purity = self._self_duplication_purity(atom)
                    entry = {
                        'fp': fp,
                        'node': atom,
                        'chunk_idx': ci,
                        'chunk': chunk,
                        'size': size,
                        'purity': purity,
                        'mask': atom_mask,
                        'is_extracted': True,
                        'parent_xpath': parent_xpath,
                        'parent_chunk_idx': ci,
                        'resource_siblings': [],
                    }
                    all_instances.append(entry)
                    cid_fp = (href_key, "") if href_key else ("", fp[1])
                    composite_atoms[id(node)].append(self._content_id(cid_fp))

        # ── Step 3: Group by content fingerprint ──
        # Two-phase grouping per §3.3:
        #   Phase A: Group by canonical_href (when available).
        #            Href is the primary content identity.
        #   Phase B: For href-absent instances, group by text_hash.
        from collections import defaultdict

        href_groups = defaultdict(list)     # canonical_href → instances
        nohref_groups = defaultdict(list)   # text_hash → instances

        for inst in all_instances:
            href_key, text_key = inst['fp']
            if href_key:
                href_groups[href_key].append(inst)
            else:
                nohref_groups[text_key].append(inst)

        # ── Step 3.5: Within-group instance purity filter ──
        # For each content fingerprint group, drop instances whose
        # element purity is significantly below the purest instance
        # of the same content. This removes rendering duplicates:
        # CBC renders the same card in div[2] (clean) and div[3]
        # (bloated with 2× heading + 2× image). These share the
        # same href but different purity levels.
        #
        # Compares across chunks: if the same article appears in
        # chunk A (purity=1.0) and chunk B (purity=0.50), the
        # chunk B instance is a rendering artifact regardless of
        # structural role.
        #
        # Exemptions:
        #   - Extracted atoms (is_extracted=True): these carry
        #     containment hierarchy and should not be dropped.
        #   - Never drop ALL instances — always keep at least one.
        #
        # Threshold: instance_purity < best_purity * 0.75
        PURITY_RATIO_THRESHOLD = 0.75

        def _filter_group_by_purity(instances):
            if len(instances) < 2:
                return instances

            # Only filter direct (non-extracted) non-composite instances.
            # Composites carry containment hierarchy (parent→child edges)
            # that would be lost if dropped. They may share a primary_href
            # with one of their children but serve a different structural
            # role: container vs. content.
            direct_noncomp = [
                i for i in instances
                if not i['is_extracted'] and not self._is_composite(i['node'])
            ]
            others = [
                i for i in instances
                if i['is_extracted'] or self._is_composite(i['node'])
            ]

            if len(direct_noncomp) < 2:
                return instances  # can't filter with < 2 candidates

            max_p = max(i['purity'] for i in direct_noncomp)
            if max_p <= 0:
                return instances

            threshold = max_p * PURITY_RATIO_THRESHOLD
            kept = [i for i in direct_noncomp if i['purity'] >= threshold]

            if not kept:
                kept = direct_noncomp  # safety: never drop all

            return kept + others

        for href_key in list(href_groups.keys()):
            href_groups[href_key] = _filter_group_by_purity(href_groups[href_key])

        for text_key in list(nohref_groups.keys()):
            nohref_groups[text_key] = _filter_group_by_purity(nohref_groups[text_key])

        # Merge into unified groups keyed by content_id
        groups = {}
        for href_key, instances in href_groups.items():
            # Use href as the identity (text_hash of the richest instance
            # is used for the content_id but doesn't split the group)
            fp = (href_key, "")
            cid = self._content_id(fp)
            groups[cid] = (fp, instances)

        for text_key, instances in nohref_groups.items():
            fp = ("", text_key)
            cid = self._content_id(fp)
            groups[cid] = (fp, instances)

        # ── Step 4: Select canonical, aggregate, build records ──
        records = []
        for content_id, (fp, instances) in groups.items():

            # Sort by effective richness (subtree_size * purity),
            # penalizing internally self-duplicated instances.
            # A clean instance (purity=1.0) keeps its full size;
            # a 2.5× self-duplicated instance (purity=0.4) is
            # penalized to 40% of its raw size.
            def sort_key(inst):
                effective_size = inst['size'] * inst['purity']
                return (
                    -effective_size,
                    -inst['purity'],          # tiebreak: prefer purer instance
                    0 if not inst['is_extracted'] else 1,
                    -inst['chunk'].frequency,
                    cached_xpath(inst['node']),
                )
            instances.sort(key=sort_key)
            canonical = instances[0]
            canonical_node = canonical['node']

            # Aggregate all xpaths
            all_xpaths = list(dict.fromkeys(
                cached_xpath(inst['node']) for inst in instances
            ))

            # Aggregate relative xpaths
            relative_xpaths = []
            for inst in instances:
                rel = get_relative_xpath(
                    inst['node'], inst['chunk'].subtree_root
                )
                relative_xpaths.append({
                    'relative_xpath': rel,
                    'template_root': inst['chunk'].subtree_root,
                    'chunk_id': inst['chunk'].chunk_id,
                })

            # Aggregate template group provenance
            seen_chunks = set()
            template_groups = []
            for inst in instances:
                cid = inst['chunk'].chunk_id
                if cid not in seen_chunks:
                    seen_chunks.add(cid)
                    template_groups.append({
                        'chunk_id': cid,
                        'signature': inst['chunk'].signature[:80],
                        'frequency': inst['chunk'].frequency,
                        'structural_sig': inst['chunk']._structural_sig[:80],
                    })

            # Aggregate all hrefs and images across all instances
            # v16: Include resources from sibling-expanded nodes
            all_hrefs = list(dict.fromkeys(
                h for inst in instances
                for node_set in [inst['node']] + inst.get('resource_siblings', [])
                for h in self._extract_all_hrefs(node_set)
            ))
            image_srcs = list(dict.fromkeys(
                s for inst in instances
                for node_set in [inst['node']] + inst.get('resource_siblings', [])
                for s in self._extract_image_srcs(node_set)
            ))
            # v18: Comprehensive embedded URL extraction (§12.1)
            embedded_urls = list(dict.fromkeys(
                u for inst in instances
                for node_set in [inst['node']] + inst.get('resource_siblings', [])
                for u in self._extract_all_embedded_urls(node_set)
            ))

            # Aggregate content types
            content_types = set()
            for inst in instances:
                content_types.update(inst['chunk'].content_types)

            # Containment info
            contained_by = []
            for inst in instances:
                if inst['parent_xpath']:
                    contained_by.append({
                        'parent_xpath': inst['parent_xpath'],
                        'parent_chunk_id': inst['parent_chunk_idx'],
                    })

            # Composite detection for the canonical instance
            is_composite = self._is_composite(canonical_node)
            child_ids = []
            if is_composite and id(canonical_node) in composite_atoms:
                child_ids = composite_atoms[id(canonical_node)]

            # Build record
            # v16: use canonical instance's semantic dedup mask
            canonical_mask = canonical.get('mask', set())

            # v16: Resource-Affinity HTML expansion — if the canonical
            # instance has resource siblings (e.g. an adjacent image
            # column sharing the same href), render ALL siblings'
            # content into the canonical HTML for a complete card.
            canonical_siblings = canonical.get('resource_siblings', [])
            if canonical_siblings:
                # Build compound HTML: canonical node + siblings in DOM order
                sibling_htmls = []
                parent = canonical_node.parent
                if parent:
                    all_children = [
                        c for c in parent.get_children()
                        if not c.tag.startswith('#')
                    ]
                    sib_ids = {id(s) for s in canonical_siblings}
                    sib_ids.add(id(canonical_node))
                    for child in all_children:
                        if id(child) in sib_ids:
                            child_mask = self._build_dedup_mask(child)
                            sibling_htmls.append(
                                self._render_deduped_html(
                                    child,
                                    max_html_length // max(len(canonical_siblings) + 1, 1),
                                    mask=child_mask,
                                )
                            )
                compound_html = '\n'.join(h for h in sibling_htmls if h.strip())
                # Also expand text
                sibling_texts = []
                for child in all_children if parent else []:
                    if id(child) in sib_ids:
                        child_mask = self._build_dedup_mask(child)
                        sibling_texts.append(
                            self._dedup_text(child, 500, mask=child_mask)
                        )
                compound_text = ' '.join(t for t in sibling_texts if t.strip())[:500]
            else:
                compound_html = self._render_deduped_html(
                    canonical_node, max_html_length, mask=canonical_mask,
                )
                compound_text = self._dedup_text(
                    canonical_node, 500, mask=canonical_mask,
                )

            record = CoagulatedRecord(
                content_id=content_id,
                canonical_xpath=cached_xpath(canonical_node),
                canonical_html=compound_html,
                text=compound_text,
                primary_href=fp[0] if fp[0] else None,
                all_hrefs=all_hrefs,
                image_srcs=image_srcs,
                embedded_urls=embedded_urls,
                all_xpaths=all_xpaths,
                relative_xpaths=relative_xpaths,
                template_groups=template_groups,
                contained_by=contained_by,
                subtree_size=canonical['size'],
                content_types=content_types,
                is_composite=is_composite,
                child_content_ids=child_ids,
            )
            records.append(record)

        # Post-coagulation: eliminate composite records whose text
        # duplicates an atomic record's text.  Single-child sections
        # produce identical text to the child card they contain;
        # keeping both violates record-level text uniqueness.
        atomic_text_fps: set[str] = set()
        for r in records:
            if not r.is_composite:
                t = ' '.join(r.text.split()).lower()[:200]
                if len(t) >= 20:
                    atomic_text_fps.add(t)
        if atomic_text_fps:
            before_ct = len(records)
            records = [
                r for r in records
                if not r.is_composite
                or ' '.join(r.text.split()).lower()[:200] not in atomic_text_fps
            ]
            removed = before_ct - len(records)
            # Silently filter — no logging needed

        # Sort: composites first, then by subtree_size descending
        records.sort(key=lambda r: (0 if r.is_composite else 1, -r.subtree_size))
        return records

    # -----------------------------------------------------------------
    # Output Formatting
    # -----------------------------------------------------------------

    def summary(self, records: list[CoagulatedRecord]) -> str:
        """Human-readable summary of coagulated records."""
        lines = []
        total = len(records)
        composites = sum(1 for r in records if r.is_composite)
        atoms = total - composites
        duped = sum(1 for r in records if len(r.all_xpaths) > 1)

        lines.append(f"Coagulated: {total} unique records "
                      f"({composites} composite, {atoms} atomic, "
                      f"{duped} appeared in multiple positions)")
        lines.append("")

        for r in records:
            positions = len(r.all_xpaths)
            templates = len(r.template_groups)
            tag = "COMPOSITE" if r.is_composite else "ATOMIC"
            href_display = r.primary_href[:55] if r.primary_href else "(no href)"
            text_preview = r.text[:60].replace('\n', ' ')

            lines.append(
                f"[{tag:>9}] size={r.subtree_size:>3} "
                f"×{positions} positions, {templates} templates"
            )
            lines.append(f"  href: {href_display}")
            lines.append(f"  text: \"{text_preview}\"")
            if r.image_srcs:
                lines.append(f"  imgs: {len(r.image_srcs)}")
            if r.contained_by:
                lines.append(f"  contained_by: {len(r.contained_by)} parents")
            if r.child_content_ids:
                lines.append(f"  children: {len(r.child_content_ids)} atoms")
            lines.append("")

        return '\n'.join(lines)

    def to_graph_records(self, records: list[CoagulatedRecord]) -> list[dict]:
        """
        Export as a list of dicts suitable for knowledge graph ingestion.
        Each dict corresponds to a ContentNode with its edges.
        """
        output = []
        for r in records:
            node = {
                'content_id': r.content_id,
                'text': r.text,
                'canonical_html': r.canonical_html,
                'primary_href': r.primary_href,
                'all_hrefs': r.all_hrefs,
                'image_srcs': r.image_srcs,
                'embedded_urls': r.embedded_urls,
                'is_composite': r.is_composite,
                'subtree_size': r.subtree_size,
                'content_types': [c.value for c in r.content_types] if r.content_types else [],
                'template_signatures': [
                    tg['structural_sig'] for tg in r.template_groups
                ],
            }

            # AppearsAt edges
            appears_at = []
            for i, xpath in enumerate(r.all_xpaths):
                entry = {'xpath': xpath}
                if i < len(r.relative_xpaths):
                    entry['relative_xpath'] = r.relative_xpaths[i]['relative_xpath']
                    entry['template_root'] = r.relative_xpaths[i]['template_root']
                    entry['chunk_id'] = r.relative_xpaths[i]['chunk_id']
                appears_at.append(entry)
            node['appears_at'] = appears_at

            # Contains edges (for composites)
            if r.child_content_ids:
                node['contains'] = r.child_content_ids

            # ContainedBy edges
            if r.contained_by:
                node['contained_by'] = r.contained_by

            output.append(node)

        return output


if __name__ == "__main__":
    import sys
    import time

    if len(sys.argv) < 2:
        print("Usage: python web_distiller_v11.py <html_file>")
        sys.exit(1)

    args = [a for a in sys.argv[1:] if not a.startswith('--')]

    with open(args[0], "r", encoding="utf-8", errors="replace") as f:
        html_content = f.read()

    t0 = time.time()
    distiller = WebDistiller(html_content)
    chunks = distiller.process(verbose=True)
    elapsed = time.time() - t0

    print(f"\n=== Distillation complete: {len(chunks)} chunks in {elapsed:.2f}s ===")
    for chunk in chunks[:30]:
        print(
            f"Chunk {chunk.chunk_id:2d} | freq={chunk.frequency:3d} "
            f"| types={sorted(c.value for c in chunk.content_types)} "
            f"| root={chunk.subtree_root[:60]}"
        )
        print(f"   sig: {chunk.signature[:100]}")
        if chunk.samples:
            print(f"   sample_sig: {chunk.samples[0].get('signature','')[:80]}")
