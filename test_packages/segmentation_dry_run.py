import sys
sys.path.append('.')
from backend.ontology.type_handlers import TypeHandlerRegistry
from backend.ontology.interactive_ranker import InteractiveRanker

registry = TypeHandlerRegistry()
raw_node = {
    'xpath': '/html/body/div/input',
    'tag_name': 'input', 
    'attributes': '{"type": "search", "placeholder": "Search here..."}',
    'class_name': 'nav-input'
}
typed = registry.convert_node(raw_node)
print('Typed Node Tag:', typed.tag)

ranker = InteractiveRanker()
ranked = ranker.rank_search_inputs([typed])
print('Ranked inputs:', len(ranked), [r.search_input_score for r in ranked])
