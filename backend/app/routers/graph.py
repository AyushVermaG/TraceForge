"""Graph exploration and progressive Cypher querying endpoints."""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.graph_service import graph_service
from app.models.graph_models import GraphResponse
from app.models.api_models import SearchResponse

router = APIRouter(prefix="/graph", tags=["Graph"])

@router.get("/overview", response_model=GraphResponse)
def get_overview(
    repo_id: str = Query(..., description="Repository ID to inspect"),
    limit: int = Query(35, ge=5, le=100, description="Node count threshold to avoid hairballs")
):
    """Retrieve initial clean module and file overview of repository."""
    return graph_service.get_overview(repo_id=repo_id, limit=limit)

@router.get("/expand", response_model=GraphResponse)
def expand_neighborhood(
    node_id: str = Query(..., description="Target node ID to expand"),
    limit: int = Query(30, ge=1, le=100, description="Max neighbor nodes")
):
    """Progressively expand the 1-hop connected neighborhood of a node."""
    return graph_service.expand_node(node_id=node_id, limit=limit)

@router.get("/search", response_model=SearchResponse)
def search_symbols(
    q: str = Query(..., min_length=1, description="Symbol name or prefix query"),
    repo_id: str = Query("", description="Optional repo scope"),
    limit: int = Query(20, ge=1, le=50)
):
    """Search functions, classes, and modules by identifier name."""
    return graph_service.search_symbols(repo_id=repo_id, query=q, limit=limit)
