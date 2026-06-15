import pytest
from unittest.mock import MagicMock
from backend.services.retrieval_stream import RetrievalStreamService

def test_stream_append():
    mock_db = MagicMock()
    mock_embed = MagicMock()
    mock_segment = MagicMock()
    
    stream = RetrievalStreamService(mock_db, mock_embed, mock_segment)
    
    entry = stream.append("human", "test", "my query")
    assert entry.data.get("actor") == "human"
    assert entry.data.get("query_text") == "my query"
    
    history = stream.get_history()
    assert len(history) == 1
    assert history[0]["entry_id"] == entry.entry_id

def test_search_human_logging_pipeline():
    mock_db = MagicMock()
    mock_embed = MagicMock()
    mock_segment = MagicMock()
    mock_segment.hybrid_search.return_value = [{"node_id": "abc", "score": 1.0}]
    
    stream = RetrievalStreamService(mock_db, mock_embed, mock_segment)
    stream.search_human("find this item")
    
    history = stream.get_history()
    assert len(history) == 1
    assert history[0]["trigger"] == "search"
    assert history[0]["results"][0]["node_id"] == "abc"
    assert "vector_content" in history[0]["legs"]

def test_node_selection():
    mock_db = MagicMock()
    stream = RetrievalStreamService(mock_db, MagicMock(), MagicMock())
    stream.select_node("node_123")
    
    history = stream.get_history()
    assert history[0]["trigger"] == "node_select"
    assert history[0]["focal"] == "node_123"
