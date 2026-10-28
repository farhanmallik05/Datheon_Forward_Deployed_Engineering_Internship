"""Enterprise tool parameter validation loops and resilient retry policies.

Validates all tool input payloads against strict Pydantic schemas before invocation
and applies exponential backoff retries on transient operational failures.
"""
import functools
import re
import time
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field, field_validator

from src.core.exceptions import AgentToolExecutionError
from src.core.logger import get_logger
from src.core.telemetry import AGENT_RETRY_COUNT

logger = get_logger("agent.validation")


# Pydantic Schemas for Tool Invocations
class InventoryLookupSchema(BaseModel):
    sku: str = Field(description="Unique inventory item SKU (e.g. SKU-H100-80G)")

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^SKU-[A-Z0-9\-]+$", v):
            raise ValueError(f"Invalid SKU format '{v}'. Expected pattern 'SKU-[A-Z0-9-]+'")
        return v


class InventoryStockUpdateSchema(BaseModel):
    sku: str = Field(description="Unique inventory item SKU")
    delta: int = Field(description="Quantity adjustment (positive to add, negative to deduct)")


class LeadStatusUpdateSchema(BaseModel):
    lead_id: str = Field(description="CRM Lead identifier (e.g. LEAD-2026-101)")
    new_stage: str = Field(description="Target CRM pipeline stage")
    notes: Optional[str] = Field(default=None, description="Optional audit notes")

    @field_validator("new_stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        valid_stages = {"QUALIFIED", "DISCOVERY", "PROPOSAL_DELIVERED", "NEGOTIATION", "CLOSED_WON", "CLOSED_LOST"}
        upper_v = v.strip().upper()
        if upper_v not in valid_stages:
            raise ValueError(f"Invalid stage '{v}'. Must be one of: {sorted(valid_stages)}")
        return upper_v


class TicketCreateSchema(BaseModel):
    account_id: str = Field(description="Enterprise customer account code (e.g. ACC-5001)")
    subject: str = Field(min_length=5, max_length=200, description="Clear description of issue")
    priority: str = Field(default="MEDIUM", description="Severity: LOW, MEDIUM, HIGH, CRITICAL")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid_priorities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        upper_v = v.strip().upper()
        if upper_v not in valid_priorities:
            raise ValueError(f"Invalid priority '{v}'. Must be one of: {sorted(valid_priorities)}")
        return upper_v


class PurchaseOrderCreateSchema(BaseModel):
    vendor: str = Field(min_length=3, description="Approved corporate vendor name")
    amount_usd: float = Field(gt=0.0, description="Total order amount in USD")


class PurchaseOrderApproveSchema(BaseModel):
    po_number: str = Field(description="Purchase order identifier (e.g. PO-88210)")
    token: str = Field(min_length=16, description="Cryptographic HMAC approval token")


class RAGSearchSchema(BaseModel):
    query: str = Field(min_length=3, description="Enterprise knowledge retrieval query")


class ToolValidator:
    """Dispatches schema validation for known enterprise tools."""

    _SCHEMAS: Dict[str, type[BaseModel]] = {
        "inventory_lookup": InventoryLookupSchema,
        "update_inventory_stock": InventoryStockUpdateSchema,
        "update_lead_status": LeadStatusUpdateSchema,
        "create_support_ticket": TicketCreateSchema,
        "create_purchase_order": PurchaseOrderCreateSchema,
        "approve_purchase_order": PurchaseOrderApproveSchema,
        "rag_knowledge_search": RAGSearchSchema,
    }

    @classmethod
    def validate(cls, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validates payload against tool schema, returning normalized dictionary."""
        schema = cls._SCHEMAS.get(tool_name)
        if not schema:
            return payload

        try:
            instance = schema(**payload)
            return instance.model_dump()
        except Exception as e:
            logger.error("Validation error for tool '%s': %s", tool_name, str(e))
            raise AgentToolExecutionError(f"Tool parameter validation error for '{tool_name}': {e}") from e


def with_retry(max_retries: int = 3, initial_delay: float = 0.1, backoff_factor: float = 2.0):
    """Decorator to retry transient API execution failures with exponential backoff."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    tool_name = func.__name__
                    AGENT_RETRY_COUNT.labels(tool_name=tool_name).inc()
                    logger.warning(
                        "[RETRY ATTEMPT %d/%d] Tool %s failed with: %s. Backing off for %.2fs",
                        attempt,
                        max_retries,
                        tool_name,
                        str(e),
                        delay,
                    )
                    if attempt == max_retries:
                        break
                    time.sleep(delay)
                    delay *= backoff_factor

            logger.error("All %d retries exhausted for tool %s", max_retries, func.__name__)
            raise AgentToolExecutionError(f"Tool {func.__name__} failed after {max_retries} retries: {last_exception}") from last_exception

        return wrapper
    return decorator
