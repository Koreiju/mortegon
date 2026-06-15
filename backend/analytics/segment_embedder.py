from typing import Dict, List
import uuid
from datetime import datetime
from backend.ontology.type_handlers import TypedDomNode
from backend.services.embedding_service import EmbeddingService

class SegmentEmbedder:
    """Embeds segmented DOM text chunks via quantized nomic-embed-text."""
    
    def __init__(self, embedding_service: EmbeddingService, db_conn):
        self.embedder = embedding_service
        self.conn = db_conn

    def embed_segmentation(self, snapshot_id: str,
                           cluster_assignments: Dict[str, int],
                           labels: Dict[int, str],
                           typed_nodes: Dict[str, TypedDomNode]
                          ) -> List[Dict]:
        """
        Embed all segments from a clustered snapshot.
        1. Group nodes by cluster_id
        2. concatenate text_content
        3. embed each chunk
        4. store in KuzuDB
        """
        clusters_text = {}
        for xpath, cluster_id in cluster_assignments.items():
            if xpath in typed_nodes:
                node = typed_nodes[xpath]
                if node.text_content and node.text_content.strip():
                    if cluster_id not in clusters_text:
                        clusters_text[cluster_id] = []
                    clusters_text[cluster_id].append(node.text_content.strip())
                    
        chunk_texts = []
        cluster_ids = []
        cluster_labels = []
        
        for cid, texts in clusters_text.items():
            combined = " ".join(texts)
            chunk_texts.append(combined)
            cluster_ids.append(cid)
            cluster_labels.append(labels.get(cid, "unlabeled"))
            
        if not chunk_texts:
            return []
            
        embeddings = self.embedder.embed_texts(chunk_texts)
        
        results = []
        for i, text in enumerate(chunk_texts):
            emb_list = embeddings[i].tolist()
            emb_id = str(uuid.uuid4())
            cid = cluster_ids[i]
            label = cluster_labels[i]
            token_count = len(text.split())
            patricia_pattern = "" 
            url = "" 
            created_at = datetime.utcnow().isoformat()
            
            query = """
            CREATE (s:SegmentEmbedding {
                embedding_id: $emb_id,
                snapshot_id: $snap_id,
                cluster_id: $cid,
                label: $label,
                text_content: $text,
                embedding: $emb,
                token_count: $tokens,
                patricia_pattern: $pattern,
                url: $url,
                created_at: $created_at
            })
            """
            
            params = {
                "emb_id": emb_id,
                "snap_id": snapshot_id,
                "cid": cid,
                "label": label,
                "text": text,
                "emb": emb_list,
                "tokens": token_count,
                "pattern": patricia_pattern,
                "url": url,
                "created_at": created_at
            }
            
            try:
                self.conn.execute(query, parameters=params)
                
                self.conn.execute("""
                    MATCH (s:SegmentEmbedding {embedding_id: $emb_id}), (d:DomSnapshot {snapshot_id: $snap_id})
                    CREATE (s)-[:DERIVED_FROM]->(d)
                """, parameters={"emb_id": emb_id, "snap_id": snapshot_id})
                
                results.append({
                    "embedding_id": emb_id,
                    "cluster_id": cid,
                    "label": label,
                    "token_count": token_count
                })
            except Exception as e:
                print(f"Error inserting segment embedding {emb_id}: {e}")
                
        return results

    def hybrid_search(self, query: str,
                      graph_filter: Dict = None,
                      pattern_filter: str = None,
                      top_k: int = 10) -> List[Dict]:
        """Hybrid graph-vector search over segment embeddings."""
        query_emb = self.embedder.embed_query(query).tolist()
        
        q = """
        MATCH (s:SegmentEmbedding)
        WITH s, array_cosine_similarity(s.embedding, $q_emb) AS score
        ORDER BY score DESC
        LIMIT $top_k
        RETURN s.embedding_id AS id, s.label AS label, s.text_content AS text, s.url AS url, score
        """
        try:
            res = self.conn.execute(q, parameters={"q_emb": query_emb, "top_k": top_k})
            results = []
            while res.has_next():
                r = res.get_next()
                results.append({
                    "embedding_id": r[0],
                    "label": r[1],
                    "content_preview": r[2][:100] if r[2] else "",
                    "url": r[3],
                    "score": r[4],
                    "patricia_pattern": ""
                })
            return results
        except Exception as e:
            print(f"Hybrid search failed: {e}")
            return []
