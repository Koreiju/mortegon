import pytest
from backend.agentic.tool_registry import ToolRegistry, AgentTool

def test_tool_registry_registration():
    reg = ToolRegistry()
    
    # Defaults should be loaded
    assert "web_search" in reg.tools
    assert "database_search" in reg.tools

    # Register custom
    def dummy_tool(x): return "dummy"
    reg.register(AgentTool("dummy", "Dummy desc", dummy_tool))
    assert "dummy" in reg.tools

def test_tool_inventory_formatting():
    reg = ToolRegistry()
    inventory = reg.get_tool_inventory(["web_search", "dom_retrieval"])
    
    # We expect actual implementations to only grab the requested tools
    assert "web_search" in inventory
    assert "dom_retrieval" in inventory
    # It must NOT include unrequested tools if tool_names are provided
    assert "database_search" not in inventory

def test_tool_chunking():
    reg = ToolRegistry()
    # If max_tokens is small, it should split the inventory
    # The mock returns a raw list of [inventory_string]. Let's test that it actually limits strings.
    chunks = reg.chunk_inventory(max_tokens=10) # 10 tokens is very small
    # Current mock fails this. It should split it.
    assert len(chunks) > 1, "ToolRegistry should chunk inventory if it exceeds max_tokens"
