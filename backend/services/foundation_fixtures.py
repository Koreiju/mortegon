"""Foundation fixture concept nodes (Workstream W11b; domain anchor
§8D.12, §8D.27, §8D.32, §8D.35; §9.5.1 fixtures; §S.1 deprecation).

The **three** foundational concept nodes (``Database``, ``WebBrowser``,
``Agent``) are pre-wired with backing pointers to app infrastructure.
They are always-present on the canvas; they cannot be deleted; their
backing pointers resolve through the runtime registry (C4).

**§S.1 (2026-06-12) — the fourth fixture, ``Editor``, is DEPRECATED and
removed.** Its create/link/overwrite/delete graph-mutation gestures are
intrinsic to the unified knowledge-panel ↔ compute-graph scheme (in-node
editing + markdown-gesture syntax parsing perform graph mutation
implicitly), so a separate ``Editor`` *fixture* (card + python_object
tree) is redundant. The gestures survive as the panel scheme's own
mutation path — ``/concepts`` + ``/concept_edges`` (and the ``/editor/*``
gesture routes) over the same ``create_concept`` / ``create_concept_edge``
/ ``update_concept`` / ``delete_concept`` lifecycle the agent emitter uses.

Per ``docs/code_constraints/backend_services.md`` §1.10 (anti-goal
§18.27) ``ensure_foundation_fixtures(workspace_id)`` MUST produce
exactly THREE root python_object ConceptNodes plus their member trees.

This module idempotently materialises them on workspace open. The
``ensure_foundation_fixtures(workspace_id)`` call is safe to invoke
repeatedly — the graph_editor's create is idempotent on concept_id.

Concept IDs are stable per workspace so re-opens find the same
fixtures:

  * ``fixture::database::<workspace_id>``     — Database card
  * ``fixture::web_browser::<workspace_id>``  — WebBrowser card
  * ``fixture::agent::<workspace_id>``        — Agent card (§8D.27)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _ws_slug(workspace_id: str) -> str:
    return (workspace_id or "_default").replace("/", "_").replace("\\", "_")


# ---------------------------------------------------------------------------
# Fixture definitions
# ---------------------------------------------------------------------------

def _database_fixture_spec(workspace_id: str) -> Dict[str, Any]:
    ws = _ws_slug(workspace_id)
    return {
        "concept_id": f"fixture::database::{ws}",
        "name": "Database",
        "description": (
            "Unified workspace memory (§8D.35). Holds the empirical "
            "chunk corpus, concept graph, web ontology, live "
            "computation graph, and meta-cognitive sub-region. "
            "Methods: tfidf_retrieve(query, k), cypher(query), "
            "search(natural_language), walk(node_id, depth), "
            "fly_to(node_id), frame_all(), focus_workspace(url), "
            "set_visibility(url, hidden), recompute_umap()."
        ),
        "data": json.dumps({
            "method_axes": ["retrieval", "recursion", "interaction", "navigation", "ontology_walk"],
            "scope_default": "workspace",
        }, indent=2),
        "backing_pointer": "fixture::database",
        "provenance": "user-authored",   # foundational; not derived
        "workspace_id": workspace_id,
        "type_hint": "fixture_database",
    }


def _web_browser_fixture_spec(workspace_id: str) -> Dict[str, Any]:
    ws = _ws_slug(workspace_id)
    return {
        "concept_id": f"fixture::web_browser::{ws}",
        "name": "WebBrowser",
        "description": (
            "Live Selenium-backed web runtime (§8D.12). Methods: "
            "snapshot(), navigate(url), click(xpath), search(query), "
            "more_results(), filter(facet, value), scan(url, query?, "
            "duration_s?), web_query(url, query?, samples). scan's "
            "duration_s is the §15.10 timed-scan time-box (Q.2). Emits "
            "chunks into Database on scan."
        ),
        "data": json.dumps({
            "methods": ["snapshot", "navigate", "click", "search",
                        "more_results", "filter", "web_query"],
        }, indent=2),
        "backing_pointer": "fixture::web_browser",
        "provenance": "user-authored",
        "workspace_id": workspace_id,
        "type_hint": "fixture_web_browser",
    }


# §S.1 (2026-06-12) — the Editor fourth foundational fixture is DEPRECATED.
# `_editor_fixture_spec` was removed: in-node editing + markdown-gesture
# syntax parsing over recursive text structures already perform graph
# mutation implicitly within the unified knowledge-panel ↔ compute-graph
# scheme, so a separate Editor *fixture* (card + python_object tree) is
# redundant. The create/link/overwrite/delete gestures survive as the panel
# scheme's own mutation path — the `/concepts` + `/concept_edges` routes the
# panel uses and the same `create_concept` / `create_concept_edge` /
# `update_concept` / `delete_concept` lifecycle the agent emitter calls (the
# `/editor/*` routes remain only as generic gesture-drivers). There are now
# THREE fixtures: Agent, WebBrowser, Database (DOMAIN_MODEL §9.5 / §18.27).


def _agent_fixture_spec(workspace_id: str) -> Dict[str, Any]:
    """§8D.27 — the Agent fixture: structural pillar that anchors any
    user-authored agent body (perception / transformer / emitter cards
    per §8D.27.2) and exposes the meta-cognition tick + spawn / fork
    surface (§8D.32). Like Database and WebBrowser this is a structural
    fixture — un-deletable, always present, declares its method
    catalogue in its data block so ConceptComputeNode + the user's
    suggester surface have a typed handle to wire from.

    The Agent fixture is intentionally lightweight — the actual agent
    body lives in user-authored concept nodes that the user designates
    as the parameter card (§8D.37). The fixture is the discoverability
    anchor: a place every workspace radiates from for "spawn an agent",
    "wire an action emitter", "read cascade status".
    """
    ws = _ws_slug(workspace_id)
    return {
        "concept_id": f"fixture::agent::{ws}",
        "name": "Agent",
        "description": (
            "SLM primitive surface + meta-cognition tick (§9.5.1, §8D.27, "
            "§8D.32). Primary primitives: meta_prompt(text) — set the "
            "system / meta directive; prompt(text) — issue the immediate "
            "user-style prompt; output(schema?) — fire the SLM and "
            "return free text or a pydantic-typed structured result. "
            "Companions: invoke(meta_prompt, prompt, output_template?) "
            "as the legacy three-in-one convenience wrapper, "
            "tick(parameter_card_id), spawn(goal, name?), "
            "fork(source_id, name?), perceive(parameter_card_id), "
            "emit(action_json). Action vocabulary: CreateCardAction, "
            "LinkAction, WriteFieldAction, InvokeAction, DeleteAction, "
            "CommitSubgraphAction, RequestUserReviewAction, "
            "SpawnAgentAction. The agent's body is the user's wired "
            "computation graph; this fixture is the structural anchor "
            "that exposes the SLM primitives + the cascade scheduler."
        ),
        "data": json.dumps({
            "methods": [
                "meta_prompt", "prompt", "output",
                "invoke", "tick", "spawn", "fork",
                "perceive", "emit",
            ],
            "action_vocabulary": [
                "CreateCardAction", "LinkAction", "WriteFieldAction",
                "InvokeAction", "DeleteAction", "CommitSubgraphAction",
                "RequestUserReviewAction", "SpawnAgentAction",
            ],
            "io_signature": {
                "meta_prompt": {"inputs": ["text:str"],
                                "output": "None"},
                "prompt":      {"inputs": ["text:str"],
                                "output": "None"},
                "output":      {"inputs": ["schema:BaseModel?"],
                                "output": "BaseModel|str"},
                "invoke":      {"inputs": ["meta_prompt:str", "prompt:str",
                                           "output_template:BaseModel?"],
                                "output": "BaseModel|str"},
                "tick":        {"inputs": ["parameter_card_id:ConceptId"],
                                "output": "MetaCognitionAction"},
                "spawn":       {"inputs": ["goal:str", "name:str?"],
                                "output": "ConceptId"},
                "fork":        {"inputs": ["source_id:ConceptId", "name:str?"],
                                "output": "ConceptId"},
            },
        }, indent=2),
        "backing_pointer": "fixture::agent",
        "provenance": "user-authored",
        "workspace_id": workspace_id,
        "type_hint": "fixture_agent",
    }


# ---------------------------------------------------------------------------
# Materialisation
# ---------------------------------------------------------------------------

# §8D.4.2 + §9.5.1 — qualified-name map for the **three** fixtures'
# Python-native Object trees. Pinned here so workspace bootstrap can
# call the python_api_materialiser idempotently for each fixture,
# producing the read-only Property/Function subgraphs the user expands
# via right-click.
#
# These are the *capabilities* the fixture cards represent. A fixture's
# concept card is the discoverability anchor (always-present); the
# Python-native subtree is the operational handle on the backing class.
#
# §S.1 (2026-06-12): the former fourth `Editor` target (also backed by
# `GraphEditor`) is removed — its graph-mutation gestures are intrinsic to
# the unified panel↔compute-graph scheme, not a fixture. The mutation
# primitives still live on `GraphEditor` (Database's backing class) and are
# reached via `/concepts` + `/concept_edges` + the `/editor/*` gesture
# routes; they no longer need their own fixture tree.
FOUNDATION_PYTHON_TARGETS: Dict[str, str] = {
    "Database":   "backend.services.graph_editor.GraphEditor",
    "WebBrowser": "backend.services.selenium_client.WebBrowserManager",
    "Agent":      "backend.services.agent_runtime.MetaCognitionTick",
}

# §3.1 — the workspace's canonical imports module. `ensure_foundation_python_trees`
# materialises it via the library-imports middleware (the three-fixture trees are
# the first application of the §9.7 rule); the per-qualname loop above is the
# fallback when the module can't be imported.
WORKSPACE_IMPORTS_MODULE = "backend.wfh_imports"


def ensure_foundation_python_trees(
    graph_editor,
    *,
    workspace_id: str = "",
    concept_index=None,
) -> List[Dict[str, Any]]:
    """§8D.4.2 — materialise the Python-native Object/Property/Function
    tree for each foundational fixture on workspace bootstrap.

    Idempotent — re-runs reuse existing concept ids and bump the
    backing-pointer version per §8D.39.6 so dependent compiles re-fire.
    Best-effort: import / class-resolution failures are logged and
    skipped without raising; the fixture cards stay usable even when
    a Python class can't be resolved at boot time.
    """
    try:
        from backend.services.python_api_materialiser import PythonAPIMaterialiser
    except Exception as e:
        logger.warning("FoundationPythonTrees: materialiser import failed: %s", e)
        return []

    mat = PythonAPIMaterialiser(graph_editor=graph_editor,
                                concept_index=concept_index)
    materialised: List[Dict[str, Any]] = []
    # §3.1 — preferred path: materialise the whole workspace imports module via
    # the library-imports middleware (the three-fixture trees are the first
    # application of the §9.7 rule). If it yields roots we're done; otherwise
    # fall through to the per-qualname loop (e.g. the imports module failed to
    # import for any reason — the fixtures must still come up).
    try:
        roots = mat.materialise_module(
            WORKSPACE_IMPORTS_MODULE, workspace_id=workspace_id,
        )
        if roots:
            for r in roots:
                materialised.append({
                    "fixture": (r.get("name") or ""),
                    "qualified_name": (r.get("backing_pointer", "")
                                       .split("::", 1)[-1]),
                    "object_concept_id": r.get("concept_id"),
                })
            return materialised
    except Exception as e:
        logger.warning("FoundationPythonTrees: materialise_module(%s) failed, "
                       "falling back to per-qualname loop: %s",
                       WORKSPACE_IMPORTS_MODULE, e)
    for fixture_name, qualified in FOUNDATION_PYTHON_TARGETS.items():
        try:
            rec = mat.materialise_qualified_name(
                qualified, workspace_id=workspace_id,
            )
            if rec is not None:
                materialised.append({
                    "fixture": fixture_name,
                    "qualified_name": qualified,
                    "object_concept_id": rec.get("concept_id"),
                })
            else:
                logger.info("FoundationPythonTrees: %s (%s) — class not resolvable",
                            fixture_name, qualified)
        except Exception as e:
            logger.warning("FoundationPythonTrees: %s materialise failed: %s",
                           qualified, e)
    return materialised


def ensure_foundation_fixtures(
    graph_editor,
    *,
    workspace_id: str = "",
    concept_index=None,
    materialise_python: bool = True,
) -> List[Dict[str, Any]]:
    """Idempotent: create all fixtures if they don't exist.

    Returns a list of the materialised fixture dicts (whether newly
    created or already present). Safe to call on every workspace
    open — graph_editor.create_concept returns the existing record
    on concept_id collision.

    When ``materialise_python=True`` (the default), the three fixtures'
    Python-native Object/Property/Function trees (§8D.4.2) are also
    materialised so right-click expansion of a fixture immediately
    surfaces its read-only subgraph.
    """
    out: List[Dict[str, Any]] = []
    # §S.1 MIGRATION — purge any deprecated Editor fixture left in a
    # pre-existing default workspace (created before §S removed it). The
    # `fixture::` delete-guard now refuses to remove it through normal
    # paths, so we use the guard-bypassing `force=True` (this is the ONLY
    # call site that does). Idempotent: a no-op once the card is gone.
    try:
        ws = _ws_slug(workspace_id)
        stale_editor = f"fixture::editor::{ws}"
        if graph_editor.get_concept(stale_editor) is not None:
            graph_editor.delete_concept(stale_editor, force=True)
            logger.info("FoundationFixtures: purged deprecated Editor fixture %s (§S.1)",
                        stale_editor)
            if concept_index is not None:
                try:
                    concept_index.remove_slot(stale_editor, workspace_id=workspace_id)
                except Exception:
                    pass
    except Exception as e:
        logger.warning("FoundationFixtures: Editor-fixture migration failed: %s", e)

    # §9.5.1 / §S.1 — exactly THREE foundational fixtures (the former fourth,
    # Editor, was deprecated: its mutation gestures are intrinsic to the
    # unified panel↔compute-graph scheme, not a fixture). Anti-goal §18.27
    # (foundation fixture count drift).
    for spec in (_database_fixture_spec(workspace_id),
                 _web_browser_fixture_spec(workspace_id),
                 _agent_fixture_spec(workspace_id)):
        try:
            node = graph_editor.create_concept(
                concept_id=spec["concept_id"],
                name=spec["name"],
                description=spec["description"],
                data=spec["data"],
                backing_pointer=spec["backing_pointer"],
                provenance=spec["provenance"],
                workspace_id=spec["workspace_id"],
                type_hint=spec["type_hint"],
            )
            if node and concept_index is not None:
                try:
                    concept_index.upsert_slot(
                        card_id=node.concept_id,
                        description=node.description,
                        rendering=node.rendering,
                        provenance=node.provenance,
                        workspace_id=node.workspace_id,
                    )
                except Exception:
                    pass
            out.append({
                "concept_id": node.concept_id if node else spec["concept_id"],
                "name": spec["name"],
                "type_hint": spec["type_hint"],
            })
        except Exception as e:
            logger.warning("FoundationFixtures create failed for %s: %s",
                           spec['name'], e)

    # §8D.4.2 — also materialise the Python-native subtrees so the
    # right-click compile expansion has its members ready at first use.
    if materialise_python:
        try:
            python_trees = ensure_foundation_python_trees(
                graph_editor,
                workspace_id=workspace_id,
                concept_index=concept_index,
            )
            for tree in python_trees:
                out.append({
                    "object_concept_id": tree.get("object_concept_id"),
                    "name": f"py::{tree.get('fixture')}",
                    "type_hint": "python_object",
                    "qualified_name": tree.get("qualified_name"),
                })
        except Exception as e:
            logger.warning("FoundationPythonTrees bootstrap failed: %s", e)
    return out
