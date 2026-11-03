"""Source evidence and caller/callee context endpoints."""
from fastapi import APIRouter, Query, HTTPException
from app.services.evidence_service import evidence_service
from app.models.graph_models import EvidenceDetail

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.get("/{node_id:path}", response_model=EvidenceDetail)
def get_node_evidence(node_id: str):
    """Retrieve exact source code slice, line numbers, and dependency references for a node."""
    return evidence_service.get_node_evidence(node_id=node_id)
