"""
pattern_labeler.py — Pattern-level SLM labeling (Phase 3).

One semantic label per generalized pattern. Labels are keyed by
``TriePattern.pattern_id``, never per-instance — the whole point of the
trie is that instances share the same identity. Only *content* patterns
get a label; non-content structural scaffolding is skipped.

The prompt we hand the SLM is literally the knowledge panel that the
``ChunkBuilder`` already aggregated. That's the user's thesis in a single
line: **the knowledge panel IS the prompt.**

Public API
----------
    labeler = PatternLabeler()              # uses the default SLMClient
    row = labeler.label_pattern(chunk, tag_set)
    rows = labeler.label_trie(built, chunks)
    persist_pattern_labels(conn, rows)
    rows = load_pattern_labels(conn, version_id)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from backend.dom.trie_persistence import BuiltTrie, PatternRow
from backend.mapper.chunk_builder import Chunk

logger = logging.getLogger(__name__)


VALID_ROLES = {
    "nav", "card", "list_item", "article", "form",
    "filter", "banner", "footer", "ad", "unknown",
}


class PatternLabelingError(RuntimeError):
    """SLM returned something we cannot turn into a label."""


@dataclass
class PatternLabelRow:
    """A single row destined for the ``PatternLabel`` Kuzu table."""

    label_id: str
    pattern_id: str
    version_id: str
    role: str
    category: str
    summary: str
    confidence: float
    raw_json: str
    model: str
    created_at: str


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_KNOWLEDGE_PANEL_ORDER = (
    "text.title",
    "text.heading",
    "text.subtitle",
    "text.body",
    "text.visible",
    "text.caption",
    "interactive.label",
    "interactive.placeholder",
    "interactive.value",
    "urls.link",
    "urls.nav",
    "media.images",
    "media.video",
    "json_data",
)


def _knowledge_panel_text(content_fields: Dict[str, List[str]],
                          max_per_cat: int = 6,
                          max_value_len: int = 120) -> str:
    """Render ``content_fields`` as a deterministic compact panel."""
    if not content_fields:
        return "(empty)"

    # Order known categories first, then any novel ones alphabetically.
    seen: set = set()
    ordered: List[str] = []
    for cat in _KNOWLEDGE_PANEL_ORDER:
        if cat in content_fields:
            ordered.append(cat)
            seen.add(cat)
    for cat in sorted(content_fields.keys()):
        if cat not in seen:
            ordered.append(cat)

    lines: List[str] = []
    for cat in ordered:
        values = content_fields.get(cat) or []
        if not values:
            continue
        sample = values[:max_per_cat]
        rendered = " | ".join(_truncate(v, max_value_len) for v in sample)
        lines.append(f"{cat}: {rendered}")
    return "\n".join(lines) if lines else "(empty)"


def _truncate(text: str, limit: int) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _build_prompt(chunk: Chunk, tag_set: List[str]) -> str:
    """The user-turn prompt fed into ``SLMClient.generate_json``."""
    kp = _knowledge_panel_text(chunk.content_fields)
    tag_str = ", ".join(tag_set) if tag_set else "(none)"
    # Keep the XPath out of the prompt — it's not semantic, and the SLM
    # doesn't need to know the page structure; it needs to know WHAT this
    # repeating region represents.
    return (
        f"Repeating DOM pattern, observed {chunk.commutation_count} times.\n"
        f"Content categories observed: {tag_str}.\n\n"
        f"Knowledge panel:\n{kp}\n\n"
        f"Classify this pattern. Return ONLY JSON with keys: "
        f"role, category, summary, confidence."
    )


# ---------------------------------------------------------------------------
# Core labeler
# ---------------------------------------------------------------------------


class PatternLabeler:
    """Run the SLM on one content pattern at a time."""

    SYSTEM_PROMPT = (
        "You are labeling a repeating DOM pattern on a website. "
        "Output ONLY JSON with keys: role, category, summary, confidence. "
        "role must be one of: nav, card, list_item, article, form, "
        "filter, banner, footer, ad, unknown. "
        "category is 1-3 words in snake_case (e.g. tarot_card, daily_horoscope_link). "
        "summary is a single sentence describing what this repeating region represents. "
        "confidence is a float in [0,1] reflecting how sure you are. "
        "Never add explanation outside the JSON."
    )

    def __init__(self, slm: Optional[Any] = None, *,
                 model_name: str = "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
                 max_retries: int = 3):
        self._slm_factory: Optional[Callable[[], Any]] = None
        self._slm = slm
        self.model_name = model_name
        self.max_retries = max(1, int(max_retries))

    # -- lazy SLM access so tests can inject a stub --------------------

    @property
    def slm(self) -> Any:
        if self._slm is None:
            from backend.services.slm_client import SLMClient
            self._slm = SLMClient(model_name=self.model_name)
        return self._slm

    # -- public API ----------------------------------------------------

    def label_pattern(self, chunk: Chunk, tag_set: List[str]) -> Dict[str, Any]:
        """Return a normalized label dict for one pattern.

        Raises :class:`PatternLabelingError` when the SLM fails to
        produce parseable JSON after ``max_retries`` attempts.
        """
        base_prompt = _build_prompt(chunk, tag_set)
        last_raw = ""
        for attempt in range(self.max_retries):
            prompt = base_prompt
            if attempt > 0:
                prompt += (
                    "\n\nYour previous response was not valid JSON. "
                    "Return ONLY a strict JSON object. No prose."
                )
            raw = self.slm.generate_json(prompt, system_prompt=self.SYSTEM_PROMPT)
            last_raw = json.dumps(raw) if isinstance(raw, dict) else str(raw)
            label = _normalize_label(raw)
            if label is not None:
                return label
        raise PatternLabelingError(
            f"SLM failed to produce a valid label for pattern "
            f"{chunk.pattern!r} after {self.max_retries} attempts. "
            f"Last raw response: {last_raw[:500]}"
        )

    def label_trie(
        self,
        built: BuiltTrie,
        chunks: List[Chunk],
        *,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[PatternLabelRow]:
        """Label every content-bearing chunk in ``built``.

        A chunk is the partitioning unit that carries a knowledge panel
        (``content_fields``). The SLM labels each chunk once; the label
        is keyed to the chunk-root's ``pattern_id`` so Phase 4 can
        attach an embedding to the same row.

        Container chunk-roots (e.g. ``/main/section/article``) routinely
        have an empty ``TriePattern.tag_set`` because tags live on the
        descendant leaves, not on the container. We use
        ``chunk.content_fields`` — which aggregates across all tagged
        descendants — as the de-facto tag set for the SLM prompt.

        Patterns with no chunk mapping (pure structural scaffolding) are
        skipped, matching the handoff's rule that they carry no
        meaningful label.
        """
        rows: List[PatternLabelRow] = []
        pat_by_key = built.by_pattern_key
        candidates: List[Tuple[PatternRow, Chunk, List[str]]] = []
        for chunk in chunks:
            if not chunk.content_fields:
                continue  # nothing to label — no knowledge panel
            pat = pat_by_key.get(chunk.pattern)
            if pat is None:
                continue
            effective_tag_set = (
                list(pat.tag_set)
                if pat.tag_set
                else sorted(chunk.content_fields.keys())
            )
            candidates.append((pat, chunk, effective_tag_set))

        total = len(candidates)
        for idx, (pat, chunk, tag_set) in enumerate(candidates, 1):
            if progress_cb:
                progress_cb(idx, total, pat.pattern)
            try:
                label = self.label_pattern(chunk, tag_set)
            except PatternLabelingError as exc:
                logger.warning("Pattern labeling failed for %s: %s", pat.pattern, exc)
                # Record a low-confidence fallback so downstream phases
                # still have something to embed, but mark it clearly.
                label = {
                    "role": "unknown",
                    "category": "unknown",
                    "summary": "SLM labeling failed; fallback label.",
                    "confidence": 0.0,
                    "raw_json": "{}",
                }
            rows.append(
                _make_row(
                    pattern_id=pat.pattern_id,
                    version_id=pat.version_id,
                    label=label,
                    model=self.model_name,
                )
            )
        return rows


# ---------------------------------------------------------------------------
# Label normalization
# ---------------------------------------------------------------------------


def _normalize_label(raw: Any) -> Optional[Dict[str, Any]]:
    """Coerce an SLM response into a clean label dict, or ``None``.

    Requires at minimum ``role`` and ``summary``. Fills in safe defaults
    for ``category`` and ``confidence`` because small models routinely
    drop them.
    """
    if not isinstance(raw, dict) or not raw:
        return None

    role = str(raw.get("role", "")).strip().lower()
    if role not in VALID_ROLES:
        # Tolerate near-hits: tiny models will say "Card" or "navigation".
        role = _coerce_role(role)
        if role not in VALID_ROLES:
            return None

    summary = str(raw.get("summary", "")).strip()
    if not summary:
        return None

    category = str(raw.get("category", "")).strip().lower()
    if not category:
        category = role
    # snake_case normalize
    category = category.replace(" ", "_").replace("-", "_")
    category = "".join(ch for ch in category if ch.isalnum() or ch == "_")
    if not category:
        category = role

    try:
        confidence = float(raw.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return {
        "role": role,
        "category": category,
        "summary": summary,
        "confidence": confidence,
        "raw_json": json.dumps(raw, sort_keys=True, separators=(",", ":")),
    }


def _coerce_role(role: str) -> str:
    """Best-effort mapping of fuzzy roles onto the controlled vocabulary."""
    role = role.strip().lower()
    if not role:
        return "unknown"
    mapping = {
        "navigation": "nav",
        "menu": "nav",
        "link": "nav",
        "tile": "card",
        "item": "list_item",
        "listitem": "list_item",
        "list-item": "list_item",
        "post": "article",
        "blog_post": "article",
        "search": "filter",
        "search_box": "filter",
        "input": "form",
        "hero": "banner",
        "advertisement": "ad",
    }
    if role in mapping:
        return mapping[role]
    # Substring fallbacks catch "tarot_card" -> "card"
    for token in ("card", "nav", "article", "list_item", "form",
                  "filter", "banner", "footer", "ad"):
        if token in role:
            return token
    return "unknown"


# ---------------------------------------------------------------------------
# Row assembly
# ---------------------------------------------------------------------------


def _make_row(pattern_id: str, version_id: str, label: Dict[str, Any],
              model: str) -> PatternLabelRow:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    label_id = _label_id(pattern_id, version_id)
    return PatternLabelRow(
        label_id=label_id,
        pattern_id=pattern_id,
        version_id=version_id,
        role=label["role"],
        category=label["category"],
        summary=label["summary"],
        confidence=float(label["confidence"]),
        raw_json=label.get("raw_json") or json.dumps(label, sort_keys=True),
        model=model,
        created_at=now,
    )


def _label_id(pattern_id: str, version_id: str) -> str:
    """Deterministic: one label per (pattern, version)."""
    return hashlib.sha1(f"lbl|{version_id}|{pattern_id}".encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------------------------
# Kuzu persistence
# ---------------------------------------------------------------------------


def persist_pattern_labels(conn, rows: Iterable[PatternLabelRow]) -> None:
    """Idempotent write of label rows keyed on ``(pattern_id, version_id)``.

    Overwrites existing rows for the same key so re-running Phase 3
    doesn't duplicate entries — a requirement from the handoff's
    idempotence test.
    """
    rows = list(rows)
    if not rows:
        return

    for row in rows:
        # Idempotence: delete any prior label for this (pattern, version).
        conn.execute(
            "MATCH (l:PatternLabel {label_id: $lid}) DETACH DELETE l",
            parameters={"lid": row.label_id},
        )
        conn.execute(
            "CREATE (l:PatternLabel {"
            "label_id: $label_id, pattern_id: $pattern_id, version_id: $version_id, "
            "role: $role, category: $category, summary: $summary, "
            "confidence: $confidence, raw_json: $raw_json, model: $model, "
            "created_at: $created_at})",
            parameters={
                "label_id": row.label_id,
                "pattern_id": row.pattern_id,
                "version_id": row.version_id,
                "role": row.role,
                "category": row.category,
                "summary": row.summary,
                "confidence": float(row.confidence),
                "raw_json": row.raw_json,
                "model": row.model,
                "created_at": row.created_at,
            },
        )
        # Link label -> TriePattern if the pattern exists.
        try:
            conn.execute(
                "MATCH (l:PatternLabel {label_id: $lid}), "
                "(t:TriePattern {pattern_id: $pid}) "
                "MERGE (l)-[:LABELS_PATTERN]->(t)",
                parameters={"lid": row.label_id, "pid": row.pattern_id},
            )
        except Exception:
            # Test schemas may omit LABELS_PATTERN — non-fatal.
            pass


def load_pattern_labels(conn, version_id: str) -> List[PatternLabelRow]:
    """Read every label for a given trie version."""
    res = conn.execute(
        "MATCH (l:PatternLabel {version_id: $vid}) RETURN "
        "l.label_id, l.pattern_id, l.version_id, l.role, l.category, "
        "l.summary, l.confidence, l.raw_json, l.model, l.created_at",
        parameters={"vid": version_id},
    )
    out: List[PatternLabelRow] = []
    while res.has_next():
        r = res.get_next()
        out.append(
            PatternLabelRow(
                label_id=r[0],
                pattern_id=r[1],
                version_id=r[2],
                role=r[3],
                category=r[4],
                summary=r[5],
                confidence=float(r[6]),
                raw_json=r[7] or "{}",
                model=r[8] or "",
                created_at=r[9] or "",
            )
        )
    return out
