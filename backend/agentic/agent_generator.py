"""Domain-expert agent-team generation from user context.

Previously a stub that ignored the SLM entirely and returned ``Agent_0``
placeholders — an empty mock in a production path (the
``/api/agentic/instantiate`` route reaches it via the fluid engine). It now
drives the injected SLM client for real: one JSON team-design call, parsed
into ``AgentSpec``s, each with a system prompt that weaves the agent's
identity and the source context together.

The SLM boundary is duck-typed: the production ``SLMClient`` exposes
``generate_text(prompt, system_prompt=...)``; older injected clients with a
``generate(system_prompt, user_prompt)`` shape still work.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.services.slm_client import SLMClient

#: Default tool grants when the SLM's team spec doesn't assign any.
_DEFAULT_TOOLS = ["web_search", "dom_retrieval", "read_note"]

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class AgentSpec:
    name: str
    domain: str
    description: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)


class AgentGenerator:
    """Generate domain-expert agents from user context."""

    def __init__(self, slm: SLMClient):
        self.slm = slm

    # ------------------------------------------------------------------
    # SLM boundary (duck-typed)
    # ------------------------------------------------------------------

    def _slm_text(self, prompt: str, system_prompt: str) -> str:
        slm = self.slm
        try:
            if hasattr(slm, "generate_text"):
                return str(slm.generate_text(prompt, system_prompt=system_prompt) or "")
            if hasattr(slm, "generate"):
                return str(slm.generate(system_prompt, prompt) or "")
        except Exception:
            return ""
        return ""

    # ------------------------------------------------------------------
    # Team generation
    # ------------------------------------------------------------------

    def generate_team(self, context_chunk: str,
                      team_size: int = 10) -> List[AgentSpec]:
        """Design a team of up to ``team_size`` agents for ``context_chunk``.

        1. One SLM call requesting a strict-JSON team spec
           (``{"agents": [{name, domain, description, tools}]}``).
        2. Parse the first JSON object out of the response (models often
           wrap JSON in prose).
        3. Per agent: synthesize the tailored system prompt
           (:meth:`_design_system_prompt`) and normalise the tool grant.

        Unparseable SLM output yields an empty team — the caller sees the
        honest result rather than placeholder agents.
        """
        raw = self._slm_text(
            prompt=(
                "Design a team of domain-expert agents for the following "
                f"user context. Return STRICT JSON of the form "
                '{"agents": [{"name": str, "domain": str, "description": str, '
                f'"tools": [str]}}]}} with at most {int(team_size)} agents.\n\n'
                f"Context:\n{context_chunk}"
            ),
            system_prompt=(
                "You are an agent-team designer. Respond with strict JSON "
                "only — no prose, no code fences."
            ),
        )
        entries = self._parse_team_json(raw)[: max(0, int(team_size))]
        agents: List[AgentSpec] = []
        for e in entries:
            name = str(e.get("name") or "").strip()
            if not name:
                continue
            domain = str(e.get("domain") or "Web Graph").strip()
            description = str(e.get("description") or "").strip()
            tools = [str(t) for t in (e.get("tools") or []) if t] or list(_DEFAULT_TOOLS)
            agents.append(AgentSpec(
                name=name,
                domain=domain,
                description=description,
                system_prompt=self._design_system_prompt(
                    name, description, context_chunk,
                ),
                tools=tools,
            ))
        return agents

    @staticmethod
    def _parse_team_json(raw: str) -> List[Dict[str, Any]]:
        """Extract the ``agents`` list from the SLM response. Tolerates
        prose around the JSON object; returns ``[]`` when nothing
        parseable is present."""
        if not raw:
            return []
        m = _JSON_BLOCK_RE.search(raw)
        if not m:
            return []
        try:
            parsed = json.loads(m.group(0))
        except Exception:
            return []
        agents = parsed.get("agents") if isinstance(parsed, dict) else None
        return [a for a in (agents or []) if isinstance(a, dict)]

    def _design_system_prompt(self, agent_name: str,
                              agent_description: str,
                              context_chunk: str) -> str:
        """Tailored system prompt weaving the agent's identity and the
        source context. Deterministic formatting — the SLM designed the
        team; the prompt frame itself must be stable and auditable."""
        ctx = (context_chunk or "").strip()
        if len(ctx) > 600:
            ctx = ctx[:597] + "..."
        return (
            f"You are {agent_name}, a domain-expert agent. "
            f"Your specialty: {agent_description}\n\n"
            f"You operate over the user's workspace context:\n{ctx}\n\n"
            "Stay within your specialty; cite the workspace context when "
            "reasoning; prefer tool calls over speculation."
        )
