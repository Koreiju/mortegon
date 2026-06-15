"""
snapshot_store.py — Database + filesystem adapter for DOM snapshots.

Handles:
  - Saving/loading full DOM HTML strings to disk (file-backed)
  - Registering snapshots, domains, and content trees in KuzuDB
  - Merge-conscious timeline: identical snapshots are not duplicated
  - Loading content trees and label data from DB
"""

from __future__ import annotations

import os
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from urllib.parse import urlparse

from backend.database import get_connection

# Directory for persisted HTML files
SNAPSHOTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'snapshots')
)


def _ensure_dir():
    Path(SNAPSHOTS_DIR).mkdir(parents=True, exist_ok=True)


def _content_hash(html: str) -> str:
    """SHA256 hash of the HTML string, truncated to 16 hex chars."""
    return hashlib.sha256(html.encode('utf-8', errors='replace')).hexdigest()[:16]


def _url_to_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.hostname or url
    except Exception:
        return url


def _safe_filename(url: str, snapshot_id: str) -> str:
    """Generate a filesystem-safe filename from URL + snapshot id."""
    safe = url.replace('https://', '').replace('http://', '')
    safe = safe.replace('/', '_').replace(':', '_').replace('?', '_')
    safe = safe.replace('=', '_').replace('&', '_').replace('#', '_')
    # Truncate to avoid filesystem limits
    safe = safe[:80]
    return f"{safe}_{snapshot_id}.html"


class SnapshotStore:
    """
    Persistent store for DOM snapshots, content trees, and labels.

    All DB operations use the shared KuzuDB connection from backend.database.
    HTML strings are saved as files on disk; DB stores file paths.
    """

    def __init__(self):
        _ensure_dir()

    # ------------------------------------------------------------------
    # Domain registration
    # ------------------------------------------------------------------

    def register_domain(self, url: str) -> str:
        """Ensure the domain for a URL exists in the DB. Returns domain string."""
        conn = get_connection()
        domain = _url_to_domain(url)
        try:
            conn.execute(
                "MERGE (d:Domain {domain: $d}) SET d.first_seen = $ts;",
                parameters={"d": domain, "ts": time.strftime('%Y-%m-%dT%H:%M:%S')}
            )
        except Exception as e:
            print(f"[SnapshotStore] Domain register error: {e}")
        return domain

    # ------------------------------------------------------------------
    # Page registration
    # ------------------------------------------------------------------

    def register_page(self, url: str) -> None:
        """Ensure a Page node exists for this URL, linked to its domain."""
        conn = get_connection()
        domain = self.register_domain(url)
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')
        try:
            conn.execute(
                "MERGE (p:Page {url: $url}) SET p.domain = $d, p.timestamp = $ts;",
                parameters={"url": url, "d": domain, "ts": ts}
            )
        except Exception as e:
            print(f"[SnapshotStore] Page register error: {e}")

        # Link domain → page
        try:
            conn.execute(
                "MATCH (d:Domain {domain: $d}), (p:Page {url: $url}) "
                "MERGE (d)-[:HAS_PAGE]->(p);",
                parameters={"d": domain, "url": url}
            )
        except Exception:
            pass  # edge may already exist

    # ------------------------------------------------------------------
    # Snapshot save / load
    # ------------------------------------------------------------------

    def save_snapshot(self, url: str, html: str,
                      snapshot_id: str = None) -> Tuple[str, bool]:
        """
        Save a DOM snapshot. Implements merge-conscious deduplication:
        if the HTML hash matches the latest snapshot for this URL,
        no new record is created.

        Args:
            url: The page URL.
            html: Full DOM HTML string.
            snapshot_id: Optional explicit ID. Auto-generated if None.

        Returns:
            (snapshot_id, is_new) — is_new=False means duplicate was detected.
        """
        conn = get_connection()
        self.register_page(url)

        content_hash = _content_hash(html)

        # Check if latest snapshot for this URL has the same hash
        try:
            res = conn.execute(
                "MATCH (s:DomSnapshot {url: $url}) "
                "RETURN s.snapshot_id, s.content_hash "
                "ORDER BY s.captured_at DESC LIMIT 1;",
                parameters={"url": url}
            )
            if res.has_next():
                row = res.get_next()
                if row[1] == content_hash:
                    print(f"[SnapshotStore] Duplicate snapshot for {url}, "
                          f"reusing {row[0]}")
                    return row[0], False
        except Exception:
            pass  # table may not exist yet on first run

        # Generate snapshot ID
        if snapshot_id is None:
            snapshot_id = f"{content_hash}_{int(time.time())}"

        # Save HTML to file
        filename = _safe_filename(url, snapshot_id)
        filepath = os.path.join(SNAPSHOTS_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        # Create DomSnapshot record
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')
        node_count = html.count('<')  # rough estimate
        try:
            conn.execute(
                "CREATE (s:DomSnapshot {"
                "  snapshot_id: $sid, url: $url, file_path: $fp,"
                "  content_hash: $ch, captured_at: $ts, node_count: $nc"
                "});",
                parameters={
                    "sid": snapshot_id, "url": url, "fp": filepath,
                    "ch": content_hash, "ts": ts, "nc": node_count
                }
            )
        except Exception as e:
            print(f"[SnapshotStore] Snapshot create error: {e}")

        # Link Page → Snapshot
        try:
            conn.execute(
                "MATCH (p:Page {url: $url}), "
                "      (s:DomSnapshot {snapshot_id: $sid}) "
                "MERGE (p)-[:HAS_SNAPSHOT]->(s);",
                parameters={"url": url, "sid": snapshot_id}
            )
        except Exception:
            pass

        print(f"[SnapshotStore] Saved snapshot {snapshot_id} -> {filepath}")
        return snapshot_id, True

    def load_snapshot_html(self, snapshot_id: str) -> Optional[str]:
        """Load the HTML string for a snapshot from disk."""
        conn = get_connection()
        try:
            res = conn.execute(
                "MATCH (s:DomSnapshot {snapshot_id: $sid}) "
                "RETURN s.file_path;",
                parameters={"sid": snapshot_id}
            )
            if res.has_next():
                filepath = res.get_next()[0]
                if filepath and os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return f.read()
        except Exception as e:
            print(f"[SnapshotStore] Load error: {e}")
        return None

    def get_snapshots_for_url(self, url: str) -> List[Dict[str, Any]]:
        """Return all snapshots for a URL, newest first."""
        conn = get_connection()
        results = []
        try:
            res = conn.execute(
                "MATCH (s:DomSnapshot {url: $url}) "
                "RETURN s.snapshot_id, s.captured_at, s.content_hash, "
                "       s.node_count "
                "ORDER BY s.captured_at DESC;",
                parameters={"url": url}
            )
            while res.has_next():
                row = res.get_next()
                results.append({
                    'snapshot_id': row[0],
                    'captured_at': row[1],
                    'content_hash': row[2],
                    'node_count': row[3],
                })
        except Exception:
            pass
        return results

    def get_all_registered_urls(self) -> List[Dict[str, Any]]:
        """Return all URLs that have at least one snapshot."""
        conn = get_connection()
        results = []
        try:
            res = conn.execute(
                "MATCH (p:Page)-[:HAS_SNAPSHOT]->(s:DomSnapshot) "
                "RETURN p.url, p.domain, count(s) AS snap_count "
                "ORDER BY snap_count DESC;"
            )
            while res.has_next():
                row = res.get_next()
                results.append({
                    'url': row[0], 'domain': row[1],
                    'snapshot_count': row[2],
                })
        except Exception:
            pass
        return results

    # ------------------------------------------------------------------
    # Content tree save / load
    # ------------------------------------------------------------------

    def save_content_tree(self, snapshot_id: str, url: str,
                          tree_json: Dict[str, Any]) -> str:
        """Save a content xpath tree to the DB as a JSON string."""
        conn = get_connection()
        tree_id = f"tree_{snapshot_id}"
        tree_str = json.dumps(tree_json, separators=(',', ':'))

        try:
            conn.execute(
                "MERGE (t:ContentTree {tree_id: $tid}) "
                "SET t.url = $url, t.xpath_json = $json;",
                parameters={"tid": tree_id, "url": url, "json": tree_str}
            )
        except Exception as e:
            print(f"[SnapshotStore] Content tree save error: {e}")

        # Link snapshot → content tree
        try:
            conn.execute(
                "MATCH (s:DomSnapshot {snapshot_id: $sid}), "
                "      (t:ContentTree {tree_id: $tid}) "
                "MERGE (s)-[:HAS_CONTENT_TREE]->(t);",
                parameters={"sid": snapshot_id, "tid": tree_id}
            )
        except Exception:
            pass

        return tree_id

    def load_content_tree(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Load the content tree JSON for a snapshot."""
        conn = get_connection()
        tree_id = f"tree_{snapshot_id}"
        try:
            res = conn.execute(
                "MATCH (t:ContentTree {tree_id: $tid}) "
                "RETURN t.xpath_json;",
                parameters={"tid": tree_id}
            )
            if res.has_next():
                raw = res.get_next()[0]
                return json.loads(raw)
        except Exception as e:
            print(f"[SnapshotStore] Tree load error: {e}")
        return None

    # ------------------------------------------------------------------
    # Content chunk save / load / label
    # ------------------------------------------------------------------

    def save_chunks(self, snapshot_id: str, url: str,
                    chunks: List[Any]) -> int:
        """
        Persist a list of Chunk dataclass instances for a snapshot.
        Existing chunks for the same snapshot are left alone — chunks are
        keyed by chunk_id (stable per pattern+ordinal), so repeated scans
        overwrite their own rows via MERGE.

        Returns the number of chunks written.
        """
        conn = get_connection()
        ts = time.strftime('%Y-%m-%dT%H:%M:%S')
        written = 0

        for ch in chunks:
            payload = ch.as_dict() if hasattr(ch, 'as_dict') else dict(ch)
            members_json = json.dumps(payload.get('member_xpaths', []),
                                      separators=(',', ':'))
            fields_json = json.dumps(payload.get('content_fields', {}),
                                     separators=(',', ':'))
            trie_json = json.dumps(payload.get('extraction_trie', {}),
                                   separators=(',', ':'))
            try:
                conn.execute(
                    "MERGE (c:ContentChunk {chunk_id: $cid}) "
                    "SET c.snapshot_id = $sid, c.url = $url, "
                    "    c.pattern = $pat, c.representative_xpath = $rep, "
                    "    c.member_xpaths_json = $members, "
                    "    c.char_count = $chars, "
                    "    c.commutation_count = $commut, "
                    "    c.content_fields_json = $fields, "
                    "    c.text_preview = $preview, "
                    "    c.label = $label, "
                    "    c.extraction_trie_json = $ext_trie, "
                    "    c.created_at = $ts;",
                    parameters={
                        "cid": payload['chunk_id'],
                        "sid": snapshot_id,
                        "url": url,
                        "pat": payload['pattern'],
                        "rep": payload['representative_xpath'],
                        "members": members_json,
                        "chars": int(payload.get('char_count', 0)),
                        "commut": int(payload.get('commutation_count', 0)),
                        "fields": fields_json,
                        "preview": payload.get('text_preview', ''),
                        "label": payload.get('label') or '',
                        "ext_trie": trie_json,
                        "ts": ts,
                    }
                )
            except Exception as e:
                print(f"[SnapshotStore] Chunk save error: {e}")
                continue

            try:
                conn.execute(
                    "MATCH (s:DomSnapshot {snapshot_id: $sid}), "
                    "      (c:ContentChunk {chunk_id: $cid}) "
                    "MERGE (s)-[:HAS_CHUNK]->(c);",
                    parameters={"sid": snapshot_id, "cid": payload['chunk_id']}
                )
            except Exception:
                pass
            written += 1
        return written

    def load_chunks(self, snapshot_id: str) -> List[Dict[str, Any]]:
        """Return all chunks recorded for a snapshot, newest first."""
        conn = get_connection()
        out: List[Dict[str, Any]] = []
        try:
            res = conn.execute(
                "MATCH (c:ContentChunk {snapshot_id: $sid}) "
                "RETURN c.chunk_id, c.url, c.pattern, c.representative_xpath, "
                "       c.member_xpaths_json, c.char_count, c.commutation_count, "
                "       c.content_fields_json, c.text_preview, c.label, "
                "       c.extraction_trie_json, c.created_at "
                "ORDER BY c.created_at DESC;",
                parameters={"sid": snapshot_id}
            )
            while res.has_next():
                row = res.get_next()
                try:
                    members = json.loads(row[4]) if row[4] else []
                except Exception:
                    members = []
                try:
                    fields = json.loads(row[7]) if row[7] else {}
                except Exception:
                    fields = {}
                try:
                    trie = json.loads(row[10]) if row[10] else {}
                except Exception:
                    trie = {}
                out.append({
                    'chunk_id': row[0],
                    'snapshot_id': snapshot_id,
                    'url': row[1],
                    'pattern': row[2],
                    'representative_xpath': row[3],
                    'member_xpaths': members,
                    'char_count': row[5],
                    'commutation_count': row[6],
                    'content_fields': fields,
                    'text_preview': row[8],
                    'label': row[9] or None,
                    'extraction_trie': trie,
                    'created_at': row[11],
                })
        except Exception as e:
            print(f"[SnapshotStore] Chunk load error: {e}")
        return out

    def set_chunk_label(self, chunk_id: str, label: str) -> bool:
        """Manually assign (or clear) a label on a chunk. Persists to DB."""
        conn = get_connection()
        try:
            conn.execute(
                "MATCH (c:ContentChunk {chunk_id: $cid}) "
                "SET c.label = $label;",
                parameters={"cid": chunk_id, "label": label or ''}
            )
            return True
        except Exception as e:
            print(f"[SnapshotStore] Chunk label error: {e}")
            return False

    def load_content_tree_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Load the most recent content tree for a URL."""
        conn = get_connection()
        try:
            res = conn.execute(
                "MATCH (s:DomSnapshot {url: $url})"
                "-[:HAS_CONTENT_TREE]->(t:ContentTree) "
                "RETURN t.xpath_json "
                "ORDER BY s.captured_at DESC LIMIT 1;",
                parameters={"url": url}
            )
            if res.has_next():
                raw = res.get_next()[0]
                return json.loads(raw)
        except Exception:
            pass
        return None
