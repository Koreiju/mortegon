import pytest
from backend.ontology.field_types import TypeHandlerRegistry, TagEnum

def test_tag_enum_validation():
    """Verify rigid constraint over HTML string tags."""
    # Transforms caps natively
    valid_tag = TypeHandlerRegistry.handle_tag("DIV")
    assert valid_tag == TagEnum.DIV
    
    # Returns null fallback for malformed tags
    invalid = TypeHandlerRegistry.handle_tag("NON_EXISTENT")
    assert invalid is None

def test_url_selection_srcset():
    """Verify smart media URL parsing resolving highest-fidelity from srcset definitions."""
    srcset_string = "small.png 200w, large.png 800w, medium.png 400w"
    
    # Handler should extract the largest variant (800w)
    url = TypeHandlerRegistry.handle_media_url(srcset_string)
    assert url == "large.png"
