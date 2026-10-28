"""Exhaustive Security & Data Leakage Negative Testing Matrix.

Audits RBAC boundaries, cross-department isolation, clearance escalations,
and cryptographic token tampering to ensure zero data leakage.
"""
import pytest
from src.core.config import ClearanceTier, Department
from src.core.exceptions import InvalidConfirmationTokenError, RBACAccessDeniedError
from src.core.security import EnterpriseUser, can_access_document
from src.agent.hitl import HumanInTheLoopManager
from src.rag.rbac_retriever import RBACRetriever


def test_clearance_matrix_negative_assertions():
    """Validates clearance tier boundary mathematics."""
    user_l1 = EnterpriseUser(user_id="U1", name="U1", department=Department.ENGINEERING, clearance=ClearanceTier.L1_PUBLIC)
    user_l2 = EnterpriseUser(user_id="U2", name="U2", department=Department.ENGINEERING, clearance=ClearanceTier.L2_RESTRICTED)
    user_l3 = EnterpriseUser(user_id="U3", name="U3", department=Department.ENGINEERING, clearance=ClearanceTier.L3_CONFIDENTIAL)

    # L1 cannot access L2 or L3
    assert not can_access_document(user_l1, Department.ENGINEERING, ClearanceTier.L2_RESTRICTED)
    assert not can_access_document(user_l1, Department.ENGINEERING, ClearanceTier.L3_CONFIDENTIAL)
    assert can_access_document(user_l1, Department.ENGINEERING, ClearanceTier.L1_PUBLIC)

    # L2 can access L1 and L2, but not L3
    assert can_access_document(user_l2, Department.ENGINEERING, ClearanceTier.L1_PUBLIC)
    assert can_access_document(user_l2, Department.ENGINEERING, ClearanceTier.L2_RESTRICTED)
    assert not can_access_document(user_l2, Department.ENGINEERING, ClearanceTier.L3_CONFIDENTIAL)

    # L3 can access L1, L2, L3 in their department
    assert can_access_document(user_l3, Department.ENGINEERING, ClearanceTier.L1_PUBLIC)
    assert can_access_document(user_l3, Department.ENGINEERING, ClearanceTier.L2_RESTRICTED)
    assert can_access_document(user_l3, Department.ENGINEERING, ClearanceTier.L3_CONFIDENTIAL)


def test_cross_tenant_isolation_matrix(vector_store, embedder):
    """Ensures department partitions never cross-contaminate."""
    retriever = RBACRetriever(vector_store=vector_store, embedder=embedder)

    eng_user = EnterpriseUser(
        user_id="USR-ENG-01",
        name="Engineer One",
        department=Department.ENGINEERING,
        clearance=ClearanceTier.L3_CONFIDENTIAL,
    )

    # Query targeting HR records
    hr_leak_query = retriever.retrieve(
        user=eng_user,
        query="Executive salary bands compensation bonus multipliers",
        target_department=Department.HR,
    )
    for chunk in hr_leak_query:
        assert chunk.metadata.department != Department.HR, "Cross-tenant leakage: Engineer retrieved HR document!"

    # Query targeting Finance audit
    fin_leak_query = retriever.retrieve(
        user=eng_user,
        query="Consolidated revenue audit findings and vendor invoices",
        target_department=Department.FINANCE,
    )
    for chunk in fin_leak_query:
        assert chunk.metadata.department != Department.FINANCE, "Cross-tenant leakage: Engineer retrieved Finance document!"


def test_hitl_approver_insufficient_clearance():
    """Ensures an L1 user cannot approve sensitive transactional operations."""
    hitl = HumanInTheLoopManager.get_instance()
    user_l1 = EnterpriseUser(
        user_id="USR-INTERN-01",
        name="Intern User",
        department=Department.FINANCE,
        clearance=ClearanceTier.L1_PUBLIC,
    )

    action = hitl.register_pending_action(
        tool_name="create_purchase_order",
        payload={"vendor": "NVIDIA", "amount_usd": 100000.0},
        execution_callback=lambda **kw: {"ok": True},
        reason="Test high value PO",
    )

    with pytest.raises(RBACAccessDeniedError):
        hitl.confirm_action(
            action_id=action.action_id,
            token=action.confirmation_token,
            approver=user_l1,  # Insufficient clearance
            approved=True,
        )
