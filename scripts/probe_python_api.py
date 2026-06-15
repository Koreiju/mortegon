"""Verify §8D.4.2 Python-native API materialiser produces the expected
Object/Property/Function ConceptNode tree with read-only + no_datablock
sentinels."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

import tempfile
import textwrap
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import backing_version
from backend.services.graph_editor import GraphEditor
from backend.services.python_api_materialiser import PythonAPIMaterialiser


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# Define a synthetic target class so the test is self-contained (doesn't
# depend on backend internals that may change).
class _SyntheticBrowser:
    """Toy class for testing the materialiser. Mimics WebBrowser shape."""

    current_url: str = ""
    """The browser's current URL."""

    @property
    def title(self) -> str:
        """The page title."""
        return ""

    def snapshot(self) -> dict:
        """Capture the current DOM and return a snapshot."""
        return {}

    def navigate(self, url: str, timeout: int = 30) -> bool:
        """Navigate to a URL. Returns True on success."""
        return False

    def _private(self) -> None:
        """Should NOT be materialised."""
        return None


# Module-level so eval_str=True can resolve the class annotations against this
# module's globals (a nested class would not be in globals → NameError →
# type edges skipped). Used by check_type_edges.
class _TypeSnapshot:
    """A DOM snapshot."""
    url: str = ""


class _TypePage:
    """A web page."""

    def capture(self) -> _TypeSnapshot:
        """Capture a snapshot."""
        return _TypeSnapshot()

    def load(self, snap: _TypeSnapshot) -> bool:
        """Restore from a snapshot."""
        return True


def check_materialiser_shape() -> None:
    backing_version.reset()
    ge = GraphEditor()
    mat = PythonAPIMaterialiser(graph_editor=ge)
    ws = "probe_pyapi_ws"
    rec = mat.materialise_class(_SyntheticBrowser, workspace_id=ws)
    _assert(rec is not None, "materialise_class returned None")
    _assert(rec["type_hint"] == "python_object", "expected python_object")
    _assert(rec["provenance"] == "derived-from-chunk",
            f"unexpected provenance: {rec['provenance']}")
    _assert(rec["backing_pointer"].startswith("python_object::"),
            "backing_pointer prefix wrong")

    obj_data = json.loads(rec["data"])
    _assert(obj_data["read_only"] is True, "object must be read_only")
    _assert("members" in obj_data, "object data must list members")
    print(f"  object record OK ({len(obj_data['members'])} members)")

    # Enumerate all concept nodes the editor now holds for this workspace
    # so we can assert the children are present + shaped correctly.
    nodes = list(ge._concepts.values())
    nodes_by_type = {}
    for n in nodes:
        nodes_by_type.setdefault(n.type_hint, []).append(n)

    _assert("python_object" in nodes_by_type, "missing python_object")
    _assert("python_property" in nodes_by_type, "missing python_property")
    _assert("python_function" in nodes_by_type, "missing python_function")

    # Properties: current_url, title
    prop_names = sorted(n.name for n in nodes_by_type["python_property"])
    _assert("current_url" in prop_names, f"missing current_url: {prop_names}")
    _assert("title" in prop_names, f"missing title: {prop_names}")
    _assert("_private" not in prop_names, "_private should be skipped")

    # Functions: snapshot, navigate
    fn_names = sorted(n.name for n in nodes_by_type["python_function"])
    _assert("snapshot" in fn_names, f"missing snapshot: {fn_names}")
    _assert("navigate" in fn_names, f"missing navigate: {fn_names}")
    _assert("_private" not in fn_names, "_private should be skipped")

    print(f"  {len(prop_names)} properties + {len(fn_names)} functions materialised")

    # Verify read_only + no_datablock on a property
    cu = next(n for n in nodes_by_type["python_property"] if n.name == "current_url")
    cu_data = json.loads(cu.data)
    _assert(cu_data["read_only"] is True, "property must carry read_only:true")
    _assert(cu_data["no_datablock"] is True, "property must carry no_datablock:true")
    _assert(cu_data["value_type"] == "str", f"value_type: {cu_data['value_type']}")

    # Verify ports on a function
    nav = next(n for n in nodes_by_type["python_function"] if n.name == "navigate")
    nav_data = json.loads(nav.data)
    _assert(nav_data["read_only"] is True, "function must carry read_only:true")
    _assert(nav_data["no_datablock"] is True, "function must carry no_datablock:true")
    _assert("body" in nav_data and "no-datablock" in nav_data["body"].lower(),
            "function body should be no-datablock sentinel")
    ports = nav_data["ports"]
    input_names = [p["name"] for p in ports["inputs"]]
    _assert("url" in input_names, f"navigate.url port missing: {input_names}")
    _assert("timeout" in input_names, f"navigate.timeout port missing: {input_names}")
    timeout_port = next(p for p in ports["inputs"] if p["name"] == "timeout")
    _assert(timeout_port["required"] is False, "timeout has default → not required")
    _assert(timeout_port.get("default") == 30, "timeout default 30 should be captured")
    url_port = next(p for p in ports["inputs"] if p["name"] == "url")
    _assert(url_port["required"] is True, "url is required")

    print(f"  read_only + no_datablock sentinels OK on property + function")
    print(f"  port schema correct on navigate(url: str, timeout: int = 30) -> bool")

    # Edges MUST persist (§2.3.5 / §7 anti-pattern guard). These silently
    # failed for a long time because _safe_create_edge called the legacy
    # ontology-node writer with a workspace_id kwarg it rejects → TypeError
    # → swallowed. The probe now asserts the OBJECT_HAS_* edges exist so the
    # regression cannot recur invisibly.
    ge._ensure_concept_stores()
    ec = Counter(e.edge_type for e in ge._concept_edges.values())
    _assert(ec["OBJECT_HAS_PROPERTY"] == 2,
            f"expected 2 OBJECT_HAS_PROPERTY edges, got {dict(ec)}")
    _assert(ec["OBJECT_HAS_FUNCTION"] == 2,
            f"expected 2 OBJECT_HAS_FUNCTION edges, got {dict(ec)}")
    print(f"  OBJECT_HAS_* edges persist ({ec['OBJECT_HAS_PROPERTY']} props "
          f"+ {ec['OBJECT_HAS_FUNCTION']} funcs)")


def check_idempotent() -> None:
    """Re-running against the same target should not duplicate records."""
    backing_version.reset()
    ge = GraphEditor()
    mat = PythonAPIMaterialiser(graph_editor=ge)
    ws = "probe_pyapi_ws"
    mat.materialise_class(_SyntheticBrowser, workspace_id=ws)
    count_first = len(ge._concepts)

    # Fresh materialiser instance — simulates a hot reload.
    mat2 = PythonAPIMaterialiser(graph_editor=ge)
    mat2.materialise_class(_SyntheticBrowser, workspace_id=ws)
    count_second = len(ge._concepts)

    _assert(count_first == count_second,
            f"idempotent expected: first={count_first} second={count_second}")
    print(f"  idempotent OK ({count_first} nodes both passes)")


def check_backing_version_bumps() -> None:
    """Each materialise call should bump every node's backing version."""
    backing_version.reset()
    ge = GraphEditor()
    mat = PythonAPIMaterialiser(graph_editor=ge)
    ws = "probe_pyapi_ws_bv"
    mat.materialise_class(_SyntheticBrowser, workspace_id=ws)

    snap1 = backing_version.snapshot()
    _assert(any(ws in key for key in snap1), "version registry should record this ws")
    # Every materialised concept should be at version 1 after first run.
    for key, seq in snap1.items():
        if ws in key:
            _assert(seq == 1, f"expected version 1, got {seq} for {key}")

    # Second run — fresh materialiser, same workspace + class. Idempotent
    # via _materialised_objects within a session, so we need a fresh
    # materialiser to simulate a hot reload.
    mat2 = PythonAPIMaterialiser(graph_editor=ge)
    mat2.materialise_class(_SyntheticBrowser, workspace_id=ws)

    snap2 = backing_version.snapshot()
    bumped = sum(1 for key, seq in snap2.items() if ws in key and seq >= 2)
    _assert(bumped > 0, "second materialise should have bumped versions")
    print(f"  backing version bumps OK ({bumped} nodes at seq>=2 after re-materialise)")


def check_type_edges() -> None:
    """FUNCTION_INPUT_TYPE / FUNCTION_OUTPUT_TYPE edges + transitive type
    materialisation (§2.3.5 / §7 — the §8D.42.1 type ontology that
    autocomplete + closest-inverse depend on)."""
    backing_version.reset()
    ge = GraphEditor()
    mat = PythonAPIMaterialiser(graph_editor=ge)
    ws = "probe_pyapi_types"

    # max_depth=2 → walk _TypePage, then transitively materialise _TypeSnapshot
    # via the type edges so the cross-type closure resolves to real
    # python_object nodes.
    mat.materialise_class(_TypePage, workspace_id=ws, max_depth=2)
    ge._ensure_concept_stores()
    ec = Counter(e.edge_type for e in ge._concept_edges.values())
    _assert(ec["FUNCTION_OUTPUT_TYPE"] >= 1,
            f"capture()->_TypeSnapshot should emit FUNCTION_OUTPUT_TYPE: {dict(ec)}")
    _assert(ec["FUNCTION_INPUT_TYPE"] >= 1,
            f"load(snap: _TypeSnapshot) should emit FUNCTION_INPUT_TYPE: {dict(ec)}")
    obj_names = {n.name for n in ge._concepts.values()
                 if n.type_hint == "python_object"}
    _assert("_TypeSnapshot" in obj_names and "_TypePage" in obj_names,
            f"transitive type materialisation missing: {obj_names}")
    print(f"  FUNCTION_*_TYPE edges + transitive type closure OK ({dict(ec)})")


def check_materialise_module() -> None:
    """§2.1 / §9.7 — the library-imports middleware: materialise a whole module
    of `import`-ed classes (the `wfh_imports.py` generalisation). Asserts every
    public class becomes a python_object root, private (`_*`) classes + plain
    functions are skipped, and get_materialised_qualname finds a root."""
    backing_version.reset()
    ge = GraphEditor()
    mat = PythonAPIMaterialiser(graph_editor=ge)
    ws = "probe_pyapi_module"

    # §R.9 — janitor-managed throwaway dir (guaranteed atexit removal).
    from backend.services.db_janitor import new_temp_db_path, register_for_cleanup
    tmpdir = register_for_cleanup(new_temp_db_path("imports_probe"))
    mod_name = "_wfh_probe_imports_mod"
    src = textwrap.dedent('''
        """Synthetic imports module (a wfh_imports.py analogue)."""
        class Alpha:
            """First imported class."""
            a_field: str = ""
            def do_alpha(self, x: int) -> bool:
                """An alpha method."""
                return True
        class Beta:
            """Second imported class."""
            def do_beta(self) -> str:
                """A beta method."""
                return ""
        class _Private:
            """Must NOT be materialised (private)."""
        def helper() -> None:
            """A module function — not a class, not materialised."""
    ''')
    with open(os.path.join(tmpdir, mod_name + ".py"), "w", encoding="utf-8") as fh:
        fh.write(src)
    sys.path.insert(0, tmpdir)
    try:
        importlib.invalidate_caches()
        roots = mat.materialise_module(mod_name, workspace_id=ws, max_walk_depth=4)
        names = sorted(r["name"] for r in roots)
        _assert("Alpha" in names, f"Alpha should materialise: {names}")
        _assert("Beta" in names, f"Beta should materialise: {names}")
        _assert("_Private" not in names, f"_Private must be skipped: {names}")
        _assert("helper" not in names, f"a function must not materialise: {names}")
        existing = mat.get_materialised_qualname(f"{mod_name}.Alpha", workspace_id=ws)
        _assert(existing is not None, "get_materialised_qualname should find Alpha")
        print(f"  materialise_module OK ({len(roots)} class roots: {names})")
    finally:
        try:
            sys.path.remove(tmpdir)
        except ValueError:
            pass
        sys.modules.pop(mod_name, None)
        shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    print("[probe_python_api] verifying §8D.4.2 Object/Property/Function trees")
    check_materialiser_shape()
    check_idempotent()
    check_backing_version_bumps()
    check_type_edges()
    check_materialise_module()
    print("[probe_python_api] ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
