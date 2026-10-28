"""FastAPI endpoints for Vector ETL pipeline management."""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.core.config import ClearanceTier, Department, get_settings
from src.core.security import EnterpriseUser, get_authenticated_user
from src.etl.pipeline import IngestionReport, VectorETLPipeline
from src.etl.vector_store import VectorStoreFactory

router = APIRouter(prefix="/api/v1/ingest", tags=["Vector ETL Pipeline"])


class BatchIngestRequest(BaseModel):
    directory_path: Optional[str] = Field(default=None, description="Path relative to workspace or absolute")
    department_override: Optional[Department] = None
    clearance_override: Optional[ClearanceTier] = None
    batch_size: int = Field(default=16, ge=1, le=128)


@router.post("/batch", response_model=dict, status_code=status.HTTP_200_OK)
def trigger_batch_ingestion(
    request: BatchIngestRequest,
    current_user: EnterpriseUser = Depends(get_authenticated_user),
):
    """Triggers batch ingestion across target directory of unstructured documents."""
    settings = get_settings()
    pipeline = VectorETLPipeline()

    target_dir = Path(request.directory_path) if request.directory_path else settings.DATA_DIR / "raw"
    if not target_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target directory '{target_dir}' does not exist on host.",
        )

    report = pipeline.ingest_directory(
        directory_path=target_dir,
        batch_size=request.batch_size,
    )
    return {
        "status": "COMPLETED",
        "initiator": current_user.user_id,
        "report": report.to_dict(),
    }


@router.get("/stats", status_code=status.HTTP_200_OK)
def get_vector_store_statistics(
    current_user: EnterpriseUser = Depends(get_authenticated_user),
):
    """Returns vector store indexing metrics."""
    store = VectorStoreFactory.get_vector_store()
    return {
        "status": "ONLINE",
        "total_indexed_vectors": store.count(),
        "backend": type(store).__name__,
        "caller_clearance": current_user.clearance.value,
    }
