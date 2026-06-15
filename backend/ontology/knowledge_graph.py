from dataclasses import dataclass, field
from typing import List, Dict, Any, Union

@dataclass
class KnowledgeNode:
    """Base structural bounds for KuzuDB offline User Entities."""
    entity_id: str

@dataclass
class UserNote(KnowledgeNode):
    """Personal unstructured string memory connected by Vector Semantic similarities."""
    content: str
    tags: List[str] = field(default_factory=list)

@dataclass
class OntologyNode(KnowledgeNode):
    """Rigid typed User definitions enforcing semantic taxonomy bounds onto agentic algorithms."""
    label_name: str
    label_type: str  # i.e., "concept", "entity", "category"
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PinnedComponent(KnowledgeNode):
    """A mathematically discrete Subtree from a DOM snapshot pinned dynamically by LCA matrices."""
    source_snapshot: str
    lca_xpath: str
    
class ContextAssembly:
    """Orchestrates array sequences of KnowledgeNodes into prioritized Agentic simulation payloads."""
    def __init__(self, assembly_id: str, name: str):
        self.assembly_id = assembly_id
        self.name = name
        self._nodes: List[Dict[str, Any]] = []
        
    def add_node(self, node: KnowledgeNode, priority: int = 0):
        """Attaches a node securely into the Context block based on Priority weight."""
        self._nodes.append({
            "node": node,
            "priority": priority
        })
        
    def get_ordered_nodes(self) -> List[KnowledgeNode]:
        """Translates dynamic array payloads into strictly sorted blocks maximizing SLM token efficiency."""
        # Sort entirely by priority descending
        sorted_elements = sorted(self._nodes, key=lambda d: d["priority"], reverse=True)
        return [elem["node"] for elem in sorted_elements]
