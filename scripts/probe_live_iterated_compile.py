"""LIVE end-to-end probe for the §8D.49 unified iterated-compile use case.

The synthesis of §8D.45 (outside-in scan), §8D.47 (inside-out authoring),
and §8D.48 (autonomous agent) into a single trajectory:

  1. Confirm /api/subsystem_status.all_real == True (§8D.46).
  2. Ensure the chunk pool is populated from a real archive.org scan
     (re-using a prior scan if present; triggering a fresh scan only
     when the pool is empty).
  3. Pull N chunks from the pool via real TF-IDF retrieval over the
     query "university library".
  4. Author the three-node templated compute graph:
       leaf:        chunk_sample (rebinds each iteration; its value
                    is the chunk's rendered_text on each step)
       middle:      structured_prompt (compute_kind=prompt; data
                    references {chunk_sample}; SLM-generated)
       root:        formatted_output (data references {structured_prompt})
  5. Wire leaf → middle → root with typed edges (PROVIDES_VALUE_FOR).
  6. ITERATE: for each of K=3 chunks, PATCH the leaf's data to the
     chunk's content, fire /api/conceptual/compile_chain rooted at
     the formatter, capture the real GPT4All rendering, print the
     head so the operator reads what the model said about REAL
     archive.org content.
  7. Verify halo + right-click compile/collapse round-trip on the
     compiled-graph nodes (§8D.2.2).
  8. Cleanup.

Run as:  python scripts/probe_live_iterated_compile.py [BACKEND_URL]
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
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_BACKEND = "http://127.0.0.1:8080"
QUERY = "university library"
N_ITERATIONS = 3


def _section(title: str) -> None:
    print(f"\n== {title} {'=' * max(0, 60 - len(title))}")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _http(method: str, url: str, *,
          body: Optional[Dict[str, Any]] = None,
          timeout: float = 60.0) -> Dict[str, Any]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _get(url: str, **kw) -> Dict[str, Any]:    return _http("GET", url, **kw)
def _post(url: str, body: Dict[str, Any], **kw) -> Dict[str, Any]:
    return _http("POST", url, body=body, **kw)
def _patch(url: str, body: Dict[str, Any], **kw) -> Dict[str, Any]:
    return _http("PATCH", url, body=body, **kw)
def _delete(url: str, **kw) -> Dict[str, Any]: return _http("DELETE", url, **kw)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_subsystems_real(backend: str) -> None:
    _section("1) Subsystems all real (§8D.46)")
    s = _get(f"{backend}/api/subsystem_status")
    _assert(s.get("all_real") is True,
            f"subsystems NOT all real: {s}")
    print(f"  slm={s['slm']['backend']} ({s['slm'].get('model')})")
    print(f"  embedder={s['embedder']['backend']} (device={s['embedder'].get('device')})")
    print(f"  selenium={s['selenium']['backend']}  langgraph={s['langgraph']['backend']}")


def step_chunk_pool(backend: str) -> List[Dict[str, Any]]:
    _section(f"2) Chunk pool for query {QUERY!r}")
    # Check chunk_nodes first — if pool is empty, the user must have
    # purged; we fail loudly rather than auto-scanning (auto-scan
    # would add 30+s to every probe run; the §8D.45 probe is the
    # right harness to populate the pool freshly).
    nodes_resp = _get(f"{backend}/api/chunk_nodes", timeout=60)
    n = len((nodes_resp or {}).get("nodes") or [])
    print(f"  chunk pool size: {n}")
    _assert(n > 0,
            f"chunk pool is empty; run probe_live_archive_scan.py first "
            f"to populate from a real scan")
    # TF-IDF retrieval — gives us real chunks ranked for the query.
    search = _post(f"{backend}/api/chunk_search", {
        "query": QUERY, "page_limit": 1, "instance_limit_per_page": N_ITERATIONS,
    }, timeout=60)
    instances: List[Dict[str, Any]] = []
    for p in (search.get("pages") or []):
        for inst in (p.get("instances") or []):
            instances.append(inst)
            if len(instances) >= N_ITERATIONS:
                break
        if len(instances) >= N_ITERATIONS:
            break
    print(f"  retrieved {len(instances)} chunk(s) for the iteration bank")
    for i, inst in enumerate(instances):
        txt = (inst.get("rendered_text") or "")[:80].replace("\n", " ")
        print(f"    [{i}] id={inst.get('id', '?')[:20]}  score={inst.get('score', 0):.4f}  text={txt!r}")
    _assert(len(instances) >= 1,
            f"no chunks retrieved for {QUERY!r}: {search}")
    return instances


def step_ensure_fixtures(backend: str) -> None:
    _section("3) Foundation fixtures ensured")
    _post(f"{backend}/api/foundation/ensure", {"workspace_id": ""})
    print("  fixtures ready (Database / WebBrowser / Agent + Python trees)")


def step_author_template(backend: str) -> Dict[str, str]:
    _section("4) Author three-node templated compute graph (§8D.49.1)")

    # Leaf — chunk_sample. Starts empty; iteration rebinds its data to
    # the next chunk's text content. Compute kind is `plain` so the
    # rendering just tree-prints the current value.
    leaf = _post(f"{backend}/api/concepts", {
        "name": "chunk_sample",
        "description": "The active sample chunk for this iteration step.",
        "data": json.dumps({"text": "(uninitialised — set by iteration)"}),
        "workspace_id": "",
    })
    leaf_id = leaf.get("concept_id") or ""
    _assert(bool(leaf_id), f"leaf create failed: {leaf}")
    print(f"  leaf:   {leaf_id}  (chunk_sample, kind=plain)")

    # Middle — structured_prompt. compute_kind=prompt; references
    # {chunk_sample}; fires real GPT4All on each compile.
    middle = _post(f"{backend}/api/concepts", {
        "name": "structured_prompt",
        "description": "SLM extracts title + one-sentence summary from {chunk_sample}.",
        "data": json.dumps({
            "compute_kind": "prompt",
            "prompt": (
                "From the following text, output exactly one line of the form "
                "'TITLE | SUMMARY' where TITLE is the most likely document "
                "title and SUMMARY is one concise sentence about it.\n\n"
                "Text:\n{chunk_sample}\n"
            ),
        }),
        "workspace_id": "",
    })
    middle_id = middle.get("concept_id") or ""
    _assert(bool(middle_id), f"middle create failed: {middle}")
    print(f"  middle: {middle_id}  (structured_prompt, kind=prompt → real GPT4All)")

    # Root — formatted_output. compute_kind=plain; references the
    # structured_prompt's compiled rendering.
    root = _post(f"{backend}/api/concepts", {
        "name": "formatted_output",
        "description": "Final user-facing formatted output per chunk.",
        "data": json.dumps({
            "line": "→ {structured_prompt}",
        }),
        "workspace_id": "",
    })
    root_id = root.get("concept_id") or ""
    _assert(bool(root_id), f"root create failed: {root}")
    print(f"  root:   {root_id}  (formatted_output, kind=plain)")

    # Typed edges so compile_chain has back-references to walk.
    for src, tgt in [(leaf_id, middle_id), (middle_id, root_id)]:
        _post(f"{backend}/api/concept_edges", {
            "source_id": src, "target_id": tgt,
            "edge_type": "PROVIDES_VALUE_FOR", "workspace_id": "",
        })
    print(f"  wired: chunk_sample → structured_prompt → formatted_output")
    return {"leaf": leaf_id, "middle": middle_id, "root": root_id}


def step_iterate(backend: str, ids: Dict[str, str],
                 chunks: List[Dict[str, Any]]) -> None:
    _section(f"5) Iterate: compile_chain over {len(chunks)} real chunks "
             f"(real GPT4All per iteration)")
    for i, chunk in enumerate(chunks):
        chunk_text = (chunk.get("rendered_text") or "").strip()
        if not chunk_text:
            print(f"  iter {i}: chunk had no rendered_text; skipping")
            continue
        # Trim to first 600 chars so the SLM's context isn't blown up
        # by long page concatenations.
        chunk_text_head = chunk_text[:600]
        print(f"\n  --- iter {i} (chunk {chunk.get('id', '?')[:18]}) ---")
        print(f"      input head: {chunk_text_head[:90]!r}")
        # Rebind the leaf's data to the chunk's content. The cascade
        # re-fires the rendering automatically per §8D.14.
        _patch(f"{backend}/api/concepts/{ids['leaf']}", {
            "data": json.dumps({"text": chunk_text_head}),
        })
        # Wait briefly for the cascade to settle.
        time.sleep(1.0)
        # Compile the chain rooted at the root (formatted_output). The
        # chain walks leaf → middle → root; middle's prompt dispatch
        # fires real GPT4All; root's rendering shows the formatted line.
        t0 = time.monotonic()
        chain = _post(f"{backend}/api/conceptual/compile_chain", {
            "focal_id": ids["root"], "workspace_id": "",
            "max_depth": 5, "use_slm": True,
        }, timeout=600)
        elapsed = time.monotonic() - t0
        ordered = chain.get("ordered") or []
        state = chain.get("state") or {}
        print(f"      compile elapsed: {elapsed:.1f}s; ordered={len(ordered)}")
        # The middle (prompt) node's rendering is the real SLM output.
        middle_state = state.get(ids["middle"]) or {}
        middle_kind = middle_state.get("kind", "?")
        middle_rendering = (middle_state.get("rendering") or "").strip()
        print(f"      middle: kind={middle_kind}, "
              f"rendering={middle_rendering[:140]!r}")
        # Assertion: the middle's rendering must NOT be the stub trailer.
        _assert(not middle_rendering.startswith("[stub-slm]"),
                f"iter {i}: middle was stub: {middle_rendering!r}")
        _assert(len(middle_rendering.strip()) > 0,
                f"iter {i}: middle rendering empty: {middle_state}")
        # The root's rendering should incorporate the middle's content
        # (after the {structured_prompt} ref resolves).
        root_state = state.get(ids["root"]) or {}
        root_rendering = (root_state.get("rendering") or "").strip()
        print(f"      root:   {root_rendering[:140]!r}")
        _assert(len(root_rendering) > 0,
                f"iter {i}: root rendering empty: {root_state}")


def step_halo_and_toggle(backend: str, ids: Dict[str, str]) -> None:
    _section("6) Halo + right-click compile/collapse round-trip (§8D.2.2)")
    middle_id = ids["middle"]
    # 6a — focal halo on the middle node (compiled-graph node in the
    # editor surface). Real apparition retrieval against the workspace
    # via real nomic + pagerank + tfidf.
    halo = _get(f"{backend}/api/apparitions/{middle_id}?k=5")
    cands = halo.get("candidates") or []
    print(f"  halo on structured_prompt: {len(cands)} candidate(s)")
    for c in cands[:4]:
        cid = (c.get("card_id") or "?")[:36]
        print(f"    {cid:36}  score={c.get('score', 0):.4f}"
              f"  nomic={c.get('nomic_cos', 0):.4f}"
              f"  tfidf={c.get('tfidf_cos', 0):.4f}")
    _assert(len(cands) > 0,
            f"halo returned no candidates: {halo}")
    real = [c for c in cands if abs(float(c.get("nomic_cos", 0))) > 1e-6]
    _assert(len(real) > 0,
            f"no halo candidate has non-zero nomic cosine: {cands}")
    print(f"  [OK] {len(real)} candidate(s) with real nomic cosines")

    # 6b — right-click expand mirror.
    exp = _post(f"{backend}/api/ui/compile_expand", {
        "workspace_id": "",
        "central_id":   middle_id,
        "children":     ["compute_kind", "prompt", "chunk_sample"],
    })
    exp_state = (exp.get("state") or {}).get("compile_expansions") or {}
    _assert(middle_id in exp_state,
            f"compile_expand didn't record central: {exp_state}")
    print(f"  [OK] compile_expand recorded {list(exp_state.keys())}")

    # 6c — right-click collapse — re-folds to the panel.
    col = _post(f"{backend}/api/ui/compile_collapse", {
        "workspace_id": "", "central_id": middle_id,
    })
    col_state = (col.get("state") or {}).get("compile_expansions") or {}
    _assert(middle_id not in col_state,
            f"compile_collapse didn't clear central: {col_state}")
    print(f"  [OK] compile_collapse cleared (remaining: {len(col_state)})")


def step_cleanup(backend: str, ids: Dict[str, str]) -> None:
    _section("7) Cleanup template nodes (chunk pool stays intact)")
    for label, cid in ids.items():
        try:
            _delete(f"{backend}/api/concepts/{cid}")
            print(f"  deleted {label}: {cid}")
        except Exception as e:
            print(f"  cleanup {label} ({cid}) raised: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    backend = DEFAULT_BACKEND
    if len(sys.argv) > 1:
        backend = sys.argv[1]
    print(f"[probe_live_iterated_compile] §8D.49 LIVE unified iterated-compile "
          f"against {backend}")
    print(f"[probe_live_iterated_compile] query={QUERY!r}  iterations={N_ITERATIONS}")

    try:
        step_subsystems_real(backend)
        chunks = step_chunk_pool(backend)
        step_ensure_fixtures(backend)
        ids = step_author_template(backend)
        step_iterate(backend, ids, chunks)
        step_halo_and_toggle(backend, ids)
        step_cleanup(backend, ids)
        print(f"\n[probe_live_iterated_compile] ALL CHECKS PASS — "
              f"unified iterated-compile runs end-to-end against real subsystems")
        return 0
    except AssertionError as e:
        print(f"\n[probe_live_iterated_compile] FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
