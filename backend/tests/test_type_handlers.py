import pytest
from backend.ontology.type_handlers import TypeHandlerRegistry, TypedDomNode, ContentCategory, InteractiveType, TagEnum, InputType

# NOTE — the raw_node wire shape below is the LIVE caller's contract
# (mapper.py::convert flow builds {'xpath','tagName','depth','textContent',
# 'attributes': dict}); an older draft of these tests used 'tag'/'text_content'
# with JSON-string attributes, which no live path ever sends.

def test_type_conversion_search_input():
    registry = TypeHandlerRegistry()
    raw_node = {
        "tagName": "input",
        "attributes": {"type": "search", "placeholder": "Find something..."},
        "textContent": ""
    }
    typed_node = registry.convert_node(raw_node)

    assert typed_node.tag == TagEnum.INPUT
    assert typed_node.input_type == InputType.SEARCH
    assert typed_node.raw_attrs.get("type") == "search"

def test_type_conversion_link_navigation():
    registry = TypeHandlerRegistry()
    raw_node = {
        "tagName": "a",
        "attributes": {"href": "/next-page", "class": "paginate-next"},
        "textContent": "Next Page"
    }
    typed_node = registry.convert_node(raw_node)

    assert typed_node.tag == TagEnum.A
    assert typed_node.text_content == "Next Page"
    assert typed_node.href == "/next-page"
    assert "paginate-next" in typed_node.class_names

def test_aria_label_lands_on_typed_field():
    registry = TypeHandlerRegistry()
    typed_node = registry.convert_node({
        "tagName": "button",
        "attributes": {"aria-label": "Close dialog"},
        "textContent": "×"
    })
    assert typed_node.aria_label == "Close dialog"

def test_fallback_defaults():
    registry = TypeHandlerRegistry()
    raw_node = {} # malformed missing expected keys
    typed_node = registry.convert_node(raw_node)
    
    assert typed_node.tag == TagEnum.UNKNOWN
    assert typed_node.depth == 0
    assert len(typed_node.class_names) == 0
