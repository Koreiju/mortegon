from typing import List, Tuple
import networkx as nx

class CrossPageTracer:
    """Tracks cross-page logical flows mapping URL cycles globally inside MCP architectures."""
    
    def __init__(self):
        # We track edges across URL endpoints
        self.graph = nx.DiGraph()
        
    def log_transition(self, source: str, target: str):
        """Append a directed agent progression vector."""
        self.graph.add_edge(source, target)
        
    def detect_loops(self) -> List[List[str]]:
        """Identify cyclic structural patterns across external bounds."""
        # Simple loops using standard NetworkX recursive circuit algorithms
        try:
            return list(nx.simple_cycles(self.graph))
        except nx.NetworkXNoCycle:
            return []
