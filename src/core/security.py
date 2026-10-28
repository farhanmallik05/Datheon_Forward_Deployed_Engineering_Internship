"""Enterprise Role-Based Access Control (RBAC) and Security Primitives.

Implements multi-tenant department isolation, clearance tier filtering,
and HMAC-based cryptographic authorization for sensitive operations.
"""
import hashlib
import hmac
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import Header, HTTPException, status

from src.core.config import ClearanceTier, Department, get_settings


class EnterpriseUser(BaseModel):
    """Authenticated enterprise principal model."""
    user_id: str = Field(description="Unique employee corporate identity ID")
    name: str = Field(description="Full employee name")
    department: Department = Field(description="Primary assigned department")
    clearance: ClearanceTier = Field(description="Verified security clearance tier")
    is_admin: bool = Field(default=False, description="System administrator flag")
    additional_allowed_departments: List[Department] = Field(
        default_factory=list,
        description="Cross-department project access allowances",
    )

    def can_access(self, doc_department: Department, doc_clearance: ClearanceTier) -> bool:
        """Determines if this principal can read a specific document."""
        return can_access_document(self, doc_department, doc_clearance)


def can_access_document(
    user: EnterpriseUser,
    doc_department: Department,
    doc_clearance: ClearanceTier,
) -> bool:
    """Evaluates whether an enterprise user has sufficient clearance and tenant rights.

    Security Rules:
    1. Clearance Hierarchy: user.clearance must meet or exceed doc_clearance.
       (e.g., L1 cannot read L2 or L3; L2 cannot read L3; L3 can read L1, L2, L3).
    2. Department Boundary:
       - Cross-functional documents are visible across departments if clearance is met.
       - Executive clearance (or is_admin) allows cross-department oversight.
       - Otherwise, document department must match user department or explicit allowances.
    """
    # 1. Clearance Enforcement
    if not user.clearance.allows(doc_clearance):
        return False

    # 2. Executive / Admin Oversight
    if user.is_admin or user.department == Department.EXECUTIVE:
        return True

    # 3. Cross-Functional Assets
    if doc_department == Department.CROSS_FUNCTIONAL:
        return True

    # 4. Department Tenancy Enforcement
    if doc_department == user.department:
        return True

    if doc_department in user.additional_allowed_departments:
        return True

    return False


def verify_clearance(user: EnterpriseUser, required_clearance: ClearanceTier) -> None:
    """Raises HTTPException if user does not possess required clearance."""
    if not user.clearance.allows(required_clearance):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Security clearance violation: Principal clearance '{user.clearance.value}' "
                f"is insufficient for required tier '{required_clearance.value}'."
            ),
        )


def generate_hitl_signature(action_id: str, payload: dict, secret: Optional[str] = None) -> str:
    """Computes a SHA-256 HMAC cryptographic confirmation token for Human-In-The-Loop actions."""
    settings = get_settings()
    key = (secret or settings.HITL_HMAC_SECRET).encode("utf-8")
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    message = f"{action_id}:{canonical_payload}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_hitl_signature(action_id: str, payload: dict, token: str, secret: Optional[str] = None) -> bool:
    """Verifies that an approval token matches the cryptographic HMAC signature."""
    expected_token = generate_hitl_signature(action_id, payload, secret)
    return hmac.compare_digest(expected_token, token)


async def get_authenticated_user(
    x_user_id: Optional[str] = Header(default="USR-ENG-4401", alias="X-User-Id"),
    x_user_name: Optional[str] = Header(default="Alex Mercer", alias="X-User-Name"),
    x_user_department: Optional[str] = Header(default="engineering", alias="X-User-Department"),
    x_user_clearance: Optional[str] = Header(default="L2_RESTRICTED", alias="X-User-Clearance"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> EnterpriseUser:
    """FastAPI dependency to extract and validate the enterprise principal from headers."""
    settings = get_settings()

    # Determine Admin status based on API Key
    is_admin = (x_api_key == settings.ADMIN_API_KEY)

    try:
        dept = Department(x_user_department.lower())
    except (ValueError, AttributeError):
        dept = Department.ENGINEERING

    try:
        clearance = ClearanceTier(x_user_clearance.upper())
    except (ValueError, AttributeError):
        clearance = ClearanceTier.L1_PUBLIC

    return EnterpriseUser(
        user_id=x_user_id or "USR-ANON",
        name=x_user_name or "Anonymous Principal",
        department=dept,
        clearance=clearance,
        is_admin=is_admin,
    )
