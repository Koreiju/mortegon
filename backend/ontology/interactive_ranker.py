from typing import List, Dict
from backend.ontology.type_handlers import TypedDomNode, InteractiveType, TagEnum, InputType

class InteractiveRanker:
    """Ranks interactive DOM elements by attribute substring occurrence."""
    
    SEARCH_SIGNALS = {
        'search': 3.0, 'query': 2.5, 'find': 2.0, 'lookup': 1.5,
        'keyword': 1.5, 'term': 1.0, 'filter': 0.5, 'text': 0.5
    }

    PAGINATION_SIGNALS = {
        'next': 3.0, 'prev': 3.0, 'previous': 3.0, 'paginat': 3.0,
        'load-more': 2.5, 'loadmore': 2.5, 'load_more': 2.5,
        'show-more': 2.0, 'showmore': 2.0, 'older': 1.5, 'newer': 1.5
    }

    def _score_node(self, node: TypedDomNode, signals: Dict[str, float]) -> float:
        score = 0.0
        
        texts_to_check = [
            node.raw_attrs.get('id', ''),
            node.raw_attrs.get('name', ''),
            ' '.join(node.class_names),
            node.aria_label or '',
            node.raw_attrs.get('placeholder', '')
        ]
        
        lower_texts = [t.lower() for t in texts_to_check if t]
        
        for k, weight in signals.items():
            for t in lower_texts:
                if k in t:
                    score += weight
                    break 
                    
        return score

    def rank_search_inputs(self, nodes: List[TypedDomNode]) -> List[TypedDomNode]:
        """Score and rank candidate search input fields."""
        candidates = []
        for n in nodes:
            if n.tag == TagEnum.INPUT and n.input_type in (InputType.TEXT, InputType.SEARCH):
                score = self._score_node(n, self.SEARCH_SIGNALS)
                if n.input_type == InputType.SEARCH:
                    score += 5.0
                if score > 0:
                    n.search_input_score = score
                    n.interactive_type = InteractiveType.SEARCH_INPUT
                    candidates.append(n)
            elif n.tag == TagEnum.FORM:
                score = self._score_node(n, self.SEARCH_SIGNALS)
                if score > 0:
                    n.search_input_score = score
                    candidates.append(n)
                    
        return sorted(candidates, key=lambda x: (x.search_input_score or 0), reverse=True)

    def rank_pagination_controls(self, nodes: List[TypedDomNode]) -> List[TypedDomNode]:
        """Score and rank candidate pagination/load-more controls."""
        candidates = []
        for n in nodes:
            if n.tag in (TagEnum.A, TagEnum.BUTTON) or n.role == "button":
                score = self._score_node(n, self.PAGINATION_SIGNALS)
                if n.text_content:
                    lt = n.text_content.lower()
                    for k, w in self.PAGINATION_SIGNALS.items():
                        if k in lt:
                            score += w
                            break
                            
                if score > 0:
                    n.pagination_score = score
                    n.interactive_type = InteractiveType.PAGINATION_CONTROL
                    candidates.append(n)
                    
        return sorted(candidates, key=lambda x: (x.pagination_score or 0), reverse=True)
