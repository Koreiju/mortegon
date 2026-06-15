import pytest
from backend.ontology.knowledge_graph import UserNote, OntologyNode, ContextAssembly

def test_context_assembly_priority():
    """Verify context assembly strictly formats prompt payload tokens based on structural priority integer weights."""
    note = UserNote(entity_id="note_1", content="These DOM structures represent financial cards.")
    onto = OntologyNode(entity_id="onto_1", label_name="Asset", label_type="entity")
    
    assembly = ContextAssembly(assembly_id="ctx_1", name="Finance Exploration")
    
    # Add nodes mapping priority configurations
    assembly.add_node(onto, priority=5)
    assembly.add_node(note, priority=10) # 10 > 5, so note goes first in prompt
    
    ordered = assembly.get_ordered_nodes()
    
    assert len(ordered) == 2
    assert ordered[0].entity_id == "note_1"
    assert ordered[1].entity_id == "onto_1"
