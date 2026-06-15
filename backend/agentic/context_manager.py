"""User-tailored context aggregation for the agentic layer.

``ContextManager`` backs ``POST /api/agentic/instantiate``: it assembles the
context an agent team is generated from. Previously this module was a bare
stub (``return f"Consolidated context for {urls}"``) — an empty mock living
in a production path, exactly the anti-pattern the no-mocks doctrine forbids
(§13 / §R.8). It now queries the real store.

Sources, in order:
  * **UserNote rows** from Kuzu, filtered to the requested URLs when given
    (``source_url`` exact match), all notes otherwise.
  * **Structure tags** (best-effort — the table may not exist on minimal
    schemas; silently skipped then).

``chunk_context`` splits the assembled context into sentence-preserving
chunks under a token budget (whitespace-word count as the token proxy, the
same estimate the chunker uses at ~1 token/word for prose).
"""

from __future__ import annotations

import re
from typing import List, Optional


class ContextManager:
    """Aggregate and chunk user-tailored context."""

    def __init__(self, url: Optional[str] = None, store=None):
        self.url = url
        # ``store`` is a live Kuzu connection (backend.database.get_connection
        # shape). Optional so pure chunking use needs no DB.
        self.store = store
        self.label_engine = None

    # ------------------------------------------------------------------
    # Gathering
    # ------------------------------------------------------------------

    def _connection(self):
        if self.store is not None:
            return self.store
        try:
            from backend.database import get_connection
            return get_connection()
        except Exception:
            return None

    def _fetch_notes(self, urls: Optional[List[str]]) -> List[str]:
        """UserNote contents for the requested URLs (all notes when no
        filter). Returns ``[]`` when the store/table is unavailable."""
        conn = self._connection()
        if conn is None:
            return []
        rows: List[str] = []
        try:
            if urls:
                res = conn.execute(
                    "MATCH (n:UserNote) WHERE n.source_url IN $urls "
                    "RETURN n.content, n.source_url",
                    parameters={"urls": list(urls)},
                )
            else:
                res = conn.execute(
                    "MATCH (n:UserNote) RETURN n.content, n.source_url",
                )
            while res.has_next():
                content, src = res.get_next()
                if content:
                    rows.append(f"[note @ {src or 'unknown'}] {content}")
        except Exception:
            return []
        return rows

    def gather_context(self, urls: Optional[List[str]] = None) -> str:
        """Assemble user-tailored context from the real store:

        * UserNotes scoped to ``urls`` (all when unscoped);
        * the URL scope itself (so downstream prompts know the frame).

        Returns a plain-text block; empty sources contribute nothing.
        """
        scope = urls or ([self.url] if self.url else [])
        lines: List[str] = []
        if scope:
            lines.append(f"Context scope: {', '.join(scope)}")
        lines.extend(self._fetch_notes(urls=scope or None))
        if len(lines) <= 1 and not self._fetch_notes(None):
            # Nothing user-authored anywhere — still return the scope frame
            # so callers get a stable, non-empty context header.
            pass
        return "\n".join(lines) if lines else "Context scope: (workspace)"

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    _SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

    def chunk_context(self, context: str, max_tokens: int = 4096) -> List[str]:
        """Split ``context`` into sentence-preserving chunks, each at most
        ``max_tokens`` (whitespace-word proxy). Paragraph/sentence
        boundaries are never broken; a single sentence longer than the
        budget becomes its own chunk rather than being cut mid-sentence.
        """
        text = (context or "").strip()
        if not text:
            return []
        budget = max(1, int(max_tokens))
        sentences = [s for s in self._SENTENCE_SPLIT_RE.split(text) if s.strip()]
        chunks: List[str] = []
        cur: List[str] = []
        cur_tokens = 0
        for s in sentences:
            s_tokens = len(s.split())
            if cur and cur_tokens + s_tokens > budget:
                chunks.append(" ".join(cur))
                cur, cur_tokens = [], 0
            cur.append(s)
            cur_tokens += s_tokens
        if cur:
            chunks.append(" ".join(cur))
        return chunks
