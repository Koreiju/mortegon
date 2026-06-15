import pytest
from backend.services.schema_introspector import SchemaIntrospector
from backend.services.open_link_resolver import OpenLinkResolver

class MockEmbedder:
    def embed_text(self, text):
        return [0.1, 0.2, 0.3]
    def calculate_cosine_similarity(self, a, b):
        return 0.85

def test_resolve_halo_state(clean_db):
    introspector = SchemaIntrospector(clean_db)
    resolver = OpenLinkResolver(clean_db, MockEmbedder(), introspector)
    
    res = resolver.resolve_halo('node123', 'OntologyNode', {'tag': 'div'})
    
    assert 'db_slots' in res
    assert 'action_slots' in res
    assert 'data_links' in res
    assert 'schema_compass' in res

def test_get_candidates(clean_db):
    # Setup some test data in KuzuDB
    clean_db.execute("CREATE (n:OntologyNode {ontology_node_id: 'target1', label_name: 'Test Target', label_type: 'Concept'})")
    
    introspector = SchemaIntrospector(clean_db)
    resolver = OpenLinkResolver(clean_db, MockEmbedder(), introspector)
    
    candidates = resolver.get_candidates('source123', 'IS_A', 'outgoing')
    
    assert isinstance(candidates, list)
    assert len(candidates) > 0, "Resolver should fetch unconnected target candidates."
    assert candidates[0]['ontology_node_id'] == 'target1'
