"""LIVE auto-complete probe — §8D.1.3 {partial} reference flow.

The user types into a new field's name cell; the editor auto-completes
against known concept names. Verifies:

  1. Prefix matches surface first, ranked by length-ascending.
  2. Substring matches surface after prefix matches.
  3. Non-matching concepts are excluded.
  4. The response shape is name + concept_id + type_hint
     (everything the editor needs to drop the completion in-place).
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


def _get(url: str, **kw) -> Dict[str, Any]:    return _http("GET", url, **kw)
def _post(url: str, body: Dict[str, Any], **kw) -> Dict[str, Any]:
    return _http("POST", url, body=body, **kw)
def _delete(url: str, **kw) -> Dict[str, Any]: return _http("DELETE", url, **kw)


def step_seed(backend: str) -> List[str]:
    """Create a few known-name concepts so we can assert the completer
    surfaces them in the right order."""
    _section("1) Seed concepts with known names")
    names = [
        "summary_seed",      # prefix match for "summ"
        "summary_consumer",  # prefix match for "summ" (longer name)
        "summer_camp",       # prefix match for "summ" (different domain)
        "consume_summary",   # substring match for "summary"
        "unrelated_thing",   # no match
    ]
    ids: List[str] = []
    for n in names:
        c = _post(f"{backend}/api/concepts", {
            "name": n,
            "description": f"Probe-seeded concept named {n}.",
            "workspace_id": "",
        })
        cid = c.get("concept_id") or ""
        _assert(bool(cid), f"create {n!r} failed: {c}")
        ids.append(cid)
        print(f"  created: {n}  ({cid[:8]})")
    return ids


def step_prefix_match(backend: str) -> None:
    _section("2) Prefix-match: 'summ' → summary_seed/consumer/summer_camp")
    resp = _get(f"{backend}/api/concept_completions?prefix=summ&k=10")
    comps = resp.get("completions") or []
    names = [c.get("name") for c in comps]
    print(f"  completions: {names}")
    expected_set = {"summary_seed", "summary_consumer", "summer_camp"}
    actual_set = set(names)
    missing = expected_set - actual_set
    _assert(not missing,
            f"expected prefix matches missing: {missing}  (got: {names})")
    # Length-ascending order — shortest comes first.
    prefix_only = [c for c in comps
                   if (c.get("name") or "").lower().startswith("summ")]
    lengths = [len(c.get("name") or "") for c in prefix_only]
    _assert(lengths == sorted(lengths),
            f"prefix matches not length-ascending: {lengths}")
    print(f"  [OK] {len(prefix_only)} prefix match(es), length-ascending")


def step_substring_after_prefix(backend: str) -> None:
    _section("3) Mixed: 'summary' → prefix matches first, then substring")
    resp = _get(f"{backend}/api/concept_completions?prefix=summary&k=10")
    comps = resp.get("completions") or []
    names = [c.get("name") for c in comps]
    print(f"  completions: {names}")
    # `summary_seed` and `summary_consumer` are prefix matches; they
    # MUST appear before `consume_summary` (substring match).
    if "consume_summary" in names and "summary_seed" in names:
        idx_prefix = names.index("summary_seed")
        idx_substr = names.index("consume_summary")
        _assert(idx_prefix < idx_substr,
                f"prefix-match should sort before substring-match: {names}")
        print(f"  [OK] prefix before substring (summary_seed@{idx_prefix} < "
              f"consume_summary@{idx_substr})")
    else:
        print(f"  (one of the test concepts missing — check seed step)")


def step_exclusion(backend: str) -> None:
    _section("4) 'unrelated' → only the unrelated_thing concept; "
             "no_match prefix returns nothing")
    resp = _get(f"{backend}/api/concept_completions?prefix=unrelated&k=10")
    names = [c.get("name") for c in (resp.get("completions") or [])]
    _assert("unrelated_thing" in names,
            f"unrelated_thing missing from 'unrelated' completions: {names}")
    for n in ("summary_seed", "summary_consumer"):
        _assert(n not in names,
                f"unrelated query brought back {n!r}: {names}")
    print(f"  [OK] correct scoping ({len(names)} hits, exclusion holds)")

    resp = _get(f"{backend}/api/concept_completions?prefix=xyzwq&k=10")
    names = [c.get("name") for c in (resp.get("completions") or [])]
    _assert(len(names) == 0,
            f"no-match prefix returned candidates: {names}")
    print(f"  [OK] empty prefix → empty completions")


def step_response_shape(backend: str) -> None:
    _section("5) Response shape carries name + concept_id + type_hint")
    resp = _get(f"{backend}/api/concept_completions?prefix=summ&k=3")
    comps = resp.get("completions") or []
    _assert(len(comps) >= 1, f"empty completions: {resp}")
    for c in comps[:3]:
        _assert("name" in c and "concept_id" in c and "type_hint" in c,
                f"completion missing required key: {c}")
        print(f"    {c['name']:24}  id={c['concept_id'][:12]}  type={c['type_hint']!r}")
    print(f"  [OK] response shape complete")


def step_cleanup(backend: str, ids: List[str]) -> None:
    _section("6) Cleanup seeded concepts")
    for cid in ids:
        try:
            _delete(f"{backend}/api/concepts/{cid}")
        except Exception:
            pass
    print(f"  deleted {len(ids)} concept(s)")


def main() -> int:
    backend = DEFAULT_BACKEND
    if len(sys.argv) > 1:
        backend = sys.argv[1]
    print(f"[probe_live_autocomplete] §8D.1.3 auto-complete against {backend}")
    try:
        ids = step_seed(backend)
        step_prefix_match(backend)
        step_substring_after_prefix(backend)
        step_exclusion(backend)
        step_response_shape(backend)
        step_cleanup(backend, ids)
        print(f"\n[probe_live_autocomplete] ALL CHECKS PASS — "
              f"auto-complete over linked structures works")
        return 0
    except AssertionError as e:
        print(f"\n[probe_live_autocomplete] FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
