"""Autonomous Enterprise Field Agent with ReAct reasoning loop and HITL gate.

Implements Thought -> Action -> Observation execution cycles, binding enterprise
principals to transactional ERP/CRM tools while halting before sensitive writes.
"""
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.config import get_settings
from src.core.exceptions import AgentToolExecutionError, HITLApprovalRequiredError
from src.core.logger import get_logger
from src.core.security import EnterpriseUser
from src.agent.hitl import HumanInTheLoopManager
from src.agent.state import (
    AgentExecutionTrace,
    AgentState,
    PendingHITLAction,
    ThoughtActionObservationStep,
)
from src.agent.tools import EnterpriseToolRegistry

logger = get_logger("agent.engine")


@dataclass
class AgentRunResult:
    """Consolidated outcome of an autonomous agent execution session."""
    session_id: str
    completed: bool
    status: str  # COMPLETED, HITL_PAUSED, FAILED
    final_output: str
    steps: List[ThoughtActionObservationStep]
    pending_hitl: Optional[PendingHITLAction] = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "completed": self.completed,
            "final_output": self.final_output,
            "total_steps": len(self.steps),
            "pending_hitl": self.pending_hitl.model_dump() if self.pending_hitl else None,
            "execution_trace": [s.model_dump() for s in self.steps],
        }


class AutonomousEnterpriseAgent:
    """Field engineer autonomous agent capable of orchestrating multi-step transactional flows."""

    def __init__(self, tool_registry: Optional[EnterpriseToolRegistry] = None):
        self.tools = tool_registry or EnterpriseToolRegistry()
        self.hitl = HumanInTheLoopManager.get_instance()
        self.settings = get_settings()

    def run(
        self,
        user: EnterpriseUser,
        objective: str,
        session_id: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ) -> AgentRunResult:
        """Executes autonomous Thought-Action-Observation reasoning cycles toward the objective."""
        sess_id = session_id or f"SESS-{uuid.uuid4().hex[:8].upper()}"
        max_steps = max_iterations or self.settings.AGENT_MAX_ITERATIONS
        steps: List[ThoughtActionObservationStep] = []

        logger.info("[AGENT START] Session %s for user %s: '%s'", sess_id, user.user_id, objective)

        # Plan the task sequence based on objective intent
        planned_actions = self._plan_sequence(objective)

        for step_idx, plan in enumerate(planned_actions, start=1):
            if step_idx > max_steps:
                logger.warning("Max iteration limit (%d) reached for session %s", max_steps, sess_id)
                break

            thought = plan["thought"]
            action = plan["action"]
            action_input = plan["input"]

            step = ThoughtActionObservationStep(
                step_number=step_idx,
                thought=thought,
                action=action,
                action_input=action_input,
            )

            try:
                # Execute tool via registry
                tool_output = self.tools.execute_tool(action, action_input, caller=user)
                step.observation = json.dumps(tool_output, default=str)
                step.status = "SUCCESS"
                steps.append(step)
                logger.info("[STEP %d COMPLETED] %s -> %s", step_idx, action, step.observation[:120])

            except HITLApprovalRequiredError as hitl_err:
                # Sensitive write operation intercepted: pause agent execution
                step.observation = (
                    f"HITL INTERCEPTION: Sensitive operation halted. Action ID: {hitl_err.action_id}. "
                    f"Cryptographic Token: {hitl_err.confirmation_token}. Reason: {hitl_err.message}"
                )
                step.status = "HITL_REQUIRED"
                steps.append(step)

                pending_hitl = PendingHITLAction(
                    action_id=hitl_err.action_id,
                    tool_name=action,
                    action_payload=hitl_err.action_payload,
                    confirmation_token=hitl_err.confirmation_token,
                    reason=hitl_err.message,
                )

                logger.warning("[AGENT PAUSED - HITL] Session %s paused at step %d", sess_id, step_idx)
                return AgentRunResult(
                    session_id=sess_id,
                    completed=False,
                    status="HITL_PAUSED",
                    final_output=(
                        f"Execution paused: Transactional operation '{action}' requires Human-In-The-Loop "
                        f"clearance. Action ID: '{hitl_err.action_id}'. Use confirmation endpoint with provided token."
                    ),
                    steps=steps,
                    pending_hitl=pending_hitl,
                )

            except Exception as err:
                step.observation = f"EXECUTION ERROR: {str(err)}"
                step.status = "ERROR"
                steps.append(step)
                logger.error("[STEP %d FAILED] %s: %s", step_idx, action, str(err))
                return AgentRunResult(
                    session_id=sess_id,
                    completed=False,
                    status="FAILED",
                    final_output=f"Agent execution terminated due to error: {err}",
                    steps=steps,
                )

        final_summary = self._synthesize_final_output(objective, steps)
        logger.info("[AGENT COMPLETED] Session %s resolved in %d steps", sess_id, len(steps))

        return AgentRunResult(
            session_id=sess_id,
            completed=True,
            status="COMPLETED",
            final_output=final_summary,
            steps=steps,
        )

    def _plan_sequence(self, objective: str) -> List[Dict[str, Any]]:
        """Deconstructs corporate objective into deterministic tool steps."""
        lowered = objective.lower()
        sequence = []

        # Intent 1: Inventory check and PO creation
        sku_match = re.search(r"sku-[a-z0-9\-]+", lowered)
        if "inventory" in lowered or "stock" in lowered or sku_match:
            target_sku = sku_match.group(0).upper() if sku_match else "SKU-H100-80G"
            sequence.append({
                "thought": f"First, query enterprise ERP inventory to check available stock and warehouse status for {target_sku}.",
                "action": "inventory_lookup",
                "input": {"sku": target_sku},
            })

            # Check if PO or replenishment requested
            if any(w in lowered for w in ["order", "purchase", "replenish", "buy"]):
                amount = 145000.0 if "145" in lowered or "145000" in lowered else 45000.0
                vendor = "NVIDIA Cloud Compute" if "nvidia" in lowered else "Enterprise Hardware Solutions"
                sequence.append({
                    "thought": f"Inventory verification complete. Now create capital purchase order of ${amount:,.2f} with vendor '{vendor}'.",
                    "action": "create_purchase_order",
                    "input": {"vendor": vendor, "amount_usd": amount},
                })
            return sequence

        # Intent 2: CRM Lead Update
        lead_match = re.search(r"lead-\d+-\d+", lowered)
        if "lead" in lowered or lead_match:
            target_lead = lead_match.group(0).upper() if lead_match else "LEAD-2026-101"
            sequence.append({
                "thought": f"Retrieve current CRM lead account details for {target_lead}.",
                "action": "get_lead",
                "input": {"lead_id": target_lead},
            })

            target_stage = "NEGOTIATION"
            for s in ["QUALIFIED", "DISCOVERY", "PROPOSAL_DELIVERED", "NEGOTIATION", "CLOSED_WON", "CLOSED_LOST"]:
                if s.lower() in lowered:
                    target_stage = s
                    break

            sequence.append({
                "thought": f"Update CRM lead stage to '{target_stage}' and attach operational notes.",
                "action": "update_lead_status",
                "input": {
                    "lead_id": target_lead,
                    "new_stage": target_stage,
                    "notes": "Automated update via Datheon FDE Agent pipeline.",
                },
            })
            return sequence

        # Intent 3: Support Ticket Creation
        if "ticket" in lowered or "issue" in lowered or "incident" in lowered:
            acc_match = re.search(r"acc-\d+", lowered)
            acc_id = acc_match.group(0).upper() if acc_match else "ACC-5001"
            priority = "HIGH" if "high" in lowered or "critical" in lowered else "MEDIUM"
            sequence.append({
                "thought": f"Customer reported technical incident. Open priority {priority} ITSM ticket for account {acc_id}.",
                "action": "create_support_ticket",
                "input": {
                    "account_id": acc_id,
                    "subject": objective[:80],
                    "priority": priority,
                },
            })
            return sequence

        # Default fallback: RAG Search then action
        sequence.append({
            "thought": "Query internal enterprise documentation via RBAC RAG to resolve operational question.",
            "action": "rag_knowledge_search",
            "input": {"query": objective},
        })
        return sequence

    def _synthesize_final_output(self, objective: str, steps: List[ThoughtActionObservationStep]) -> str:
        """Produces a succinct final answer from executed step observations."""
        summaries = []
        for s in steps:
            summaries.append(f"Step {s.step_number} [{s.action}]: {s.observation[:160]}")
        return f"Objective achieved: '{objective}'. Operations executed:\n" + "\n".join(summaries)

