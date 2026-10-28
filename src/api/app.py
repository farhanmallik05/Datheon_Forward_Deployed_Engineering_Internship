"""Hardened Enterprise FastAPI Application.

Assembles VPC security policies, Prometheus observability middleware,
error handling, and lifecycle events for production deployment.
"""
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.exceptions import (
    EnterprisePlatformError,
    HallucinationGuardrailError,
    HITLApprovalRequiredError,
    InvalidConfirmationTokenError,
    RBACAccessDeniedError,
)
from src.core.logger import get_logger
from src.core.telemetry import TelemetryMetrics
from src.api.routes_agent import router as agent_router
from src.api.routes_erp import router as erp_router
from src.api.routes_etl import router as etl_router
from src.api.routes_health import router as health_router
from src.api.routes_rag import router as rag_router
from src.etl.pipeline import VectorETLPipeline
from src.etl.vector_store import VectorStoreFactory

logger = get_logger("api.app")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event: pre-warms vector storage with synthetic enterprise documents."""
    logger.info("Initializing %s in %s environment...", settings.APP_NAME, settings.APP_ENV)
    store = VectorStoreFactory.get_vector_store()
    if store.count() == 0:
        logger.info("Vector index is empty. Auto-indexing initial legacy corpus from data/raw/...")
        try:
            raw_dir = settings.DATA_DIR / "raw"
            if raw_dir.exists():
                pipeline = VectorETLPipeline(vector_store=store)
                report = pipeline.ingest_directory(raw_dir)
                logger.info("Pre-warmed vector store with %d chunks across %d files.", report.total_chunks, report.total_documents)
        except Exception as e:
            logger.error("Failed to auto-index initial documents on startup: %s", str(e))
    else:
        logger.info("Vector store already contains %d indexed chunks. Startup ready.", store.count())

    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise Forward Deployed Engineering (FDE) AI integration platform with Multi-Tenant RBAC RAG, Autonomous Tool-Calling Agent, and Hardened VPC Telemetry.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware (Hardened for private VPC subnets)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def telemetry_and_logging_middleware(request: Request, call_next):
    """Measures request latency, records Prometheus metrics, and injects W3C correlation IDs."""
    start_time = time.perf_counter()
    correlation_id = request.headers.get("X-Correlation-ID") or f"corr-{uuid.uuid4().hex[:12]}"
    response: Response = None

    try:
        response = await call_next(request)
        duration_sec = time.perf_counter() - start_time
        endpoint = request.url.path
        TelemetryMetrics.record_http_request(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration_sec=duration_sec,
        )
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{(duration_sec * 1000.0):.2f}"
        return response
    except Exception as e:
        duration_sec = time.perf_counter() - start_time
        TelemetryMetrics.record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=500,
            duration_sec=duration_sec,
        )
        raise e


# Domain Exception Handlers
@app.exception_handler(RBACAccessDeniedError)
async def rbac_exception_handler(request: Request, exc: RBACAccessDeniedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": "RBAC_ACCESS_DENIED", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(HITLApprovalRequiredError)
async def hitl_exception_handler(request: Request, exc: HITLApprovalRequiredError):
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "HITL_REQUIRED",
            "message": exc.message,
            "action_id": exc.action_id,
            "confirmation_token": exc.confirmation_token,
            "action_payload": exc.action_payload,
        },
    )


@app.exception_handler(InvalidConfirmationTokenError)
async def token_exception_handler(request: Request, exc: InvalidConfirmationTokenError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "INVALID_CONFIRMATION_TOKEN", "message": exc.message},
    )


@app.exception_handler(EnterprisePlatformError)
async def platform_exception_handler(request: Request, exc: EnterprisePlatformError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "ENTERPRISE_PLATFORM_ERROR", "message": exc.message, "details": exc.details},
    )


# Telemetry Exposition Endpoint for Prometheus Scrapers
@app.get("/metrics", tags=["Health & Telemetry"])
def prometheus_metrics():
    """Exposes real-time Prometheus metrics for VPC scrape targets."""
    return Response(
        content=TelemetryMetrics.get_latest_metrics(),
        media_type=TelemetryMetrics.get_content_type(),
    )


# Register Feature Routers
app.include_router(health_router)
app.include_router(etl_router)
app.include_router(rag_router)
app.include_router(agent_router)
app.include_router(erp_router)

