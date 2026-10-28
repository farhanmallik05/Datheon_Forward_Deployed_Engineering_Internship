"""Custom domain exceptions for the Datheon Enterprise FDE Platform."""


class EnterprisePlatformError(Exception):
    """Base exception for all domain-specific platform errors."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RBACAccessDeniedError(EnterprisePlatformError):
    """Raised when an enterprise user attempts to access documents outside clearance or tenant boundary."""
    pass


class HallucinationGuardrailError(EnterprisePlatformError):
    """Raised when generated output contains ungrounded claims or lacks verifiable citations."""
    pass


class DocumentExtractionError(EnterprisePlatformError):
    """Raised when a legacy file (PDF, CSV, MD) cannot be read, parsed, or decoded."""
    pass


class AgentToolExecutionError(EnterprisePlatformError):
    """Raised when an ERP/CRM transactional tool fails or encounters an unrecoverable API error."""
    pass


class HITLApprovalRequiredError(EnterprisePlatformError):
    """Raised when a sensitive operation must be deferred until human cryptographic approval is granted."""
    def __init__(self, message: str, action_id: str, confirmation_token: str, action_payload: dict):
        super().__init__(message, details={"action_id": action_id, "action_payload": action_payload})
        self.action_id = action_id
        self.confirmation_token = confirmation_token
        self.action_payload = action_payload


class InvalidConfirmationTokenError(EnterprisePlatformError):
    """Raised when an invalid or forged HITL confirmation token is submitted."""
    pass
