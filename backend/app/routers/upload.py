"""Repository upload and ingestion endpoint."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.ingestion_service import ingestion_service
from app.models.api_models import UploadResponse

router = APIRouter(prefix="/upload", tags=["Upload"])

@router.post("", response_model=UploadResponse)
async def upload_repository(
    file: UploadFile = File(..., description="ZIP archive containing Python repository"),
    name: str = Form(..., description="Human-readable project name")
):
    """Securely upload, parse with Python AST, and persist into Neo4j."""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Repository name cannot be blank")

    try:
        response = await ingestion_service.ingest_repository(upload_file=file, repo_name=name.strip())
        return response
    except HTTPException:
        raise
    except ConnectionError as ce:
        raise HTTPException(status_code=503, detail=str(ce))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
