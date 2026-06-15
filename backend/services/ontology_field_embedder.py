import uuid
from typing import Dict, List
from datetime import datetime
from backend.services.embedding_service import EmbeddingService

class OntologyFieldEmbedder:
    """Embeds standalone Ontology Typed metadata strings mapped strictly to source Nodes."""
    def __init__(self, embedder: EmbeddingService, db_conn):
        self.embedder = embedder
        self.conn = db_conn

    def embed_node_fields(self, node_id: str, fields: Dict[str, str]):
        """Embeds single localized field mappings for a focused search schema."""
        for field_name, field_value in fields.items():
            if not field_value or not str(field_value).strip():
                continue
            
            embedding = self.embedder.embed_query(str(field_value)).tolist()
            emb_id = str(uuid.uuid4())
            updated = datetime.utcnow().isoformat()
            query = """
            CREATE (o:OntologyFieldEmbedding {
                embedding_id: $emb_id,
                node_id: $n_id,
                node_type: "DOM",
                field_name: $f_name,
                field_value: $f_val,
                embedding: $emb,
                updated_at: $updated
            })
            """
            
            try:
                self.conn.execute(query, parameters={
                    "emb_id": emb_id, "n_id": node_id, "f_name": field_name,
                    "f_val": str(field_value), "emb": embedding, "updated": updated
                })
                self.conn.execute(
                    "MATCH (o:OntologyFieldEmbedding {embedding_id: $emb_id}), (n:DomNode {node_id: $n_id}) "
                    "CREATE (o)-[:DESCRIBES]->(n)", 
                    parameters={"emb_id": emb_id, "n_id": node_id}
                )
            except Exception as e:
                print(f"Error inserting field embedding {field_name}: {e}")

    def search_by_field(self, field_name: str, query: str, top_k: int = 5) -> List[Dict]:
        q_emb = self.embedder.embed_query(query).tolist()
        cypher = """
        MATCH (o:OntologyFieldEmbedding)
        WHERE o.field_name = $fname
        WITH o, array_cosine_similarity(o.embedding, $q_emb) AS score
        ORDER BY score DESC
        LIMIT $top_k
        RETURN o.node_id AS node_id, o.field_value AS value, score
        """
        try:
            res = self.conn.execute(cypher, parameters={"fname": field_name, "q_emb": q_emb, "top_k": top_k})
            results = []
            while res.has_next():
                r = res.get_next()
                results.append({"node_id": r[0], "value": r[1], "score": r[2]})
            return results
        except Exception:
            return []
