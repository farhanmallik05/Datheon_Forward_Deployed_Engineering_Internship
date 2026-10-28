"""Unit and integration tests for Task 4: Hardened FastAPI Microservice & Telemetry."""
import pytest


def test_health_probes(api_client):
    # Liveness probe
    res = api_client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Datheon Enterprise FDE Platform"

    # Readiness probe
    res_ready = api_client.get("/readyz")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["status"] == "ready"
    assert data_ready["database_connected"] is True


def test_prometheus_metrics_endpoint(api_client):
    res = api_client.get("/metrics")
    assert res.status_code == 200
    content = res.text
    # Verify presence of custom enterprise metric series
    assert "datheon_http_requests_total" in content
    assert "datheon_http_request_duration_seconds" in content
    assert "datheon_etl_documents_total" in content


def test_rag_query_endpoint(api_client):
    headers = {
        "X-User-Id": "USR-FIN-9901",
        "X-User-Department": "finance",
        "X-User-Clearance": "L3_CONFIDENTIAL",
    }
    payload = {
        "query": "What was Datheon consolidated revenue in Q3 2026?",
    }
    res = api_client.post("/api/v1/rag/query", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert data["clearance"] == "L3_CONFIDENTIAL"
    assert data["department"] == "finance"
    assert len(data["citations"]) > 0


def test_agent_chat_and_hitl_endpoints(api_client):
    headers = {
        "X-User-Id": "USR-ENG-4401",
        "X-User-Department": "engineering",
        "X-User-Clearance": "L2_RESTRICTED",
    }

    # 1. Non-sensitive action
    res = api_client.post(
        "/api/v1/agent/chat",
        json={"prompt": "Check stock for SKU-H100-80G."},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["completed"] is True

    # 2. Sensitive action triggering HITL
    res_sensitive = api_client.post(
        "/api/v1/agent/chat",
        json={"prompt": "Check SKU-H100-80G and order $145,000 from NVIDIA Cloud Compute."},
        headers=headers,
    )
    assert res_sensitive.status_code == 200
    sens_data = res_sensitive.json()
    assert sens_data["status"] == "HITL_PAUSED"
    assert sens_data["pending_hitl"] is not None

    action_id = sens_data["pending_hitl"]["action_id"]
    token = sens_data["pending_hitl"]["confirmation_token"]

    # 3. Confirm action via /confirm-action
    officer_headers = {
        "X-User-Id": "USR-FIN-9901",
        "X-User-Department": "finance",
        "X-User-Clearance": "L3_CONFIDENTIAL",
    }
    confirm_res = api_client.post(
        "/api/v1/agent/confirm-action",
        json={"action_id": action_id, "confirmation_token": token, "approved": True},
        headers=officer_headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "EXECUTED"


def test_mock_erp_rest_endpoints(api_client):
    res = api_client.get("/api/v1/erp/inventory/SKU-H100-80G")
    assert res.status_code == 200
    assert res.json()["sku"] == "SKU-H100-80G"

    res_audit = api_client.get("/api/v1/erp/audit-log")
    assert res_audit.status_code == 200
    assert "audit_log" in res_audit.json()
