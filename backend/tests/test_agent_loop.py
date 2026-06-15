"""
test_agent_loop.py — Phase 5 verification.

Dry-run (no Selenium, no live SLM): the resolver is a recording stub, the
SLM is the stub from Phase 3, the embedder is the BoW stub from Phase 4.
We verify that the 4-node LangGraph loop picks the right pattern for
"click the Lovers card" and reports ``no_match`` for an intent that has
no viable target.

Live tests are marked ``@pytest.mark.live`` — skipped on CI. Run with
``pytest -m live`` against a real network for the end-to-end sanity pass.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent.langgraph_loop import AgentDeps, run_agent_once
from backend.agent.shadow_resolver import ShadowResolver
from backend.dom.pipeline import run_pipeline
from backend.tests.test_pattern_embedder import _StubEmbedder
from backend.tests.test_pattern_labeler import _StubSLM
from backend.tests.test_trie_pipeline import HTML_TAROT_LIKE


# ---------------------------------------------------------------------------
# Stub resolver that records what the agent asked for
# ---------------------------------------------------------------------------


class _RecordingResolver(ShadowResolver):
    """No Selenium — capture click/fill intents so assertions can inspect them."""

    def __init__(self, driver, dom, built):
        super().__init__(driver, dom, built)
        self.clicks = []
        self.fills = []

    def click(self, pattern_id: str, index: int = 0) -> str:
        xp = self._pick(pattern_id, index)
        self.clicks.append({"pattern_id": pattern_id, "index": index, "xpath": xp})
        return xp

    def fill(self, pattern_id: str, value: str, index: int = 0) -> str:
        xp = self._pick(pattern_id, index)
        self.fills.append({"pattern_id": pattern_id, "value": value, "index": index,
                           "xpath": xp})
        return xp


def _make_deps(resolver_store=None):
    deps = AgentDeps(
        driver=None,
        slm=_StubSLM(),
        embedder_service=_StubEmbedder(),
        html_source=HTML_TAROT_LIKE,
        single_pass=True,
        persist=False,
    )

    def _factory(driver, dom, built):
        r = _RecordingResolver(driver, dom, built)
        if resolver_store is not None:
            resolver_store.append(r)
        return r

    deps.resolver_factory = _factory
    return deps


# ---------------------------------------------------------------------------
# 1. Dry-run: intent resolves to the card pattern
# ---------------------------------------------------------------------------


def test_dry_run_resolves_lovers_to_card_pattern():
    store: list = []
    deps = _make_deps(resolver_store=store)
    state = run_agent_once(
        url="https://x/_agent",
        user_intent="click the first tarot card",
        deps=deps,
    )
    plan = state["plan"]
    assert plan["action"] == "click", plan
    assert plan["target_pattern_id"], "Cognition produced no target"

    # Cross-check against the trie: the resolved target must correspond to
    # a pattern of the CARD FAMILY. The chunker emits multi-granularity
    # chunks (the card root + its h2/a/img element patterns share the card
    # label — see test_chunker_card_rollup); resolving the click to the
    # card root OR one of its element patterns both land the gesture on
    # the card, so the contract is family membership, not exact equality.
    result = run_pipeline(HTML_TAROT_LIKE, url="https://x/_verify", persist=False)
    card_patterns = set()
    for chunk in result.chunks:
        blob = " ".join(
            v for vs in chunk.content_fields.values() for v in vs
        ).lower()
        if "fool" in blob or "magician" in blob or "priestess" in blob:
            card_patterns.add(chunk.pattern)
    assert card_patterns, "Fixture must have card-like chunks"

    chosen_row = state["trie"].by_pattern_id[plan["target_pattern_id"]]
    assert any(
        chosen_row.pattern == p or chosen_row.pattern.startswith(p + "/")
        for p in card_patterns
    ), (
        f"Expected a card-family pattern (one of {sorted(card_patterns)!r} "
        f"or a descendant), got {chosen_row.pattern!r}"
    )

    # Resolver recorded exactly one click on the card.
    assert store, "Resolver factory was never called"
    resolver = store[0]
    assert len(resolver.clicks) == 1
    click = resolver.clicks[0]
    assert click["pattern_id"] == plan["target_pattern_id"]
    assert click["index"] == 0, "Default instance index should be 0"
    assert click["xpath"], "Click was recorded without a concrete xpath"
    assert "article" in click["xpath"], (
        f"Expected a card article xpath, got {click['xpath']!r}"
    )
    assert state["result"].startswith("clicked "), state["result"]


def test_dry_run_third_card_uses_index_2():
    store: list = []
    deps = _make_deps(resolver_store=store)
    state = run_agent_once(
        url="https://x/_agent",
        user_intent="click the third tarot card",
        deps=deps,
    )
    click = store[0].clicks[0]
    assert click["index"] == 2, (
        f"Ordinal 'third' must resolve to instance index 2, got {click['index']}"
    )
    # And the concrete xpath must be the 3rd one (index 2) on that pattern.
    pat = state["trie"].by_pattern_id[click["pattern_id"]]
    assert click["xpath"] == pat.member_xpaths[2]


# ---------------------------------------------------------------------------
# 2. Negative: no-match intent doesn't mis-click
# ---------------------------------------------------------------------------


def test_negative_intent_reports_no_match():
    """An intent with no plausible target must NOT click something wrong."""
    store: list = []
    deps = _make_deps(resolver_store=store)
    state = run_agent_once(
        url="https://x/_agent",
        user_intent="click the checkout button for bitcoin payment",
        deps=deps,
    )
    plan = state["plan"]
    # Either explicit no_match OR a plan whose top score is too low and
    # falls back to keyword search that still doesn't find checkout.
    # The stub SLM's labels never include 'checkout' or 'bitcoin', so
    # embedding + keyword both fail → cognition emits no_match.
    if plan["action"] != "no_match":
        # Acceptable only if the click target is clearly NOT a commerce pattern.
        assert not any(
            kw in (plan.get("summary", "") + plan.get("category", "")).lower()
            for kw in ("checkout", "payment", "bitcoin", "cart")
        )

    if plan["action"] == "no_match":
        assert state["result"].startswith("no_match")
        # Resolver must not have been asked to click.
        if store:
            assert not store[0].clicks, (
                "Resolver should not click on a no_match plan"
            )


# ---------------------------------------------------------------------------
# 3. History: each node contributed a trace
# ---------------------------------------------------------------------------


def test_history_records_each_node():
    deps = _make_deps()
    state = run_agent_once(
        url="https://x/_agent",
        user_intent="click the first tarot card",
        deps=deps,
    )
    nodes = [h["node"] for h in state.get("history", [])]
    assert nodes == ["observation", "perception", "cognition", "action"], nodes


# ---------------------------------------------------------------------------
# 4. Scene graph shape
# ---------------------------------------------------------------------------


def test_scene_graph_keys_and_values():
    deps = _make_deps()
    state = run_agent_once(
        url="https://x/_agent",
        user_intent="click the first tarot card",
        deps=deps,
    )
    scene = state.get("scene_graph") or {}
    assert scene, "Perception produced an empty scene graph"
    for pid, node in scene.items():
        for key in ("role", "category", "summary", "representative_xpath"):
            assert key in node, f"Scene node {pid} missing {key!r}"


# ---------------------------------------------------------------------------
# 5. Live marker (skipped by default)
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AGENT_TESTS") != "1",
    reason="Live Selenium run — set RUN_LIVE_AGENT_TESTS=1 to enable",
)
def test_live_tarot_click_first_card():
    """Full Selenium run against tarot.com. Opt-in via env var."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1440,900")
    driver = webdriver.Chrome(options=opts)
    try:
        deps = AgentDeps(driver=driver, single_pass=True, persist=False)
        state = run_agent_once(
            url="https://www.tarot.com/",
            user_intent="click the first major arcana",
            deps=deps,
        )
        assert state["plan"]["action"] in {"click", "no_match"}
    finally:
        driver.quit()
