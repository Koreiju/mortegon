from pydantic import BaseModel
from typing import Optional, List

class DomGraphNode(BaseModel):
    xpath: str
    tag: str
    label: str = ""
    is_user_labeled: bool = False
    depth: int = 0
    html_raw: str = ""
    layout_x: float = 0.0
    layout_y: float = 0.0
    layout_z: float = 0.0

class DomKnowledgeGraph(BaseModel):
    nodes: List[DomGraphNode]
    # Any general metadata or global graph configs could go here
