"""
signal_fields.py — Site-wide search + pagination detection, adapted
from :mod:`backend.dom.web_distiller_freq`.

Two specialized field types live outside the generic trie/chunk
pipeline because they're *cross-URL* anchors rather than per-instance
content:

* **SearchInputField** — any ``<input>`` / ``role="searchbox"``-like
  element that the agent should treat as the site's primary search box.
* **PaginationField** — any button/link whose text or attribute tokens
  identify it as next/prev/page/load-more.

Tracking
--------
Per the design call in the plan, coalesce on
``(domain, generalized_xpath)``. Repeat scans of the same site update
``last_seen`` rather than inserting a new row. The ``last_seen_url`` /
``last_seen_absolute_xpath`` columns record the most recent instance we
saw, so agents can still point at a live target.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from backend.dom.shadow_html_parser import ShadowDOM, ShadowNode, get_absolute_xpath
from backend.services.xpath_utils import generalize_xpath

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Row dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SignalFieldRow:
    """Shared shape for SearchInputField / PaginationField rows."""

    field_id: str
    domain: str
    generalized_xpath: str
    last_seen_url: str
    last_seen_absolute_xpath: str
    tag: str
    text_hint: str
    attributes_json: str
    score: int
    first_seen: str
    last_seen: str


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _domain_of(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        return host.lower()
    except Exception:
        return url


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _text_hint(node: ShadowNode) -> str:
    """Short, human-readable hint for a field — used in dedup + UI.

    Prefers explicit labels: ``aria-label``, ``placeholder``, ``title``,
    ``alt``, and lastly the visible text. Capped at 120 chars.
    """
    for attr in ("aria-label", "placeholder", "title", "alt", "name"):
        v = (node.get_attr(attr) or "").strip()
        if v:
            return v[:120]
    visible = (node.get_text() or "").strip()
    return visible[:120]


def _attributes_snapshot(node: ShadowNode) -> Dict[str, str]:
    """Pick the top ~6 discriminative attributes for forensics."""
    keep = {}
    for k, v in node.attributes.items():
        if not v:
            continue
        keep[str(k)] = str(v)[:200]
        if len(keep) >= 8:
            break
    return keep


def _mk_field_id(domain: str, generalized_xpath: str, text_hint: str) -> str:
    h = hashlib.sha1(
        f"{domain}|{generalized_xpath}|{text_hint}".encode("utf-8")
    ).hexdigest()[:20]
    return h


def _to_row(
    node: ShadowNode,
    url: str,
    score: int,
) -> SignalFieldRow:
    abs_xp = get_absolute_xpath(node)
    gen_xp = generalize_xpath(abs_xp)
    domain = _domain_of(url)
    hint = _text_hint(node)
    now = _now()
    return SignalFieldRow(
        field_id=_mk_field_id(domain, gen_xp, hint),
        domain=domain,
        generalized_xpath=gen_xp,
        last_seen_url=url,
        last_seen_absolute_xpath=abs_xp,
        tag=node.tag.lower(),
        text_hint=hint,
        attributes_json=json.dumps(_attributes_snapshot(node), sort_keys=True),
        score=int(score),
        first_seen=now,
        last_seen=now,
    )


def _run_collector(dom: ShadowDOM, url: str, collector_cls: type) -> List[SignalFieldRow]:
    """Instantiate a web_distiller collector and flatten its output."""
    collector = collector_cls()
    try:
        chunk = collector.collect(dom)
    except TypeError:
        # PaginationCollector takes an optional structural_chunks list.
        chunk = collector.collect(dom, None)
    if chunk is None:
        return []
    nodes = getattr(chunk, "_instance_nodes", []) or []
    # Scores are already ranked high→low.
    rows: List[SignalFieldRow] = []
    for i, node in enumerate(nodes):
        # Higher rank → higher score; use a descending small int for stability.
        score = len(nodes) - i
        rows.append(_to_row(node, url, score))
    return rows


def collect_signal_fields(
    dom: ShadowDOM,
    url: str,
) -> Tuple[List[SignalFieldRow], List[SignalFieldRow]]:
    """Return ``(search_fields, pagination_fields)`` for one page."""
    # Lazy import — web_distiller_freq is heavy.
    from backend.dom.web_distiller_freq import (
        SearchInputCollector,
        PaginationCollector,
    )
    searches = _run_collector(dom, url, SearchInputCollector)
    paginates = _run_collector(dom, url, PaginationCollector)
    logger.info(
        "Signal fields on %s: %d search, %d pagination",
        url, len(searches), len(paginates),
    )
    return searches, paginates


# ---------------------------------------------------------------------------
# Kuzu persistence — coalesce on field_id
# ---------------------------------------------------------------------------


def _upsert_signal_field(conn, table: str, row: SignalFieldRow) -> None:
    """Insert if new; otherwise bump ``last_seen`` + refresh recency fields.

    ``first_seen`` is preserved from the original row — that's what
    distinguishes "tracked across many scans" from "just seen today".
    """
    existing_first_seen: Optional[str] = None
    res = conn.execute(
        f"MATCH (f:{table} {{field_id: $fid}}) RETURN f.first_seen",
        parameters={"fid": row.field_id},
    )
    while res.has_next():
        r = res.get_next()
        existing_first_seen = r[0] if r and r[0] else None
        break

    conn.execute(
        f"MATCH (f:{table} {{field_id: $fid}}) DETACH DELETE f",
        parameters={"fid": row.field_id},
    )
    first_seen = existing_first_seen or row.first_seen
    conn.execute(
        f"CREATE (f:{table} {{"
        "field_id: $field_id, domain: $domain, generalized_xpath: $generalized_xpath, "
        "last_seen_url: $last_seen_url, last_seen_absolute_xpath: $last_seen_absolute_xpath, "
        "tag: $tag, text_hint: $text_hint, attributes_json: $attributes_json, "
        "score: $score, first_seen: $first_seen, last_seen: $last_seen})",
        parameters={
            "field_id": row.field_id,
            "domain": row.domain,
            "generalized_xpath": row.generalized_xpath,
            "last_seen_url": row.last_seen_url,
            "last_seen_absolute_xpath": row.last_seen_absolute_xpath,
            "tag": row.tag,
            "text_hint": row.text_hint,
            "attributes_json": row.attributes_json,
            "score": row.score,
            "first_seen": first_seen,
            "last_seen": row.last_seen,
        },
    )
    # Link Domain -> field if the Domain row exists.
    rel_name = (
        "HAS_SEARCH_FIELD" if table == "SearchInputField"
        else "HAS_PAGINATION_FIELD"
    )
    try:
        conn.execute(
            f"MATCH (d:Domain {{domain: $dom}}), (f:{table} {{field_id: $fid}}) "
            f"MERGE (d)-[:{rel_name}]->(f)",
            parameters={"dom": row.domain, "fid": row.field_id},
        )
    except Exception:
        pass


def persist_signal_fields(
    conn,
    search_fields: Iterable[SignalFieldRow],
    pagination_fields: Iterable[SignalFieldRow],
) -> Tuple[int, int]:
    """Upsert both collections. Returns ``(search_count, paginate_count)``.

    W11c / §8D.39.1 — also auto-materialise a SearchableURL concept
    node for every detected search input field (pagination button is
    paired by URL where available). The concept node is the user-
    and agent-facing handle on the search-and-paginate behaviour.
    """
    # Save search rows first so we can pair pagination rows by URL.
    search_list = list(search_fields)
    pagination_list = list(pagination_fields)
    sc = 0
    for row in search_list:
        _upsert_signal_field(conn, "SearchInputField", row)
        sc += 1
    pc = 0
    for row in pagination_list:
        _upsert_signal_field(conn, "PaginationField", row)
        pc += 1

    # W11c — auto-materialise SearchableURL concept nodes.
    try:
        from backend.services.compiled_from_scans import CompiledFromScansMaterialiser
        from backend.services.graph_editor import GraphEditor
        from backend.services.concept_index_service import get_concept_index_service
        ge = GraphEditor(db_conn=conn)
        ci = get_concept_index_service(graph_editor=ge)
        mat = CompiledFromScansMaterialiser(graph_editor=ge, concept_index=ci)
        # Build URL→pagination_xpath index for pairing.
        pag_by_url: Dict[str, str] = {}
        for prow in pagination_list:
            url = prow.last_seen_url or ""
            xp = prow.last_seen_absolute_xpath or prow.generalized_xpath or ""
            if url and url not in pag_by_url:
                pag_by_url[url] = xp
        for srow in search_list:
            try:
                mat.materialise_searchable_url(
                    url=srow.last_seen_url or "",
                    search_field_xpath=srow.last_seen_absolute_xpath or srow.generalized_xpath or "",
                    query_param_name="q",
                    pagination_button_xpath=pag_by_url.get(srow.last_seen_url or "", ""),
                    detected_at=srow.last_seen or "",
                    workspace_id="",
                )
            except Exception:
                pass
    except Exception:
        # Materialisation is best-effort; legacy SearchInputField
        # persistence above is the source of truth.
        pass

    return sc, pc


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


_SIGNAL_COLS = (
    "f.field_id, f.domain, f.generalized_xpath, f.last_seen_url, "
    "f.last_seen_absolute_xpath, f.tag, f.text_hint, f.attributes_json, "
    "f.score, f.first_seen, f.last_seen"
)


def _row_to_signal(r) -> SignalFieldRow:
    return SignalFieldRow(
        field_id=r[0],
        domain=r[1],
        generalized_xpath=r[2],
        last_seen_url=r[3],
        last_seen_absolute_xpath=r[4],
        tag=r[5] or "",
        text_hint=r[6] or "",
        attributes_json=r[7] or "{}",
        score=int(r[8] or 0),
        first_seen=r[9] or "",
        last_seen=r[10] or "",
    )


def load_search_fields(conn, domain: Optional[str] = None) -> List[SignalFieldRow]:
    if domain:
        res = conn.execute(
            f"MATCH (f:SearchInputField {{domain: $d}}) RETURN {_SIGNAL_COLS}",
            parameters={"d": domain},
        )
    else:
        res = conn.execute(f"MATCH (f:SearchInputField) RETURN {_SIGNAL_COLS}")
    out: List[SignalFieldRow] = []
    while res.has_next():
        out.append(_row_to_signal(res.get_next()))
    return out


def load_pagination_fields(conn, domain: Optional[str] = None) -> List[SignalFieldRow]:
    if domain:
        res = conn.execute(
            f"MATCH (f:PaginationField {{domain: $d}}) RETURN {_SIGNAL_COLS}",
            parameters={"d": domain},
        )
    else:
        res = conn.execute(f"MATCH (f:PaginationField) RETURN {_SIGNAL_COLS}")
    out: List[SignalFieldRow] = []
    while res.has_next():
        out.append(_row_to_signal(res.get_next()))
    return out
