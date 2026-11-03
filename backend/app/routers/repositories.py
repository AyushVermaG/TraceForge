"""Repository management endpoints."""
import shutil
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.services.graph_service import graph_service
from app.models.api_models import RepositoryListResponse, RepositorySummary

router = APIRouter(prefix="/repositories", tags=["Repositories"])

@router.get("", response_model=RepositoryListResponse)
def list_repositories():
    """List all ingested code repositories stored in Neo4j."""
    repos = graph_service.list_repositories()
    return RepositoryListResponse(repositories=repos)

@router.delete("/{repo_id}")
def delete_repository(repo_id: str):
    """Delete a repository from Neo4j and disk cache."""
    graph_service.delete_repository(repo_id)
    
    # Remove local source cache if exists
    repo_dir = settings.storage_path / repo_id
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    return {"status": "SUCCESS", "message": f"Repository '{repo_id}' successfully removed"}
