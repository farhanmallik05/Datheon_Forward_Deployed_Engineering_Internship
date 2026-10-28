"""Human-in-the-loop (HITL) authorization and cryptographic token verification.

Gates sensitive transactional write operations (e.g. capital purchase orders > $50k,
lead closure, ticket deletions) behind a cryptographic HMAC confirmation protocol.
"""
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.exceptions import (
    HITLApprovalRequiredError,
    InvalidConfirmationTokenError,
    RBACAccessDeniedError,
)
from src.core.logger import get_logger
from src.core.security import (
    EnterpriseUser,
    generate_hitl_signature,
    verify_hitl_signature,
)
from src.core.telemetry import (
    AGENT_HITL_ACTIONS_RESOLVED,
    AGENT_HITL_QUEUE_SIZE,
)
from src.agent.state import PendingHITLAction

logger = get_logger("agent.hitl")


class HumanInTheLoopManager:
    """Manages the pending approval queue for sensitive autonomous agent transactions."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._pending_actions: Dict[str, Tuple[PendingHITLAction, Callable]] = {}

    @classmethod
    def get_instance(cls) -> "HumanInTheLoopManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = HumanInTheLoopManager()
            return cls._instance

    def is_sensitive_operation(self, tool_name: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Determines if a proposed operation requires mandatory human authorization."""
        if tool_name == "create_purchase_order":
            amount = float(payload.get("amount_usd", 0.0))
            if amount >= 50000.0:
                return True, f"Capital purchase order of ${amount:,.2f} exceeds automatic threshold ($50,000.00)."

        if tool_name == "update_lead_status":
            new_stage = str(payload.get("new_stage", "")).upper()
            if new_stage in ["CLOSED_WON", "CLOSED_LOST"]:
                return True, f"Modifying CRM deal stage to terminal state '{new_stage}' requires Sales Director sign-off."

        if tool_name == "approve_purchase_order":
            return True, "Direct wire disbursement approval requires verified secondary officer token."

        return False, ""

    def register_pending_action(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        execution_callback: Callable,
        reason: str,
    ) -> PendingHITLAction:
        """Enqueues an action and yields a cryptographic confirmation token."""
        action_id = f"HITL-ACT-{uuid.uuid4().hex[:8].upper()}"
        token = generate_hitl_signature(action_id, payload)

        pending_action = PendingHITLAction(
            action_id=action_id,
            tool_name=tool_name,
            action_payload=payload,
            confirmation_token=token,
            reason=reason,
        )

        with self._lock:
            self._pending_actions[action_id] = (pending_action, execution_callback)
            AGENT_HITL_QUEUE_SIZE.set(len(self._pending_actions))

        logger.warning(
            "[HITL GATE ACTIVATED] Action %s queued for tool %s. Reason: %s (Token: %s...)",
            action_id,
            tool_name,
            reason,
            token[:12],
        )
        return pending_action

    def confirm_action(
        self,
        action_id: str,
        token: str,
        approver: EnterpriseUser,
        approved: bool = True,
    ) -> Dict[str, Any]:
        """Validates token, executes the deferred callback if approved, and records audit state."""
        with self._lock:
            entry = self._pending_actions.get(action_id)
            if not entry:
                raise InvalidConfirmationTokenError(f"No pending HITL action found with ID: {action_id}")

            pending_action, callback = entry

            # Verify cryptographic HMAC signature
            if not verify_hitl_signature(action_id, pending_action.action_payload, token):
                logger.error("[HITL SECURITY BREACH] Forged or corrupted token provided for action %s", action_id)
                raise InvalidConfirmationTokenError("Cryptographic token verification failed. Signature mismatch.")

            # Verify approver clearance
            if approver.clearance.level < 2:  # Must be at least L2 Restricted
                raise RBACAccessDeniedError(
                    f"Approver clearance '{approver.clearance.value}' is insufficient. Minimum L2 required."
                )

            # Pop from queue
            del self._pending_actions[action_id]
            AGENT_HITL_QUEUE_SIZE.set(len(self._pending_actions))

        decision_label = "approved" if approved else "rejected"
        AGENT_HITL_ACTIONS_RESOLVED.labels(decision=decision_label).inc()

        if not approved:
            logger.info("[HITL REJECTED] Action %s rejected by %s (%s)", action_id, approver.user_id, approver.name)
            return {
                "action_id": action_id,
                "status": "REJECTED",
                "approver": approver.user_id,
                "message": f"Action {action_id} was rejected by human operator.",
            }

        # Execute approved mutation callback
        logger.info("[HITL APPROVED] Executing authorized mutation %s by %s", action_id, approver.user_id)
        result = callback(approver_id=approver.user_id, token=token)

        return {
            "action_id": action_id,
            "status": "EXECUTED",
            "approver": approver.user_id,
            "result": result,
            "message": f"Action {action_id} verified and executed successfully.",
        }

    def list_pending_actions(self) -> List[dict]:
        with self._lock:
            return [act.model_dump() for act, _ in self._pending_actions.values()]
