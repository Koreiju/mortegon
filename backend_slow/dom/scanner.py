"""
scanner.py — Pure DOM scanner with merge-tree deduplication.

Extracts the full shadow DOM from a live Selenium WebDriver session,
incrementally merges snapshots into a master tree via structural
signature dedup, and returns the final complete HTML string.

Merge-tree approach (ported from dom_deep_serializer backup):
  - Additive merging: new children are appended, existing recursed into
  - No subtree pruning — full DOM structure is preserved
  - Signatures based on tag + id + key attributes + text prefix

This module has NO database, layout, or GUI dependencies.
It is a pure scan → merge → serialize pipeline.
"""

from __future__ import annotations

import time
import json
import logging
from typing import Optional, Set, Callable, Tuple, List, Dict, Iterator
from copy import deepcopy

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JavaScript: MutationObserver-based DOM settle detection.
#
# Installed once per page load.  The observer watches the entire subtree for
# childList mutations (content injection).  When a mutation fires it clears
# the "ready" flag and arms a 200 ms debounce timer; when the timer fires
# without further mutations the flag is reset to true.
#
# This is strictly faster than polling scrollHeight because:
#   - It resolves as soon as DOM mutations stop (≈200 ms after last injection)
#     rather than needing a fixed stable-window measured at coarse intervals.
#   - No-content scrolls (already at bottom, nothing new) resolve immediately
#     after a single poll, whereas scrollHeight polling always burns the full
#     stable_for window.
# ---------------------------------------------------------------------------
INSTALL_OBSERVER_JS = """
(function() {
    if (window._wfhMO) return;
    window._wfhMOReady = true;
    window._wfhMOTimer = null;
    window._wfhMO = new MutationObserver(function() {
        window._wfhMOReady = false;
        if (window._wfhMOTimer) clearTimeout(window._wfhMOTimer);
        window._wfhMOTimer = setTimeout(function() {
            window._wfhMOReady = true;
        }, 200);
    });
    var target = document.body || document.documentElement;
    if (target) window._wfhMO.observe(target, {childList: true, subtree: true});
})();
"""

# Returns true only when the observer exists AND has been quiet for 200 ms.
CHECK_OBSERVER_JS = "return !!(window._wfhMO) && window._wfhMOReady !== false;"

# ---------------------------------------------------------------------------
# JavaScript: extract current DOM state as JSON (including Shadow Roots)
# ---------------------------------------------------------------------------
EXTRACT_DOM_JSON_JS = """
function extract(node, depth) {
    if (!node || depth > 100) return null;
    depth = depth || 0;

    var obj = { nodeType: node.nodeType, nodeName: node.nodeName };
    var selfText = '';

    if (node.nodeType === Node.ELEMENT_NODE) {
        var tag = node.tagName.toLowerCase();

        // Skip non-content containers up-front.
        // - <head>: link/meta/title — no scannable content.
        // - <style>: CSS blobs can be megabytes; never content.
        // - <script>: JS source same; keep only JSON-LD data schemas.
            if (tag === 'head' || tag === 'style') return null;
            if (tag === 'script') {
            var t = (node.getAttribute('type') || '').toLowerCase();
            if (t.indexOf('json') < 0) return null;
        }

        obj.tagName = tag;
        if (node.id) obj.id = node.id;
        if (node.className && typeof node.className === 'string')
            obj.className = node.className;

        if (node.attributes.length > 0) {
            obj.attributes = {};
            for (var i = 0; i < node.attributes.length; i++) {
                var attr = node.attributes[i];
                obj.attributes[attr.name] = attr.value;
            }
        }

        if (node.shadowRoot) {
            var srChildren = [];
            var srNodes = node.shadowRoot.childNodes;
            for (var i = 0; i < srNodes.length; i++) {
                var res = extract(srNodes[i], depth + 1);
                if (res) {
                    srChildren.push(res.obj);
                    // Accumulate text only until the 500-char budget is met.
                    if (selfText.length < 500) selfText += res.text;
                }
            }
            obj.shadowRoot = {
                mode: node.shadowRoot.mode,
                children: srChildren
            };
        }

        var children = [];
        var childNodes = node.childNodes;
        for (var i = 0; i < childNodes.length; i++) {
            var res = extract(childNodes[i], depth + 1);
            if (res) {
                children.push(res.obj);
                if (selfText.length < 500) {
                    var room = 500 - selfText.length;
                    selfText += res.text.length > room ? res.text.substring(0, room) : res.text;
                }
            }
        }
        if (children.length > 0) obj.children = children;

        if (selfText.trim()) {
            var hash = 0;
            var limit = selfText.length < 500 ? selfText.length : 500;
            for (var i = 0; i < limit; i++) {
                hash = ((hash << 5) - hash) + selfText.charCodeAt(i);
                hash |= 0;
            }
            if (!obj.attributes) obj.attributes = {};
            obj.attributes['data-content-hash'] = hash.toString(16);
        }
    }
    else if (node.nodeType === Node.TEXT_NODE) {
        obj.textContent = node.textContent;
        if (!obj.textContent.trim()) return null;
        selfText = obj.textContent.length > 500
            ? obj.textContent.substring(0, 500) : obj.textContent;
    }
    else if (node.nodeType === Node.DOCUMENT_TYPE_NODE) {
        // Keep DOCTYPE so serialize_to_html can emit <!DOCTYPE html>.
        obj.name = node.name;
    }
    else {
        // COMMENT_NODE and anything else: no scannable content, skip.
        return null;
    }

    return { obj: obj, text: selfText };
}
var rootRes = extract(document.documentElement);
return rootRes ? JSON.stringify(rootRes.obj) : null;
"""


# ---------------------------------------------------------------------------
# Signature computation (matches backup architecture)
# ---------------------------------------------------------------------------

def compute_node_signature(node: dict) -> str:
    """
    Deterministic identity for a DOM node.

    Uses tag + id + key attributes (href, src, data-id, data-index,
    aria-label) + text content prefix for text nodes.
    """
    if not node:
        return ''

    if '_node_sig' in node:
        return node['_node_sig']

    tag = node.get('tagName', node.get('nodeName', ''))
    parts = [tag]

    if 'id' in node:
        parts.append(f"id:{node['id']}")

    # REMOVED: className. Classes change dynamically in SPAs (hover, focus, lazy-load)
    # which causes the node to be appended as a duplicate sibling instead of merged cleanly.

    attrs = node.get('attributes')
    if attrs:
        for key in ('href', 'src', 'data-id', 'data-index', 'name', 'type', 'role'):
            if key in attrs:
                parts.append(f"{key}:{str(attrs[key])[:50]}")

        # ADDED: data-content-hash. Strictly prevents Frankenstein merging of recycled DOM nodes 
        # in virtualized lists by binding structural identity to actual content state. 
        # Excluded from high-level skeletons to prevent entire-page ancestor duplication.
        if tag.lower() not in ('html', 'body', 'head', 'main', '#document', 'header', 'footer', 'nav'):
            ch = attrs.get('data-content-hash')
            if ch:
                parts.append(f"ch:{ch}")

    if node.get('nodeType') == 3:  # Text node
        text = ' '.join((node.get('textContent') or '').split())
        if text:
            parts.append(f"txt:{text[:30]}")

    sig = '|'.join(parts)
    node['_node_sig'] = sig
    return sig


# ---------------------------------------------------------------------------
# Tree utilities
# ---------------------------------------------------------------------------

def count_nodes(node: dict) -> int:
    """Count total nodes in a JSON DOM tree."""
    if not node:
        return 0
    total = 1
    for child in node.get('children', []):
        total += count_nodes(child)
    shadow = node.get('shadowRoot')
    if shadow:
        for s_child in shadow.get('children', []):
            total += count_nodes(s_child)
    return total


def serialize_to_html(node: dict) -> str:
    """
    Convert a JSON DOM tree back to an HTML string with
    declarative shadow DOM (<template shadowrootmode>).
    """
    parts = []
    _serialize_node(node, parts)
    return "".join(parts)

def _serialize_node(node: dict, parts: list) -> None:
    if not node:
        return

    node_type = node.get('nodeType', 0)

    # Text
    if node_type == 3:
        text = node.get('textContent', '')
        parts.append(text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        return

    # Comment
    if node_type == 8:
        parts.append(f"<!--{node.get('nodeValue', '')}-->")
        return

    # Doctype
    if node_type == 10:
        parts.append(f"<!DOCTYPE {node.get('name', 'html')}>")
        return

    # Element
    if node_type == 1:
        tag = node.get('tagName', 'div')
        parts.append(f"<{tag}")

        attrs = node.get('attributes')
        if attrs:
            for k, v in attrs.items():
                parts.append(f' {k}="{str(v).replace(chr(34), "&quot;")}"')
        parts.append(">")

        # Void elements
        if tag in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                    'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'):
            return

        # Shadow DOM
        shadow = node.get('shadowRoot')
        if shadow:
            mode = shadow.get('mode', 'open')
            parts.append(f'<template shadowrootmode="{mode}">')
            for child in shadow.get('children', []):
                _serialize_node(child, parts)
            parts.append('</template>')

        # Light DOM children
        for child in node.get('children', []):
            _serialize_node(child, parts)

        parts.append(f"</{tag}>")


# ---------------------------------------------------------------------------
# Core scanner — merge-tree architecture
# ---------------------------------------------------------------------------

class ShadowDOMScanner:
    """
    Pure DOM scanner using merge-tree deduplication.

    Instead of pruning seen subtrees (which causes truncation), we
    accumulate ALL content into a master tree via additive merging.
    This preserves the full DOM structure across scroll positions.

    No database, no layout, no GUI dependencies.

    Usage:
        scanner = ShadowDOMScanner(driver)
        html = scanner.scan('https://example.com', max_duration=60)
        # html is the fully merged, complete DOM as an HTML string
    """

    # Termination tuning -----------------------------------------------
    #
    # Two consecutive quiet iterations are enough to confirm the page has
    # no more lazy content — the legacy three-iteration limit was defensive
    # against slow React hydration, but with MutationObserver settling we
    # already wait until the DOM is truly quiescent before each capture,
    # so a second quiet iteration is genuine signal not noise.
    NO_CHANGE_LIMIT: int = 2

    # MutationObserver-based settling: wait at most SETTLE_TIMEOUT seconds
    # for the observer's 200 ms debounce to fire.  SETTLE_STABLE_FOR is only
    # used by the scrollHeight fallback path (observer unavailable).
    SETTLE_TIMEOUT: float = 2.0
    SETTLE_STABLE_FOR: float = 0.25
    # Poll cadence for both the observer check and the scrollHeight fallback.
    POLL_INTERVAL: float = 0.05
    MAX_SCROLLS: int = 60
    # Scroll step as a fraction of viewport height. A small step keeps content
    # in view long enough for lazy-load hooks (IntersectionObserver, infinite
    # scroll shims) to fire and for the next batch of tiles to render before
    # we move on. A full-viewport jump outran slow feeds and caused the
    # scanner to miss rows on pages with expensive row hydration.
    SCROLL_STEP_FRACTION: float = 0.4

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.master_tree: Optional[dict] = None
        self._changes_detected: bool = False
        self._added_nodes: list = []
        self._sig_cache: dict = {}

    def scan(self, url: str, max_duration: int = 60, pause: float = 3.0) -> Iterator[Tuple[dict, list]]:
        """
        Scan a URL, scrolling and merging incrementally.

        Args:
            url: Target URL to scan.
            max_duration: Max seconds to run the scroll loop.
            pause: Render-slack sleep after each scroll (seconds).  Gives the
                   browser time to respond to the scroll event and dispatch any
                   IntersectionObserver / async fetch before the MutationObserver
                   settle check begins.  0.3 s is sufficient for CDN-delivered
                   content; increase to 0.5–1.0 for very slow networks.

        Returns:
            Yields (master_tree, added_nodes) at each step.
        """
        # Navigate (skip if already there)
        try:
            current = self.driver.current_url
        except Exception as e:
            logger.warning(f"Failed to get current URL (window closed?): {e}")
            try:
                handles = self.driver.window_handles
                if handles:
                    self.driver.switch_to.window(handles[0])
                    current = self.driver.current_url
                else:
                    logger.error("No windows available.")
                    return
            except Exception as inner_e:
                logger.error(f"Cannot recover driver window: {inner_e}")
                return

        if current != url and current != url + '/':
            logger.info(f"Navigating to {url}")
            try:
                self.driver.get(url)
            except Exception as e:
                logger.error(f"Failed to navigate to {url}: {e}")
                return
        else:
            logger.info(f"Already on {url}")

        # Wait for page load
        try:
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        except Exception:
            logger.warning("Page load timeout, proceeding anyway.")

        # Install the MutationObserver used by _wait_for_dom_settled().
        # Must run after the page has loaded so document.body exists.
        self._install_dom_observer()

        # readyState='complete' fires before most SPAs finish hydrating.
        # Give the framework one render-cycle before watching for mutations.
        time.sleep(0.15)
        self._wait_for_dom_settled(timeout=self.SETTLE_TIMEOUT)

        # Initial capture → becomes the master tree
        self.master_tree = self._capture()
        initial_count = count_nodes(self.master_tree)
        logger.info(f"Initial snapshot: {initial_count} nodes")

        yield self.master_tree, [self.master_tree]

        # Scroll + merge loop
        start = time.time()
        iteration = 0
        no_change_streak = 0

        while time.time() - start < max_duration:
            if iteration >= self.MAX_SCROLLS:
                logger.info(f"Iter {iteration}: reached MAX_SCROLLS limit ({self.MAX_SCROLLS}). Stopping scan.")
                break
                
            iteration += 1
            self._scroll(pause)

            snapshot = self._capture()

            # Reset change flag and added nodes, merge new snapshot into master
            self._changes_detected = False
            self._added_nodes = []
            self._sig_cache.clear()
            self._merge_trees(self.master_tree, snapshot)

            if self._changes_detected:
                logger.info(
                    "Iter %d: merged %d new node(s)",
                    iteration, len(self._added_nodes),
                )
                no_change_streak = 0
                yield self.master_tree, self._added_nodes
                continue

            # No merge-observed changes this iteration.
            no_change_streak += 1
            logger.info(
                f"Iter {iteration}: no new content "
                f"({no_change_streak}/{self.NO_CHANGE_LIMIT})."
            )

            # NOTE: no blind bottom-jump here. The per-iteration
            # progressive scroll + ``_try_click_load_more`` is the only
            # advancement mechanism. A late ``scrollTo(body.scrollHeight)``
            # was previously fired after two quiet iterations to flush
            # footer lazy loads, but on virtualized lists it recycled
            # mid-page rows before we'd captured them and on long SPAs
            # it caused visible, jarring teleports to the page bottom.
            # We rely purely on the steady viewport-sized scrollBy
            # progression instead.

            if no_change_streak >= self.NO_CHANGE_LIMIT:
                logger.info(
                    f"Iter {iteration}: {self.NO_CHANGE_LIMIT} quiet iterations. "
                    f"Stopping scan."
                )
                break

    def scan_single(self, url: str) -> Tuple[str, dict]:
        """
        Single-pass scan: capture and serialize. No scrolling, but we
        still wait for the DOM to stop growing so the capture includes
        any hydration / lazy loads that complete between
        ``readyState=='complete'`` and the first frame being stable.

        Returns:
            (html_string, raw_tree_dict)
        """
        try:
            current = self.driver.current_url
        except Exception:
            try:
                handles = self.driver.window_handles
                if handles:
                    self.driver.switch_to.window(handles[0])
                    current = self.driver.current_url
                else:
                    return "", {}
            except Exception:
                return "", {}
                
        if current != url and current != url + '/':
            try:
                self.driver.get(url)
            except Exception:
                pass

        try:
            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        except Exception:
            pass

        self._install_dom_observer()
        time.sleep(0.15)
        self._wait_for_dom_settled(timeout=self.SETTLE_TIMEOUT)
        self.master_tree = self._capture()
        html = serialize_to_html(self.master_tree)
        return html, self.master_tree

    # ------------------------------------------------------------------
    # Merge-tree deduplication (ported from dom_deep_serializer backup)
    # ------------------------------------------------------------------

    def _merge_trees(self, target: dict, source: dict) -> None:
        """Recursively merge source nodes into the target master tree."""
        if not target or not source:
            return

        # Early exit: source is a leaf — no children to contribute to target.
        # This avoids the dict key lookups and list checks below for the
        # majority of nodes that appear at the bottom of the trie.
        if 'shadowRoot' not in source and 'children' not in source:
            return

        # 1. Merge Shadow Root
        if 'shadowRoot' in source:
            if 'shadowRoot' not in target:
                target['shadowRoot'] = source['shadowRoot']
                self._changes_detected = True
                self._added_nodes.append(target['shadowRoot'])
            else:
                self._merge_child_lists(
                    target['shadowRoot'].setdefault('children', []),
                    source['shadowRoot'].get('children', [])
                )

        # 2. Merge Light DOM Children
        if 'children' in source:
            if 'children' not in target:
                target['children'] = source['children']
                self._changes_detected = True
                self._added_nodes.extend(target['children'])
            else:
                self._merge_child_lists(
                    target['children'],
                    source['children']
                )

    def _get_subtree_content_signatures(self, node: dict, depth=0) -> set:
        """Gather content-bearing signatures of direct children to establish structural identity.

        Depth is capped at 1 (direct children only).  Going 3 levels deep
        was the original design, but ``data-content-hash`` in the primary
        signature already handles recycled-item disambiguation for content
        nodes; for structural wrappers (which have no hash) looking at
        immediate children is sufficient to distinguish container types.
        The shallower limit also means stale cache entries from a previous
        iteration are far less likely to produce wrong merge decisions.
        """
        if depth > 1:
            return set()
            
        node_id = id(node)
        if node_id in self._sig_cache:
            return self._sig_cache[node_id]
            
        sigs = set()
        sig = compute_node_signature(node)
        if ':' in sig and not sig.startswith('id:'):
            sigs.add(sig)
        for c in node.get('children', []):
            sigs.update(self._get_subtree_content_signatures(c, depth+1))
        shadow = node.get('shadowRoot')
        if shadow:
            for c in shadow.get('children', []):
                sigs.update(self._get_subtree_content_signatures(c, depth+1))
                
        self._sig_cache[node_id] = sigs
        return sigs

    def _should_merge(self, target_node: dict, src_node: dict) -> bool:
        """Determine if a matching signature is truly the same node, or a recycled virtualized item."""
        tag = target_node.get('tagName', target_node.get('nodeName', '')).lower()
        if tag in ('html', 'body', 'head', 'main', '#document', 'header', 'footer', 'nav'):
            return True
            
        t_sigs = self._get_subtree_content_signatures(target_node)
        s_sigs = self._get_subtree_content_signatures(src_node)
        
        if not t_sigs and not s_sigs:
            return True
        if not t_sigs or not s_sigs:
            return True
            
        intersection = t_sigs.intersection(s_sigs)
        t_ratio = len(intersection) / len(t_sigs)
        s_ratio = len(intersection) / len(s_sigs)
        
        # If they share almost no content signatures, they are conceptually different recycled items
        if t_ratio < 0.25 and s_ratio < 0.25:
            return False
        return True

    def _merge_child_lists(self, target_list: list, source_list: list) -> None:
        """Deduplicate and merge lists of children based on signatures."""
        # Build target signature index.  Use a separate counter dict so
        # duplicate signatures get distinct keys (sig_0, sig_1, …) without
        # the old O(dup²) while-loop membership probe.
        target_sigs: Dict[str, int] = {}
        target_sig_counts: Dict[str, int] = {}
        for i, node in enumerate(target_list):
            sig = compute_node_signature(node)
            count = target_sig_counts.get(sig, 0)
            target_sig_counts[sig] = count + 1
            target_sigs[f"{sig}_{count}"] = i

        source_counts: Dict[str, int] = {}

        for src_node in source_list:
            sig = compute_node_signature(src_node)
            count = source_counts.get(sig, 0)
            source_counts[sig] = count + 1

            sig_key = f"{sig}_{count}"

            if sig_key in target_sigs:
                target_node = target_list[target_sigs[sig_key]]
                if self._should_merge(target_node, src_node):
                    self._merge_trees(target_node, src_node)
                else:
                    target_list.append(src_node)
                    self._changes_detected = True
                    self._added_nodes.append(src_node)
            else:
                # Node is new — append it
                target_list.append(src_node)
                self._changes_detected = True
                self._added_nodes.append(src_node)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _capture(self) -> dict:
        """Execute JS extraction and parse the result."""
        raw = self.driver.execute_script(EXTRACT_DOM_JSON_JS)
        return json.loads(raw)

    def _scroll(self, pause: float) -> None:
        """Progressive, viewport-sized scroll with a real stabilization wait.

        The legacy serializer did two things per iteration that together
        caused content to be skipped:

        1. A viewport-sized ``scrollBy`` (fine, this progressively
           reveals items and triggers intersection-observer lazy loads).
        2. A blind ``window.scrollTo(0, document.body.scrollHeight)``
           jump to the bottom (aggressive; it skips past whatever the
           page was about to render at intermediate positions and, on
           virtualized lists, can recycle off-screen items before we've
           captured them).

        We keep #1 and drop #2 *entirely*. No bottom-jump runs per
        iteration and none runs later either — the steady progressive
        scroll is the only advancement mechanism. Footer-only lazy
        loads are reached the same way: the progressive scroll will
        eventually arrive at the bottom on its own, and the
        ``_try_click_load_more`` probe handles the "Load more" case.

        We also replace the legacy ``performance.getEntries().length > 0``
        "network idle" check — which is effectively always true after
        initial load — with a real ``scrollHeight`` stabilization wait.
        """
        # 1. Bite-sized step, container-aware for custom feeds. A fractional
        #    advance (rather than a full viewport) lets slow feeds hydrate
        #    the next row or two before we move on.
        self.driver.execute_script(
            """
            const frac = arguments[0];
            let container = document.querySelector('[data-testid="feedScrollView"]');
            if (container) {
                container.scrollBy(0, Math.max(40, container.clientHeight * frac));
            } else {
                window.scrollBy(0, Math.max(40, window.innerHeight * frac));
            }
            """,
            self.SCROLL_STEP_FRACTION,
        )

        # 2. Render-slack sleep: gives the browser time to respond to the
        #    scroll event and fire any IntersectionObserver / async fetch
        #    before the MutationObserver check begins.  The observer then
        #    waits for those fetched mutations to quiesce, so together these
        #    two steps replace the old fixed sleep + scrollHeight poll.
        time.sleep(pause)
        self._wait_for_dom_settled(timeout=self.SETTLE_TIMEOUT)

        # 3. Opportunistic "Load more" click — re-settle afterwards so the
        #    freshly injected rows land in the DOM before the next capture.
        self._try_click_load_more()

    def _try_click_load_more(self) -> None:
        """Click a visible Load/Show/See-more control if one exists."""
        try:
            # normalize-space() tolerates surrounding whitespace; text()
            # alone misses e.g. ``<button>  Load more  </button>``.
            xp = (
                "//*[self::button or self::a or self::span or self::div]"
                "[contains(normalize-space(.), 'Load more') "
                " or contains(normalize-space(.), 'Show more') "
                " or contains(normalize-space(.), 'See more')]"
            )
            candidates = self.driver.find_elements(By.XPATH, xp)
            for el in candidates:
                try:
                    if el.is_displayed() and el.is_enabled():
                        el.click()
                        logger.info("Clicked 'Load more' control.")
                        self._wait_for_dom_settled(timeout=self.SETTLE_TIMEOUT)
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def _install_dom_observer(self) -> None:
        """Install the MutationObserver used by _wait_for_dom_settled.

        Idempotent — the JS guard ``if (window._wfhMO) return`` makes
        repeated calls on the same page a no-op.  Safe to call after every
        page navigation; the previous observer is garbage-collected with the
        old document.
        """
        try:
            self.driver.execute_script(INSTALL_OBSERVER_JS)
        except Exception as exc:
            logger.debug("MutationObserver install failed (%s); "
                         "falling back to scrollHeight polling.", exc)

    def _wait_for_dom_settled(self, timeout: float = 2.0) -> None:
        """Block until the MutationObserver signals the DOM is quiescent.

        The observer's 200 ms debounce timer resets on every childList
        mutation, so this resolves as soon as content injection stops —
        typically much faster than the old scrollHeight-stable approach.

        Falls back to ``_wait_for_scroll_height_stable`` if the observer is
        not available (e.g. page navigated before install, or JS disabled).
        """
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(self.POLL_INTERVAL)
            try:
                if self.driver.execute_script(CHECK_OBSERVER_JS):
                    return
            except Exception:
                # Observer unavailable — degrade gracefully.
                remaining = max(0.1, timeout - (time.time() - start))
                self._wait_for_scroll_height_stable(
                    timeout=remaining,
                    stable_for=self.SETTLE_STABLE_FOR,
                )
                return
        # Timeout: DOM still mutating (live feed / animation) — proceed.

    def _wait_for_scroll_height_stable(
        self,
        timeout: float = 2.0,
        stable_for: float = 0.25,
        poll_interval: float = None,
    ) -> None:
        """Fallback settler: block until scrollHeight stops growing.

        Used when the MutationObserver is unavailable.  Prefer
        ``_wait_for_dom_settled`` for the primary settle path.
        """
        poll_interval = poll_interval if poll_interval is not None else self.POLL_INTERVAL
        start = time.time()
        try:
            last_h = self.driver.execute_script(
                "return document.documentElement.scrollHeight"
            )
        except Exception:
            return
        last_change = time.time()
        while time.time() - start < timeout:
            time.sleep(poll_interval)
            try:
                h = self.driver.execute_script(
                    "return document.documentElement.scrollHeight"
                )
            except Exception:
                return
            if h != last_h:
                last_h = h
                last_change = time.time()
                continue
            if time.time() - last_change >= stable_for:
                return
