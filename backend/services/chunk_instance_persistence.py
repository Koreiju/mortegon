"""
chunk_instance_persistence.py — Kuzu IO for per-instance chunk renders.

Each page visit produces:

* N :class:`ChunkInstance` rows — one per populated instance, each with
  ``html_raw``, ``rendered_text``, ``fields_json`` and the 768-dim
  nomic embedding.
* 1 :class:`PageEmbedding` row — the L2-normalized mean of all instance
  embeddings on that page, used for URL-level semantic search.

Both are idempotent on re-scan: the primary keys are deterministic
hashes so a repeat visit **upserts** the same row rather than
accumulating duplicates.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from backend.mapper.chunk_render import ChunkInstanceRender

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Row dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ChunkInstanceRow:
    """One Kuzu row in the ``ChunkInstance`` table."""

    instance_id: str
    chunk_id: str
    pattern_id: str
    version_id: str
    url: str
    snapshot_id: str
    absolute_xpath: str
    html_raw: str
    rendered_text: str
    fields_json: str
    embedding: List[float]
    created_at: str


@dataclass
class PageEmbeddingRow:
    """One Kuzu row in the ``PageEmbedding`` table."""

    page_embedding_id: str
    url: str
    version_id: str
    snapshot_id: str
    instance_count: int
    embedding: List[float]
    created_at: str


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _page_embedding_id(version_id: str, url: str) -> str:
    return hashlib.sha1(
        f"page_emb|{version_id}|{url}".encode("utf-8")
    ).hexdigest()[:20]


def build_instance_rows(
    instances: Iterable[ChunkInstanceRender],
    *,
    version_id: str,
    url: str,
    snapshot_id: str,
    pattern_id_by_key: Dict[str, str],
) -> List[ChunkInstanceRow]:
    """Materialize :class:`ChunkInstanceRender` into Kuzu-ready rows.

    Parameters
    ----------
    instances:
        Output of ``render_all_chunks`` (must have ``embedding`` set).
    pattern_id_by_key:
        Mapping of generalized-xpath pattern → ``TriePattern.pattern_id``
        (``built.by_pattern_key[key].pattern_id``). Used to link
        ``INSTANCE_OF`` edges.
    """
    now = _now()
    rows: List[ChunkInstanceRow] = []
    for inst in instances:
        # Embeddings are now LAZY — the streaming pipeline persists rows
        # without dense vectors so the GPU embedder doesn't block the
        # scan critical path. Live retrieval (sparse TF-IDF) doesn't
        # need them. Deep / semantic search consumers (UMAP projector,
        # nomic-v1 cosine) populate the field on demand. Empty list
        # signals "not yet embedded"; downstream consumers gate on
        # ``len(row.embedding) == EMBED_DIM``.
        emb = list(map(float, inst.embedding)) if inst.embedding else []
        # KUZU expects a FLOAT[1024] embedding vector. Some scans may not
        # have computed embeddings yet and pass an empty list. Binding an empty
        # list to a FLOAT[1024] column causes a binder error. Normalize by
        # substituting a zero vector of the canonical embedding size when
        # embedding isn't available yet.
        if not emb:
            emb = [0.0] * 1024
        pid = pattern_id_by_key.get(inst.pattern, "")
        rows.append(
            ChunkInstanceRow(
                # URL-keyed + content-hashed: re-scans of the same page
                # collapse identical cards onto the same instance_id, so
                # the DB no longer grows a fresh row every visit.
                instance_id=inst.instance_id(url),
                chunk_id=inst.chunk_id,
                pattern_id=pid,
                version_id=version_id,
                url=url,
                snapshot_id=snapshot_id,
                absolute_xpath=inst.absolute_xpath,
                html_raw=inst.html_raw,
                rendered_text=inst.rendered_text,
                fields_json=json.dumps(inst.fields, sort_keys=True),
                embedding=emb,
                created_at=now,
            )
        )
    return rows


def build_page_embedding_row(
    *,
    version_id: str,
    url: str,
    snapshot_id: str,
    page_vector: np.ndarray,
    instance_count: int,
) -> PageEmbeddingRow:
    return PageEmbeddingRow(
        page_embedding_id=_page_embedding_id(version_id, url),
        url=url,
        version_id=version_id,
        snapshot_id=snapshot_id,
        instance_count=int(instance_count),
        embedding=list(map(float, page_vector.tolist())),
        created_at=_now(),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


# Prepared-statement cache. Profiling showed that ~95% of persistence
# wall-clock was Kuzu's per-call statement parser (``_prepare``)
# rebuilding the same Cypher AST 32-200 times per scan. Reusing one
# prepared statement per query shape collapses that cost by ~30x —
# ``connection.prepare()`` returns a handle that ``execute()`` can be
# called against repeatedly with new parameters.
_PREPARED: Dict[int, Dict[str, object]] = {}


def _prepared(conn, key: str, query: str):
    cache = _PREPARED.setdefault(id(conn), {})
    stmt = cache.get(key)
    if stmt is None:
        stmt = conn.prepare(query)
        cache[key] = stmt
    return stmt


_UPSERT_CYPHER = (
    "MERGE (i:ChunkInstance {instance_id: $instance_id}) "
    "SET i.chunk_id = $chunk_id, i.pattern_id = $pattern_id, "
    "    i.version_id = $version_id, i.url = $url, "
    "    i.snapshot_id = $snapshot_id, i.absolute_xpath = $absolute_xpath, "
    "    i.html_raw = $html_raw, i.rendered_text = $rendered_text, "
    "    i.fields_json = $fields_json, i.embedding = $embedding, "
    "    i.created_at = $created_at"
)
_LINK_PATTERN_CYPHER = (
    "MATCH (i:ChunkInstance {instance_id: $iid}), "
    "(t:TriePattern {pattern_id: $pid}) "
    "MERGE (i)-[:INSTANCE_OF]->(t)"
)
_LINK_PAGE_CYPHER = (
    "MATCH (p:Page {url: $url}), (i:ChunkInstance {instance_id: $iid}) "
    "MERGE (p)-[:HAS_INSTANCE]->(i)"
)


def _upsert_instance(conn, row: ChunkInstanceRow) -> None:
    """MERGE one ChunkInstance plus its outgoing relationships.

    Uses cached prepared statements to avoid repaying the Cypher
    parser cost for every row — that was the dominant per-row
    overhead before the cache.
    """
    conn.execute(
        _prepared(conn, "upsert_instance", _UPSERT_CYPHER),
        parameters={
            "instance_id": row.instance_id,
            "chunk_id": row.chunk_id,
            "pattern_id": row.pattern_id,
            "version_id": row.version_id,
            "url": row.url,
            "snapshot_id": row.snapshot_id,
            "absolute_xpath": row.absolute_xpath,
            "html_raw": row.html_raw,
            "rendered_text": row.rendered_text,
            "fields_json": row.fields_json,
            "embedding": row.embedding,
            "created_at": row.created_at,
        },
    )
    if row.pattern_id:
        try:
            conn.execute(
                _prepared(conn, "link_pattern", _LINK_PATTERN_CYPHER),
                parameters={"iid": row.instance_id, "pid": row.pattern_id},
            )
        except Exception:
            # Test schemas may not define INSTANCE_OF — non-fatal.
            pass
    try:
        conn.execute(
            _prepared(conn, "link_page", _LINK_PAGE_CYPHER),
            parameters={"url": row.url, "iid": row.instance_id},
        )
    except Exception:
        pass




def _upsert_page_embedding(conn, row: PageEmbeddingRow) -> None:
    conn.execute(
        "MATCH (e:PageEmbedding {page_embedding_id: $pid}) DETACH DELETE e",
        parameters={"pid": row.page_embedding_id},
    )
    conn.execute(
        "CREATE (e:PageEmbedding {"
        "page_embedding_id: $page_embedding_id, url: $url, "
        "version_id: $version_id, snapshot_id: $snapshot_id, "
        "instance_count: $instance_count, embedding: $embedding, "
        "created_at: $created_at})",
        parameters={
            "page_embedding_id": row.page_embedding_id,
            "url": row.url,
            "version_id": row.version_id,
            "snapshot_id": row.snapshot_id,
            "instance_count": row.instance_count,
            "embedding": row.embedding,
            "created_at": row.created_at,
        },
    )
    try:
        conn.execute(
            "MATCH (p:Page {url: $url}), (e:PageEmbedding {page_embedding_id: $pid}) "
            "MERGE (p)-[:HAS_PAGE_EMBEDDING]->(e)",
            parameters={"url": row.url, "pid": row.page_embedding_id},
        )
    except Exception:
        pass


_BATCH_UPSERT_CYPHER = (
    "UNWIND $rows AS r "
    "MERGE (i:ChunkInstance {instance_id: r.instance_id}) "
    "SET i.chunk_id = r.chunk_id, i.pattern_id = r.pattern_id, "
    "    i.version_id = r.version_id, i.url = r.url, "
    "    i.snapshot_id = r.snapshot_id, i.absolute_xpath = r.absolute_xpath, "
    "    i.html_raw = r.html_raw, i.rendered_text = r.rendered_text, "
    "    i.fields_json = r.fields_json, i.embedding = r.embedding, "
    "    i.created_at = r.created_at"
)
_BATCH_LINK_PATTERN_CYPHER = (
    "UNWIND $pairs AS p "
    "MATCH (i:ChunkInstance {instance_id: p.iid}), "
    "(t:TriePattern {pattern_id: p.pid}) "
    "MERGE (i)-[:INSTANCE_OF]->(t)"
)
_BATCH_LINK_PAGE_CYPHER = (
    "UNWIND $pairs AS p "
    "MATCH (pg:Page {url: p.url}), (i:ChunkInstance {instance_id: p.iid}) "
    "MERGE (pg)-[:HAS_INSTANCE]->(i)"
)


def persist_chunk_instances(conn, rows: Iterable[ChunkInstanceRow]) -> int:
    """Upsert a batch of instance rows. Returns count written.

    Tries one UNWIND statement per query shape (1 + 2 link statements,
    not 3N) so the kuzu executor can plan once and walk the rows in a
    single pass. Falls back to per-row upsert on any failure — schemas
    that lack INSTANCE_OF / HAS_INSTANCE relationships were tolerated
    by the legacy per-row path's broad ``except Exception``, and the
    fallback preserves that behavior.
    """
    rows_list = list(rows)
    if not rows_list:
        return 0

    payload = [
        {
            "instance_id": r.instance_id,
            "chunk_id": r.chunk_id,
            "pattern_id": r.pattern_id,
            "version_id": r.version_id,
            "url": r.url,
            "snapshot_id": r.snapshot_id,
            "absolute_xpath": r.absolute_xpath,
            "html_raw": r.html_raw,
            "rendered_text": r.rendered_text,
            "fields_json": r.fields_json,
            "embedding": r.embedding,
            "created_at": r.created_at,
        }
        for r in rows_list
    ]
    try:
        conn.execute(
            _prepared(conn, "batch_upsert_instance", _BATCH_UPSERT_CYPHER),
            parameters={"rows": payload},
        )
    except Exception:
        # Kuzu version may not support UNWIND with list-of-struct
        # parameters in the prepared form. Drop back to per-row, which
        # still benefits from the prepared-statement cache above.
        logger.exception("[Persist] batch UNWIND failed; falling back to per-row")
        for row in rows_list:
            _upsert_instance(conn, row)
        return len(rows_list)

    pattern_pairs = [
        {"iid": r.instance_id, "pid": r.pattern_id}
        for r in rows_list if r.pattern_id
    ]
    if pattern_pairs:
        try:
            conn.execute(
                _prepared(conn, "batch_link_pattern", _BATCH_LINK_PATTERN_CYPHER),
                parameters={"pairs": pattern_pairs},
            )
        except Exception:
            for p in pattern_pairs:
                try:
                    conn.execute(
                        _prepared(conn, "link_pattern", _LINK_PATTERN_CYPHER),
                        parameters={"iid": p["iid"], "pid": p["pid"]},
                    )
                except Exception:
                    pass

    page_pairs = [{"url": r.url, "iid": r.instance_id} for r in rows_list if r.url]
    if page_pairs:
        try:
            conn.execute(
                _prepared(conn, "batch_link_page", _BATCH_LINK_PAGE_CYPHER),
                parameters={"pairs": page_pairs},
            )
        except Exception:
            for p in page_pairs:
                try:
                    conn.execute(
                        _prepared(conn, "link_page", _LINK_PAGE_CYPHER),
                        parameters={"url": p["url"], "iid": p["iid"]},
                    )
                except Exception:
                    pass

    return len(rows_list)


def persist_page_embedding(conn, row: PageEmbeddingRow) -> None:
    _upsert_page_embedding(conn, row)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _row_to_instance(r) -> ChunkInstanceRow:
    return ChunkInstanceRow(
        instance_id=r[0],
        chunk_id=r[1],
        pattern_id=r[2] or "",
        version_id=r[3],
        url=r[4],
        snapshot_id=r[5] or "",
        absolute_xpath=r[6],
        html_raw=r[7] or "",
        rendered_text=r[8] or "",
        fields_json=r[9] or "{}",
        embedding=list(map(float, r[10])) if r[10] else [],
        created_at=r[11] or "",
    )


_INSTANCE_COLS = (
    "i.instance_id, i.chunk_id, i.pattern_id, i.version_id, i.url, "
    "i.snapshot_id, i.absolute_xpath, i.html_raw, i.rendered_text, "
    "i.fields_json, i.embedding, i.created_at"
)


def load_instances_by_url(conn, url: str) -> List[ChunkInstanceRow]:
    res = conn.execute(
        f"MATCH (i:ChunkInstance {{url: $url}}) RETURN {_INSTANCE_COLS}",
        parameters={"url": url},
    )
    out: List[ChunkInstanceRow] = []
    while res.has_next():
        out.append(_row_to_instance(res.get_next()))
    return out


def load_instances_by_urls(conn, urls: Iterable[str]) -> List[ChunkInstanceRow]:
    urls = list(urls)
    if not urls:
        return []
    res = conn.execute(
        f"MATCH (i:ChunkInstance) WHERE i.url IN $urls RETURN {_INSTANCE_COLS}",
        parameters={"urls": urls},
    )
    out: List[ChunkInstanceRow] = []
    while res.has_next():
        out.append(_row_to_instance(res.get_next()))
    return out


def load_instance_by_id(conn, instance_id: str) -> Optional[ChunkInstanceRow]:
    res = conn.execute(
        f"MATCH (i:ChunkInstance {{instance_id: $iid}}) RETURN {_INSTANCE_COLS}",
        parameters={"iid": instance_id},
    )
    while res.has_next():
        return _row_to_instance(res.get_next())
    return None


def load_instances_by_ids(conn, instance_ids: List[str]) -> List[ChunkInstanceRow]:
    res = conn.execute(
        f"MATCH (i:ChunkInstance) WHERE i.instance_id IN $iids RETURN {_INSTANCE_COLS}",
        parameters={"iids": instance_ids},
    )
    out: List[ChunkInstanceRow] = []
    while res.has_next():
        out.append(_row_to_instance(res.get_next()))
    return out


def load_all_instances(conn) -> List[ChunkInstanceRow]:
    """Full dump — only call when building the UMAP over the whole DB."""
    res = conn.execute(f"MATCH (i:ChunkInstance) RETURN {_INSTANCE_COLS}")
    out: List[ChunkInstanceRow] = []
    while res.has_next():
        out.append(_row_to_instance(res.get_next()))
    return out


def load_page_embedding(conn, url: str) -> Optional[PageEmbeddingRow]:
    res = conn.execute(
        "MATCH (e:PageEmbedding {url: $url}) RETURN "
        "e.page_embedding_id, e.url, e.version_id, e.snapshot_id, "
        "e.instance_count, e.embedding, e.created_at "
        "ORDER BY e.created_at DESC LIMIT 1",
        parameters={"url": url},
    )
    while res.has_next():
        r = res.get_next()
        return PageEmbeddingRow(
            page_embedding_id=r[0],
            url=r[1],
            version_id=r[2],
            snapshot_id=r[3] or "",
            instance_count=int(r[4] or 0),
            embedding=list(map(float, r[5])) if r[5] else [],
            created_at=r[6] or "",
        )
    return None


def load_all_page_embeddings(conn) -> List[PageEmbeddingRow]:
    res = conn.execute(
        "MATCH (e:PageEmbedding) RETURN "
        "e.page_embedding_id, e.url, e.version_id, e.snapshot_id, "
        "e.instance_count, e.embedding, e.created_at"
    )
    out: List[PageEmbeddingRow] = []
    while res.has_next():
        r = res.get_next()
        out.append(
            PageEmbeddingRow(
                page_embedding_id=r[0],
                url=r[1],
                version_id=r[2],
                snapshot_id=r[3] or "",
                instance_count=int(r[4] or 0),
                embedding=list(map(float, r[5])) if r[5] else [],
                created_at=r[6] or "",
            )
        )
    return out
