"""FastAPI endpoints for Autonomous Field Agent orchestration and HITL confirmations."""
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.core.security import EnterpriseUser, get_authenticated_user
from src.agent.engine import AutonomousEnterpriseAgent
from src.agent.hitl import HumanInTheLoopManager

router = APIRouter(prefix="/api/v1/agent", tags=["Autonomous Field Agent"])

_agent_instance = None


def get_agent() -> AutonomousEnterpriseAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AutonomousEnterpriseAgent()
    return _agent_instance


class AgentChatRequest(BaseModel):
    prompt: str = Field(min_length=3, description="High-level operational instruction")
    session_id: Optional[str] = Field(default=None, description="Optional persistent session identifier")


class ActionConfirmationRequest(BaseModel):
    action_id: str = Field(description="Action identifier from HITL pause")
    confirmation_token: str = Field(description="HMAC cryptographic token")
    approved: bool = Field(default=True, description="Approval verdict: True to execute, False to reject")


@router.post("/chat", status_code=status.HTTP_200_OK)
def run_agent_turn(
    request: AgentChatRequest,
    current_user: EnterpriseUser = Depends(get_authenticated_user),
    agent: AutonomousEnterpriseAgent = Depends(get_agent),
):
    """Executes Thought-Action-Observation cycles towards the requested enterprise objective."""
    result = agent.run(
        user=current_user,
        objective=request.prompt,
        session_id=request.session_id,
    )
    return result.to_dict()


@router.post("/confirm-action", status_code=status.HTTP_200_OK)
def confirm_hitl_action(
    request: ActionConfirmationRequest,
    current_user: EnterpriseUser = Depends(get_authenticated_user),
):
    """Submits human cryptographic authorization to release or reject a paused sensitive operation."""
    hitl = HumanInTheLoopManager.get_instance()
    result = hitl.confirm_action(
        action_id=request.action_id,
        token=request.confirmation_token,
        approver=current_user,
        approved=request.approved,
    )
    return result


@router.get("/pending-actions", status_code=status.HTTP_200_OK)
def list_pending_hitl_actions(
    current_user: EnterpriseUser = Depends(get_authenticated_user),
):
    """Lists sensitive transactional operations currently awaiting human confirmation."""
    hitl = HumanInTheLoopManager.get_instance()
    return {
        "count": len(hitl.list_pending_actions()),
        "pending_actions": hitl.list_pending_actions(),
        "caller": current_user.user_id,
    }
