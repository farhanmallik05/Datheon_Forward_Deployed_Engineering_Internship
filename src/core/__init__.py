"""Core platform modules: configuration, security, telemetry, and structured logging."""
from src.core.config import get_settings, ClearanceTier, Department
from src.core.security import EnterpriseUser, verify_clearance, can_access_document
from src.core.telemetry import TelemetryMetrics
from src.core.logger import get_logger
from src.core.exceptions import (
    EnterprisePlatformError,
    RBACAccessDeniedError,
    HallucinationGuardrailError,
    DocumentExtractionError,
    AgentToolExecutionError,
    HITLApprovalRequiredError,
)

__all__ = [
    "get_settings",
    "ClearanceTier",
    "Department",
    "EnterpriseUser",
    "verify_clearance",
    "can_access_document",
    "TelemetryMetrics",
    "get_logger",
    "EnterprisePlatformError",
    "RBACAccessDeniedError",
    "HallucinationGuardrailError",
    "DocumentExtractionError",
    "AgentToolExecutionError",
    "HITLApprovalRequiredError",
]

