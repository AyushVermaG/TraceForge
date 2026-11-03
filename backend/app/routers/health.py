"""Health check and Neo4j connectivity status endpoints."""
from fastapi import APIRouter
from app.config import settings
from app.database.neo4j_client import neo4j_client
from app.models.api_models import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=HealthResponse)
def get_health():
    """Verify backend API and Neo4j database health status."""
    ping_result = neo4j_client.ping()
    is_healthy = ping_result["connected"]
    
    return HealthResponse(
        status="UP" if is_healthy else "DEGRADED",
        environment=settings.ENVIRONMENT,
        neo4j_connected=ping_result["connected"],
        neo4j_uri_configured=ping_result["configured"],
        neo4j_version=ping_result.get("version"),
        error=ping_result.get("error")
    )

@router.get("/db")
def get_db_health():
    """Detailed Neo4j connectivity diagnostic."""
    return neo4j_client.ping()
