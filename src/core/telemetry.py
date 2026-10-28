"""Prometheus telemetry and instrumentation for enterprise VPC observability.

Exposes low-overhead counters, latency histograms, and gauges to track
ETL throughput, RAG performance, agent tool calls, and security guardrail events.
"""
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

# HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "datheon_http_requests_total",
    "Total incoming HTTP requests partitioned by endpoint, method, and HTTP status code.",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "datheon_http_request_duration_seconds",
    "HTTP request latency distribution in seconds.",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ETL Pipeline Metrics (Task 1)
ETL_DOCUMENTS_TOTAL = Counter(
    "datheon_etl_documents_total",
    "Total client raw documents processed by the ETL pipeline.",
    ["department", "format", "status"],
)

ETL_CHUNKS_TOTAL = Counter(
    "datheon_etl_chunks_total",
    "Total semantic chunks generated and embedded into vector storage.",
    ["department", "clearance"],
)

ETL_INGESTION_DURATION_SECONDS = Histogram(
    "datheon_etl_batch_ingestion_duration_seconds",
    "Latency of ETL batch ingestion runs in seconds.",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 15.0, 30.0, 60.0],
)

# RAG Metrics (Task 2)
RAG_QUERY_TOTAL = Counter(
    "datheon_rag_queries_total",
    "Total enterprise RAG queries received.",
    ["department", "clearance"],
)

RAG_QUERY_DURATION_SECONDS = Histogram(
    "datheon_rag_query_duration_seconds",
    "End-to-end RAG response generation latency in seconds.",
    ["department"],
    buckets=[0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
)

RAG_RETRIEVED_CHUNKS_HISTOGRAM = Histogram(
    "datheon_rag_retrieved_chunks_count",
    "Number of chunks retrieved from vector store passing RBAC boundaries.",
    buckets=[0, 1, 2, 4, 8, 16, 32],
)

RAG_GUARDRAIL_BLOCKED_TOTAL = Counter(
    "datheon_rag_guardrail_blocked_total",
    "Total RAG responses rejected or sanitized by hallucination / citation guardrails.",
    ["reason"],
)

# Agent Metrics (Task 3)
AGENT_TOOL_CALLS_TOTAL = Counter(
    "datheon_agent_tool_calls_total",
    "Total enterprise ERP/CRM tool executions by the autonomous field agent.",
    ["tool_name", "status"],
)

AGENT_RETRY_COUNT = Counter(
    "datheon_agent_retries_total",
    "Number of automated retry attempts executed on transient tool errors.",
    ["tool_name"],
)

AGENT_HITL_QUEUE_SIZE = Gauge(
    "datheon_agent_hitl_pending_actions",
    "Current count of sensitive transactional operations awaiting human cryptographic confirmation.",
)

AGENT_HITL_ACTIONS_RESOLVED = Counter(
    "datheon_agent_hitl_actions_resolved_total",
    "Total human-in-the-loop actions resolved.",
    ["decision"],  # "approved" or "rejected"
)


class TelemetryMetrics:
    """Helper wrapper to cleanly manage metric emissions throughout the application."""

    @staticmethod
    def record_http_request(method: str, endpoint: str, status_code: int, duration_sec: float) -> None:
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration_sec)

    @staticmethod
    def record_etl_run(docs_count: int, chunks_count: int, department: str, duration_sec: float) -> None:
        ETL_DOCUMENTS_TOTAL.labels(department=department, format="multi", status="success").inc(docs_count)
        ETL_CHUNKS_TOTAL.labels(department=department, clearance="multi").inc(chunks_count)
        ETL_INGESTION_DURATION_SECONDS.observe(duration_sec)

    @staticmethod
    def record_rag_query(department: str, clearance: str, duration_sec: float, chunks_count: int) -> None:
        RAG_QUERY_TOTAL.labels(department=department, clearance=clearance).inc()
        RAG_QUERY_DURATION_SECONDS.labels(department=department).observe(duration_sec)
        RAG_RETRIEVED_CHUNKS_HISTOGRAM.observe(chunks_count)

    @staticmethod
    def record_guardrail_violation(reason: str) -> None:
        RAG_GUARDRAIL_BLOCKED_TOTAL.labels(reason=reason).inc()

    @staticmethod
    def record_tool_call(tool_name: str, success: bool) -> None:
        status_label = "success" if success else "failure"
        AGENT_TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status=status_label).inc()

    @staticmethod
    def get_latest_metrics() -> bytes:
        """Serializes current in-memory metrics to Prometheus text exposition format."""
        return generate_latest()

    @staticmethod
    def get_content_type() -> str:
        return CONTENT_TYPE_LATEST

