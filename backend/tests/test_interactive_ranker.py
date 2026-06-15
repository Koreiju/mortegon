import pytest
from backend.ontology.interactive_ranker import InteractiveRanker
from backend.ontology.type_handlers import TypedDomNode, TagEnum, InteractiveType

from backend.ontology.type_handlers import TypedDomNode, TagEnum, InteractiveType, InputType

def test_search_heuristic():
    ranker = InteractiveRanker()
    node = TypedDomNode("id_1", TagEnum.INPUT, 0, input_type=InputType.SEARCH, raw_attrs={"placeholder": "Search for products..."})
    ranker.rank_search_inputs([node])
    
    assert node.interactive_type == InteractiveType.SEARCH_INPUT
    assert node.search_input_score is not None and node.search_input_score > 2.0

def test_pagination_heuristic():
    ranker = InteractiveRanker()
    node = TypedDomNode("id_2", TagEnum.A, 0, raw_attrs={"class": "paginate-next"}, text_content="Next Page")
    ranker.rank_pagination_controls([node])
    
    assert node.interactive_type == InteractiveType.PAGINATION_CONTROL
    assert node.pagination_score is not None and node.pagination_score > 2.0
