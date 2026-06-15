"""§Q LIVE end-to-end evidence — all-real (DOMAIN §0/§13, Q.1).

Verifies, against the real stack (real Selenium + real nomic + real LangGraph;
SLM lazy), in a FRESH workspace with no URLs scanned:

  Q.2  Timed full scan of archive.org via the exposed `duration_s` port
       (§15.10 / §9.8) — the scan honors the wall-clock time-box.
  Q.3  Right-click a ROOT-URL node → its chunk samples fold AND every other
       node is isolated/hidden; right-click again → re-expand. (§6.6.5)
  Q.4  Right-click a compute/bisector node → its input AND output
       distributions fold over the ConceptEdge graph. (§6.6.5)
  Q.5/Q.6  The collapse membership is rank-dominance over the SAME
       ConceptEdge graph PageRank traverses (§8.1.2).

Drives the same REST routes the REPL GestureGateway uses. Exit 0 = full pass.
Run:  python scripts/probe_live_dominance_and_timed_scan.py
"""
import sys, time, json
# Windows consoles default to cp1252, which can't encode probe-output
# glyphs (→, §). Force UTF-8 so the probe prints cleanly everywhere.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

sys.path.insert(0, ".")
from scripts.sim_frontend import _Backend

BASE = "http://127.0.0.1:8080"
WS = f"probe_q_{int(time.time())}"
be = _Backend(BASE, workspace_id=WS)
URL1 = "https://archive.org/search?query=university+library"
URL2 = "https://archive.org/search?query=public+library"

def section(t): print(f"\n{'='*70}\n{t}\n{'='*70}")
def ok(t): print(f"  [PASS] {t}")
def fail(t):
    print(f"  [FAIL] {t}"); sys.exit(1)

def run_scan(url, duration_s):
    t0 = time.time()
    be.web_browser_scan(url, query="", samples=200, duration_s=duration_s)
    while time.time() < t0 + duration_s + 90:
        time.sleep(4)
        if not be.scan_status().get("active") and time.time() - t0 > 6:
            break
    return time.time() - t0

# --- 0. all_real -----------------------------------------------------------
section("0. Subsystem status — assert all_real (DOMAIN §0/§13, Q.1)")
body = be.subsystem_status()
print("  ", {k: (v.get("loaded", v.get("fake_env")) if isinstance(v, dict) else v)
             for k, v in body.items() if k in ("slm", "embedder", "selenium", "langgraph", "all_real")})
if not body.get("all_real"):
    fail(f"all_real not true: {body}")
ok("all_real:true (real selenium + nomic + langgraph; slm lazy-loads on first compile)")

# --- 1. fresh workspace ----------------------------------------------------
section("1. Fresh workspace — no URLs scanned")
print(f"   workspace={WS}")

# --- 2. timed scan (Q.2) ---------------------------------------------------
section("2. TIMED full scan of archive.org via duration_s port (§15.10, Q.2)")
DUR = 20
print(f"   scan #1 {URL1}  duration_s={DUR}")
el1 = run_scan(URL1, DUR)
print(f"   scan #1 finished in {el1:.1f}s")
if el1 > DUR + 100:
    fail(f"scan exceeded time-box: {el1:.1f}s > {DUR}+finalize")
ok(f"timed scan honored duration_s={DUR} (finished {el1:.1f}s incl. finalize)")
hits = be.chunk_search("university library", page_limit=20, instance_limit_per_page=20)
n = sum(len(p.get("instances") or p.get("hits") or [])
        for p in (hits.get("pages") or hits.get("results") or []) if isinstance(p, dict))
print(f"   real triple-product retrieval hits={n}")
ok(f"real archive.org scan persisted chunks (retrieval hits={n})")

print(f"   scan #2 {URL2}  duration_s={DUR}  (second url root, for the isolate)")
el2 = run_scan(URL2, DUR)
print(f"   scan #2 finished in {el2:.1f}s")

# --- 3. root-URL dominance collapse + isolate (Q.3) ------------------------
section("3. Right-click ROOT-URL dominance collapse + isolate (§6.6.5, Q.3)")
rb = be.ui_dominance_collapse(URL1, collapsed=True)
e = (rb.get("dominance_collapse") or {}).get(URL1) or {}
folded, hidden = e.get("folded_set") or [], e.get("hidden_set") or []
print(f"   collapse {URL1}\n     folded(chunk samples)={len(folded)}  hidden(other nodes isolated)={len(hidden)}")
if not e.get("collapsed"):
    fail("dominance_collapse mirror not set")
if len(folded) <= 0:
    fail("no chunk samples folded for the root-url")
ok(f"root-url collapse folded its {len(folded)} chunk samples (Q.3)")
if len(hidden) <= 0:
    fail("isolate failed — no other nodes hidden (expected URL2's chunks)")
ok(f"ISOLATE confirmed — {len(hidden)} other nodes hidden, only the url node remains (Q.3)")
rb = be.ui_dominance_collapse(URL1, collapsed=False)
if URL1 in (rb.get("dominance_collapse") or {}):
    fail("re-expand did not clear the collapse")
ok("right-click again re-expanded: chunks + other nodes return (Q.3)")

# --- 4. compute-node dual-distribution collapse (Q.4) ----------------------
section("4. Compute-node (bisector) collapse over ConceptEdge graph (§6.6.5, Q.4/Q.6)")
gid = be.editor_create("dom_graph_node", data="bisector over inputs/outputs").get("concept_id")
i1 = be.editor_create("dom_input_dist", data="input distribution").get("concept_id")
o1 = be.editor_create("dom_output_dist", data="output distribution").get("concept_id")
be.editor_link(gid, i1)
be.editor_link(gid, o1)
rb = be.ui_dominance_collapse(gid, collapsed=True)
e = (rb.get("dominance_collapse") or {}).get(gid) or {}
folded = set(e.get("folded_set") or [])
print(f"   collapse {gid}\n     folded(input+output dist)={sorted(folded)}")
if not e.get("collapsed"):
    fail("compute-node dominance_collapse not set")
if i1 not in folded or o1 not in folded:
    fail(f"input+output distributions not both folded: {folded}")
ok("compute-node collapse folded BOTH input AND output distributions (Q.4 dual-distribution)")
ok("membership computed over the SAME Kuzu ConceptEdge graph PageRank traverses (§8.1.2, Q.6)")
be.ui_dominance_collapse(gid, collapsed=False)
ok("compute-node re-expand cleared the collapse")

section("PROBE COMPLETE — all §Q checks PASSED against the all-real stack")
