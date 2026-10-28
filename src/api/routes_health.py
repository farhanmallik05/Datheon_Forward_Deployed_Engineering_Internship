"""Enterprise health checks and VPC container readiness probes."""
from datetime import datetime, timezone
from fastapi import APIRouter, status
from pydantic import BaseModel

from src.core.config import get_settings
from src.etl.vector_store import VectorStoreFactory
from src.services.mock_erp_crm import MockEnterpriseService

router = APIRouter(tags=["Health & Telemetry"])


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    service: str
    version: str
    environment: str


class ReadinessStatus(HealthStatus):
    vector_store_points: int
    database_connected: bool


@router.get("/healthz", response_model=HealthStatus, status_code=status.HTTP_200_OK)
def health_check():
    """Liveness probe: verifies process is alive and accepting TCP connections."""
    settings = get_settings()
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )


@router.get("/readyz", response_model=ReadinessStatus, status_code=status.HTTP_200_OK)
def readiness_check():
    """Readiness probe: validates vector database and persistence layer are initialized."""
    settings = get_settings()
    store = VectorStoreFactory.get_vector_store()
    erp = MockEnterpriseService()

    return ReadinessStatus(
        status="ready",
        timestamp=datetime.now(timezone.utc).isoformat(),
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        vector_store_points=store.count(),
        database_connected=erp.db_path.exists(),
    )


@router.get("/livez", status_code=status.HTTP_200_OK)
def live_check():
    return {"status": "alive"}

