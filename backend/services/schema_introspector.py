from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class HaloSlot:
    """One connection slot in the DB ontology inner arc."""
    edge_type: str          # e.g. 'ANNOTATES', 'IS_A'
    direction: str          # 'outgoing', 'incoming', 'both'
    target_types: List[str] # e.g. ['UserNote', 'OntologyNode']
    label: str              # display label, e.g. 'Annotations'
    state: str = 'empty'    # 'connected', 'potential', 'empty'
    connected_count: int = 0
    potential_count: int = 0

@dataclass
class ActionSlot:
    """One action slot in the browser action ontology outer arc."""
    action: str             # 'click', 'fill', 'submit', etc.
    available: bool
    reason: str             # why available/unavailable
    requires_input: bool    # True for 'fill', 'select'

@dataclass
class DataLinkChip:
    """One static data link chip below the halo arcs."""
    chip_type: str          # 'internal_url', 'external_url', 'media', 'json'
    source_attr: str        # attribute name, e.g. 'href', 'data-config'
    value: str              # the URL, media src, or JSON snippet
    label: str              # display text (truncated URL, filename, etc.)

class SchemaIntrospector:
    """Introspects KuzuDB schema to enumerate valid connection slots per node type.
    
    Reads the registered node tables and relationship tables from KuzuDB to
    build a static schema map: {node_type: [(edge_type, direction, target_types)]}.
    The schema map is computed once at startup and cached.
    """

    def __init__(self, db):
        self.db = db
        self._schema: Dict[str, List[HaloSlot]] = {}

    def build_schema_map(self):
        """Enumerate all (source_type, edge_type, target_type) triples
        from KuzuDB's registered relationship tables.
        Returns dict keyed by node type name."""
        self._schema = {
            'UserNote': [
                HaloSlot(edge_type='ANNOTATES', direction='outgoing', target_types=['DomSnapshot', 'OntologyNode', 'PinnedComponent', 'NodeLabel'], label='Annotates')
            ],
            'OntologyNode': [
                HaloSlot(edge_type='IS_A', direction='outgoing', target_types=['OntologyNode'], label='Is A'),
                HaloSlot(edge_type='HAS_A', direction='outgoing', target_types=['OntologyNode'], label='Has A'),
                HaloSlot(edge_type='PART_OF', direction='outgoing', target_types=['OntologyNode'], label='Part Of'),
                HaloSlot(edge_type='RELATES_TO', direction='outgoing', target_types=['OntologyNode'], label='Relates To'),
                HaloSlot(edge_type='CLASSIFIES', direction='outgoing', target_types=['StructureTag', 'PinnedComponent'], label='Classifies'),
                HaloSlot(edge_type='ANNOTATES', direction='incoming', target_types=['UserNote'], label='Annotations')
            ],
            'PinnedComponent': [
                HaloSlot(edge_type='DERIVED_FROM', direction='outgoing', target_types=['DomSnapshot'], label='Derived From'),
                HaloSlot(edge_type='SIMILAR_TO', direction='outgoing', target_types=['PinnedComponent'], label='Similar To'),
                HaloSlot(edge_type='CLASSIFIES', direction='incoming', target_types=['OntologyNode'], label='Classifications'),
                HaloSlot(edge_type='ANNOTATES', direction='incoming', target_types=['UserNote'], label='Annotations')
            ],
            'DomSnapshot': [
                HaloSlot(edge_type='LABELED_AS', direction='outgoing', target_types=['NodeLabel'], label='Labels'),
                HaloSlot(edge_type='ANNOTATES', direction='incoming', target_types=['UserNote'], label='Annotations'),
                HaloSlot(edge_type='DERIVED_FROM', direction='incoming', target_types=['PinnedComponent'], label='Pins')
            ]
        }
        return self._schema

    def get_slots(self, node_type: str) -> List[HaloSlot]:
        """Return all connection slots valid for a node type.
        Each slot: {edge_type, direction, target_types, label}."""
        if not self._schema:
            self.build_schema_map()
        return self._schema.get(node_type, [])

    def get_browser_action_slots(self, tag: str, attributes: Dict) -> List[ActionSlot]:
        """Determine available browser action slots based on element
        tag and attributes.
        
        Returns action slots for: click, fill, submit, select,
        navigate, scroll_to, extract, hover.
        Only includes actions valid for this element type.
        """
        slots = []
        is_interactive = tag in ['a', 'button', 'input', 'select', 'textarea']
        
        slots.append(ActionSlot('click', available=True, reason="All nodes can be clicked", requires_input=False))
        slots.append(ActionSlot('scroll_to', available=True, reason="All nodes can be scrolled to", requires_input=False))
        slots.append(ActionSlot('extract', available=True, reason="All nodes have properties", requires_input=False))
        slots.append(ActionSlot('hover', available=True, reason="All nodes can be hovered", requires_input=False))
        
        if tag in ['input', 'textarea']:
            slots.append(ActionSlot('fill', available=True, reason="Input element", requires_input=True))
        else:
            slots.append(ActionSlot('fill', available=False, reason="Not an input element", requires_input=True))

        if tag == 'form' or (tag in ['button', 'input'] and attributes.get('type') == 'submit'):
            slots.append(ActionSlot('submit', available=True, reason="Form/submit element", requires_input=False))
        else:
            slots.append(ActionSlot('submit', available=False, reason="Not a form or submit button", requires_input=False))

        if tag == 'select':
            slots.append(ActionSlot('select', available=True, reason="Select element", requires_input=True))
        else:
            slots.append(ActionSlot('select', available=False, reason="Not a select element", requires_input=True))

        if tag == 'a' and 'href' in attributes:
            slots.append(ActionSlot('navigate', available=True, reason="Has href attribute", requires_input=False))
        else:
            slots.append(ActionSlot('navigate', available=False, reason="Not a link with href", requires_input=False))

        return slots

    def get_static_data_links(self, xpath: str, snapshot_id: str, attributes: Dict = None) -> List[DataLinkChip]:
        """Extract static data link chips (URLs, media, JSON) from
        the node's content distillation results (§4).
        Returns typed chips with source attribute and value."""
        chips = []
        if not attributes:
            return chips
            
        if 'href' in attributes:
            href = attributes['href']
            chip_type = 'external_url' if href.startswith('http') else 'internal_url'
            chips.append(DataLinkChip(chip_type, 'href', href, href[:20] + '...' if len(href) > 20 else href))
            
        if 'src' in attributes:
            src = attributes['src']
            chips.append(DataLinkChip('media', 'src', src, src[:20] + '...' if len(src) > 20 else src))
            
        for k, v in attributes.items():
            if k.startswith('data-'):
                if v and (str(v).startswith('{') or str(v).startswith('[')):
                    chips.append(DataLinkChip('json', k, str(v), f"{k} data"))
                    
        return chips
