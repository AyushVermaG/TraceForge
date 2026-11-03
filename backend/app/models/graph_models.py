"""Graph entity definitions and schema models."""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class NodeKind(str, Enum):
    REPOSITORY = "Repository"
    FILE = "File"
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"
    EXTERNAL_PACKAGE = "ExternalPackage"

class RelationshipKind(str, Enum):
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"

class GraphNode(BaseModel):
    id: str = Field(..., description="Unique persistent identifier across graph")
    kind: NodeKind = Field(..., description="Entity classification")
    name: str = Field(..., description="Short display label for graph visualization")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Metadata properties")

class GraphEdge(BaseModel):
    id: str = Field(..., description="Edge identifier")
    source: str = Field(..., description="Source node id")
    target: str = Field(..., description="Target node id")
    type: RelationshipKind = Field(..., description="Relationship kind")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties (e.g. line_no, confidence)")

class GraphResponse(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    total_nodes_in_scope: int = 0
    returned_nodes_count: int = 0
    truncated: bool = False
    message: Optional[str] = None

class DependencyRef(BaseModel):
    node_id: str
    name: str
    kind: NodeKind
    line_no: Optional[int] = None
    confidence: Optional[str] = None
    file_path: Optional[str] = None

class EvidenceDetail(BaseModel):
    node_id: str
    kind: NodeKind
    name: str
    qualified_name: str
    file_path: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    code_snippet: str
    signature: Optional[str] = None
    is_async: Optional[bool] = None
    is_method: Optional[bool] = None
    inbound_dependencies: List[DependencyRef] = Field(default_factory=list)
    outbound_dependencies: List[DependencyRef] = Field(default_factory=list)
