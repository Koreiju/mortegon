import uuid
from typing import List, Dict
from datetime import datetime
from backend.services.embedding_service import EmbeddingService
from backend.analytics.segment_embedder import SegmentEmbedder

class RetrievalStreamEntry:
    def __init__(self, **kwargs):
        self.entry_id = str(uuid.uuid4())
        self.created_at = datetime.utcnow().isoformat()
        self.data = kwargs

class RetrievalStreamService:
    """Append-only ordered log of all retrieval events."""
    
    def __init__(self, db_conn, embedder: EmbeddingService, segment_embedder: SegmentEmbedder):
        self.db = db_conn
        self.embedder = embedder
        self.segment_embedder = segment_embedder
        self.stream_log: List[RetrievalStreamEntry] = []

    def append(self, actor: str, trigger: str, query_text: str,
               cypher_query: str = None,
               legs_used: List[str] = None,
               results: List[Dict] = None,
               focal_node_id: str = None,
               pinned_node_ids: List[str] = None) -> RetrievalStreamEntry:
        """Append to memory bus and broadcast."""
        entry = RetrievalStreamEntry(actor=actor, trigger=trigger, query_text=query_text, 
                                     cypher=cypher_query, legs=legs_used, results=results,
                                     focal=focal_node_id, pinned=pinned_node_ids)
        self.stream_log.append(entry)
        return entry

    def search_human(self, query_text: str, pinned_node_ids: List[str] = None, field_scope: str = None) -> RetrievalStreamEntry:
        """Two-leg embedding-direct search for human queries."""
        segment_results = self.segment_embedder.hybrid_search(query_text)
        return self.append(
            actor="human", trigger="search", query_text=query_text,
            legs_used=["vector_content", "rrf"], results=segment_results,
            pinned_node_ids=pinned_node_ids
        )

    def select_node(self, node_id: str) -> RetrievalStreamEntry:
        """Generate a stream entry from node selection (graph neighborhood default)."""
        return self.append(
            actor="human", trigger="node_select", query_text=f"Selected node {node_id}",
            legs_used=["graph_neighbor"], results=[], focal_node_id=node_id
        )

    def get_history(self) -> List[Dict]:
        return [{"entry_id": e.entry_id, "created_at": e.created_at, **e.data} for e in self.stream_log]
