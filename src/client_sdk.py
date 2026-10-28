"""Enterprise Python Client SDK for Datheon FDE Platform.

Provides a production-grade, typed client interface for client enterprise engineering teams:
  - Transparent RBAC header injection
  - Automatic exponential backoff retries on transient errors and HTTP 429
  - W3C Correlation ID generation and tracking
  - Fully typed request and response objects
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import httpx

from src.core.config import ClearanceTier, Department


@dataclass
class ClientConfig:
    """Configuration for enterprise client SDK instance."""
    base_url: str = "http://localhost:8000"
    employee_id: str = "USR-ENG-4401"
    name: str = "Alex Mercer"
    department: str = "engineering"
    clearance: str = "L2_RESTRICTED"
    timeout_sec: float = 15.0
    max_retries: int = 3
    retry_backoff_factor: float = 0.5


class DatheonFDEClient:
    """Official Forward Deployed Engineering client for internal microservices."""

    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self._session = httpx.Client(
            base_url=self.config.base_url,
            timeout=self.config.timeout_sec,
        )

    def _get_headers(self, custom_correlation_id: Optional[str] = None) -> Dict[str, str]:
        """Assembles standard compliance headers."""
        return {
            "X-Employee-ID": self.config.employee_id,
            "X-Employee-Name": self.config.name,
            "X-Department": self.config.department,
            "X-Clearance-Tier": self.config.clearance,
            "X-Correlation-ID": custom_correlation_id or f"sdk-corr-{uuid.uuid4().hex[:12]}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _execute_with_retry(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Executes HTTP request with clearance-aware retry and backoff logic."""
        headers = self._get_headers(kwargs.pop("correlation_id", None))
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        attempt = 0
        while attempt < self.config.max_retries:
            attempt += 1
            try:
                response = self._session.request(method, path, headers=headers, **kwargs)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 1.0))
                    time.sleep(retry_after)
                    continue
                if response.status_code >= 500 and attempt < self.config.max_retries:
                    time.sleep(self.config.retry_backoff_factor * (2 ** (attempt - 1)))
                    continue
                return response
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if attempt >= self.config.max_retries:
                    raise err
                time.sleep(self.config.retry_backoff_factor * (2 ** (attempt - 1)))

        return response

    def health(self) -> Dict[str, Any]:
        """Pings microservice liveness probe."""
        res = self._execute_with_retry("GET", "/healthz")
        res.raise_for_status()
        return res.json()

    def query_rag(
        self,
        query: str,
        target_department: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Queries the multi-tenant RBAC RAG engine."""
        payload = {
            "query": query,
            "target_department": target_department,
            "conversation_context": context,
        }
        res = self._execute_with_retry("POST", "/api/v1/rag/query", json=payload)
        res.raise_for_status()
        return res.json()

    def execute_agent_task(
        self,
        task: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches an operational task to the autonomous field agent."""
        payload = {
            "task": task,
            "session_id": session_id,
        }
        res = self._execute_with_retry("POST", "/api/v1/agent/chat", json=payload)
        res.raise_for_status()
        return res.json()

    def confirm_hitl_action(
        self,
        action_id: str,
        confirmation_token: str,
        approved: bool = True,
    ) -> Dict[str, Any]:
        """Authorizes or rejects a pending high-risk transaction."""
        payload = {
            "action_id": action_id,
            "confirmation_token": confirmation_token,
            "approved": approved,
        }
        res = self._execute_with_retry("POST", "/api/v1/agent/hitl/confirm", json=payload)
        res.raise_for_status()
        return res.json()

    def get_erp_inventory(self, sku: str) -> Dict[str, Any]:
        """Direct ERP inventory inquiry."""
        res = self._execute_with_retry("GET", f"/api/v1/erp/inventory/{sku}")
        res.raise_for_status()
        return res.json()

    def close(self):
        """Closes the underlying HTTP connection pool."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
