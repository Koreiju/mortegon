import pytest
from backend.agentic.agent_generator import AgentGenerator

class _CannedSLMClient:
    """Boundary injection with the PRODUCTION SLMClient interface
    (`generate_text(prompt, system_prompt=...)`) returning a canned
    team-design response — the parse/format logic under test is real."""
    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        return ('Sure! Here is the team:\n'
                '{"agents": [{"name": "Crawler", "domain": "Navigation", '
                '"description": "Navigates pages", "tools": ["dom_retrieval"]}]}')

MockSLMClient = _CannedSLMClient  # legacy alias

def test_agent_team_generation():
    slm = MockSLMClient()
    gen = AgentGenerator(slm)
    
    # We expect the agent generator to parse the string from the SLM
    agents = gen.generate_team("Lots of context about navigation.", team_size=1)
    
    assert len(agents) == 1
    # Current mock always returns name 'Agent_0'. We want the JSON parsed out.
    assert agents[0].name == "Crawler", "Agent name should be derived from SLM JSON"
    assert agents[0].domain == "Navigation"
    assert "dom_retrieval" in agents[0].tools

def test_system_prompt_design():
    slm = MockSLMClient()
    gen = AgentGenerator(slm)
    
    prompt = gen._design_system_prompt("Crawler", "Navigates pages", "Context about navigation")
    # Current mock returns "Generated prompt mocked". The actual implementation will format strings.
    # TDD assertion: The generated prompt must weave in the agent description and context
    assert "Navigates pages" in prompt
    assert "Crawler" in prompt
