"""Tests for the GraphEditor service."""
import pytest
from backend.services.graph_editor import GraphEditor, EDGE_TYPES


@pytest.fixture
def editor():
    return GraphEditor()


# --- UserNote CRUD ---

def test_create_note(editor):
    note = editor.create_note("This is a test note", tags=["test", "demo"])
    assert note.note_id
    assert note.content == "This is a test note"
    assert "test" in note.tags


def test_get_note(editor):
    note = editor.create_note("Find me")
    retrieved = editor.get_note(note.note_id)
    assert retrieved is not None
    assert retrieved.content == "Find me"


def test_update_note(editor):
    note = editor.create_note("Original")
    updated = editor.update_note(note.note_id, content="Modified")
    assert updated.content == "Modified"


def test_delete_note(editor):
    note = editor.create_note("Delete me")
    assert editor.delete_note(note.note_id)
    assert editor.get_note(note.note_id) is None


def test_list_notes_with_tag_filter(editor):
    editor.create_note("Note A", tags=["alpha"])
    editor.create_note("Note B", tags=["beta"])
    editor.create_note("Note C", tags=["alpha", "gamma"])

    alpha_notes = editor.list_notes(tag_filter="alpha")
    assert len(alpha_notes) == 2


# --- OntologyNode CRUD ---

def test_create_ontology_node(editor):
    node = editor.create_ontology_node(
        label_name="Product Card",
        label_type="concept",
        description="A card displaying product information",
    )
    assert node.node_id
    assert node.label_name == "Product Card"


def test_update_ontology_node(editor):
    node = editor.create_ontology_node("Widget", description="A UI widget")
    updated = editor.update_ontology_node(node.node_id, description="An interactive UI widget")
    assert updated.description == "An interactive UI widget"


def test_delete_ontology_node(editor):
    node = editor.create_ontology_node("Temp")
    assert editor.delete_ontology_node(node.node_id)
    assert editor.get_ontology_node(node.node_id) is None


# --- PinnedComponent ---

def test_create_pin(editor):
    pin = editor.create_pin(
        source_snapshot="snap-1",
        lca_xpath="/html/body/div[1]",
        label_summary="Navigation bar",
    )
    assert pin.pin_id
    assert pin.lca_xpath == "/html/body/div[1]"


# --- ContextAssembly ---

def test_create_assembly(editor):
    note = editor.create_note("Research note")
    node = editor.create_ontology_node("Topic")
    assembly = editor.create_assembly(
        name="Research Thread",
        fragments=[note.note_id, node.node_id],
        priority=5,
    )
    assert assembly.name == "Research Thread"
    assert len(assembly.fragments) == 2


def test_add_to_assembly(editor):
    assembly = editor.create_assembly("Thread")
    note = editor.create_note("New finding")
    editor.add_to_assembly(assembly.assembly_id, note.note_id)
    updated = editor.get_assembly(assembly.assembly_id)
    assert note.note_id in updated.fragments


# --- Edges ---

def test_create_edge(editor):
    n1 = editor.create_ontology_node("A")
    n2 = editor.create_ontology_node("B")
    edge = editor.create_edge(n1.node_id, n2.node_id, "RELATES_TO")
    assert edge["edge_type"] == "RELATES_TO"


def test_invalid_edge_type_raises(editor):
    with pytest.raises(ValueError, match="Invalid edge type"):
        editor.create_edge("a", "b", "INVALID_TYPE")


def test_get_edges(editor):
    n1 = editor.create_ontology_node("X")
    n2 = editor.create_ontology_node("Y")
    editor.create_edge(n1.node_id, n2.node_id, "IS_A")
    edges = editor.get_edges(n1.node_id)
    assert len(edges) == 1


def test_delete_edge(editor):
    n1 = editor.create_ontology_node("X")
    n2 = editor.create_ontology_node("Y")
    edge = editor.create_edge(n1.node_id, n2.node_id, "HAS_A")
    assert editor.delete_edge(edge["edge_id"])
    assert len(editor.get_edges(n1.node_id)) == 0


# --- Search ---

def test_substring_search(editor):
    editor.create_note("DOM tree analysis")
    editor.create_note("CSS layout parsing")
    editor.create_ontology_node("Tree Structure", description="Hierarchical DOM representation")

    results = editor.search("tree")
    assert len(results) >= 2


# --- Edit history & Undo ---

def test_edit_history(editor):
    editor.create_note("First")
    editor.create_note("Second")
    history = editor.get_edit_history()
    assert len(history) == 2
    assert history[0]["operation"] == "create"


def test_undo_create(editor):
    note = editor.create_note("Undoable")
    assert editor.get_note(note.note_id) is not None
    assert editor.undo_last()
    assert editor.get_note(note.note_id) is None
