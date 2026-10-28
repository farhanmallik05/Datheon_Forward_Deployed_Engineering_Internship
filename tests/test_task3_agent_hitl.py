"""Unit and integration tests for Task 3: Autonomous Field Agent & ERP/CRM HITL."""
import pytest
from src.core.exceptions import InvalidConfirmationTokenError
from src.agent.engine import AutonomousEnterpriseAgent
from src.agent.hitl import HumanInTheLoopManager
from src.agent.tools import EnterpriseToolRegistry
from src.services.mock_erp_crm import MockEnterpriseService


def test_mock_erp_crud_operations(mock_erp):
    # 1. Inventory
    item = mock_erp.get_inventory_item("SKU-H100-80G")
    assert item is not None
    assert item["quantity_on_hand"] >= 10

    # Stock mutation
    updated = mock_erp.update_inventory_stock("SKU-H100-80G", delta=-2, user_id="TEST_USER")
    assert updated["quantity_on_hand"] == item["quantity_on_hand"] - 2

    # 2. CRM Lead
    lead = mock_erp.get_lead("LEAD-2026-101")
    assert lead is not None
    lead_up = mock_erp.update_lead_status("LEAD-2026-101", new_stage="QUALIFIED", notes="Initial discovery complete")
    assert lead_up["pipeline_stage"] == "QUALIFIED"

    # 3. ITSM Ticket
    tck = mock_erp.create_support_ticket(account_id="ACC-9999", subject="API gateway latency spike", priority="HIGH")
    assert tck["ticket_id"].startswith("TCK-")


def test_agent_thought_action_observation_cycle(mock_erp, user_eng_l2):
    registry = EnterpriseToolRegistry(erp_service=mock_erp)
    agent = AutonomousEnterpriseAgent(tool_registry=registry)

    result = agent.run(
        user=user_eng_l2,
        objective="Check inventory for SKU-H100-80G and verify stock count.",
    )

    assert result.completed is True
    assert result.status == "COMPLETED"
    assert len(result.steps) >= 1
    first_step = result.steps[0]
    assert first_step.action == "inventory_lookup"
    assert first_step.thought != ""
    assert "quantity_on_hand" in first_step.observation
    assert first_step.status == "SUCCESS"


def test_hitl_sensitive_write_interception_and_approval(mock_erp, user_eng_l2, user_fin_l3):
    registry = EnterpriseToolRegistry(erp_service=mock_erp)
    agent = AutonomousEnterpriseAgent(tool_registry=registry)
    hitl = HumanInTheLoopManager.get_instance()

    # Trigger objective requiring purchase order >= $50,000 (Sensitive write)
    result = agent.run(
        user=user_eng_l2,
        objective="Check SKU-H100-80G and order $145,000 from NVIDIA Cloud Compute.",
    )

    # Must pause for HITL approval!
    assert result.completed is False
    assert result.status == "HITL_PAUSED"
    assert result.pending_hitl is not None

    action_id = result.pending_hitl.action_id
    token = result.pending_hitl.confirmation_token
    assert action_id.startswith("HITL-ACT-")
    assert len(token) >= 32

    # 1. Attempt approval with invalid token (should fail)
    with pytest.raises(InvalidConfirmationTokenError):
        hitl.confirm_action(
            action_id=action_id,
            token="FORGED_INVALID_TOKEN_99999",
            approver=user_fin_l3,
            approved=True,
        )

    # 2. Approve with valid cryptographic HMAC token by authorized officer
    approval_res = hitl.confirm_action(
        action_id=action_id,
        token=token,
        approver=user_fin_l3,
        approved=True,
    )
    assert approval_res["status"] == "EXECUTED"
    assert "purchase_order" in approval_res["result"]
    assert approval_res["result"]["purchase_order"]["amount_usd"] == 145000.0
