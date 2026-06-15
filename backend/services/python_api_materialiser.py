"""Python-native API materialiser (domain anchor §8D.4.2).

Walks a target Python class or module via ``inspect`` and produces an
Object/Property/Function ConceptNode tree in the unified Database.

Every materialised record carries:

  * ``read_only: true`` — the editor refuses field edits; latch hidden;
    🔒 indicator rendered.
  * ``no_datablock: true`` (functions and properties) — the data field
    holds *signature metadata only*; the function body / property getter
    source is **not** projected into the editor. The Python module is
    the substrate; the ConceptNode is the editor-facing handle.
  * ``backing_pointer`` of the form ``python_object::<qualified_name>``,
    ``python_property::<qualified_name>``, ``python_function::<qualified_name>``.

Edges materialised between the records:

  * ``OBJECT_HAS_PROPERTY`` — class → property
  * ``OBJECT_HAS_FUNCTION`` — class → function
  * ``FUNCTION_INPUT_TYPE`` — function → input parameter's type
  * ``FUNCTION_OUTPUT_TYPE`` — function → return annotation's type

The materialiser is idempotent on qualified name — re-running against
the same target updates existing records in place rather than
duplicating. This makes hot-reload of a Python module a one-call
re-materialisation, with the §8D.39.6 backing-pointer version bumped
so dependent compiles re-fire.
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import re
from dataclasses import is_dataclass, fields as dataclass_fields
from typing import Any, Dict, List, Optional, Tuple

from backend.services import backing_version

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NO_DATABLOCK = "<no-datablock — function body is read-only Python source>"


def _qualified_name(obj: Any) -> str:
    """Return ``module.Class.member`` or ``module.member`` qualified name."""
    mod = getattr(obj, "__module__", "") or ""
    qual = getattr(obj, "__qualname__", "") or getattr(obj, "__name__", "") or ""
    if mod and qual:
        return f"{mod}.{qual}"
    return qual or repr(obj)


def _short_concept_id(qualified: str, kind: str) -> str:
    """Stable, slug-shaped concept id for a Python-native record."""
    # Replace anything not [A-Za-z0-9_.] with underscore; keep dots in the
    # middle so the id is human-scannable.
    safe = re.sub(r"[^A-Za-z0-9_.]+", "_", qualified)
    return f"py_{kind}::{safe}"


def _doc(obj: Any) -> str:
    raw = inspect.getdoc(obj)
    if not raw:
        return ""
    # Single-line summary up to first blank line, plus rest at full fidelity.
    return raw.strip()


def _format_annotation(annot: Any) -> str:
    """Render a type annotation as a readable string."""
    if annot is inspect.Parameter.empty or annot is inspect.Signature.empty:
        return "Any"
    if hasattr(annot, "__name__"):
        return annot.__name__
    return str(annot).replace("typing.", "")


def _classify_type_for_edges(annot: Any) -> Optional[Tuple[str, str]]:
    """If ``annot`` is a class we can edge to, return ``(qualified_name, kind)``.

    Returns ``None`` for primitives, generics like ``list[str]``, and
    annotations we cannot resolve. Returns ``(qualified_name, "python_object")``
    for class annotations.
    """
    if annot is inspect.Parameter.empty or annot is inspect.Signature.empty:
        return None
    if not inspect.isclass(annot):
        return None
    # Skip primitives — they don't get their own ConceptNode trees.
    if annot in (str, int, float, bool, bytes, type(None), list, dict, tuple, set):
        return None
    qn = _qualified_name(annot)
    if not qn or qn.startswith("builtins."):
        return None
    return (qn, "python_object")


# ---------------------------------------------------------------------------
# Inspectors
# ---------------------------------------------------------------------------

def _inspect_properties(cls: type) -> List[Dict[str, Any]]:
    """Return one descriptor per property / dataclass field / instance attr.

    Skips dunder, private (``_*``), and inherited-from-object members.
    """
    out: List[Dict[str, Any]] = []
    seen: set = set()

    # Dataclass fields first (typed declarations).
    if is_dataclass(cls):
        for f in dataclass_fields(cls):
            if f.name.startswith("_"):
                continue
            seen.add(f.name)
            out.append({
                "name": f.name,
                "qualified_name": f"{_qualified_name(cls)}.{f.name}",
                "value_type": _format_annotation(f.type),
                "static": False,
                "doc": "",
            })

    # @property descriptors and class attributes.
    for name, value in inspect.getmembers(cls):
        if name in seen:
            continue
        if name.startswith("_"):
            continue
        if inspect.isfunction(value) or inspect.ismethod(value) or inspect.isbuiltin(value):
            continue
        # @property descriptors live on the class object as `property` instances.
        if isinstance(value, property):
            out.append({
                "name": name,
                "qualified_name": f"{_qualified_name(cls)}.{name}",
                "value_type": _format_annotation(
                    inspect.signature(value.fget).return_annotation
                    if value.fget else inspect.Signature.empty
                ),
                "static": False,
                "doc": _doc(value),
            })
            continue
        # Plain class attribute (constant-like).
        if not callable(value):
            out.append({
                "name": name,
                "qualified_name": f"{_qualified_name(cls)}.{name}",
                "value_type": type(value).__name__,
                "static": True,
                "doc": "",
            })
    return out


def _inspect_functions(cls: type) -> List[Dict[str, Any]]:
    """Return one descriptor per public method / function.

    Skips dunder, private (``_*``), and inherited-from-object members.
    Captures input port schema (per §8D.4.1) and output type.
    """
    out: List[Dict[str, Any]] = []
    base_attrs = set(dir(object))
    for name, value in inspect.getmembers(cls, predicate=callable):
        if name in base_attrs:
            continue
        if name.startswith("_"):
            continue
        # eval_str=True resolves PEP 563 / ``from __future__ import
        # annotations`` string annotations back to real type objects so the
        # FUNCTION_INPUT_TYPE / FUNCTION_OUTPUT_TYPE classifier sees classes,
        # not strings. Most modern modules (including this one) defer
        # annotations, so without this the type ontology edges silently
        # vanish. Fall back to the raw signature if a forward ref cannot be
        # evaluated (then those particular type edges are skipped, but the
        # node + OBJECT_HAS_* edges still materialise).
        sig = None
        for _eval_str in (True, False):
            try:
                sig = inspect.signature(value, eval_str=_eval_str)
                break
            except Exception:
                sig = None
        if sig is None:
            continue
        inputs: List[Dict[str, Any]] = []
        # Raw class objects for FUNCTION_INPUT_TYPE / FUNCTION_OUTPUT_TYPE edge
        # wiring. Held OUT of ``ports`` because a class object is not
        # JSON-serialisable and ``ports`` is persisted into the node's data.
        type_targets: List[Dict[str, Any]] = []
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            inputs.append({
                "name": pname,
                "type": _format_annotation(param.annotation),
                "required": param.default is inspect.Parameter.empty,
                **({"default": param.default}
                   if param.default is not inspect.Parameter.empty
                      and isinstance(param.default, (str, int, float, bool, type(None)))
                   else {}),
            })
            if _classify_type_for_edges(param.annotation) is not None:
                type_targets.append({"direction": "input", "cls": param.annotation})
        output_type = _format_annotation(sig.return_annotation)
        outputs = [{"name": "return", "type": output_type}]
        if _classify_type_for_edges(sig.return_annotation) is not None:
            type_targets.append({"direction": "output", "cls": sig.return_annotation})
        out.append({
            "name": name,
            "qualified_name": f"{_qualified_name(cls)}.{name}",
            "ports": {"inputs": inputs, "outputs": outputs},
            "type_targets": type_targets,
            "doc": _doc(value),
            "signature": str(sig),
        })
    return out


# ---------------------------------------------------------------------------
# Materialiser
# ---------------------------------------------------------------------------

# §2.4 / §3.3 — process-global registry of which qualnames each imports-module
# materialised, keyed ``"<module_path>::<workspace_id>"``. Lets re_materialise
# scope its removed-symbol GC to a single module's prior set (never the
# fixtures / another module). In-memory: a fresh process treats the first
# re-walk as all-new (no deletes), which is the safe default.
_MODULE_MATERIALISED: Dict[str, set] = {}


class PythonAPIMaterialiser:
    """Projects Python classes into Object/Property/Function ConceptNode trees.

    Idempotent on qualified-name → concept-id mapping. Re-runs against the
    same target produce the same concept ids and update records in place
    (with backing-pointer version bumps so cascades re-fire).
    """

    def __init__(self, graph_editor=None, concept_index=None):
        self._graph_editor = graph_editor
        self._concept_index = concept_index
        # Track classes we've already materialised this session to break
        # cycles when a function's input/output type points back at us.
        self._materialised_objects: set = set()

    def materialise_class(
        self,
        cls: type,
        *,
        workspace_id: str = "",
        max_depth: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """Materialise the class as a python_object + child property/function
        ConceptNodes. Returns the object's record dict.

        ``max_depth=1`` (default) walks the class's own members but does not
        transitively materialise the classes referenced by function input/
        output types. ``max_depth=2`` walks one level of referenced classes;
        and so on. Cycles are broken by the ``_materialised_objects`` set.
        """
        if not self._graph_editor:
            return None
        qn = _qualified_name(cls)
        if qn in self._materialised_objects:
            # Already materialised this session; return the existing record.
            return self._get_existing(_short_concept_id(qn, "object"))
        self._materialised_objects.add(qn)

        # Build the object record first so its concept_id is available for
        # OBJECT_HAS_* edges from its members.
        object_concept_id = _short_concept_id(qn, "object")
        property_descriptors = _inspect_properties(cls)
        function_descriptors = _inspect_functions(cls)

        object_data = json.dumps({
            "qualified_name": qn,
            "read_only": True,
            "members": [
                _short_concept_id(p["qualified_name"], "property")
                for p in property_descriptors
            ] + [
                _short_concept_id(f["qualified_name"], "function")
                for f in function_descriptors
            ],
            "ports": None,
        }, indent=2)
        object_description = _doc(cls) or f"Python class `{qn}`."
        object_backing = f"python_object::{qn}"

        object_node = self._graph_editor.create_concept(
            concept_id=object_concept_id,
            name=getattr(cls, "__name__", qn.split(".")[-1]),
            description=object_description,
            data=object_data,
            rendering="",
            backing_pointer=object_backing,
            provenance="derived-from-chunk",  # auto-materialised, not user-typed
            workspace_id=workspace_id,
            type_hint="python_object",
        )
        backing_version.bump(workspace_id, object_backing)
        self._upsert_index(object_node)

        # Build property records.
        for prop in property_descriptors:
            self._materialise_property(prop, parent_object_id=object_concept_id,
                                       workspace_id=workspace_id)

        # Build function records.
        for fn in function_descriptors:
            self._materialise_function(fn, parent_object_id=object_concept_id,
                                       workspace_id=workspace_id,
                                       max_depth=max_depth)

        return self._node_to_dict(object_node)

    def materialise_qualified_name(
        self,
        qualified_name: str,
        *,
        workspace_id: str = "",
        max_depth: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """Convenience wrapper — import a class by qualified name and materialise."""
        if "." not in qualified_name:
            return None
        module_name, _, class_name = qualified_name.rpartition(".")
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name, None)
        except (ImportError, AttributeError) as e:
            logger.warning("[python_api] failed to import %s: %s", qualified_name, e)
            return None
        if not inspect.isclass(cls):
            return None
        return self.materialise_class(cls, workspace_id=workspace_id, max_depth=max_depth)

    # -- Library-imports middleware (§9.7 / PythonAPIMaterialiser.md §2.1-§3.1) --

    def get_materialised_qualname(
        self,
        qualified_name: str,
        *,
        workspace_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """§2.2 — look up an already-materialised python_object root by its
        qualified name (the idempotency check the middleware runs before a
        re-walk). Returns the object record dict or ``None``."""
        return self._get_existing(_short_concept_id(qualified_name, "object"))

    def walk_hierarchy(
        self,
        symbol: Any,
        *,
        workspace_id: str = "",
        max_depth: int = 4,
        _type_depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """§2.3 — recursively walk a resolved symbol (class or module),
        depth-bounded.

          * class  → materialise as a python_object tree (``materialise_class``,
            which itself wires function input/output type edges + recurses into
            type targets up to ``_type_depth``).
          * module → materialise every public CLASS member; recurse into TRUE
            submodules (depth-bounded by ``max_depth``).

        The submodule guard (a member module recurses only when its
        ``__name__`` is a dotted child of the parent's) is the §7
        explosion safeguard: it stops the walk wandering into re-exported
        third-party / stdlib roots (a bare ``import numpy`` is not transitively
        walked — import the specific class instead). Private (``_*``) members
        are skipped. Returns the list of materialised object-root records.
        """
        out: List[Dict[str, Any]] = []
        if symbol is None or max_depth <= 0:
            return out
        if inspect.isclass(symbol):
            rec = self.materialise_class(symbol, workspace_id=workspace_id,
                                         max_depth=_type_depth)
            if rec:
                out.append(rec)
            return out
        if inspect.ismodule(symbol):
            mod_name = getattr(symbol, "__name__", "") or ""
            names = getattr(symbol, "__all__", None)
            if not names:
                names = [n for n in dir(symbol) if not n.startswith("_")]
            for name in names:
                if not isinstance(name, str) or name.startswith("_"):
                    continue
                member = getattr(symbol, name, None)
                if inspect.isclass(member):
                    rec = self.materialise_class(member, workspace_id=workspace_id,
                                                 max_depth=_type_depth)
                    if rec:
                        out.append(rec)
                elif inspect.ismodule(member) and max_depth > 1:
                    sub_name = getattr(member, "__name__", "") or ""
                    if sub_name.startswith(mod_name + "."):
                        out.extend(self.walk_hierarchy(
                            member, workspace_id=workspace_id,
                            max_depth=max_depth - 1, _type_depth=_type_depth,
                        ))
        return out

    def materialise_module(
        self,
        module_path: str,
        *,
        workspace_id: str = "",
        max_walk_depth: int = 4,
    ) -> List[Dict[str, Any]]:
        """§2.1 / §2.2 / §3.1 — the library-imports middleware entry point.

        Imports the module at ``module_path`` (typically the workspace's
        ``wfh_imports.py``, whose body is ``import`` / ``from … import …``
        statements) and materialises a ConceptNode tree for every top-level
        resolved symbol — each imported class becomes a python_object root. The
        four foundational fixtures are the first application of this rule; any
        user-imported library flows through the same pipeline.

        Idempotent on qualified name (re-running over an updated imports module
        reuses existing concept ids + bumps backing-pointer versions via
        ``materialise_class``). Returns the list of materialised object-root
        records.
        """
        if not self._graph_editor:
            return []
        try:
            module = importlib.import_module(module_path)
        except Exception as e:
            logger.warning("[python_api] failed to import imports-module %s: %s",
                           module_path, e)
            return []
        roots = self.walk_hierarchy(module, workspace_id=workspace_id,
                                    max_depth=max_walk_depth)
        # Record this imports-module's materialised root qualnames so
        # re_materialise can scope its removed-symbol GC to JUST this module
        # (never touching the fixtures or another module's trees, §3.3).
        qns = {self._root_qualname(r) for r in roots}
        qns.discard("")
        _MODULE_MATERIALISED[f"{module_path}::{workspace_id}"] = qns
        return roots

    @staticmethod
    def _root_qualname(root: Dict[str, Any]) -> str:
        """The unmangled qualified name of a materialised object-root record
        (carried verbatim on its ``python_object::<qn>`` backing pointer)."""
        bp = (root or {}).get("backing_pointer", "") or ""
        return bp.split("::", 1)[1] if bp.startswith("python_object::") else ""

    def re_materialise(
        self,
        module_path: str,
        *,
        workspace_id: str = "",
        max_walk_depth: int = 4,
    ) -> Dict[str, Any]:
        """§2.4 / §3.3 — re-walk an imports module after it changed.

        Idempotent re-walk (add new symbols, refresh existing in place with a
        backing-pointer version bump via ``materialise_class``) PLUS the diff
        DELETE of symbols no longer imported — dissolving their subtrees via
        the graph editor. The removed-set is scoped to THIS module's previously-
        recorded qualnames (``_MODULE_MATERIALISED``), so a re-materialise can
        never delete the foundation fixtures or another imports-module's trees.
        Returns ``{roots, added, removed, kept}`` qualname sets (as lists).
        """
        key = f"{module_path}::{workspace_id}"
        prior = set(_MODULE_MATERIALISED.get(key, set()))
        roots = self.materialise_module(
            module_path, workspace_id=workspace_id, max_walk_depth=max_walk_depth,
        )
        current = {self._root_qualname(r) for r in roots}
        current.discard("")
        removed = prior - current
        for qn in removed:
            self._dissolve_object_tree(qn, workspace_id=workspace_id)
        return {
            "roots": sorted(current),
            "added": sorted(current - prior),
            "removed": sorted(removed),
            "kept": sorted(current & prior),
        }

    def _dissolve_object_tree(self, qualified_name: str, *, workspace_id: str = "") -> None:
        """Delete a materialised python_object root + its property/function
        members (§2.4 removed-import GC). Best-effort + idempotent."""
        if not self._graph_editor:
            return
        object_id = _short_concept_id(qualified_name, "object")
        member_ids: List[str] = []
        try:
            node = self._graph_editor.get_concept(object_id)
            if node is not None and getattr(node, "data", ""):
                data = json.loads(node.data)
                member_ids = list(data.get("members") or [])
        except Exception:
            member_ids = []
        for cid in member_ids + [object_id]:
            try:
                self._graph_editor.delete_concept(cid)
            except Exception as e:
                logger.debug("[python_api] dissolve %s failed: %s", cid, e)
        self._materialised_objects.discard(qualified_name)

    # -- Internal -------------------------------------------------------

    def _materialise_property(self, prop: Dict[str, Any], *,
                              parent_object_id: str,
                              workspace_id: str) -> Optional[Any]:
        qn = prop["qualified_name"]
        concept_id = _short_concept_id(qn, "property")
        data = json.dumps({
            "qualified_name": qn,
            "read_only": True,
            "no_datablock": True,
            "value_type": prop["value_type"],
            "static": prop["static"],
        }, indent=2)
        description = prop["doc"] or f"Property `{qn}` of type `{prop['value_type']}`."
        backing = f"python_property::{qn}"
        node = self._graph_editor.create_concept(
            concept_id=concept_id,
            name=prop["name"],
            description=description,
            data=data,
            rendering="",
            backing_pointer=backing,
            provenance="derived-from-chunk",
            workspace_id=workspace_id,
            type_hint="python_property",
        )
        backing_version.bump(workspace_id, backing)
        self._upsert_index(node)
        # Edge: object HAS_PROPERTY property
        self._safe_create_edge(parent_object_id, concept_id,
                               "OBJECT_HAS_PROPERTY", workspace_id)
        return node

    def _materialise_function(self, fn: Dict[str, Any], *,
                              parent_object_id: str,
                              workspace_id: str,
                              max_depth: int) -> Optional[Any]:
        qn = fn["qualified_name"]
        concept_id = _short_concept_id(qn, "function")
        data = json.dumps({
            "qualified_name": qn,
            "read_only": True,
            "no_datablock": True,
            "signature": fn["signature"],
            "ports": fn["ports"],
            "body": _NO_DATABLOCK,
        }, indent=2)
        description = fn["doc"] or f"Function `{qn}`."
        backing = f"python_function::{qn}"
        node = self._graph_editor.create_concept(
            concept_id=concept_id,
            name=fn["name"],
            description=description,
            data=data,
            rendering="",
            backing_pointer=backing,
            provenance="derived-from-chunk",
            workspace_id=workspace_id,
            type_hint="python_function",
        )
        backing_version.bump(workspace_id, backing)
        self._upsert_index(node)
        # Edge: object HAS_FUNCTION function
        self._safe_create_edge(parent_object_id, concept_id,
                               "OBJECT_HAS_FUNCTION", workspace_id)
        # Edges: function → input/output type objects (§8D.42.1 type ontology).
        # The doc §7 anti-patterns table forbids skipping these — autocomplete
        # + closest-inverse depend on them. Recurse into the target class when
        # depth allows so cross-type edges resolve to real python_object nodes
        # (transitive closure within max_depth; cycles broken by the
        # _materialised_objects set). When depth is exhausted the edge still
        # fires, pointing at the deterministic python_object::<qn> id so a
        # later import of that type resolves it (cross-library composability).
        for tgt in fn.get("type_targets", []):
            tgt_cls = tgt["cls"]
            tgt_qn = _qualified_name(tgt_cls)
            tgt_object_id = _short_concept_id(tgt_qn, "object")
            edge_type = ("FUNCTION_INPUT_TYPE" if tgt["direction"] == "input"
                         else "FUNCTION_OUTPUT_TYPE")
            if max_depth > 1 and tgt_qn not in self._materialised_objects:
                self.materialise_class(tgt_cls, workspace_id=workspace_id,
                                       max_depth=max_depth - 1)
            self._safe_create_edge(concept_id, tgt_object_id,
                                   edge_type, workspace_id)
        return node

    def _safe_create_edge(self, source_id: str, target_id: str,
                          edge_type: str, workspace_id: str) -> None:
        # MUST be ``create_concept_edge`` — the ConceptEdge-table writer that
        # accepts ``workspace_id`` and does not whitelist ``edge_type``. The
        # legacy ``create_edge`` (ontology-node edges) rejects ``workspace_id``
        # and validates against EDGE_TYPES, so calling it here silently
        # TypeError'd and dropped every OBJECT_HAS_* / FUNCTION_*_TYPE edge —
        # the §7-forbidden "skipping the type edges" state.
        try:
            self._graph_editor.create_concept_edge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                workspace_id=workspace_id,
            )
        except Exception as e:
            logger.debug("[python_api] create_concept_edge %s→%s %s failed: %s",
                         source_id, target_id, edge_type, e)

    def _upsert_index(self, node) -> None:
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

    def _get_existing(self, concept_id: str) -> Optional[Dict[str, Any]]:
        if not self._graph_editor:
            return None
        try:
            node = self._graph_editor.get_concept(concept_id)
            return self._node_to_dict(node) if node else None
        except Exception:
            return None

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
            "backing_pointer": node.backing_pointer,
            "workspace_id": node.workspace_id,
        }
