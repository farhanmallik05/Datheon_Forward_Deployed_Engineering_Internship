"""Enterprise tool definitions and execution registry for ERP, CRM, and RAG.

Binds the autonomous field agent to mock enterprise backend services with
schema validation, retry logic, and Human-in-the-Loop gating.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.core.config import Department, get_settings
from src.core.exceptions import AgentToolExecutionError, HITLApprovalRequiredError
from src.core.logger import get_logger
from src.core.security import EnterpriseUser
from src.core.telemetry import TelemetryMetrics
from src.agent.hitl import HumanInTheLoopManager
from src.agent.validation import ToolValidator, with_retry
from src.services.mock_erp_crm import MockEnterpriseService

logger = get_logger("agent.tools")


@dataclass
class ToolDefinition:
    """Enterprise metadata for an executable tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    execute: Callable


class EnterpriseToolRegistry:
    """Registry exposing operational capabilities to the autonomous agent."""

    def __init__(self, erp_service: Optional[MockEnterpriseService] = None):
        self.erp = erp_service or MockEnterpriseService()
        self.hitl = HumanInTheLoopManager.get_instance()
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_all_tools()

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def execute_tool(self, tool_name: str, payload: Dict[str, Any], caller: EnterpriseUser) -> Any:
        """Executes a tool with validation, HITL gating, retry handling, and telemetry."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise AgentToolExecutionError(f"Requested tool '{tool_name}' is not registered.")

        # 1. Schema Validation
        validated_payload = ToolValidator.validate(tool_name, payload)

        # 2. Check for Sensitive Write Operation (HITL Gate)
        is_sensitive, reason = self.hitl.is_sensitive_operation(tool_name, validated_payload)
        if is_sensitive:
            logger.info("Sensitive operation detected on tool '%s'. Initiating HITL interception.", tool_name)
            # Create deferred execution closure
            def deferred_executor(approver_id: str, token: str):
                return tool.execute(validated_payload, caller, approver_id=approver_id, approval_token=token)

            pending_action = self.hitl.register_pending_action(
                tool_name=tool_name,
                payload=validated_payload,
                execution_callback=deferred_executor,
                reason=reason,
            )
            # Raise HITL error to pause agent execution loop cleanly
            raise HITLApprovalRequiredError(
                message=f"Action paused for human review: {reason}",
                action_id=pending_action.action_id,
                confirmation_token=pending_action.confirmation_token,
                action_payload=validated_payload,
            )

        # 3. Direct Execution
        try:
            result = tool.execute(validated_payload, caller)
            TelemetryMetrics.record_tool_call(tool_name, success=True)
            return result
        except Exception as e:
            TelemetryMetrics.record_tool_call(tool_name, success=False)
            logger.error("Execution failed for tool '%s': %s", tool_name, str(e))
            raise

    def _register_all_tools(self):
        # 1. Inventory Lookup
        @with_retry(max_retries=3)
        def _inventory_lookup(payload: dict, caller: EnterpriseUser, **kwargs):
            sku = payload["sku"]
            item = self.erp.get_inventory_item(sku)
            if not item:
                return {"status": "NOT_FOUND", "message": f"No item found with SKU {sku}"}
            return {"status": "SUCCESS", "item": item}

        self._tools["inventory_lookup"] = ToolDefinition(
            name="inventory_lookup",
            description="Lookup hardware components, servers, or parts in enterprise ERP by SKU.",
            parameters={"sku": {"type": "string", "description": "e.g. SKU-H100-80G"}},
            execute=_inventory_lookup,
        )

        # 2. Update Inventory Stock
        @with_retry(max_retries=2)
        def _update_inventory_stock(payload: dict, caller: EnterpriseUser, **kwargs):
            sku = payload["sku"]
            delta = payload["delta"]
            updated = self.erp.update_inventory_stock(sku, delta, user_id=caller.user_id)
            return {"status": "SUCCESS", "updated_record": updated}

        self._tools["update_inventory_stock"] = ToolDefinition(
            name="update_inventory_stock",
            description="Adjust warehouse stock levels for an existing SKU.",
            parameters={
                "sku": {"type": "string"},
                "delta": {"type": "integer", "description": "Stock change count"},
            },
            execute=_update_inventory_stock,
        )

        # 3. CRM Lead Lookup
        @with_retry(max_retries=2)
        def _get_lead(payload: dict, caller: EnterpriseUser, **kwargs):
            lead_id = payload.get("lead_id", "")
            lead = self.erp.get_lead(lead_id)
            if not lead:
                return {"status": "NOT_FOUND", "message": f"No CRM lead found with ID {lead_id}"}
            return {"status": "SUCCESS", "lead": lead}

        self._tools["get_lead"] = ToolDefinition(
            name="get_lead",
            description="Retrieve CRM customer account status, ARR, and sales stage.",
            parameters={"lead_id": {"type": "string", "description": "e.g. LEAD-2026-101"}},
            execute=_get_lead,
        )

        # 4. CRM Lead Status Update
        @with_retry(max_retries=2)
        def _update_lead_status(payload: dict, caller: EnterpriseUser, **kwargs):
            lead_id = payload["lead_id"]
            new_stage = payload["new_stage"]
            notes = payload.get("notes")
            approver_id = kwargs.get("approver_id", caller.user_id)
            updated = self.erp.update_lead_status(lead_id, new_stage, notes=notes, user_id=approver_id)
            return {"status": "SUCCESS", "lead": updated}

        self._tools["update_lead_status"] = ToolDefinition(
            name="update_lead_status",
            description="Advance CRM deal stage (QUALIFIED, NEGOTIATION, CLOSED_WON, CLOSED_LOST). Sensitive stages trigger HITL.",
            parameters={
                "lead_id": {"type": "string"},
                "new_stage": {"type": "string"},
                "notes": {"type": "string", "description": "Update notes"},
            },
            execute=_update_lead_status,
        )

        # 5. ITSM Ticket Creation
        @with_retry(max_retries=2)
        def _create_support_ticket(payload: dict, caller: EnterpriseUser, **kwargs):
            account_id = payload["account_id"]
            subject = payload["subject"]
            priority = payload.get("priority", "MEDIUM")
            ticket = self.erp.create_support_ticket(account_id, subject, priority, user_id=caller.user_id)
            return {"status": "SUCCESS", "ticket": ticket}

        self._tools["create_support_ticket"] = ToolDefinition(
            name="create_support_ticket",
            description="Create an IT service management (ITSM) ticket for customer issues.",
            parameters={
                "account_id": {"type": "string"},
                "subject": {"type": "string"},
                "priority": {"type": "string", "description": "LOW, MEDIUM, HIGH, CRITICAL"},
            },
            execute=_create_support_ticket,
        )

        # 6. Create Purchase Order (Sensitive if >= $50k)
        @with_retry(max_retries=2)
        def _create_purchase_order(payload: dict, caller: EnterpriseUser, **kwargs):
            vendor = payload["vendor"]
            amount_usd = payload["amount_usd"]
            approver_id = kwargs.get("approver_id", caller.user_id)
            order = self.erp.create_purchase_order(vendor, amount_usd, user_id=approver_id)
            return {"status": "SUCCESS", "purchase_order": order}

        self._tools["create_purchase_order"] = ToolDefinition(
            name="create_purchase_order",
            description="Create ERP hardware or software purchase order. Orders >= $50,000 USD trigger HITL.",
            parameters={
                "vendor": {"type": "string"},
                "amount_usd": {"type": "number"},
            },
            execute=_create_purchase_order,
        )

        # 7. Approve Purchase Order (Always sensitive)
        @with_retry(max_retries=2)
        def _approve_purchase_order(payload: dict, caller: EnterpriseUser, **kwargs):
            po_number = payload["po_number"]
            token = kwargs.get("approval_token", payload.get("token", "OFFICER_OVERRIDE"))
            approver_id = kwargs.get("approver_id", caller.user_id)
            approved = self.erp.approve_purchase_order(po_number, token, user_id=approver_id)
            return {"status": "SUCCESS", "approved_order": approved}

        self._tools["approve_purchase_order"] = ToolDefinition(
            name="approve_purchase_order",
            description="Authorize and release accounts payable wire for an ERP purchase order. Requires cryptographic HITL approval.",
            parameters={
                "po_number": {"type": "string"},
                "token": {"type": "string", "description": "Cryptographic approval token"},
            },
            execute=_approve_purchase_order,
        )

        # 8. RAG Knowledge Search
        def _rag_knowledge_search(payload: dict, caller: EnterpriseUser, **kwargs):
            from src.rag.engine import EnterpriseRAGEngine
            rag = EnterpriseRAGEngine()
            query = payload["query"]
            response = rag.query(user=caller, query_text=query)
            return {
                "status": "SUCCESS",
                "answer": response.answer,
                "citations": response.citations,
                "chunks_count": response.chunks_retrieved,
            }

        self._tools["rag_knowledge_search"] = ToolDefinition(
            name="rag_knowledge_search",
            description="Search internal VPC corporate documentation and policies via the RBAC RAG engine.",
            parameters={"query": {"type": "string"}},
            execute=_rag_knowledge_search,
        )

