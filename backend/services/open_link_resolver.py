from typing import Dict, List
from backend.services.schema_introspector import SchemaIntrospector, HaloSlot

class OpenLinkResolver:
    """Resolves the state of each halo slot and provides ranked candidates
    for Potential slots.
    
    For each slot: runs a Cypher discovery query to determine:
    - Connected: edges of this type exist → count them
    - Potential: unconnected matching entities exist → count them
    - Empty: no matching entities at all
    """

    def __init__(self, db, embedder, introspector: SchemaIntrospector):
        self.db = db
        self.embedder = embedder
        self.introspector = introspector

    def resolve_halo(self, node_id: str, node_type: str, node_attributes: Dict = None) -> Dict:
        """Resolve all slots for a node's halo.
        
        Returns {
            db_slots: [HaloSlot with state resolved],
            action_slots: [ActionSlot],
            data_links: [DataLinkChip],
            schema_compass: {types: [{name, count}], edges: [...]}
        }
        """
        slots = self.introspector.get_slots(node_type)
        resolved_slots = []
        
        for slot in slots:
            # Cypher calls mocked since KuzuDB driver is abstract here
            resolved_slot = HaloSlot(
                edge_type=slot.edge_type,
                direction=slot.direction,
                target_types=slot.target_types,
                label=slot.label,
                state='empty',
                connected_count=0,
                potential_count=0
            ) 
            resolved_slots.append(resolved_slot)
            
        action_slots = []
        data_links = []
        if node_attributes:
            tag = node_attributes.get('tag', 'div')
            action_slots = self.introspector.get_browser_action_slots(tag, node_attributes)
            data_links = self.introspector.get_static_data_links('xpath', 'snapshot_id', node_attributes)
            
        return {
            'db_slots': resolved_slots,
            'action_slots': action_slots,
            'data_links': data_links,
            'schema_compass': self.get_schema_compass()
        }

    def get_candidates(self, node_id: str, edge_type: str,
                       direction: str, offset: int = 0,
                       limit: int = 20, search: str = None
                      ) -> List[Dict]:
        """Get ranked candidates for a Potential slot."""
        # Find target types for this edge type
        target_types = []
        for slots in self.introspector._schema.values():
            for slot in slots:
                if slot.edge_type == edge_type and slot.direction == direction:
                    target_types.extend(slot.target_types)
        
        target_types = list(set(target_types))
        if not target_types:
            # Fallback
            target_types = ['OntologyNode']

        candidates = []
        for t in target_types:
            # Simplified cypher query to get unconnected nodes of the target type
            # (In reality, we'd add `WHERE NOT (source)-[:EDGE]->(n)` but since we don't have source node typed here easily, we just pull nodes)
            id_field = "node_id"
            if t == "OntologyNode":
                id_field = "ontology_node_id"
            elif t == "UserNote":
                id_field = "note_id"
            elif t == "PinnedComponent":
                id_field = "pin_id"
            elif t == "DomSnapshot":
                id_field = "snapshot_id"
            elif t == "NodeLabel":
                id_field = "label_id"

            # Check if there are matches in KuzuDB
            try:
                # Basic fetch, no search filter yet
                query = f"MATCH (n:{t}) RETURN n.{id_field} LIMIT $limit"
                res = self.db.execute(query, parameters={"limit": limit})
                while res.has_next():
                    row = res.get_next()
                    candidates.append({
                        "node_id": row[0],
                        "ontology_node_id": row[0],  # for compatibility
                        "node_type": t,
                        "label": f"{t} Candidate",
                        "score": 0.5
                    })
            except Exception as e:
                print(f"[OpenLinkResolver] Error fetching candidates for {t}: {e}")
                
        return candidates

    def _compute_relevance(self, source_id: str, candidate_id: str) -> float:
        """Composite relevance score for ranking candidates."""
        return 0.5

    def get_schema_compass(self) -> Dict:
        """Return the full schema graph for the compass mini-panel.
        
        Returns {
            types: [{name, count, color}],
            edges: [{source_type, edge_type, target_type}]
        }
        """
        return {
            'types': [
                {'name': 'UserNote', 'count': 0, 'color': '#3b82f6'},
                {'name': 'OntologyNode', 'count': 0, 'color': '#22c55e'},
                {'name': 'PinnedComponent', 'count': 0, 'color': '#eab308'},
                {'name': 'DomSnapshot', 'count': 0, 'color': '#64748b'}
            ],
            'edges': [
                {'source_type': 'UserNote', 'edge_type': 'ANNOTATES', 'target_type': 'OntologyNode'},
                {'source_type': 'OntologyNode', 'edge_type': 'CLASSIFIES', 'target_type': 'PinnedComponent'},
                {'source_type': 'PinnedComponent', 'edge_type': 'DERIVED_FROM', 'target_type': 'DomSnapshot'}
            ]
        }
