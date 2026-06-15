import pytest
from unittest.mock import MagicMock
from backend.analytics.segment_embedder import SegmentEmbedder
from backend.ontology.type_handlers import TypedDomNode, TagEnum

def test_segment_embedder_chunking():
    mock_conn = MagicMock()
    mock_embedder = MagicMock()
    mock_embedder.embed_texts.return_value = [MagicMock(tolist=lambda: [0.1]*768)]
    
    segment_embedder = SegmentEmbedder(mock_embedder, mock_conn)
    
    nodes = {
        "n1": TypedDomNode("n1", TagEnum.DIV, 0, text_content="Sentence one."),
        "n2": TypedDomNode("n2", TagEnum.P, 0, text_content="Sentence two."),
    }
    
    cluster_assignments = {"n1": 1, "n2": 1}
    labels = {1: "Cluster 1 Label"}
    segment_embedder.embed_segmentation("snap1", cluster_assignments, labels, nodes)
    
    assert mock_conn.execute.called
    assert mock_embedder.embed_texts.called

def test_hybrid_search_dispatch():
    mock_conn = MagicMock()
    cursor_mock = MagicMock()
    cursor_mock.has_next.side_effect = [True, False]
    cursor_mock.get_next.return_value = ["emb_123", "Cluster 1", "Sentence one.", "http://example.com", 0.95]
    mock_conn.execute.return_value = cursor_mock
    
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = MagicMock(tolist=lambda: [0.1]*768)
    
    segment_embedder = SegmentEmbedder(mock_embedder, mock_conn)
    
    results = segment_embedder.hybrid_search("Sentence")
    assert len(results) == 1
    assert results[0]["embedding_id"] == "emb_123"
    assert "score" in results[0]
