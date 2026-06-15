"""
Enhanced Content Distiller
==========================
A robust content distiller that preserves nodes with meaningful text, links,
media, or interactive elements. Uses agnostic attribute inspection to capture
URLs from any attribute, and retains a cleaned HTML structure suitable for
browser viewing.

Reuses utilities from `web_distiller_freq.py` and `shadow_html_parser.py`.
"""

from __future__ import annotations
from typing import Set, Optional
from collections import deque

from .shadow_html_parser import ShadowDOM, ShadowNode, VOID_ELEMENTS
from .web_distiller_freq import (
    SKIP_TAGS,
    AgnosticAttr,
    AttributeTokenizer,
    URLExtractor,          # kept for backward compatibility but not strictly needed
)

# ----------------------------------------------------------------------
# Attributes that are always kept (structural or inherently content‑bearing)
# ----------------------------------------------------------------------
ALWAYS_KEEP_ATTRS = frozenset({
    # Core structural / identity
    'class', 'id', 'role', 'type', 'name', 'value',
    # Content from standard attributes
    'href', 'src', 'alt', 'title', 'aria-label', 'placeholder',
    'aria-describedby', 'aria-labelledby', 'data-content', 'data-title',
    # Form‑related
    'for', 'action', 'method',
    # Media
    'poster', 'srcset', 'sizes',
})

# ----------------------------------------------------------------------
# Main distiller class
# ----------------------------------------------------------------------
class EnhancedContentDistiller:
    """
    Distills HTML by retaining nodes that contain substantive content.
    Uses a post‑order traversal to mark nodes:
      - any node that itself has text, a URL, is a media element, or is interactive,
      - any node that has at least one such descendant.
    When rendering, only attributes that are either in ALWAYS_KEEP_ATTRS or
    contain a URL (detected agnostically) are preserved.
    """

    def __init__(self, html: str):
        self.dom = ShadowDOM(html)
        self.keep_set: Set[int] = set()

    # ------------------------------------------------------------------
    # Content detection (agnostic)
    # ------------------------------------------------------------------
    def is_content_node(self, node: ShadowNode) -> bool:
        """
        Determine if a node itself carries content (ignoring children).
        Returns True if the node has:
          - non‑empty visible text (node.text or node.tail), or
          - at least one URL in any of its attributes (agnostic detection), or
          - is a media container/element, or
          - is interactive (button‑like, input‑like), or
          - has a content‑bearing attribute like alt/title/aria-label.
        """
        tag = node.tag.lower()
        if tag.startswith("#") or tag in SKIP_TAGS:
            return False

        # 1. Visible text (own text or tail)
        if node.text and node.text.strip():
            return True
        if node.tail and node.tail.strip():
            return True

        # 2. URLs in any attribute (agnostic)
        if AgnosticAttr.urls_from_node(node):
            return True

        # 3. Media elements / containers
        if AgnosticAttr.primary_media_key(node):
            return True
        if tag in ('img', 'video', 'audio', 'source', 'picture'):
            return True

        # 4. Interactive elements
        if AgnosticAttr.is_button_like(node):
            return True
        if AgnosticAttr.is_input_like(node):
            return True
        if AgnosticAttr.is_heading_like(node):
            return True

        # 5. Specific content‑bearing attributes (even without URLs)
        for key, val in node.attributes.items():
            kl = key.lower()
            if kl in ('alt', 'title', 'aria-label', 'placeholder', 'value'):
                if val and isinstance(val, str) and val.strip():
                    return True

        return False

    # ------------------------------------------------------------------
    # Keep‑set computation (post‑order)
    # ------------------------------------------------------------------
    def compute_keep_set(self) -> Set[int]:
        """Mark nodes that are contentful themselves or have contentful descendants."""
        keep = set()

        def _dfs(node: ShadowNode) -> bool:
            any_child_kept = False
            for child in node.get_children(include_shadow=True):
                if _dfs(child):
                    any_child_kept = True

            self_contentful = self.is_content_node(node)

            if self_contentful or any_child_kept:
                keep.add(id(node))
                return True
            return False

        _dfs(self.dom.root)
        return keep

    # ------------------------------------------------------------------
    # HTML rendering with intelligent attribute filtering
    # ------------------------------------------------------------------
    def render_node(self, node: ShadowNode, keep_set: Set[int], indent: int = 0) -> str:
        """Recursively render a kept node and its kept children."""
        if id(node) not in keep_set:
            return ""
        if node.tag.startswith("#"):
            return ""

        # Filter attributes: keep if in ALWAYS_KEEP_ATTRS or if value contains a URL
        attrs = []
        for key, val in node.attributes.items():
            kl = key.lower()
            if kl in ALWAYS_KEEP_ATTRS:
                # Always keep these (they are either structural or important content)
                attrs.append(f'{key}="{val}"')
                continue
            # Otherwise, check if the value looks like a URL (agnostic)
            if isinstance(val, str) and AgnosticAttr.is_url(val.strip()):
                attrs.append(f'{key}="{val}"')
                # Also keep the attribute if it's a media source candidate
            elif kl in ('srcset', 'data-src', 'data-lazy-src', 'data-original'):
                # These often contain URLs even if the value isn't a simple URL
                # We'll keep them unconditionally
                attrs.append(f'{key}="{val}"')
            # Optionally, keep attributes that tokenize to meaningful words? Not implemented.

        attr_str = " ".join(attrs)
        opening = f"<{node.tag} {attr_str}>" if attr_str else f"<{node.tag}>"

        if node.tag.lower() in VOID_ELEMENTS:
            return opening

        children_html = []
        for child in node.get_children(include_shadow=True):
            child_html = self.render_node(child, keep_set, indent + 1)
            if child_html:
                children_html.append(child_html)

        text_part = node.text or ""

        prefix = "  " * indent
        if not children_html and not text_part:
            return f"{prefix}{opening}</{node.tag}>"
        parts = [f"{prefix}{opening}"]
        if text_part:
            parts.append(f"{'  ' * (indent + 1)}{text_part}")
        parts.extend(children_html)
        parts.append(f"{prefix}</{node.tag}>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def distill(self) -> str:
        """Generate a cleaned HTML string containing all content‑bearing nodes."""
        self.keep_set = self.compute_keep_set()
        root = self.dom.root

        # Try to locate the <html> element
        html_elem = None
        for child in root.get_children():
            if child.tag.lower() == "html" and not child.tag.startswith("#"):
                html_elem = child
                break

        if html_elem:
            return self.render_node(html_elem, self.keep_set)
        else:
            # Fallback: render all top‑level element children
            fragments = []
            for child in root.get_children():
                if not child.tag.startswith("#"):
                    child_html = self.render_node(child, self.keep_set)
                    if child_html:
                        fragments.append(child_html)
            return "\n".join(fragments)

    def save(self, filepath: str) -> None:
        """Write the distilled HTML to a file."""
        html = self.distill()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)


# ----------------------------------------------------------------------
# Command‑line entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_content_distiller.py <html_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "distilled.html"

    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        html_content = f.read()

    distiller = EnhancedContentDistiller(html_content)
    distiller.save(output_file)
    print(f"Distilled HTML saved to {output_file}")