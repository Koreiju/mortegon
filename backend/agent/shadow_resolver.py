"""
shadow_resolver.py — Phase 5 bridge from trie-space to live Selenium.

The Patricia trie collapses every repeating structure into a single
``TriePattern`` keyed on the generalized xpath. At action time the agent
knows which pattern it wants to touch, but it still needs a concrete
indexed xpath to hand to Selenium. That translation is what this module
owns.

Resolution order
----------------

1. ``PatternRow.member_xpaths`` — if the trie was built with the Phase 5
   member-xpath patch (Phase-3/4 handoff §5 gotcha #6 resolved), the
   concrete xpaths for every pattern live right on the row.
2. ``ShadowDOM.iter_all`` — fallback path for tries loaded from older
   rows without ``member_xpaths``. We walk the live DOM, generalize each
   xpath, and pick the ones that match.
3. ``BuiltTrie`` (in-memory only) — last resort: reconstruct from the
   chunks a pipeline run just produced.

This class is deliberately small. All "what should I click" logic lives
in the cognition node of ``langgraph_loop.py``; ``ShadowResolver`` only
knows how to turn pattern_id + index into a Selenium call.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.dom.shadow_html_parser import ShadowDOM, get_absolute_xpath
from backend.dom.trie_persistence import BuiltTrie, PatternRow
from backend.services.xpath_utils import generalize_xpath

logger = logging.getLogger(__name__)


class ShadowResolverError(RuntimeError):
    """Raised when a pattern has no live xpath or the click/fill fails."""


class ShadowResolver:
    """
    Translate ``pattern_id + index`` into a live Selenium interaction.

    Parameters
    ----------
    driver
        A Selenium WebDriver (or a duck-typed stub in tests).
    dom
        The ``ShadowDOM`` from the last pipeline run, used as a fallback
        when ``member_xpaths`` isn't present on pattern rows.
    built
        The ``BuiltTrie`` that corresponds to the driver's current page.
        Pattern lookups go through ``built.by_pattern_id``.
    """

    def __init__(self, driver: Any, dom: Optional[ShadowDOM], built: BuiltTrie):
        self.driver = driver
        self.dom = dom
        self.built = built
        self._pattern_xpaths_cache: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def xpaths_for_pattern(self, pattern_id: str) -> List[str]:
        """All concrete indexed xpaths matching the generalized pattern."""
        if pattern_id in self._pattern_xpaths_cache:
            return self._pattern_xpaths_cache[pattern_id]

        row = self.built.by_pattern_id.get(pattern_id)
        if row is None:
            raise ShadowResolverError(f"Unknown pattern_id {pattern_id!r}")

        xpaths: List[str] = []

        # 1. Trust the persisted member_xpaths.
        if row.member_xpaths:
            xpaths = list(row.member_xpaths)
        else:
            # 2. Rebuild from the DOM if we have one.
            xpaths = self._rebuild_from_dom(row)

        # Deduplicate while keeping the DOM order where possible.
        seen: set = set()
        deduped: List[str] = []
        for xp in xpaths:
            if xp in seen:
                continue
            seen.add(xp)
            deduped.append(xp)

        self._pattern_xpaths_cache[pattern_id] = deduped
        return deduped

    def representative_xpath(self, pattern_id: str) -> str:
        """Pick the first xpath for a pattern, or raise if none exist."""
        xps = self.xpaths_for_pattern(pattern_id)
        if not xps:
            raise ShadowResolverError(
                f"No live xpaths for pattern_id {pattern_id!r}; "
                f"the DOM may have shifted since the scan."
            )
        return xps[0]

    def click(self, pattern_id: str, index: int = 0) -> str:
        """Click the ``index``-th instance of ``pattern_id``; return the xpath.

        Raises ``ShadowResolverError`` if the pattern has no live instance
        or Selenium cannot find / click the element.
        """
        xp = self._pick(pattern_id, index)
        self._perform_click(xp)
        return xp

    def fill(self, pattern_id: str, value: str, index: int = 0) -> str:
        """Focus the input and type ``value``. Returns the xpath used."""
        xp = self._pick(pattern_id, index)
        self._perform_fill(xp, value)
        return xp

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _pick(self, pattern_id: str, index: int) -> str:
        xps = self.xpaths_for_pattern(pattern_id)
        if not xps:
            raise ShadowResolverError(
                f"No concrete xpaths for pattern_id {pattern_id!r}"
            )
        if index < 0 or index >= len(xps):
            raise ShadowResolverError(
                f"index {index} out of range for pattern {pattern_id} "
                f"(has {len(xps)} instances)"
            )
        return xps[index]

    def _rebuild_from_dom(self, row: PatternRow) -> List[str]:
        """Walk ``self.dom`` and collect xpaths that generalize to ``row.pattern``."""
        if self.dom is None:
            return [row.representative_xpath] if row.representative_xpath else []

        target = row.pattern
        out: List[str] = []
        try:
            for node in self.dom.iter_all():
                try:
                    xp = get_absolute_xpath(node)
                except Exception:
                    continue
                if xp and generalize_xpath(xp) == target:
                    out.append(xp)
        except Exception:
            logger.debug("shadow rebuild failed for pattern %r", target, exc_info=True)

        if not out and row.representative_xpath:
            out.append(row.representative_xpath)
        return out

    def _perform_click(self, xpath: str) -> None:
        """Actual Selenium click; catches the usual WebDriver exceptions."""
        try:
            # Import here so the module loads in CI without selenium installed.
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import WebDriverException
        except ImportError:
            By = None
            WebDriverException = Exception

        try:
            if By is not None:
                element = self.driver.find_element(By.XPATH, xpath)
            else:
                element = self.driver.find_element("xpath", xpath)
            element.click()
        except Exception as exc:  # WebDriverException or stub error
            raise ShadowResolverError(
                f"Click on {xpath!r} failed: {exc}"
            ) from exc

    def _perform_fill(self, xpath: str, value: str) -> None:
        try:
            from selenium.webdriver.common.by import By
        except ImportError:
            By = None
        try:
            if By is not None:
                element = self.driver.find_element(By.XPATH, xpath)
            else:
                element = self.driver.find_element("xpath", xpath)
            element.clear()
            element.send_keys(value)
        except Exception as exc:
            raise ShadowResolverError(
                f"Fill on {xpath!r} failed: {exc}"
            ) from exc
