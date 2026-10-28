"""Mock Enterprise ERP / CRM Transactional Engine (SAP/Salesforce/ServiceNow simulation).

Maintains persistent ACID-like JSON transactions for inventory records, CRM leads,
ITSM tickets, and ERP purchase orders with audit logging.
"""
import copy
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import get_settings
from src.core.exceptions import AgentToolExecutionError
from src.core.logger import get_logger

logger = get_logger("services.erp_crm")


class MockEnterpriseService:
    """Thread-safe transactional store for enterprise mock APIs."""

    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        settings = get_settings()
        self.db_path = db_path or settings.MOCK_DB_PATH
        self._ensure_db()

    def _ensure_db(self):
        """Ensures the JSON database exists with initial enterprise seed data."""
        with self._lock:
            if not self.db_path.exists():
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                initial_data = {
                    "inventory": [
                        {"sku": "SKU-H100-80G", "product_name": "NVIDIA H100 80GB SXM5 Node", "category": "Hardware", "quantity_on_hand": 14, "unit_cost_usd": 32000.0, "warehouse_id": "WH-US-EAST", "reorder_level": 5},
                        {"sku": "SKU-L40S-48G", "product_name": "NVIDIA L40S 48GB PCIe Server", "category": "Hardware", "quantity_on_hand": 38, "unit_cost_usd": 11500.0, "warehouse_id": "WH-US-WEST", "reorder_level": 10},
                        {"sku": "SKU-NET-SWITCH-400G", "product_name": "Arista 400G Enterprise Spine Switch", "category": "Networking", "quantity_on_hand": 8, "unit_cost_usd": 18200.0, "warehouse_id": "WH-US-EAST", "reorder_level": 4},
                    ],
                    "leads": [
                        {"lead_id": "LEAD-2026-101", "company_name": "Apex Global Financial", "contact_email": "cto@apexglobal.com", "estimated_arr_usd": 350000.0, "pipeline_stage": "NEGOTIATION", "assigned_rep": "Sarah Jenkins", "notes": "Requires on-prem VPC deployment."},
                        {"lead_id": "LEAD-2026-102", "company_name": "BioHealth Genomics", "contact_email": "vpe@biohealth.org", "estimated_arr_usd": 180000.0, "pipeline_stage": "QUALIFIED", "assigned_rep": "David Chen", "notes": "Evaluating vector ETL latency."},
                    ],
                    "tickets": [
                        {"ticket_id": "TCK-8801", "account_id": "ACC-5001", "subject": "Vector DB query timeout on Qdrant batch upsert", "priority": "HIGH", "status": "OPEN", "assigned_engineer": "Alex Mercer", "created_at": "2026-10-25T14:22:00Z"},
                        {"ticket_id": "TCK-8802", "account_id": "ACC-5002", "subject": "RBAC clearance denial for Finance audit team", "priority": "CRITICAL", "status": "IN_PROGRESS", "assigned_engineer": "Maria Santos", "created_at": "2026-10-26T09:10:00Z"},
                    ],
                    "purchase_orders": [
                        {"po_number": "PO-88210", "vendor": "NVIDIA Cloud Compute", "amount_usd": 145000.0, "status": "APPROVED", "requires_hitl": True, "approval_token": None},
                        {"po_number": "PO-88220", "vendor": "CrowdStrike SecOps", "amount_usd": 42000.0, "status": "PENDING_APPROVAL", "requires_hitl": True, "approval_token": None},
                    ],
                    "audit_log": [],
                }
                with open(self.db_path, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2)

    def _read_data(self) -> dict:
        with open(self.db_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_data(self, data: dict):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _log_audit(self, action: str, entity_type: str, entity_id: str, user_id: str, details: dict):
        """Records an immutable security audit entry for transactional compliance."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "details": details,
        }
        data = self._read_data()
        data.setdefault("audit_log", []).append(entry)
        self._write_data(data)
        logger.info("[AUDIT] %s on %s:%s by %s", action, entity_type, entity_id, user_id)

    # ERP Inventory Operations
    def get_inventory_item(self, sku: str) -> Optional[dict]:
        with self._lock:
            data = self._read_data()
            for item in data.get("inventory", []):
                if item["sku"].upper() == sku.upper():
                    return copy.deepcopy(item)
            return None

    def list_inventory(self, category: Optional[str] = None) -> List[dict]:
        with self._lock:
            data = self._read_data()
            items = data.get("inventory", [])
            if category:
                items = [i for i in items if i.get("category", "").lower() == category.lower()]
            return copy.deepcopy(items)

    def update_inventory_stock(self, sku: str, delta: int, user_id: str = "SYS_AGENT") -> dict:
        with self._lock:
            data = self._read_data()
            target = None
            for item in data.get("inventory", []):
                if item["sku"].upper() == sku.upper():
                    target = item
                    break

            if not target:
                raise AgentToolExecutionError(f"Inventory item with SKU '{sku}' not found.")

            old_qty = target["quantity_on_hand"]
            new_qty = old_qty + delta
            if new_qty < 0:
                raise AgentToolExecutionError(f"Insufficient stock for SKU {sku}. Current: {old_qty}, Requested delta: {delta}")

            target["quantity_on_hand"] = new_qty
            self._write_data(data)
            self._log_audit("UPDATE_STOCK", "inventory", sku, user_id, {"old_quantity": old_qty, "new_quantity": new_qty, "delta": delta})
            return copy.deepcopy(target)

    # CRM Lead Operations
    def get_lead(self, lead_id: str) -> Optional[dict]:
        with self._lock:
            data = self._read_data()
            for lead in data.get("leads", []):
                if lead["lead_id"].upper() == lead_id.upper():
                    return copy.deepcopy(lead)
            return None

    def update_lead_status(self, lead_id: str, new_stage: str, notes: Optional[str] = None, user_id: str = "SYS_AGENT") -> dict:
        with self._lock:
            data = self._read_data()
            target = None
            for lead in data.get("leads", []):
                if lead["lead_id"].upper() == lead_id.upper():
                    target = lead
                    break

            if not target:
                raise AgentToolExecutionError(f"CRM Lead with ID '{lead_id}' not found.")

            old_stage = target["pipeline_stage"]
            target["pipeline_stage"] = new_stage.upper()
            if notes:
                target["notes"] = f"{target.get('notes', '')} | [Update]: {notes}".strip(" | ")

            self._write_data(data)
            self._log_audit("UPDATE_STAGE", "leads", lead_id, user_id, {"old_stage": old_stage, "new_stage": new_stage.upper(), "notes": notes})
            return copy.deepcopy(target)

    # ITSM Ticket Operations
    def get_ticket(self, ticket_id: str) -> Optional[dict]:
        with self._lock:
            data = self._read_data()
            for ticket in data.get("tickets", []):
                if ticket["ticket_id"].upper() == ticket_id.upper():
                    return copy.deepcopy(ticket)
            return None

    def create_support_ticket(self, account_id: str, subject: str, priority: str = "MEDIUM", user_id: str = "SYS_AGENT") -> dict:
        with self._lock:
            data = self._read_data()
            tickets = data.get("tickets", [])
            new_id = f"TCK-{len(tickets) + 8801}"
            new_ticket = {
                "ticket_id": new_id,
                "account_id": account_id.upper(),
                "subject": subject,
                "priority": priority.upper(),
                "status": "OPEN",
                "assigned_engineer": "Unassigned (Queued)",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            tickets.append(new_ticket)
            data["tickets"] = tickets
            self._write_data(data)
            self._log_audit("CREATE_TICKET", "tickets", new_id, user_id, new_ticket)
            return copy.deepcopy(new_ticket)

    # ERP Purchase Order Operations
    def get_purchase_order(self, po_number: str) -> Optional[dict]:
        with self._lock:
            data = self._read_data()
            for po in data.get("purchase_orders", []):
                if po["po_number"].upper() == po_number.upper():
                    return copy.deepcopy(po)
            return None

    def create_purchase_order(self, vendor: str, amount_usd: float, user_id: str = "SYS_AGENT") -> dict:
        with self._lock:
            data = self._read_data()
            orders = data.get("purchase_orders", [])
            new_po = f"PO-{len(orders) + 88235}"
            order = {
                "po_number": new_po,
                "vendor": vendor,
                "amount_usd": float(amount_usd),
                "status": "PENDING_APPROVAL",
                "requires_hitl": (amount_usd >= 50000.0),
                "approval_token": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            orders.append(order)
            data["purchase_orders"] = orders
            self._write_data(data)
            self._log_audit("CREATE_PO", "purchase_orders", new_po, user_id, order)
            return copy.deepcopy(order)

    def approve_purchase_order(self, po_number: str, token: str, user_id: str = "SEC_OFFICER") -> dict:
        with self._lock:
            data = self._read_data()
            target = None
            for po in data.get("purchase_orders", []):
                if po["po_number"].upper() == po_number.upper():
                    target = po
                    break

            if not target:
                raise AgentToolExecutionError(f"Purchase order '{po_number}' not found.")

            target["status"] = "APPROVED"
            target["approval_token"] = token
            target["approved_at"] = datetime.now(timezone.utc).isoformat()
            target["approved_by"] = user_id
            self._write_data(data)
            self._log_audit("APPROVE_PO", "purchase_orders", po_number, user_id, {"token": token})
            return copy.deepcopy(target)

