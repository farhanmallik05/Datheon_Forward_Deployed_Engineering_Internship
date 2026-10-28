"""FastAPI endpoints exposing mock enterprise ERP / CRM REST services."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.core.security import EnterpriseUser, get_authenticated_user
from src.services.mock_erp_crm import MockEnterpriseService

router = APIRouter(prefix="/api/v1/erp", tags=["Mock Enterprise ERP/CRM"])

_erp_service = None


def get_erp_service() -> MockEnterpriseService:
    global _erp_service
    if _erp_service is None:
        _erp_service = MockEnterpriseService()
    return _erp_service


@router.get("/inventory/{sku}", status_code=status.HTTP_200_OK)
def get_inventory_item(sku: str, erp: MockEnterpriseService = Depends(get_erp_service)):
    item = erp.get_inventory_item(sku)
    if not item:
        raise HTTPException(status_code=404, detail=f"SKU '{sku}' not found.")
    return item


@router.get("/inventory", status_code=status.HTTP_200_OK)
def list_inventory(category: Optional[str] = None, erp: MockEnterpriseService = Depends(get_erp_service)):
    return erp.list_inventory(category=category)


@router.get("/leads/{lead_id}", status_code=status.HTTP_200_OK)
def get_lead(lead_id: str, erp: MockEnterpriseService = Depends(get_erp_service)):
    lead = erp.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found.")
    return lead


@router.get("/tickets/{ticket_id}", status_code=status.HTTP_200_OK)
def get_ticket(ticket_id: str, erp: MockEnterpriseService = Depends(get_erp_service)):
    t = erp.get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return t


@router.get("/purchase-orders/{po_number}", status_code=status.HTTP_200_OK)
def get_purchase_order(po_number: str, erp: MockEnterpriseService = Depends(get_erp_service)):
    po = erp.get_purchase_order(po_number)
    if not po:
        raise HTTPException(status_code=404, detail=f"Purchase order '{po_number}' not found.")
    return po


@router.get("/audit-log", status_code=status.HTTP_200_OK)
def get_audit_trail(erp: MockEnterpriseService = Depends(get_erp_service)):
    data = erp._read_data()
    return {
        "total_entries": len(data.get("audit_log", [])),
        "audit_log": data.get("audit_log", []),
    }
