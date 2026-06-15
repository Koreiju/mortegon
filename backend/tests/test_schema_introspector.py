import pytest
from backend.services.schema_introspector import SchemaIntrospector

def test_schema_introspector_builds_map(clean_db):
    introspector = SchemaIntrospector(clean_db)
    schema = introspector.build_schema_map()
    
    assert "UserNote" in schema
    assert "OntologyNode" in schema
    
    slots = introspector.get_slots("OntologyNode")
    assert len(slots) > 0
    assert any(s.edge_type == 'IS_A' and s.direction == 'outgoing' for s in slots)

def test_browser_action_slots():
    introspector = SchemaIntrospector(None)
    
    slots = introspector.get_browser_action_slots('input', {'type': 'text'})
    actions = [s.action for s in slots if s.available]
    assert 'click' in actions
    assert 'fill' in actions
    assert 'submit' not in actions
    
    slots_div = introspector.get_browser_action_slots('div', {})
    actions_div = [s.action for s in slots_div if s.available]
    assert 'click' in actions_div
    assert 'fill' not in actions_div

def test_static_data_links():
    introspector = SchemaIntrospector(None)
    chips = introspector.get_static_data_links('/html/body', 'snap1', {'href': 'https://google.com', 'data-config': '{"a": 1}'})
    
    assert len(chips) == 2
    types = [c.chip_type for c in chips]
    assert 'external_url' in types
    assert 'json' in types
