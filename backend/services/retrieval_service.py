"""
retrieval_service.py — on-demand retrieval decoupled from the scan pipeline.

Supports three query modes against the current distilled-DOM state:

  * text only                → substring search on content-bearing nodes
  * xpaths only              → enumerate content nodes under selected
                               generalized xpaths (trie-driven retrieval)
  * text + xpaths             → substring search filtered by structural
                               union (keep results whose generalized xpath
                               descends from any selected xpath)

This service never touches the scanner. It reads the latest snapshot state
from the distilled-DOM bus, and delegates DOM text resolution to the mapper
which caches per-URL DOMs. Running a retrieval query does not block nor
influence an in-flight scan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

from backend.services.distilled_dom_bus import (
    DistilledDomBus,
    DistilledSnapshotState,
    get_distilled_dom_bus,
)
from backend.services.xpath_utils import generalize_xpath

logger = logging.getLogger(__name__)


def _is_descendant_pattern(candidate: str, ancestor: str) -> bool:
    """True iff `candidate` is `ancestor` or a descendant in generalized-xpath
    space. Comparison is segment-boundary aware: `/html/body/div` is an
    ancestor of `/html/body/div/ul` but not of `/html/body/divider`.
    """
    if not ancestor:
        return True
    if candidate == ancestor:
        return True
    return candidate.startswith(ancestor + "/")


def _collect_content_nodes(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Walk the distilled tree and return [{xpath, categories}] for every
    content-bearing node. `_xpath` on each subtree is already the full
    absolute xpath after `resolve_tree_xpaths`.
    """
    out: List[Dict[str, Any]] = []

    def walk(sub: Dict[str, Any]) -> None:
        for key, child in sub.items():
            if key.startswith("_") or not isinstance(child, dict):
                continue
            xp = child.get("_xpath", key)
            categories = child.get("_content") or []
            if categories:
                out.append({"xpath": xp, "categories": list(categories)})
            walk(child)

    walk(tree)
    return out


@dataclass
class RetrievalQuery:
    snapshot_id: str
    query: Optional[str] = None
    generalized_xpaths: Sequence[str] = ()
    limit: int = 50


@dataclass
class RetrievalResponse:
    snapshot_id: str
    revision: int
    url: str
    query: Optional[str]
    selected_generalized_xpaths: List[str]
    results: List[Dict[str, Any]]
    matched_generalized_xpaths: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "revision": self.revision,
            "url": self.url,
            "query": self.query,
            "selected_generalized_xpaths": self.selected_generalized_xpaths,
            "results": self.results,
            "matched_generalized_xpaths": self.matched_generalized_xpaths,
        }


# A text-search callable: (url, query, snapshot_id, limit) -> list[result dict]
# Each result dict must carry `xpath`, and should carry `generalized_xpath`,
# `tag`, `snippet`, `categories`, `score`. The route wires `mapper.search_dom_text`.
TextSearchFn = Callable[[str, str, Optional[str], int], List[Dict[str, Any]]]


class RetrievalService:
    def __init__(self, bus: Optional[DistilledDomBus] = None,
                 text_search: Optional[TextSearchFn] = None) -> None:
        self.bus = bus or get_distilled_dom_bus()
        self._text_search = text_search

    def set_text_search(self, fn: TextSearchFn) -> None:
        self._text_search = fn

    # -- public API --------------------------------------------------

    def query(self, q: RetrievalQuery) -> RetrievalResponse:
        state = self.bus.get(q.snapshot_id)
        if state is None:
            return RetrievalResponse(
                snapshot_id=q.snapshot_id, revision=0, url="",
                query=q.query, selected_generalized_xpaths=list(q.generalized_xpaths),
                results=[], matched_generalized_xpaths=[],
            )

        selected = [gx for gx in q.generalized_xpaths if gx]
        has_text = bool(q.query and q.query.strip())

        if has_text:
            results = self._text_mode(state, q.query.strip(), q.limit)
            if selected:
                results = [
                    r for r in results
                    if self._result_under_any(r, selected)
                ]
        elif selected:
            results = self._xpath_only_mode(state, selected, q.limit)
        else:
            results = []

        matched = sorted({
            r.get("generalized_xpath") or generalize_xpath(r["xpath"])
            for r in results if r.get("xpath")
        })

        return RetrievalResponse(
            snapshot_id=q.snapshot_id,
            revision=state.revision,
            url=state.url,
            query=q.query if has_text else None,
            selected_generalized_xpaths=selected,
            results=results[: q.limit],
            matched_generalized_xpaths=matched,
        )

    # -- modes -------------------------------------------------------

    def _text_mode(self, state: DistilledSnapshotState, query: str,
                   limit: int) -> List[Dict[str, Any]]:
        if self._text_search is None:
            logger.warning("[RetrievalService] text_search not configured")
            return []
        try:
            raw = self._text_search(state.url, query, state.snapshot_id, limit)
        except Exception as e:
            logger.error(f"[RetrievalService] text_search failed: {e}", exc_info=True)
            return []

        for r in raw:
            if "generalized_xpath" not in r and r.get("xpath"):
                r["generalized_xpath"] = generalize_xpath(r["xpath"])
        return raw

    def _xpath_only_mode(self, state: DistilledSnapshotState,
                         selected: Sequence[str],
                         limit: int) -> List[Dict[str, Any]]:
        """Return every content-bearing distilled node whose generalized
        xpath descends from any selected xpath. No text query → score is
        constant; order is DFS (tree order)."""
        content_nodes = _collect_content_nodes(state.tree or {})
        selected_set: List[str] = list(selected)

        results: List[Dict[str, Any]] = []
        for node in content_nodes:
            xp = node["xpath"]
            gxp = generalize_xpath(xp)
            if not any(_is_descendant_pattern(gxp, sel) for sel in selected_set):
                continue
            results.append({
                "id": f"{state.url}:{xp}",
                "xpath": xp,
                "generalized_xpath": gxp,
                "categories": node["categories"],
                "score": 1.0,
                "is_content": True,
                "snippet": "",
                "url": state.url,
                "source": "trie_selection",
            })
            if len(results) >= limit:
                break
        return results

    # -- filtering ---------------------------------------------------

    @staticmethod
    def _result_under_any(result: Dict[str, Any],
                          selected: Sequence[str]) -> bool:
        gxp = result.get("generalized_xpath")
        if not gxp and result.get("xpath"):
            gxp = generalize_xpath(result["xpath"])
        if not gxp:
            return False
        return any(_is_descendant_pattern(gxp, sel) for sel in selected)


# Module singleton -----------------------------------------------------

_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    global _service
    if _service is None:
        _service = RetrievalService()
    return _service
