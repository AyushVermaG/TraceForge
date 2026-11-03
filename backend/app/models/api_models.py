"""API Request and Response schemas."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.models.graph_models import NodeKind

class RepositorySummary(BaseModel):
    id: str
    name: str
    ingested_at: str
    total_files: int = 0
    total_modules: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_calls: int = 0

class RepositoryListResponse(BaseModel):
    repositories: List[RepositorySummary] = Field(default_factory=list)

class UploadResponse(BaseModel):
    repo_id: str
    name: str
    status: str
    files_parsed: int
    modules_found: int
    classes_found: int
    functions_found: int
    calls_inferred: int
    warnings: List[str] = Field(default_factory=list)

class SearchItem(BaseModel):
    id: str
    kind: NodeKind
    name: str
    qualified_name: str
    file_path: Optional[str] = None
    line_no: Optional[int] = None

class SearchResponse(BaseModel):
    query: str
    results: List[SearchItem] = Field(default_factory=list)
    total: int = 0

class HealthResponse(BaseModel):
    status: str
    environment: str
    neo4j_connected: bool
    neo4j_uri_configured: bool
    neo4j_version: Optional[str] = None
    error: Optional[str] = None
