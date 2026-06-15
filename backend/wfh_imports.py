"""wfh_imports.py — the workspace's canonical imports module (§2.1 / §3.1).

The PythonAPIMaterialiser library-imports middleware reads THIS module on
foundation bootstrap (`ensure_foundation_python_trees` →
`materialise_module(WORKSPACE_IMPORTS_MODULE)`): every class imported here
becomes a materialised Object/Property/Function ConceptNode tree with the
read-only / no_datablock contract (§8D.4.2). The THREE foundational fixtures
are the first application of the rule — `GraphEditor` backs the Database
(unified store) fixture, `WebBrowserManager` backs WebBrowser (Selenium
runtime), `MetaCognitionTick` backs Agent (meta-cognition tick). Any
user-imported library added here flows through the SAME materialisation path
(§9.7 — the §1.2 generalisation of the fixture rule).

§S.1 (2026-06-12): the former fourth `Editor` fixture (also backed by
`GraphEditor`) is removed — its create/link/overwrite/delete gestures are
intrinsic to the unified panel↔compute-graph scheme, not a fixture, so
`GraphEditor` is imported once (for Database) rather than twice.

Importing the classes does NOT instantiate them (no Selenium boot, no SLM
load) — the materialiser only `inspect`s the class objects.
"""

from backend.services.graph_editor import GraphEditor            # Database
from backend.services.selenium_client import WebBrowserManager   # WebBrowser
from backend.services.agent_runtime import MetaCognitionTick     # Agent

__all__ = ["GraphEditor", "WebBrowserManager", "MetaCognitionTick"]
