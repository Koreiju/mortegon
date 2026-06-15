import pytest
from backend.agentic.cross_page_tracer import CrossPageTracer

def test_tracer_identifies_loop():
    tracer = CrossPageTracer()
    
    # Simulate an agent exploring bounds over multiple Web domains using its MCP
    tracer.log_transition(source="https://a.com", target="https://b.com")
    tracer.log_transition(source="https://b.com", target="https://c.com")
    tracer.log_transition(source="https://c.com", target="https://a.com") # Agent loops back
    
    loops = tracer.detect_loops()
    
    # Assert the loop was algorithmically closed
    assert len(loops) == 1
    assert "https://a.com" in loops[0]
    assert "https://c.com" in loops[0]
