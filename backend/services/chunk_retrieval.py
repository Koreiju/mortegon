"""
chunk_retrieval.py — URL/query retrieval over ``ChunkInstance`` rows.

Two public entry points:

* :func:`retrieve_instances_by_urls` — "give me every chunk instance
  under these URLs, optionally ranked against a query". Result rows
  carry the full HTML so the caller can render or display the content
  without a second DB hit.
* :func:`retrieve_pages_by_query` — URL-level semantic search over
  :class:`PageEmbedding`. Returns ``(url, score)`` pairs that the caller
  can feed back into ``retrieve_instances_by_urls`` to drill into the
  specific chunks on each winning page.

Similarity
----------
We prefer Kuzu's native ``array_cosine_similarity`` when available (the
column type is ``FLOAT[768]``) and fall back to in-Python cosine when
the Kuzu version doesn't expose the UDF — e.g. old test fixtures or
schemas without the embedding column. All paths are robust to the
fallback.
"""

from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import numpy as np

from backend.services.chunk_containment import filter_redundant_rollups
from backend.services.chunk_instance_persistence import (
    ChunkInstanceRow,
    PageEmbeddingRow,
    load_all_page_embeddings,
    load_instances_by_urls,
)
from backend.services.embedding_service import EmbeddingService, cosine_similarity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class InstanceHit:
    """One scored chunk-instance retrieval result.

    The ``html_raw`` field is included verbatim so retrieval consumers
    can render the instance without a second query.
    """

    instance_id: str
    chunk_id: str
    pattern_id: str
    url: str
    absolute_xpath: str
    html_raw: str
    rendered_text: str
    score: float
    # Serialized ``{extended_xpath: [values]}`` content-structure summary,
    # carried through so retrieval consumers can render the chunk's
    # semantic shape (not just its raw HTML) without a second DB hit.
    fields_json: str = ""


@dataclass
class PageHit:
    """One URL-level retrieval result."""

    url: str
    score: float
    instance_count: int


# ---------------------------------------------------------------------------
# Cosine via Kuzu vs. Python
# ---------------------------------------------------------------------------


def _kuzu_supports_cosine(conn) -> bool:
    """Cheap probe: call ``array_cosine_similarity`` on two tiny vectors."""
    try:
        res = conn.execute(
            "RETURN array_cosine_similarity(CAST([1.0, 0.0] AS FLOAT[2]), "
            "CAST([1.0, 0.0] AS FLOAT[2])) AS s"
        )
        while res.has_next():
            res.get_next()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Per-instance retrieval
# ---------------------------------------------------------------------------


def retrieve_instances_by_urls(
    conn,
    urls: Iterable[str],
    *,
    query: Optional[str] = None,
    limit: int = 20,
    embedder: Optional[EmbeddingService] = None,
) -> List[InstanceHit]:
    """Return instances from the given URLs, optionally ranked by ``query``.

    Parameters
    ----------
    conn:
        Open Kuzu connection.
    urls:
        The URLs to scope retrieval to. A single-item list acts as
        "everything I scanned on this page"; an N-item list expands the
        scope to a multi-URL retrieval session.
    query:
        Optional natural-language query. When provided, instances are
        ranked by cosine similarity between the query's
        ``search_query:`` embedding and each instance's stored vector.
        When ``None``, instances are returned in creation order (newest
        first) up to ``limit``.
    limit:
        Maximum number of results. Pass ``0`` for no cap.
    embedder:
        Optional pre-built :class:`EmbeddingService`. Tests pass a mock
        here; production calls leave it ``None`` to use the default
        v1.5-GPU instance.
    """
    url_list = [u for u in urls if u]
    if not url_list:
        return []

    if query is None:
        rows = load_instances_by_urls(conn, url_list)
        hits = [
            InstanceHit(
                instance_id=r.instance_id,
                chunk_id=r.chunk_id,
                pattern_id=r.pattern_id,
                url=r.url,
                absolute_xpath=r.absolute_xpath,
                html_raw=r.html_raw,
                rendered_text=r.rendered_text,
                score=0.0,
                fields_json=r.fields_json or "",
            )
            for r in rows
        ]
        # Newest first.
        rows_sorted = sorted(
            zip(hits, rows), key=lambda t: t[1].created_at, reverse=True,
        )
        hits = [h for h, _ in rows_sorted]
        hits = _prune_rollups_per_url(hits)
        hits = _dedupe_cross_url_shared_chunks(hits)
        return hits if not limit else hits[:limit]

    # Query path — embed once, score per row.
    embedder = embedder or EmbeddingService()
    q_vec = np.asarray(embedder.embed_query(query), dtype=np.float32)

    if _kuzu_supports_cosine(conn):
        return _rank_by_kuzu_cosine(conn, url_list, q_vec, limit)
    return _rank_by_python_cosine(conn, url_list, q_vec, limit)


def _rank_by_kuzu_cosine(
    conn, urls: List[str], q_vec: np.ndarray, limit: int,
) -> List[InstanceHit]:
    """Score via Kuzu's ``array_cosine_similarity``. Preferred path.

    We intentionally do NOT apply a ``LIMIT`` at the DB layer — the
    containment-prune pass needs to see all candidates per URL to know
    which rollups to drop, and doing that before the top-K cut avoids
    the "monster rollup beats its own children on score" failure mode.
    """
    cypher = (
        "MATCH (i:ChunkInstance) "
        "WHERE i.url IN $urls "
        "RETURN i.instance_id, i.chunk_id, i.pattern_id, i.url, "
        "i.absolute_xpath, i.html_raw, i.rendered_text, i.fields_json, "
        "array_cosine_similarity(i.embedding, $q) AS score "
        "ORDER BY score DESC"
    )
    res = conn.execute(
        cypher,
        parameters={"urls": urls, "q": list(map(float, q_vec.tolist()))},
    )
    hits: List[InstanceHit] = []
    while res.has_next():
        r = res.get_next()
        hits.append(
            InstanceHit(
                instance_id=r[0],
                chunk_id=r[1],
                pattern_id=r[2] or "",
                url=r[3],
                absolute_xpath=r[4],
                html_raw=r[5] or "",
                rendered_text=r[6] or "",
                fields_json=r[7] or "",
                score=float(r[8] if r[8] is not None else 0.0),
            )
        )
    hits = _prune_rollups_per_url(hits)
    hits = _dedupe_cross_url_shared_chunks(hits)
    if limit:
        hits = hits[:limit]
    return hits


def _rank_by_python_cosine(
    conn, urls: List[str], q_vec: np.ndarray, limit: int,
) -> List[InstanceHit]:
    """Fallback for Kuzu builds without cosine UDF. Still correct, slower."""
    rows = load_instances_by_urls(conn, urls)
    valid_rows = [r for r in rows if r.embedding]
    if not valid_rows:
        return []
        
    # Normalize query vector
    q_norm = np.linalg.norm(q_vec)
    q_vec_n = q_vec / q_norm if q_norm > 0 else q_vec
    
    # Stack and normalize all embeddings simultaneously
    V = np.stack([np.asarray(r.embedding, dtype=np.float32) for r in valid_rows])
    V_norms = np.linalg.norm(V, axis=1, keepdims=True)
    V_norms[V_norms == 0] = 1e-10
    V_n = V / V_norms
    
    # Compute cosine similarities via matrix multiplication
    scores = (V_n @ q_vec_n).tolist()
    scored = list(zip(scores, valid_rows))
    scored.sort(key=lambda t: t[0], reverse=True)
    
    hits = [
        InstanceHit(
            instance_id=r.instance_id,
            chunk_id=r.chunk_id,
            pattern_id=r.pattern_id,
            url=r.url,
            absolute_xpath=r.absolute_xpath,
            html_raw=r.html_raw,
            rendered_text=r.rendered_text,
            fields_json=r.fields_json or "",
            score=float(score),
        )
        for score, r in scored
    ]
    hits = _prune_rollups_per_url(hits)
    hits = _dedupe_cross_url_shared_chunks(hits)
    if limit:
        hits = hits[:limit]
    return hits


def _dedupe_cross_url_shared_chunks(hits: List[InstanceHit]) -> List[InstanceHit]:
    """Collapse repeated menu/footer chunks across same-domain URLs.

    Many pages on a single domain share identical header/footer/nav
    subtrees. Returning one hit per URL drowns search results in
    duplicates and clutters the 3D graph. This keeps only the copy whose
    URL has the shallowest path (closest to the homepage) — ties broken
    by shorter URL length then lexicographic order. Cross-domain hits
    are never merged; same-domain hits with different ``html_raw``
    content (i.e. page-specific tweaks) are left alone.
    """
    if not hits:
        return hits

    def _depth(url: str) -> Tuple[int, int, str]:
        try:
            parsed = urlparse(url)
            path = parsed.path or "/"
        except Exception:
            return (99, len(url), url)
        segs = [s for s in path.split("/") if s]
        return (len(segs), len(url), url)

    groups: dict[str, List[InstanceHit]] = {}
    order: dict[str, int] = {}
    for i, h in enumerate(hits):
        try:
            domain = urlparse(h.url).netloc.lower()
        except Exception:
            domain = ""
        content_hash = hashlib.sha1(
            (h.html_raw or "").encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        key = f"{domain}|{h.pattern_id or h.chunk_id}|{content_hash}"
        groups.setdefault(key, []).append(h)
        order.setdefault(h.instance_id, i)

    kept: List[InstanceHit] = []
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue
        # Shallowest URL wins; its score is the best across the group so
        # surviving hit isn't penalized for sharing content with deeper pages.
        owner = min(group, key=lambda h: _depth(h.url))
        best_score = max(h.score for h in group)
        if owner.score < best_score:
            owner.score = best_score
        kept.append(owner)
    kept.sort(key=lambda h: order.get(h.instance_id, 0))
    return kept


def _prune_rollups_per_url(hits: List[InstanceHit]) -> List[InstanceHit]:
    """Drop strict-ancestor rollup chunks, scoped per URL.

    Containment only makes sense within a single page's DOM — two
    pages may happen to share a URL-path-looking prefix on unrelated
    xpaths, and pruning globally would be wrong. Preserve input order
    so upstream ranking stays stable for the survivors.

    Legitimate coarse/fine chunk pairs both well under the chunker's
    hard char ceiling are preserved via the size gate; only oversized
    rollup chunks (those that pre-date the HTML-budget chunker or
    escaped it somehow) are dropped.
    """
    if not hits:
        return hits
    from backend.mapper.chunk_builder import HARD_CHAR_LIMIT
    rollup_threshold = 2 * HARD_CHAR_LIMIT
    by_url: dict[str, List[InstanceHit]] = {}
    order: dict[str, int] = {}
    for i, h in enumerate(hits):
        by_url.setdefault(h.url, []).append(h)
        order.setdefault(h.instance_id, i)
    pruned: List[InstanceHit] = []
    for url_hits in by_url.values():
        pruned.extend(
            filter_redundant_rollups(
                url_hits,
                xpath_of=lambda x: x.absolute_xpath,
                size_of=lambda x: len(x.html_raw or ""),
                min_rollup_size=rollup_threshold,
            )
        )
    pruned.sort(key=lambda h: order.get(h.instance_id, 0))
    return pruned


# ---------------------------------------------------------------------------
# Page-level retrieval
# ---------------------------------------------------------------------------


def retrieve_pages_by_query(
    conn,
    query: str,
    *,
    urls: Optional[List[str]] = None,
    limit: int = 10,
    embedder: Optional[EmbeddingService] = None,
) -> List[PageHit]:
    """URL-level retrieval — returns URLs ranked by ``PageEmbedding`` cosine.

    Use this to "find me the pages most relevant to 'tarot readings'",
    then feed the returned URLs into
    :func:`retrieve_instances_by_urls` to drill down.
    """
    if not query:
        return []
    embedder = embedder or EmbeddingService()
    q_vec = np.asarray(embedder.embed_query(query), dtype=np.float32)

    if _kuzu_supports_cosine(conn):
        cypher = "MATCH (e:PageEmbedding) "
        if urls is not None:
            cypher += "WHERE e.url IN $urls "
            
        cypher += (
            "RETURN e.url, e.instance_count, "
            "array_cosine_similarity(e.embedding, $q) AS score "
            "ORDER BY score DESC"
        )
        if limit:
            cypher += f" LIMIT {int(limit)}"
            
        params = {"q": list(map(float, q_vec.tolist()))}
        if urls is not None:
            params["urls"] = urls
            
        res = conn.execute(
            cypher, parameters=params,
        )
        hits: List[PageHit] = []
        while res.has_next():
            r = res.get_next()
            hits.append(
                PageHit(
                    url=r[0], instance_count=int(r[1] or 0),
                    score=float(r[2] if r[2] is not None else 0.0),
                )
            )
        return hits

    # Python fallback.
    page_rows = load_all_page_embeddings(conn)
    if urls is not None:
        url_set = set(urls)
        page_rows = [r for r in page_rows if r.url in url_set]
            
    valid_rows = [r for r in page_rows if r.embedding]
    if not valid_rows:
        return []
        
    q_norm = np.linalg.norm(q_vec)
    q_vec_n = q_vec / q_norm if q_norm > 0 else q_vec
    
    V = np.stack([np.asarray(r.embedding, dtype=np.float32) for r in valid_rows])
    V_norms = np.linalg.norm(V, axis=1, keepdims=True)
    V_norms[V_norms == 0] = 1e-10
    V_n = V / V_norms
    
    scores = (V_n @ q_vec_n).tolist()
    
    scored = list(zip(scores, valid_rows))
    scored.sort(key=lambda t: t[0], reverse=True)
    
    if limit:
        scored = scored[:limit]
        
    return [
        PageHit(url=r.url, instance_count=r.instance_count, score=float(s))
        for s, r in scored
    ]


# ---------------------------------------------------------------------------
# Convenience: page-level → instance drill-down
# ---------------------------------------------------------------------------


def retrieve_with_drilldown(
    conn,
    query: str,
    *,
    urls: Optional[List[str]] = None,
    page_limit: int = 10,
    instance_limit_per_page: int = 50,
    embedder: Optional[EmbeddingService] = None,
) -> List[Tuple[PageHit, List[InstanceHit]]]:
    """Two-stage retrieval: rank pages first, then instances within them.

    This is the "searching full database of all urls efficiently and
    recursively" path the user asked for. The top-K pages by mean-vector
    similarity are drilled into for their highest-scoring instances.
    """
    embedder = embedder or EmbeddingService()
    pages = retrieve_pages_by_query(
        conn, query, urls=urls, limit=page_limit, embedder=embedder,
    )
    out: List[Tuple[PageHit, List[InstanceHit]]] = []
    for p in pages:
        insts = retrieve_instances_by_urls(
            conn, [p.url], query=query,
            limit=instance_limit_per_page, embedder=embedder,
        )
        out.append((p, insts))
    return out
