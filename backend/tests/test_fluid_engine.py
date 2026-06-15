import pytest
import asyncio
from unittest.mock import MagicMock, patch
from backend.agentic.fluid_engine import FluidEngine, ToolRegistry, AgentGenerator

def _run_async(coro):
    return asyncio.run(coro)

@patch('backend.agentic.fluid_engine.SLMClient')
def test_fluid_engine_propagation_agents(mock_slm_class):
    mock_slm_instance = MagicMock()
    mock_slm_instance.generate_json.side_effect = [
        {"agents": [{"name": "Expert_0", "tools": ["database_search"]}, {"name": "Expert_1", "tools": ["database_search"]}]},
        {"tool": "database_search"},
        {"tool": "database_search"}
    ]
    mock_slm_class.return_value = mock_slm_instance
    
    reg = ToolRegistry()
    gen = AgentGenerator()
    engine = FluidEngine(reg, gen)

    async def collect_engine():
        events = []
        async for event in engine.propagate_fluid("start fluid propagation"):
            events.append(event)
        return events

    events = _run_async(collect_engine())

    # Check boundaries of pipeline
    assert events[0]["status"] == "starting"
    assert events[-1]["status"] == "done"
    
    # Assert generator populated 2 agents defaulting by our mocked parameters
    agents = [e for e in events if e.get("status") == "agent_action"]
    tools = [e for e in events if e.get("status") == "tool_call"]
    
    assert len(agents) == 2
    assert len(tools) == 2
    assert "Expert_0" in [a.get("agent") for a in agents]
    assert "database_search" in [t.get("tool") for t in tools]

def test_tool_registry():
    reg = ToolRegistry()
    inv = reg.get_tool_inventory()
    
    assert "web_search" in inv
    assert "database_search" in inv
