import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.chat_service import ChatService

def _run_async(coro):
    return asyncio.run(coro)

@patch('backend.services.chat_service.SLMClient')
def test_chat_service_mcp_routing(mock_slm_class):
    mock_db = MagicMock()
    mock_embedder = MagicMock()
    mock_segment = MagicMock()
    mock_segment.hybrid_search.return_value = [{"node_id": "123", "score": 0.99}]
    mock_fluid = AsyncMock() if hasattr(asyncio, "iscoroutinefunction") else MagicMock()
    
    mock_slm_instance = MagicMock()
    mock_slm_instance.generate_json.return_value = {"tool": "search_knowledge", "query": "find something"}
    async def mock_stream(*args, **kwargs):
        yield "Search complete."
    mock_slm_instance.async_stream_chat = mock_stream
    mock_slm_class.return_value = mock_slm_instance
    
    service = ChatService(mock_db, mock_embedder, mock_segment, mock_fluid)
    
    async def collect_stream():
        events = []
        async for event in service.send_message("sess_1", "Please search for items"):
            events.append(event)
        return events
        
    streamed_events = _run_async(collect_stream())
    
    tool_calls = [e for e in streamed_events if e.get("type") == "tool_call"]
    tool_results = [e for e in streamed_events if e.get("type") == "tool_result"]
    dones = [e for e in streamed_events if e.get("type") == "done"]
    
    assert len(tool_calls) == 1
    assert tool_calls[0]["tool_name"] == "search_knowledge"
    
    assert len(tool_results) == 1
    assert tool_results[0]["tool_output"]["results"][0]["node_id"] == "123"
    assert len(dones) == 1

@patch('backend.services.chat_service.SLMClient')
def test_chat_service_fluid_routing(mock_slm_class):
    mock_db = MagicMock()
    mock_embedder = MagicMock()
    mock_segment = MagicMock()
    
    mock_fluid = MagicMock()
    async def mock_propagate(*args):
        yield {"status": "starting"}
        yield {"status": "done"}
    
    mock_fluid.propagate_fluid = mock_propagate
    
    mock_slm_instance = MagicMock()
    mock_slm_instance.generate_json.return_value = {"tool": "start_fluid", "query": "Start the agent"}
    async def mock_stream(*args, **kwargs):
        yield "Fluid complete."
    mock_slm_instance.async_stream_chat = mock_stream
    mock_slm_class.return_value = mock_slm_instance
    
    service = ChatService(mock_db, mock_embedder, mock_segment, mock_fluid)
    
    async def collect_stream():
        events = []
        async for event in service.send_message("sess_1", "Start the fluid agent"):
            events.append(event)
        return events
        
    streamed_events = _run_async(collect_stream())
    
    tool_calls = [e for e in streamed_events if e.get("type") == "tool_call"]
    tool_results = [e for e in streamed_events if e.get("type") == "tool_result"]
    
    assert len(tool_calls) == 1
    assert tool_calls[0]["tool_name"] == "start_fluid"
    assert len(tool_results) == 2  # The two events yielded from propagate_fluid
