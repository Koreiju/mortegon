"""Compiled-In-From-Scans concept cards (Workstream W9; domain anchor
§8D.39, §5.4).

Hooks into the scanner pipeline to **auto-instantiate** concept nodes
whose existence derives from scan discoveries:

  * ``SearchableURL`` (§8D.39.1) — a URL whose search input field has
    been detected. Carries the search-and-paginate behaviour as a
    function-like ConceptNode (input ports query/samples; output port
    chunks).
  * ``DetectedAccessor`` (§8D.39.2) — an individual xpath → field
    selector for one named field on a specific domain.
  * ``XPathPattern`` (§8D.39.3 / §8D.15) — a generalised xpath
    identifying recurring structural roles across a domain family.
    Carries the persistent accessor table (§5.4 inverse lookup).
  * ``PinnedComponent`` is left to the legacy graph_editor path; the
    structure is the same.

Each card is auto-materialised in the unified Database (§8D.35) via
``graph_editor.create_concept``, with ``backing_pointer`` set to a
deterministic handle the runtime can later resolve to a concrete
implementation. The card's ``description`` is the canonical
functional declaration (§8D.40) used for apparition retrieval.

Callers: the scanner pipeline emits hooks via callbacks supplied at
construction. This module doesn't import the scanner directly to
avoid cycles; the dispatch lives in ``routes.py`` where the scanner
is already wired.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from backend.services import backing_version


def _domain_slug(url: str) -> str:
    """Stable slug component derived from a URL's domain."""
    if not url:
        return "unknown"
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    if not host:
        host = "unknown"
    return host.replace(".", "_").replace("-", "_")


def _short_hash(text: str, n: int = 8) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:n]


def _merge_pattern_tree(
    existing: Dict[str, Any], incoming: Dict[str, Any],
) -> Dict[str, Any]:
    """Recursively merge an incoming pattern_map tree into the existing one
    (§15.8.2 / ChunkPatternSchema.md §3.1 / §3.3 / §7 anti-pattern #3).

    Existing ``pattern_hash`` entries keep their first-discovery ``url_root`` /
    ``created_at`` and UNION their ``sampled_chunks`` (extend, don't respawn);
    new hashes are inserted; ``sub_patterns`` merge recursively.
    """
    merged: Dict[str, Any] = dict(existing)
    for phash, inc in incoming.items():
        if not isinstance(inc, dict):
            continue
        cur = merged.get(phash)
        if not isinstance(cur, dict):
            merged[phash] = inc
            continue
        out = dict(cur)
        # sampled_chunks: union, preserve order (existing first).
        seen: set = set()
        union: List[str] = []
        for cid in list(cur.get("sampled_chunks") or []) + list(inc.get("sampled_chunks") or []):
            if cid not in seen:
                seen.add(cid)
                union.append(cid)
        out["sampled_chunks"] = union
        # accessor_map: latest observation wins on conflict.
        out["accessor_map"] = {**(cur.get("accessor_map") or {}), **(inc.get("accessor_map") or {})}
        out["accessor_dict"] = dict(out["accessor_map"])
        # golden_trio: adopt incoming only if existing had none.
        if not any(cur.get("golden_trio") or []) and any(inc.get("golden_trio") or []):
            out["golden_trio"] = inc.get("golden_trio")
        # First-discovery anchor: keep existing url_root / created_at (§3.3).
        out["url_root"] = cur.get("url_root") or inc.get("url_root", "")
        out["created_at"] = cur.get("created_at") or inc.get("created_at", "")
        out["updated_at"] = inc.get("updated_at") or cur.get("updated_at", "")
        out["sub_patterns"] = _merge_pattern_tree(
            cur.get("sub_patterns") or {}, inc.get("sub_patterns") or {},
        )
        merged[phash] = out
    return merged


# ---------------------------------------------------------------------------
# Materialisers
# ---------------------------------------------------------------------------

class CompiledFromScansMaterialiser:
    """Creates compiled-from-scans concept nodes via graph_editor.

    Idempotent on ``concept_id`` collision — re-running the same hook
    is safe (re-emits the same concept_id; backend create returns the
    existing record).
    """

    def __init__(self, graph_editor=None, concept_index=None):
        self._graph_editor = graph_editor
        self._concept_index = concept_index

    # -------------------------------------------------------------------
    # SearchableURL
    # -------------------------------------------------------------------

    def materialise_searchable_url(
        self,
        *,
        url: str,
        search_field_xpath: str,
        query_param_name: str = "q",
        pagination_button_xpath: str = "",
        detected_at: str = "",
        workspace_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Auto-instantiate a SearchableURL concept node (§8D.39.1)."""
        if not self._graph_editor:
            return None
        domain = _domain_slug(url)
        cid_seed = f"searchable_url::{domain}::{_short_hash(search_field_xpath or url)}"
        concept_id = f"surl_{domain}_{_short_hash(cid_seed, 12)}"

        description = (
            f"Searches `{url}` for query strings via "
            f"`{query_param_name}`; paginates via "
            f"`{pagination_button_xpath or '<none>'}` until samples count "
            f"reached, pagination stale, or duration_s elapsed. Input ports: "
            f"query (str), samples (int), duration_s (int, time-box §15.10). "
            f"Output port: chunks (list[ChunkInstance])."
        )
        data = json.dumps({
            "url": url,
            "search_field_xpath": search_field_xpath,
            "query_param_name": query_param_name,
            "pagination_button_xpath": pagination_button_xpath,
            "detected_at": detected_at,
            # §8D.4.1 port schema: SearchableURL is a function-pattern
            # node with empirically inferred ports. Wired downstream
            # consumers read this schema for typed-edge validation.
            "ports": {
                "inputs": [
                    {"name": "query",      "type": "str", "required": True},
                    {"name": "samples",    "type": "int", "required": False, "default": 20},
                    # §15.10 / §9.8 time-box (Q.2): exposed scan duration
                    # in wall-clock seconds. 0 ⇒ sample-bounded (legacy).
                    {"name": "duration_s", "type": "int", "required": False, "default": 0},
                ],
                "outputs": [
                    {"name": "chunks", "type": "list[ChunkInstance]"},
                ],
            },
        }, indent=2)
        backing_pointer = f"compiled_from_scans::searchable_url::{concept_id}"
        node = self._graph_editor.create_concept(
            concept_id=concept_id,
            name=f"search_{domain}",
            description=description,
            data=data,
            rendering="",
            backing_pointer=backing_pointer,
            provenance="derived-from-chunk",
            workspace_id=workspace_id,
            type_hint="searchable_url",
        )
        # §8D.39.6 — every scan that materialises this node bumps the
        # backing-pointer version so dependent compiles re-fire even if
        # the data text is byte-identical.
        backing_version.bump(workspace_id, backing_pointer)
        self._upsert_index(node)
        return self._node_to_dict(node)

    # -------------------------------------------------------------------
    # DetectedAccessor
    # -------------------------------------------------------------------

    def materialise_detected_accessor(
        self,
        *,
        url: str,
        xpath: str,
        field_type: str,
        text_hint: str = "",
        workspace_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        if not self._graph_editor:
            return None
        domain = _domain_slug(url)
        cid_seed = f"detected_accessor::{domain}::{xpath}::{field_type}"
        concept_id = f"daccess_{domain}_{_short_hash(cid_seed, 12)}"

        description = (
            f"Reads `{field_type}` from `{xpath}` on `{domain}` pages."
        )
        data = json.dumps({
            "url": url,
            "xpath": xpath,
            "field_type": field_type,
            "text_hint": text_hint,
            "domain": domain,
            # §8D.4.1 port schema: DetectedAccessor takes a DomSnapshot
            # and returns a value of the empirically observed type.
            # The "<inferred>" wrapper carries the most-specific type
            # the scanner has observed for this selector.
            "ports": {
                "inputs": [
                    {"name": "dom", "type": "DomSnapshot", "required": True},
                ],
                "outputs": [
                    {"name": "value", "type": field_type or "str"},
                ],
            },
        }, indent=2)
        backing_pointer = f"compiled_from_scans::detected_accessor::{concept_id}"
        node = self._graph_editor.create_concept(
            concept_id=concept_id,
            name=f"{field_type}_at_{domain}_{_short_hash(xpath, 6)}",
            description=description,
            data=data,
            rendering="",
            backing_pointer=backing_pointer,
            provenance="derived-from-chunk",
            workspace_id=workspace_id,
            type_hint="detected_accessor",
        )
        backing_version.bump(workspace_id, backing_pointer)  # §8D.39.6
        self._upsert_index(node)
        return self._node_to_dict(node)

    # -------------------------------------------------------------------
    # XPathPattern
    # -------------------------------------------------------------------

    def materialise_xpath_pattern(
        self,
        *,
        domain: str,
        pattern: str,
        accessor_map: Optional[Dict[str, str]] = None,
        instance_count: int = 0,
        workspace_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """§8D.39.3 / §5.4 — generalised pattern with accessor table."""
        if not self._graph_editor:
            return None
        domain_safe = _domain_slug(f"http://{domain}") if domain else "unknown"
        pattern_hash = _short_hash(pattern, 12)
        concept_id = f"xpath_pattern_{domain_safe}_{pattern_hash}"

        description = (
            f"Identifies `{pattern}` instances across the `{domain or '?'}` "
            f"domain family; accessor mapping provides field selectors for "
            f"matching instances. {instance_count} instance(s) so far."
        )
        data = json.dumps({
            "pattern": pattern,
            "domain": domain,
            "accessor_map": accessor_map or {},
            "instance_count": int(instance_count),
            "pattern_hash": pattern_hash,
            # §8D.4.1 port schema: XPathPattern takes a DomSnapshot
            # and returns matching instances; each instance's shape is
            # determined by the accessor_map field types.
            "ports": {
                "inputs": [
                    {"name": "dom", "type": "DomSnapshot", "required": True},
                ],
                "outputs": [
                    {"name": "instances",
                     "type": "list[dict]",
                     "fields": list((accessor_map or {}).keys())},
                ],
            },
        }, indent=2)
        backing_pointer = f"compiled_from_scans::xpath_pattern::{concept_id}"
        node = self._graph_editor.create_concept(
            concept_id=concept_id,
            name=f"pattern_{domain_safe}_{pattern_hash[:6]}",
            description=description,
            data=data,
            rendering="",
            backing_pointer=backing_pointer,
            provenance="derived-from-chunk",
            workspace_id=workspace_id,
            type_hint="xpath_pattern",
        )
        backing_version.bump(workspace_id, backing_pointer)  # §8D.39.6
        self._upsert_index(node)
        return self._node_to_dict(node)

    # -------------------------------------------------------------------
    # pattern_map (§15.8.2)
    # -------------------------------------------------------------------

    def update_pattern_map(
        self,
        *,
        schemas: Dict[str, Dict[str, Any]],
        url_root: str = "",
        domain: str = "",
        workspace_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """§15.8.2 / ChunkPatternSchema.md §3 — upsert the workspace's single
        ``pattern_map`` ConceptNode, MERGING the incoming schema tree into the
        existing one.

        Accretive by contract (§3.1 first-detect-vs-re-detect, §3.3 cross-URL
        extension, §7 anti-pattern #3 "extend, don't respawn"): an existing
        ``pattern_hash`` keeps its first-discovery ``url_root`` / ``created_at``
        and grows its ``sampled_chunks`` (union); a new hash is inserted. Each
        call updates ``updated_at`` and re-emits the node so the panel accretes
        across snapshots/URLs during a scan (§18.29 live-update contract). The
        schema tree lives entirely inside this one node's ``data`` field — never
        a separate table (§7 one-record rule). The node is a PEER of the
        fixtures, not a child of Database.
        """
        if not self._graph_editor or not schemas:
            return None
        ws = workspace_id or "_default"
        concept_id = f"pattern_map::{ws}"
        backing_pointer = f"pattern_map::{ws}"

        existing = None
        try:
            existing = self._graph_editor.get_concept(concept_id)
        except Exception:
            existing = None

        existing_tree: Dict[str, Any] = {}
        if existing is not None and getattr(existing, "data", ""):
            try:
                parsed = json.loads(existing.data)
                existing_tree = parsed.get("patterns", parsed) if isinstance(parsed, dict) else {}
            except Exception:
                existing_tree = {}

        merged = _merge_pattern_tree(existing_tree, schemas)
        n_patterns = len(merged)
        n_trio = sum(1 for s in merged.values()
                     if isinstance(s, dict) and any(s.get("golden_trio") or []))
        data = json.dumps({
            "url_root": url_root,
            "domain": domain,
            "pattern_count": n_patterns,
            "patterns": merged,
        }, indent=2)
        description = (
            f"§15.8.2 live pattern map — {n_patterns} repeating pattern(s) "
            f"from scans of `{domain or url_root or '?'}`; {n_trio} carry a "
            f"golden trio (title+link+content)."
        )

        if existing is not None:
            node = self._graph_editor.update_concept(
                concept_id,
                data=data,
                description=description,
                rendering="",
            ) or existing
        else:
            node = self._graph_editor.create_concept(
                concept_id=concept_id,
                name="pattern_map",
                description=description,
                data=data,
                rendering="",
                backing_pointer=backing_pointer,
                provenance="derived-from-chunk",
                workspace_id=workspace_id,
                type_hint="pattern_map",
            )
        backing_version.bump(workspace_id, backing_pointer)
        self._upsert_index(node)
        return self._node_to_dict(node)

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _upsert_index(self, node) -> None:
        """Best-effort upsert into the Concept Index (W5)."""
        if self._concept_index is None or node is None:
            return
        try:
            self._concept_index.upsert_slot(
                card_id=node.concept_id,
                description=node.description,
                rendering=node.rendering,
                provenance=node.provenance,
                workspace_id=node.workspace_id,
            )
        except Exception:
            pass

    @staticmethod
    def _node_to_dict(node) -> Dict[str, Any]:
        if node is None:
            return {}
        return {
            "concept_id": node.concept_id,
            "name": node.name,
            "description": node.description,
            "data": node.data,
            "type_hint": node.type_hint,
            "provenance": node.provenance,
            "workspace_id": node.workspace_id,
        }
