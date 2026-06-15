"""
langgraph_loop.py -- Phase 5 perception/action cycle.

Four nodes, one linear pass (no retry loop on the first implementation):

    Observation  ->  Perception  ->  Cognition  ->  Action  ->  END

Each node reads and writes the ``AgentState`` TypedDict. The whole
graph is compiled once and invoked per user intent.

Node contracts
--------------

* **Observation** — runs ``run_pipeline_live`` (or an injected HTML path
  for offline/test runs). Populates ``trie`` and ``chunks``.

* **Perception** — loads Phase-3 labels and Phase-4 embeddings for the
  current ``trie.version.version_id`` and emits a compact
  ``scene_graph: {pattern_id: {role, category, summary,
  representative_xpath, image_url}}``. That's the LLM-facing view.

* **Cognition** — resolves the user intent to a pattern via embedding
  cosine + text-search fallback, and emits ``plan = {action,
  target_pattern_id, concrete_xpath}``.

* **Action** — hands ``plan`` to ``ShadowResolver`` (click/fill). Writes
  the result string back to ``state["result"]``.

The cognition node is designed to work with either a real SLM or a
stub. The demo uses the SLM only for re-ranking — pattern lookup is
primarily embedding-cosine-based (deterministic and fast).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import StateGraph, END

from backend.dom.pipeline import run_pipeline, run_pipeline_live, PipelineResult
from backend.dom.trie_persistence import BuiltTrie, PatternRow
from backend.mapper.chunk_builder import Chunk
from backend.services.pattern_embedder import (
    PatternEmbedder,
    PatternEmbeddingRow,
)
from backend.services.pattern_labeler import PatternLabelRow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """Everything that flows between nodes."""

    url: str
    user_intent: str

    # Observation output
    trie: BuiltTrie
    chunks: List[Chunk]
    html_source: str
    pipeline_result: PipelineResult

    # Perception output
    scene_graph: Dict[str, Dict[str, Any]]
    labels: List[PatternLabelRow]
    embeddings: List[PatternEmbeddingRow]

    # Cognition output
    plan: Dict[str, Any]
    candidates: List[Dict[str, Any]]

    # Action output
    result: str

    # Running trace of node -> summary for debuggability
    history: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Node dependencies bundle
# ---------------------------------------------------------------------------


@dataclass
class AgentDeps:
    """Injectables so tests don't need a real driver / SLM / embedder.

    All fields are optional; missing ones are constructed on demand.
    """

    driver: Any = None
    labeler: Any = None
    embedder_service: Any = None  # injected into PatternEmbedder
    slm: Any = None
    resolver_factory: Optional[Callable[..., Any]] = None
    html_source: Optional[str] = None  # if set, Observation skips selenium
    single_pass: bool = True
    persist: bool = False

    def make_resolver(self, built: BuiltTrie, dom=None):
        if self.resolver_factory is not None:
            return self.resolver_factory(self.driver, dom, built)
        from backend.agent.shadow_resolver import ShadowResolver
        return ShadowResolver(self.driver, dom, built)


# ---------------------------------------------------------------------------
# Node: Observation
# ---------------------------------------------------------------------------


def observation_node(state: AgentState, deps: AgentDeps) -> AgentState:
    """Run a single scan via HTML-fixture or live Selenium."""
    url = state["url"]
    if deps.html_source is not None:
        result = run_pipeline(deps.html_source, url=url, persist=deps.persist)
    else:
        result = run_pipeline_live(
            deps.driver,
            url,
            persist=deps.persist,
            single_pass=deps.single_pass,
        )

    _append_history(state, "observation", {
        "pattern_count": result.trie.version.pattern_count,
        "content_pattern_count": result.trie.version.content_pattern_count,
        "chunk_count": len(result.chunks),
        "elapsed_ms": result.elapsed_ms,
    })
    return {
        "pipeline_result": result,
        "trie": result.trie,
        "chunks": result.chunks,
        "html_source": deps.html_source or "",
        "history": state.get("history") or [],
    }


# ---------------------------------------------------------------------------
# Node: Perception
# ---------------------------------------------------------------------------


def perception_node(state: AgentState, deps: AgentDeps) -> AgentState:
    """Label every content chunk + embed them. Emit a compact scene graph."""
    from backend.services.pattern_labeler import PatternLabeler

    built: BuiltTrie = state["trie"]
    chunks: List[Chunk] = state["chunks"]

    labeler = deps.labeler
    if labeler is None:
        labeler = PatternLabeler(slm=deps.slm) if deps.slm is not None else PatternLabeler()
    labels = labeler.label_trie(built, chunks)

    embedder = PatternEmbedder(embedder=deps.embedder_service)
    embeddings = embedder.embed_labeled_patterns(built, chunks, labels)

    label_by_pid = {lbl.pattern_id: lbl for lbl in labels}
    chunk_by_pattern = {c.pattern: c for c in chunks}

    scene_graph: Dict[str, Dict[str, Any]] = {}
    for pat in built.patterns:
        label = label_by_pid.get(pat.pattern_id)
        if label is None:
            continue
        chunk = chunk_by_pattern.get(pat.pattern)
        image_url = ""
        if chunk and chunk.image_urls:
            image_url = next(iter(chunk.image_urls.values()), "")
        scene_graph[pat.pattern_id] = {
            "pattern": pat.pattern,
            "role": label.role,
            "category": label.category,
            "summary": label.summary,
            "confidence": label.confidence,
            "representative_xpath": pat.representative_xpath,
            "member_xpaths": list(pat.member_xpaths)[:16],
            "commutation_count": pat.commutation_count,
            "image_url": image_url,
        }

    _append_history(state, "perception", {
        "labels": len(labels),
        "embeddings": len(embeddings),
        "scene_nodes": len(scene_graph),
    })
    return {
        "labels": labels,
        "embeddings": embeddings,
        "scene_graph": scene_graph,
        "history": state.get("history") or [],
    }


# ---------------------------------------------------------------------------
# Node: Cognition
# ---------------------------------------------------------------------------


def cognition_node(state: AgentState, deps: AgentDeps) -> AgentState:
    """Resolve ``user_intent`` to a plan targeting one pattern.

    Strategy
    --------
    1. Embedding cosine: rank ``embeddings`` against the intent text.
    2. If the top score is below a hard cutoff, fall back to text search
       over the scene graph's summaries.
    3. If both fail, emit a 'no_match' plan so the Action node can
       report it cleanly.
    """
    intent: str = (state.get("user_intent") or "").strip()
    embeddings: List[PatternEmbeddingRow] = state.get("embeddings") or []
    scene: Dict[str, Dict[str, Any]] = state.get("scene_graph") or {}
    built: BuiltTrie = state["trie"]

    action = _infer_action(intent)
    candidates: List[Dict[str, Any]] = []

    # Strategy 1: embedding-cosine ranking.
    if embeddings:
        embedder = PatternEmbedder(embedder=deps.embedder_service)
        ranked = embedder.rank_patterns(intent, embeddings, top_k=5)
        for row, score in ranked:
            info = scene.get(row.pattern_id, {})
            candidates.append({
                "pattern_id": row.pattern_id,
                "score": float(score),
                "source": "embedding",
                "role": info.get("role", ""),
                "category": info.get("category", ""),
                "summary": info.get("summary", ""),
                "representative_xpath": info.get(
                    "representative_xpath",
                    built.by_pattern_id[row.pattern_id].representative_xpath
                    if row.pattern_id in built.by_pattern_id else "",
                ),
            })

    best = _pick_best_candidate(intent, candidates, scene, built)
    index = _infer_instance_index(intent)

    if best is None:
        plan = {
            "action": "no_match",
            "target_pattern_id": "",
            "concrete_xpath": "",
            "reason": f"no pattern matched intent {intent!r}",
            "instance_index": 0,
        }
    else:
        concrete = _pick_concrete_xpath(built, best["pattern_id"], index)
        plan = {
            "action": action,
            "target_pattern_id": best["pattern_id"],
            "concrete_xpath": concrete,
            "instance_index": index,
            "score": best.get("score"),
            "role": best.get("role"),
            "category": best.get("category"),
            "summary": best.get("summary"),
        }

    _append_history(state, "cognition", {
        "intent": intent,
        "action": plan["action"],
        "target": plan.get("target_pattern_id", ""),
        "score": plan.get("score"),
        "candidate_count": len(candidates),
    })
    return {
        "plan": plan,
        "candidates": candidates,
        "history": state.get("history") or [],
    }


# ---------------------------------------------------------------------------
# Node: Action
# ---------------------------------------------------------------------------


def action_node(state: AgentState, deps: AgentDeps) -> AgentState:
    """Execute the plan via ``ShadowResolver``. Best-effort; never raises."""
    plan: Dict[str, Any] = state.get("plan") or {}
    action = plan.get("action", "no_match")
    built: BuiltTrie = state.get("trie")  # type: ignore

    if action == "no_match" or not plan.get("target_pattern_id"):
        result_str = f"no_match: {plan.get('reason', 'no plan')}"
        _append_history(state, "action", {"outcome": result_str})
        return {"result": result_str, "history": state.get("history") or []}

    pipeline_result: Optional[PipelineResult] = state.get("pipeline_result")
    dom = pipeline_result.dom if pipeline_result is not None else None
    resolver = deps.make_resolver(built, dom=dom)

    target = plan["target_pattern_id"]
    index = int(plan.get("instance_index", 0) or 0)

    try:
        if action == "click":
            xp = resolver.click(target, index=index)
            result_str = f"clicked {xp}"
        elif action == "fill":
            value = plan.get("value", "")
            xp = resolver.fill(target, value, index=index)
            result_str = f"filled {xp}"
        else:
            result_str = f"unknown_action: {action!r}"
    except Exception as exc:
        result_str = f"action_failed: {exc}"

    _append_history(state, "action", {"outcome": result_str})
    return {"result": result_str, "history": state.get("history") or []}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_agent_graph(deps: AgentDeps):
    """Compile the 4-node perception/action graph."""
    g = StateGraph(AgentState)

    g.add_node("observation", lambda s: observation_node(s, deps))
    g.add_node("perception", lambda s: perception_node(s, deps))
    g.add_node("cognition", lambda s: cognition_node(s, deps))
    g.add_node("action", lambda s: action_node(s, deps))

    g.set_entry_point("observation")
    g.add_edge("observation", "perception")
    g.add_edge("perception", "cognition")
    g.add_edge("cognition", "action")
    g.add_edge("action", END)
    return g.compile()


def run_agent_once(
    *,
    url: str,
    user_intent: str,
    deps: AgentDeps,
) -> AgentState:
    """Convenience wrapper: compile the graph and invoke it once."""
    app = build_agent_graph(deps)
    initial: AgentState = {
        "url": url,
        "user_intent": user_intent,
        "history": [],
    }
    final = app.invoke(initial)
    return final


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_ACTION_KEYWORDS = {
    "click": ("click", "tap", "open", "go to", "follow", "press", "select"),
    "fill":  ("type", "fill", "enter", "search for", "write"),
}


def _infer_action(intent: str) -> str:
    low = intent.lower()
    for verb, keys in _ACTION_KEYWORDS.items():
        for k in keys:
            if k in low:
                return verb
    # Default: clicking is the safest "do something" action.
    return "click"


_ORDINAL_WORDS = {
    "first": 0, "1st": 0, "one": 0,
    "second": 1, "2nd": 1, "two": 1,
    "third": 2, "3rd": 2, "three": 2,
    "fourth": 3, "4th": 3, "four": 3,
    "fifth": 4, "5th": 4, "five": 4,
    "last": -1,
}


def _infer_instance_index(intent: str) -> int:
    low = intent.lower()
    for word, idx in _ORDINAL_WORDS.items():
        if f" {word} " in f" {low} ":
            return idx
    return 0


def _pick_best_candidate(
    intent: str,
    candidates: List[Dict[str, Any]],
    scene: Dict[str, Dict[str, Any]],
    built: BuiltTrie,
) -> Optional[Dict[str, Any]]:
    """Pick the most probable candidate, falling back to keyword matching."""
    if candidates:
        best = candidates[0]
        if best.get("score", 0.0) >= 0.1:
            return best

    # Keyword fallback over summaries + categories.
    low = intent.lower()
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for pid, info in scene.items():
        blob = " ".join([
            info.get("summary", ""),
            info.get("category", ""),
            info.get("role", ""),
        ]).lower()
        if not blob:
            continue
        overlap = sum(1 for tok in _tokens(low) if tok in blob)
        if overlap > 0:
            scored.append((float(overlap), {
                "pattern_id": pid,
                "score": float(overlap),
                "source": "keyword",
                "role": info.get("role", ""),
                "category": info.get("category", ""),
                "summary": info.get("summary", ""),
                "representative_xpath": info.get("representative_xpath", ""),
            }))
    if scored:
        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    # If candidates exist but scored zero, still return the top embedding hit.
    if candidates:
        return candidates[0]
    return None


def _tokens(text: str) -> List[str]:
    out: List[str] = []
    buf: List[str] = []
    for ch in text.lower():
        if ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                out.append("".join(buf))
                buf = []
    if buf:
        out.append("".join(buf))
    # Drop stop-ish words that won't help the match.
    stop = {"the", "a", "an", "to", "in", "on", "of", "for",
            "click", "tap", "open", "follow", "press", "select",
            "first", "second", "third", "show", "me"}
    return [t for t in out if t and t not in stop]


def _pick_concrete_xpath(built: BuiltTrie, pattern_id: str, index: int) -> str:
    row: Optional[PatternRow] = built.by_pattern_id.get(pattern_id)
    if row is None:
        return ""
    members = list(row.member_xpaths) if row.member_xpaths else []
    if not members and row.representative_xpath:
        members = [row.representative_xpath]
    if not members:
        return ""
    if index < 0:
        index = max(0, len(members) + index)
    if index >= len(members):
        index = len(members) - 1
    return members[index]


def _append_history(state: AgentState, node: str, payload: Dict[str, Any]) -> None:
    hist = state.get("history")
    if hist is None:
        hist = []
        state["history"] = hist
    hist.append({"node": node, **payload})
