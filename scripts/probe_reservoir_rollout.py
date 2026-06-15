"""Offline probe for the §7.8 reservoir-rollout code design (first increment).

Deterministic + browserless: a temp Kuzu DB + fake SLM/embedder gates + no
webdriver, so it runs in CI without booting the backend. Verifies the three
pure functions implemented from `code_specs/backend/{compute,layout}.md`:

  * `conceptual_compute.readout_nodes` (§7.8.2) — the readout perimeter:
    settled nodes referenced by nobody in the {ref}-connected component;
    query-invariant; the advancing abstraction front (§7.8.5).
  * `layout_service.place_compute_graph_node` (§6.6.4, P.10) — the bisector
    midpoint between the input and output centroids; hidden centroids;
    monotone settle_seq.
  * `layout_service.compute_projector_links` (§6.6.4, P.8/P.9) — the
    UMAP-independent, coordinate-free link network.

Anti-goal guard: ProjectorLink carries NO coordinates (§18.34).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Deterministic, browserless — set BEFORE importing backend modules.
# §R.9 — janitor-managed throwaway DB dir (guaranteed atexit removal).
from backend.services.db_janitor import new_temp_db_path, register_for_cleanup

os.environ["WFH_DB_PATH"] = register_for_cleanup(new_temp_db_path("reservoir_probe"))
os.environ.setdefault("WFH_FAKE_SLM", "1")
os.environ.setdefault("WFH_FAKE_EMBEDDER", "1")
os.environ.setdefault("NO_WEBDRIVER", "1")

# Windows consoles default to cp1252, which can't encode some glyphs used
# below (e.g. the → arrow). Force UTF-8 so the probe prints cleanly.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _short(ids):
    return [str(x)[:8] for x in ids]


def main() -> int:
    from backend.services.graph_editor import GraphEditor
    from backend.services.conceptual_compute import (
        readout_nodes, input_nodes, graph_component,
    )
    from backend.services.layout_service import (
        LayoutService, LayoutFrame, ProjectorLink, ComputeGraphPlacement,
    )
    from backend.services.settings import get_settings
    from backend.api.ws_frames import build_compute_graph_layout, FrameType

    ws = ""
    ge = GraphEditor()

    # ---- §7.8.2 readout_nodes -----------------------------------------
    # S (input, data "ONE") ← C (consumer, data "got {res_src}")
    s = ge.create_concept(name="res_src", data="ONE", workspace_id=ws)
    c = ge.create_concept(name="res_consumer", data="got {res_src}", workspace_id=ws)
    ge.update_concept(s.concept_id, rendering="ONE")          # settle
    ge.update_concept(c.concept_id, rendering="got ONE")      # settle

    ro = readout_nodes(c.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(c.concept_id in ro, f"consumer must be a readout (terminal): {_short(ro)}")
    _assert(s.concept_id not in ro, f"source is referenced → hidden, not readout: {_short(ro)}")

    # query-invariance: asking from the source gives the same perimeter
    ro_from_s = readout_nodes(s.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(set(ro_from_s) == set(ro), f"perimeter must be query-invariant: {_short(ro_from_s)} vs {_short(ro)}")
    print(f"  readout_nodes OK — perimeter={_short(ro)} (consumer terminal, source hidden, query-invariant)")

    # an UNSETTLED downstream node is not yet a readout, and it demotes C
    d = ge.create_concept(name="res_unsettled", data="from {res_consumer}", workspace_id=ws)
    ro_unsettled = readout_nodes(d.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(d.concept_id not in ro_unsettled, f"unsettled node must not be a readout: {_short(ro_unsettled)}")
    _assert(c.concept_id not in ro_unsettled, f"consumer now referenced by D → demoted hidden: {_short(ro_unsettled)}")

    # §7.8.5 advancing abstraction front: settle D → it becomes the new perimeter
    ge.update_concept(d.concept_id, rendering="from got ONE")
    ro_advanced = readout_nodes(s.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(d.concept_id in ro_advanced, f"settled D must be the new perimeter: {_short(ro_advanced)}")
    _assert(c.concept_id not in ro_advanced, f"C demoted to hidden state: {_short(ro_advanced)}")
    print("  abstraction-front advance OK — yesterday's readout (C) becomes hidden once D consumes it (§7.8.5)")

    # ---- §7.8.1 input_nodes (sources) + graph_component (id) -----------
    # graph is now S -> C -> D (S references nothing; C refs S; D refs C).
    ins = input_nodes(c.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(set(ins) == {s.concept_id},
            f"input sources must be exactly the source leaf S: {_short(ins)}")
    ins_from_d = input_nodes(d.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(set(ins_from_d) == set(ins), f"input_nodes must be query-invariant: {_short(ins_from_d)}")
    # inputs and readouts are disjoint complements of the hidden interior (C).
    _assert(set(ins).isdisjoint(set(ro_advanced)),
            f"inputs/readouts must be disjoint: {_short(ins)} vs {_short(ro_advanced)}")
    comp = graph_component(d.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(set(comp) == {s.concept_id, c.concept_id, d.concept_id},
            f"graph_component must span the whole {{ref}} component: {_short(comp)}")
    _assert(comp == sorted(comp), "graph_component must be sorted (stable graph_id = comp[0])")
    comp_from_s = graph_component(s.concept_id, graph_editor=ge, workspace_id=ws)
    _assert(comp_from_s == comp, f"graph_component (hence graph_id) must be query-invariant: {_short(comp_from_s)}")
    print(f"  input_nodes/graph_component OK — sources={_short(ins)}, component={_short(comp)}, "
          f"stable graph_id={comp[0][:8]} (query-invariant)")

    # ---- §6.6.4 place_compute_graph_node ------------------------------
    svc = LayoutService()
    svc._frames[ws] = LayoutFrame(workspace_id=ws, coords={
        s.concept_id: [0.0, 0.0, 0.0, 0.1, 0.2, 0.3],   # input at origin, hsv tail
        d.concept_id: [10.0, 0.0, 0.0, 0.4, 0.5, 0.6],  # readout at x=10
    })
    p = svc.place_compute_graph_node(ws, "g1", [s.concept_id], [d.concept_id])
    _assert(isinstance(p, ComputeGraphPlacement), "must return a ComputeGraphPlacement")
    _assert(abs(p.pos[0] - 5.0) < 1e-6 and abs(p.pos[1]) < 1e-6 and abs(p.pos[2]) < 1e-6,
            f"bisector midpoint must be (5,0,0): {p.pos}")
    _assert(tuple(round(x, 6) for x in p.hsv) == (0.1, 0.2, 0.3),
            f"hsv must be carried from the input: {p.hsv}")
    _assert(p.settle_seq == 1, f"settle_seq must start at 1: {p.settle_seq}")

    # output centroid moves → the node slides; settle_seq is monotone
    svc._frames[ws].coords[d.concept_id] = [20.0, 0.0, 0.0, 0.4, 0.5, 0.6]
    p2 = svc.place_compute_graph_node(ws, "g1", [s.concept_id], [d.concept_id])
    _assert(abs(p2.pos[0] - 10.0) < 1e-6, f"node must slide to new midpoint (10,0,0): {p2.pos}")
    _assert(p2.settle_seq == 2, f"settle_seq must increase per graph: {p2.settle_seq}")
    print(f"  place_compute_graph_node OK -- bisector pos={p.pos} -> {p2.pos} slides, settle_seq monotone, centroids hidden")

    # ---- §6.6.4 compute_projector_links (UMAP-independent) ------------
    links = svc.compute_projector_links(
        ws, "g1",
        input_ids=[s.concept_id], readout_ids=[d.concept_id],
        url_sample_map={"https://example.org": [s.concept_id]},
    )
    _assert(all(isinstance(l, ProjectorLink) for l in links), "all must be ProjectorLink")
    kinds = {l.kind for l in links}
    _assert({"url_to_sample", "input_to_graph", "readout_to_graph"} <= kinds,
            f"missing link kinds: {sorted(kinds)}")
    _assert(all(l.graph_id == "g1" for l in links), "every link tagged with graph_id")
    # §18.34: the link records carry NO coordinates
    for l in links:
        fieldnames = set(getattr(l, "__dataclass_fields__", {}).keys())
        _assert("pos" not in fieldnames and "coords" not in fieldnames and "layout6d" not in fieldnames,
                f"ProjectorLink must be coordinate-free (§18.34): {fieldnames}")
    print(f"  compute_projector_links OK — {len(links)} links, kinds={sorted(kinds)}, coordinate-free (§18.34)")

    # ---- constant wired through Settings ------------------------------
    s_cfg = get_settings()
    _assert(getattr(s_cfg, "readout_delta_max_inflight", None) == 64,
            f"READOUT_DELTA_MAX_INFLIGHT must default to 64: {getattr(s_cfg, 'readout_delta_max_inflight', None)}")
    print(f"  settings OK — readout_delta_max_inflight={s_cfg.readout_delta_max_inflight} (env-overridable via WFH_READOUT_DELTA_MAX_INFLIGHT)")

    # ---- §6.6.4 / contracts §3 — build_compute_graph_layout frame -----
    readout_payload = [{"chunk_id": d.concept_id, "pos": [20.0, 0.0, 0.0], "hsv": [0.4, 0.5, 0.6]}]
    frame = build_compute_graph_layout(
        workspace_id=ws, placement=p2, readouts=readout_payload, links=links,
    )
    _assert(frame.get("type") == FrameType.COMPUTE_GRAPH_LAYOUT == "compute_graph_layout",
            f"frame type must be the compute_graph_layout contract string: {frame.get('type')}")
    _assert(frame.get("graph_id") == "g1", f"frame graph_id: {frame.get('graph_id')}")
    _assert(frame.get("node", {}).get("pos") == [10.0, 0.0, 0.0], f"frame node.pos: {frame.get('node')}")
    _assert(frame.get("settle_seq") == 2, f"frame settle_seq: {frame.get('settle_seq')}")
    _assert("frame_seq" in frame, "frame must carry a monotone frame_seq (sequencing)")
    _assert(len(frame.get("links", [])) == len(links), "all links serialized")
    # §18.34: serialized links are coordinate-free ({src_id, dst_id, kind} only)
    for fl in frame.get("links", []):
        _assert(set(fl.keys()) == {"src_id", "dst_id", "kind"},
                f"link wire shape must be coordinate-free (§18.34): {sorted(fl.keys())}")
    print(f"  build_compute_graph_layout OK — type={frame['type']!r}, node.pos={frame['node']['pos']}, "
          f"{len(frame['links'])} coordinate-free links, settle_seq={frame['settle_seq']}")

    # ---- §7.8.3 stream_readout_deltas (per-node, no barrier batch) -----
    from backend.services.conceptual_compute import stream_readout_deltas
    captured = []
    emitted = stream_readout_deltas(
        s.concept_id, graph_editor=ge, layout_service=svc, workspace_id=ws,
        broadcast=lambda snap, fr: captured.append(fr),
    )
    # component is S→C→D with single readout D → exactly ONE per-node delta.
    _assert(len(emitted) == 1, f"one readout → one per-node delta (not a batch): {len(emitted)}")
    _assert(len(captured) == 1 and captured[0] is emitted[0], "delta must also be broadcast")
    _assert(emitted[0].get("type") == "compute_graph_layout", f"delta type: {emitted[0].get('type')}")
    ro_payload = emitted[0].get("readouts") or []
    _assert(len(ro_payload) == 1 and ro_payload[0].get("chunk_id") == d.concept_id,
            f"per-node delta must carry exactly the one readout D: {ro_payload}")
    for fl in emitted[0].get("links", []):
        _assert(set(fl.keys()) == {"src_id", "dst_id", "kind"},
                f"streamed link must be coordinate-free (§18.34): {sorted(fl.keys())}")
    print(f"  stream_readout_deltas OK — {len(emitted)} per-node delta (readout={d.concept_id[:8]}), "
          f"broadcast + typed + coordinate-free, no barrier batch (§7.8.3/§18.34)")

    # ---- §7.8.1 resolve_input_by_inverse_lookup + _pattern_sample_index --
    import json as _json
    from backend.services.conceptual_compute import (
        resolve_input_by_inverse_lookup, ChunkSampleRef, _pattern_sample_index,
    )
    from backend.services.apparition_service import ApparitionCandidate
    # a pattern_map with NESTED sampled_chunks — the generalized sample family.
    pm_data = _json.dumps({"patterns": {
        "patAAAA": {"sampled_chunks": ["chunk_a", "chunk_b"],
                    "sub_patterns": {"patCCCC": {"sampled_chunks": ["chunk_c"]}}},
    }})
    ge.create_concept(
        concept_id="pattern_map::_default", name="pattern_map", data=pm_data,
        workspace_id=ws, type_hint="pattern_map", provenance="derived-from-chunk")
    idx = _pattern_sample_index(ge, ws)
    _assert(idx == {"chunk_a": "patAAAA", "chunk_b": "patAAAA", "chunk_c": "patCCCC"},
            f"pattern-sample index must map chunk->pattern recursively (incl sub_patterns): {idx}")

    def _cand(cid, score):
        return ApparitionCandidate(card_id=cid, score=score, pagerank=1.0,
                                   tfidf_cos=1.0, nomic_cos=1.0)

    class _FakeAppr:
        """Controlled inverse ranking: a NON-sample ranks highest, then the
        samples — the lookup must SKIP the non-sample and return the top SAMPLE
        (the new pattern-sample filter is what we verify; closest_inverse itself
        is pre-existing + separately covered)."""
        def closest_inverse(self, output_id, *, workspace_id="", k=10):
            return [_cand("not_a_sample", 0.99), _cand("chunk_b", 0.80), _cand("chunk_a", 0.70)]

    ref = resolve_input_by_inverse_lookup(
        "consumer_node", "in_port", graph_editor=ge, workspace_id=ws,
        apparition_service=_FakeAppr())
    _assert(isinstance(ref, ChunkSampleRef), f"must return a ChunkSampleRef: {ref}")
    _assert(ref.chunk_id == "chunk_b" and ref.pattern_id == "patAAAA"
            and abs(ref.score - 0.80) < 1e-9,
            f"must return the highest-ranked SAMPLE (non-sample skipped): {ref}")

    class _FakeApprNone:
        def closest_inverse(self, output_id, *, workspace_id="", k=10):
            return [_cand("not_a_sample", 0.99)]

    _assert(resolve_input_by_inverse_lookup(
        "consumer_node", "in_port", graph_editor=ge, workspace_id=ws,
        apparition_service=_FakeApprNone()) is None,
        "no pattern-sample candidate must resolve to None")
    print(f"  resolve_input_by_inverse_lookup OK — inverse rank filtered to chunk samples "
          f"(returned {ref.chunk_id}/{ref.pattern_id}@{ref.score:.2f}; non-samples skipped; empty→None) (§7.8.1)")

    print("[probe_reservoir_rollout] ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
