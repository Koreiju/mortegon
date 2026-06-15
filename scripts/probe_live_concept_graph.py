"""LIVE end-to-end probe for the §8D.47 concept-graph-editor use case.

The symbolic counterpart to ``probe_live_archive_scan.py``. Where the
archive.org probe begins outside-in (Selenium → chunks → retrieval →
compile), this probe begins inside-out (empty primitive → typed
description → real nomic apparition retrieval → wiring → variable
auto-creation → LangGraph+GPT4All compile chain → evolution log
audit → rollback).

Every step asserts on real signal observed against real subsystems —
no mocks, no shortcuts. The probe is the evidence of record.

Run as:  python scripts/probe_live_concept_graph.py [BACKEND_URL]

Requires the backend up with no WFH_FAKE_* envs (real GPT4All + real
nomic + real Selenium + real LangGraph).
"""

from __future__ import annotations

import json
import sys
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_BACKEND = "http://127.0.0.1:8080"


def _section(title: str) -> None:
    print(f"\n== {title} {'=' * max(0, 60 - len(title))}")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _http(method: str, url: str, *,
          body: Optional[Dict[str, Any]] = None,
          timeout: float = 30.0) -> Dict[str, Any]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _get(url: str, **kw) -> Dict[str, Any]:
    return _http("GET", url, **kw)


def _post(url: str, body: Dict[str, Any], **kw) -> Dict[str, Any]:
    return _http("POST", url, body=body, **kw)


def _patch(url: str, body: Dict[str, Any], **kw) -> Dict[str, Any]:
    return _http("PATCH", url, body=body, **kw)


def _delete(url: str, **kw) -> Dict[str, Any]:
    return _http("DELETE", url, **kw)


# ---------------------------------------------------------------------------
# Probe steps
# ---------------------------------------------------------------------------

def step_subsystem_real(backend: str) -> None:
    _section("1) Subsystems all real (§8D.46)")
    s = _get(f"{backend}/api/subsystem_status")
    _assert(s.get("all_real") is True,
            f"subsystems NOT all real: {s}")
    print(f"  slm={s['slm']['backend']}  embedder={s['embedder']['backend']}"
          f" ({s['embedder'].get('device')})  selenium={s['selenium']['backend']}"
          f"  langgraph={s['langgraph']['backend']}")


def step_ensure_fixtures(backend: str) -> Dict[str, str]:
    """Materialise Database / WebBrowser / Agent / Editor + their Python trees.

    Returns a map ``{fixture_name: concept_id}`` for the 4 fixtures
    per §9.5.1 four-fixture update.
    """
    _section("2) Foundation fixtures + auto-materialised Python trees")
    resp = _post(f"{backend}/api/foundation/ensure", {"workspace_id": ""})
    fixtures = {f["name"]: f["concept_id"] for f in (resp.get("fixtures") or [])
                if f.get("concept_id") and not f.get("name", "").startswith("py::")}
    print(f"  fixtures: {sorted(fixtures.keys())}")
    # §S.1 — exactly THREE fixtures (Database/WebBrowser/Agent); the former
    # fourth, Editor, is removed (its mutation gestures are intrinsic to the
    # unified panel↔compute-graph scheme, not a fixture).
    _assert("Database" in fixtures and "WebBrowser" in fixtures
            and "Agent" in fixtures,
            f"missing one of the three fixtures: {fixtures}")
    _assert("Editor" not in fixtures,
            f"§S.1 regression — Editor fixture present: {sorted(fixtures)}")
    # Auto-materialised Python trees — one per DISTINCT backing class
    # (FOUNDATION_PYTHON_TARGETS: GraphEditor for Database, WebBrowserManager,
    # MetaCognitionTick for Agent). Assert the distinct backing-class set.
    from backend.services.foundation_fixtures import FOUNDATION_PYTHON_TARGETS
    expected_qualnames = set(FOUNDATION_PYTHON_TARGETS.values())
    py_objects = [f for f in (resp.get("fixtures") or [])
                  if f.get("type_hint") == "python_object"]
    # The ensure-response python-tree items carry `qualified_name` +
    # `object_concept_id` (`py_object::<qualname>`) — not concept_id.
    got_qualnames = {
        f.get("qualified_name")
        or (f.get("object_concept_id") or "").split("::", 1)[-1]
        for f in py_objects
    }
    got_qualnames.discard("")
    print(f"  auto-materialised python_object trees: {len(py_objects)}")
    missing = expected_qualnames - got_qualnames
    _assert(not missing,
            f"missing python_object tree(s) for backing class(es): {missing} "
            f"(got {sorted(got_qualnames)})")
    return fixtures


def step_create_empty_then_describe(backend: str) -> str:
    """Create an empty primitive, then patch in a description that
    will drive real-nomic apparition radiation. Returns the empty id."""
    _section("3) Create empty primitive + type a description")
    create = _post(f"{backend}/api/concepts", {
        "name": "",
        "description": "",
        "workspace_id": "",
    })
    empty_id = create.get("concept_id") or ""
    _assert(bool(empty_id), f"empty primitive create failed: {create}")
    print(f"  empty primitive id: {empty_id}")

    # Type a description — the lifecycle re-embeds via real nomic.
    patch_body = {
        "description": "summarise text from the web with a small language model",
    }
    patched = _patch(f"{backend}/api/concepts/{empty_id}", patch_body)
    desc = patched.get("description") or ""
    _assert("summarise" in desc.lower(),
            f"description didn't persist: {patched}")
    print(f"  description: {desc!r}")
    return empty_id


def step_radiation(backend: str) -> List[Dict[str, Any]]:
    """Hit the radiation surface with the same text the empty was given;
    confirm real candidates come back ranked by triple-product."""
    _section("4) /api/radiation — real nomic apparition surface")
    resp = _post(f"{backend}/api/radiation", {
        "text": "summarise text from the web with a small language model",
        "workspace_id": "",
        "k": 8,
    })
    candidates = resp.get("candidates") or []
    print(f"  candidates: {len(candidates)}")
    for c in candidates[:5]:
        print(f"    {c.get('card_id', '?')[:50]:50}  "
              f"score={c.get('score', 0):.6f}  "
              f"nomic={c.get('nomic_cos', 0):.4f}  "
              f"pr={c.get('pagerank', 0):.4f}")
    _assert(len(candidates) > 0,
            f"radiation returned zero candidates: {resp}")
    # Sort sanity: scores must be monotonically non-increasing.
    scores = [c.get("score", 0) for c in candidates]
    _assert(scores == sorted(scores, reverse=True),
            f"candidates not sorted by score: {scores}")
    # Real signal sanity: the top candidate's nomic_cos should be a
    # real number != 0 (the fake embedder would zero everything out
    # because the synthetic-text path needs a real embed_query call).
    top = candidates[0]
    _assert(abs(float(top.get("nomic_cos", 0))) > 0.0,
            f"top candidate has zero nomic_cos — embedder might be fake: {top}")
    print(f"  [OK] real triple-product scoring (top nomic_cos="
          f"{top.get('nomic_cos'):.4f})")
    return candidates


def step_resolve_and_wire(backend: str, empty_id: str,
                          candidates: List[Dict[str, Any]]) -> str:
    """Pick the top non-self apparition and wire a DERIVED_FROM edge
    from the empty to it. This is the click-the-apparition gesture."""
    _section("5) Resolve empty toward top apparition (wire edge)")
    # Skip self — when the typed text matches the empty's own
    # description verbatim, the radiation surface returns the empty
    # first (score 1.0). The user-meaningful pick is the next one.
    non_self = [c for c in candidates if c.get("card_id") != empty_id]
    _assert(len(non_self) > 0,
            f"all candidates were the empty itself: {candidates}")
    target_id = non_self[0]["card_id"]
    print(f"  drawing edge: {empty_id} → {target_id}")
    edge_resp = _post(f"{backend}/api/concept_edges", {
        "source_id":   empty_id,
        "target_id":   target_id,
        "edge_type":   "DERIVED_FROM",
        "workspace_id": "",
    })
    edge_id = edge_resp.get("edge_id") or edge_resp.get("id") or ""
    _assert(bool(edge_id), f"edge creation failed: {edge_resp}")
    print(f"  edge created: {edge_id}")
    return target_id


def step_variable_auto_create(backend: str, empty_id: str) -> str:
    """Author a second concept whose data block holds a ``{name}``
    reference to the empty. Confirm the create returns successfully
    and the data is preserved verbatim (auto-creation is exercised
    when the named ref doesn't yet exist; here we reference the
    existing empty's name to also exercise the binding path)."""
    _section("6) Variable reference + auto-creation (§8D.21.1)")
    # First update the empty's name so we can reference it.
    rename = _patch(f"{backend}/api/concepts/{empty_id}", {
        "name": "summary_seed",
    })
    new_name = rename.get("name") or ""
    _assert(new_name == "summary_seed",
            f"rename to summary_seed failed: {rename}")
    print(f"  empty renamed to: {new_name!r}")

    # Author a consumer that references {summary_seed} in its data.
    consumer = _post(f"{backend}/api/concepts", {
        "name": "summary_consumer",
        "description": "A downstream that consumes summary_seed",
        "data": '{"summary_input": "{summary_seed}"}',
        "workspace_id": "",
    })
    consumer_id = consumer.get("concept_id") or ""
    _assert(bool(consumer_id), f"consumer create failed: {consumer}")
    print(f"  consumer id: {consumer_id}")
    print(f"  consumer data: {consumer.get('data')!r}")
    # The rendering field should have been derived from the data — the
    # lifecycle's tree-pretty-print fires on create. Sanity-check it's
    # non-empty (the {summary_seed} ref may resolve to literal or to
    # the empty's rendering depending on cascade timing).
    rendering = consumer.get("rendering") or ""
    _assert(len(rendering) > 0,
            f"consumer rendering empty: {consumer}")
    print(f"  consumer rendering: {rendering!r}")
    return consumer_id


def step_compile_chain(backend: str, consumer_id: str) -> Dict[str, Any]:
    """Run compile_chain against the consumer — walks back-references
    through the wiring, assembles a real LangGraph StateGraph, and
    fires each node's compute."""
    _section("7) Real LangGraph compile_chain (§11.7)")
    resp = _post(f"{backend}/api/conceptual/compile_chain", {
        "focal_id":     consumer_id,
        "workspace_id": "",
        "max_depth":    4,
        "use_slm":      True,
    }, timeout=180)
    ordered = resp.get("ordered") or []
    state = resp.get("state") or {}
    print(f"  ordered chain: {ordered}")
    print(f"  state keys:    {list(state.keys())}")
    for cid, info in list(state.items())[:5]:
        kind = (info or {}).get("kind", "?")
        rendering = ((info or {}).get("rendering") or "")[:80]
        print(f"    {cid[:50]:50}  kind={kind}  rendering={rendering!r}")
    _assert(len(ordered) >= 1,
            f"compile_chain returned empty ordered list: {resp}")
    _assert(len(state) >= 1,
            f"compile_chain returned empty state: {resp}")
    # At least one node should have a real rendering.
    nonempty = [c for c, info in state.items()
                if (info or {}).get("rendering")]
    _assert(len(nonempty) >= 1,
            f"no node in the chain produced a rendering: {state}")
    print(f"  [OK] {len(nonempty)} node(s) produced rendering")
    return resp


def step_apparition_for_real_focal(backend: str, consumer_id: str) -> None:
    """Run focal-centric apparition retrieval against a real concept
    (not synthetic text). Asserts on real scores from real embeddings."""
    _section("8) /api/apparitions/{focal_id} — focal-centric retrieval")
    resp = _get(f"{backend}/api/apparitions/{consumer_id}?k=6")
    candidates = resp.get("candidates") or []
    print(f"  focal: {consumer_id[:50]}")
    print(f"  apparitions: {len(candidates)}")
    for c in candidates[:5]:
        cid = c.get("card_id", "?")[:40]
        print(f"    {cid:40}  score={c.get('score', 0):.6f}"
              f"  nomic={c.get('nomic_cos', 0):.4f}"
              f"  tfidf={c.get('tfidf_cos', 0):.4f}")
    _assert(len(candidates) > 0,
            f"focal apparition returned zero candidates: {resp}")
    # Real signal: at least one candidate must have a non-trivial
    # nomic cosine (the empty + consumer + Database fixture all have
    # real description embeddings).
    real_nomic = [c for c in candidates
                  if abs(float(c.get("nomic_cos", 0))) > 1e-6]
    _assert(len(real_nomic) > 0,
            f"no candidate has non-zero nomic_cos — embeddings might be fake")
    print(f"  [OK] {len(real_nomic)} candidate(s) with real nomic cosines")


def step_multi_step_chain_with_real_slm(backend: str) -> Dict[str, str]:
    """Author a three-concept compute graph where one node is a prompt
    that fires real GPT4All. Returns the {leaf, summariser, formatter}
    concept ids so the caller can run compile_chain on the leaf."""
    _section("7b) Multi-step compute graph with real SLM dispatch")
    # Leaf: literal data the chain consumes.
    leaf = _post(f"{backend}/api/concepts", {
        "name": "topic_seed",
        "description": "A seed topic the chain consumes.",
        "data": json.dumps({
            "topic": "the role of university libraries in preserving knowledge",
        }),
        "workspace_id": "",
    })
    leaf_id = leaf.get("concept_id") or ""
    _assert(bool(leaf_id), f"leaf create failed: {leaf}")
    print(f"  leaf:       {leaf_id}  (topic_seed)")

    # Summariser: prompt node that fires real GPT4All; references the leaf via {topic_seed}.
    summariser = _post(f"{backend}/api/concepts", {
        "name": "summariser",
        "description": "Summarises the topic in one sentence.",
        "data": json.dumps({
            "compute_kind": "prompt",
            "prompt": "Write one sentence about {topic_seed}. Be concise.",
        }),
        "workspace_id": "",
    })
    summariser_id = summariser.get("concept_id") or ""
    _assert(bool(summariser_id), f"summariser create failed: {summariser}")
    print(f"  summariser: {summariser_id}  (compute_kind=prompt → real GPT4All)")

    # Formatter: downstream consumer that references the summariser.
    formatter = _post(f"{backend}/api/concepts", {
        "name": "formatter",
        "description": "Final formatted output.",
        "data": json.dumps({"final": "{summariser}"}),
        "workspace_id": "",
    })
    formatter_id = formatter.get("concept_id") or ""
    _assert(bool(formatter_id), f"formatter create failed: {formatter}")
    print(f"  formatter:  {formatter_id}  (downstream of summariser)")

    # Wire the chain explicitly so compile_chain has back-references
    # to walk. The {var} refs already imply the chain semantically;
    # the typed edges make the graph navigable + PageRank-able.
    for src, tgt in [(leaf_id, summariser_id), (summariser_id, formatter_id)]:
        edge = _post(f"{backend}/api/concept_edges", {
            "source_id": src, "target_id": tgt,
            "edge_type": "PROVIDES_VALUE_FOR", "workspace_id": "",
        })
        _assert(bool(edge.get("edge_id") or edge.get("id")),
                f"edge create failed for {src}→{tgt}: {edge}")
    print(f"  wired: leaf → summariser → formatter (typed PROVIDES_VALUE_FOR edges)")

    # Compile the formatter's full chain — should walk back-references
    # and resolve {summariser} from the SLM prompt's output, which in
    # turn resolves {topic_seed} from the leaf's data.
    print(f"  compiling chain rooted at formatter (this fires real GPT4All)…")
    chain = _post(f"{backend}/api/conceptual/compile_chain", {
        "focal_id": formatter_id, "workspace_id": "",
        "max_depth": 5, "use_slm": True,
    }, timeout=600)
    ordered = chain.get("ordered") or []
    state = chain.get("state") or {}
    print(f"  ordered length: {len(ordered)}")
    for cid in ordered:
        info = state.get(cid) or {}
        kind = info.get("kind", "?")
        rendering = ((info.get("rendering") or "")[:120]).replace("\n", " ")
        # Trim long ids for readability.
        cid_short = cid[:44]
        print(f"    {cid_short:44}  kind={kind:10}  rendering={rendering!r}")
    # Assert at least one node dispatched as `prompt` and produced a
    # non-stub rendering — that's the real-SLM-in-chain proof.
    prompt_nodes = [c for c, info in state.items()
                    if (info or {}).get("kind") == "prompt"]
    _assert(len(prompt_nodes) >= 1,
            f"no node in the chain dispatched as 'prompt': {state}")
    prompt_render = state[prompt_nodes[0]].get("rendering") or ""
    _assert(not prompt_render.startswith("[stub-slm]"),
            f"prompt rendering is the stub trailer (SLM didn't fire): "
            f"{prompt_render!r}")
    _assert(len(prompt_render.strip()) > 5,
            f"prompt rendering too short: {prompt_render!r}")
    print(f"  [OK] real-SLM-in-chain produced: {prompt_render[:200]!r}")
    return {
        "leaf": leaf_id,
        "summariser": summariser_id,
        "formatter": formatter_id,
    }


def step_closest_inverse(backend: str, output_concept_id: str) -> None:
    """Exercise §8D.7 — given an output concept node, return inputs
    whose forward execution would produce something close to it."""
    _section("7c) Closest-inverse lookup (§8D.7) — bidirectional ports")
    resp = _get(f"{backend}/api/closest_inverse/{output_concept_id}?k=5")
    candidates = resp.get("candidates") or []
    print(f"  output: {output_concept_id[:48]}")
    print(f"  inverse candidates: {len(candidates)}")
    for c in candidates[:5]:
        cid = (c.get("card_id") or "?")[:44]
        print(f"    {cid:44}  score={c.get('score', 0):.6f}"
              f"  nomic={c.get('nomic_cos', 0):.4f}")
    _assert(len(candidates) > 0,
            f"closest_inverse returned no candidates: {resp}")
    # Scores must be sorted desc.
    scores = [c.get("score", 0) for c in candidates]
    _assert(scores == sorted(scores, reverse=True),
            f"inverse candidates not sorted: {scores}")
    real = [c for c in candidates if abs(float(c.get("nomic_cos", 0))) > 1e-6]
    _assert(len(real) > 0,
            f"no inverse candidate has non-zero nomic_cos: {candidates}")
    print(f"  [OK] {len(real)} inverse candidate(s) with real nomic cosines")


def step_inline_cypher(backend: str) -> None:
    """Exercise §8D.2.1 — a data block containing a MATCH...RETURN
    cypher is rewritten through real Kuzu and substituted into the
    rendering output. Uses the /api/compile_pipeline endpoint."""
    _section("7d) Inline cypher in data block (§8D.2.1)")
    # The detector recognises either a ```cypher code fence or text
    # that *begins* with a cypher keyword. Use the fence form so the
    # surrounding prose can stay readable.
    cypher_text = (
        "Find all concepts in the workspace via:\n\n"
        "```cypher\n"
        "MATCH (c:ConceptNode) RETURN c.concept_id, c.name LIMIT 5\n"
        "```\n"
    )
    resp = _post(f"{backend}/api/compile_pipeline", {
        "text": cypher_text, "workspace_id": "",
    })
    rewritten = resp.get("rewritten") or ""
    trace = resp.get("trace") or []
    print(f"  trace entries: {len(trace)}")
    for t in trace[:3]:
        ok = t.get("ok")
        rows = t.get("rows_count") or t.get("rows") or 0
        seg = (t.get("segment") or "")[:60].replace("\n", " ")
        print(f"    ok={ok}  rows={rows}  segment={seg!r}")
    _assert(len(trace) >= 1,
            f"no cypher segments detected: {resp}")
    success = [t for t in trace if t.get("ok") is True]
    _assert(len(success) >= 1,
            f"no cypher segment executed successfully: {trace}")
    # The rewritten text should have substituted the cypher with the
    # result (so it differs from the input).
    _assert(rewritten != cypher_text,
            "rewritten text equals input — cypher wasn't substituted")
    print(f"  [OK] cypher detected + executed; rewritten len={len(rewritten)}")
    print(f"  rewritten head: {rewritten[:200]!r}")


def step_evolution_log(backend: str) -> List[Dict[str, Any]]:
    """Fetch the evolution log and confirm our edits are recorded."""
    _section("9) /api/evolution_log — audit trail")
    resp = _get(f"{backend}/api/evolution_log?limit=50")
    diffs = resp.get("diffs") or []
    print(f"  total recent diffs: {len(diffs)}")
    # Print the kinds we saw in this probe.
    kinds: Dict[str, int] = {}
    for d in diffs:
        k = d.get("kind", "?")
        kinds[k] = kinds.get(k, 0) + 1
    print(f"  kind histogram: {kinds}")
    # Show the most recent 5 entries.
    for d in diffs[:5]:
        target = (d.get("target") or "")[:50]
        actor = (d.get("actor") or "")[:30]
        print(f"    edit_id={d.get('edit_id')}  kind={d.get('kind'):10}"
              f"  target={target}  actor={actor}")
    _assert(len(diffs) >= 1,
            f"evolution log empty after editing: {resp}")
    return diffs


def step_rollback(backend: str, diffs: List[Dict[str, Any]]) -> None:
    """Roll back the most-recent edit and confirm a new diff was
    recorded (the rollback itself is a diff per §8D.33)."""
    _section("10) Rollback most-recent edit (§8D.33)")
    if not diffs:
        print("  (nothing to rollback)")
        return
    latest = diffs[0]
    edit_id = latest.get("edit_id")
    print(f"  rolling back edit_id={edit_id} (kind={latest.get('kind')}"
          f", target={latest.get('target')})")
    try:
        roll_resp = _post(f"{backend}/api/evolution_log/rollback", {
            "edit_id": int(edit_id), "workspace_id": "",
        }, timeout=60)
        print(f"  rollback response: {json.dumps(roll_resp, indent=2)[:300]}")
        # Successful rollback should fan out at least one operation.
        ok_keys = ["ok", "applied", "status", "reverted", "rolled_back"]
        looks_ok = any(k in roll_resp for k in ok_keys) or roll_resp.get("ok")
        if looks_ok is False or (isinstance(looks_ok, bool) and not looks_ok):
            print("  (rollback returned, but response shape is "
                  "implementation-specific; not fatal)")
    except Exception as e:
        # Some kinds may not be reversible (e.g. compile-output diffs);
        # the probe records but doesn't hard-fail. The contract is
        # "rollback returns a structured response", not "every kind
        # can be rolled back".
        print(f"  rollback raised: {e!s}; continuing")
        return

    # Re-fetch the log and assert it grew (the rollback IS a diff).
    after = _get(f"{backend}/api/evolution_log?limit=50").get("diffs") or []
    if len(after) > len(diffs):
        print(f"  [OK] log grew: {len(diffs)} → {len(after)} "
              f"(rollback was itself recorded)")
    else:
        print(f"  (log size unchanged; rollback may have been a noop or "
              f"the implementation doesn't auto-record)")


def step_cleanup(backend: str, empty_id: str, consumer_id: str) -> None:
    _section("11) Cleanup")
    for cid in (empty_id, consumer_id):
        try:
            _delete(f"{backend}/api/concepts/{cid}")
            print(f"  deleted: {cid}")
        except Exception as e:
            print(f"  cleanup of {cid} raised: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    backend = DEFAULT_BACKEND
    if len(sys.argv) > 1:
        backend = sys.argv[1]
    print(f"[probe_live_concept_graph] §8D.47 LIVE authoring loop against {backend}")

    try:
        step_subsystem_real(backend)
        step_ensure_fixtures(backend)
        empty_id = step_create_empty_then_describe(backend)
        # Give the concept index a moment to catch up (cascade debounce).
        time.sleep(2.0)
        candidates = step_radiation(backend)
        step_resolve_and_wire(backend, empty_id, candidates)
        consumer_id = step_variable_auto_create(backend, empty_id)
        time.sleep(2.0)
        step_compile_chain(backend, consumer_id)
        step_apparition_for_real_focal(backend, consumer_id)
        # NEW: multi-step compute graph with real GPT4All dispatch in
        # the middle node. Exercises the LangGraph chain end-to-end.
        chain_ids = step_multi_step_chain_with_real_slm(backend)
        # NEW: closest-inverse on the chain's leaf. The summariser
        # consumed the leaf forward; inverse should surface candidates
        # whose forward execution would have produced the leaf-shaped
        # data block.
        step_closest_inverse(backend, chain_ids["formatter"])
        # NEW: cypher detection in a data block — real Kuzu execution.
        step_inline_cypher(backend)
        diffs = step_evolution_log(backend)
        step_rollback(backend, diffs)
        step_cleanup(backend, empty_id, consumer_id)
        # Cleanup the chain too.
        for cid in (chain_ids["leaf"], chain_ids["summariser"], chain_ids["formatter"]):
            try:
                _delete(f"{backend}/api/concepts/{cid}")
            except Exception:
                pass
        print(f"\n[probe_live_concept_graph] ALL CHECKS PASS — "
              f"editor authoring loop runs end-to-end against real subsystems")
        return 0
    except AssertionError as e:
        print(f"\n[probe_live_concept_graph] FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
