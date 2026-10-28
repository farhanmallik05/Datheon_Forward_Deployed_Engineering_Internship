"""Agent execution state and Thought-Action-Observation trace models.

Captures step-by-step reasoning, tool invocations, intermediate observations,
and human-in-the-loop pending transaction states.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ThoughtActionObservationStep(BaseModel):
    """A single ReAct reasoning cycle executed by the autonomous agent."""
    step_number: int = Field(description="Sequential execution index")
    thought: str = Field(description="Internal reasoning rationale preceding tool call")
    action: str = Field(description="Target tool/endpoint selected for execution")
    action_input: Dict[str, Any] = Field(default_factory=dict, description="Validated payload passed to tool")
    observation: str = Field(default="", description="Output result or error returned by API")
    status: str = Field(default="SUCCESS", description="Step status: SUCCESS, ERROR, RETRY, or HITL_REQUIRED")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def format_console(self) -> str:
        """Renders developer-readable ReAct cycle in terminal."""
        return (
            f"\n[Step {self.step_number}]"
            f"\n  THOUGHT:     {self.thought}"
            f"\n  ACTION:      {self.action}({self.action_input})"
            f"\n  OBSERVATION: {self.observation[:300]}"
            f"\n  STATUS:      {self.status}"
        )


class PendingHITLAction(BaseModel):
    """Sensitive transactional operation awaiting human cryptographic authorization."""
    action_id: str
    tool_name: str
    action_payload: Dict[str, Any]
    confirmation_token: str
    reason: str
    requires_clearance: str = "L2_RESTRICTED"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "PENDING_CONFIRMATION"  # PENDING_CONFIRMATION, APPROVED, REJECTED


class AgentState(BaseModel):
    """Persistent execution context for an autonomous field agent session."""
    session_id: str
    user_id: str
    objective: str
    department: str
    clearance: str
    steps: List[ThoughtActionObservationStep] = Field(default_factory=list)
    pending_hitl: Optional[PendingHITLAction] = None
    completed: bool = False
    final_output: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentExecutionTrace:
    """Formatted report summarizing agent thoughts, actions, and transactional mutations."""
    session_id: str
    objective: str
    steps: List[ThoughtActionObservationStep]
    completed: bool
    final_output: Optional[str] = None
    pending_hitl: Optional[PendingHITLAction] = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "objective": self.objective,
            "total_steps": len(self.steps),
            "completed": self.completed,
            "final_output": self.final_output,
            "pending_hitl": self.pending_hitl.model_dump() if self.pending_hitl else None,
            "execution_trace": [s.model_dump() for s in self.steps],
        }

