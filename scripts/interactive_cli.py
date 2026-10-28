"""Interactive Enterprise CLI for live testing of Datheon FDE features.

Allows forward deployed engineers and client evaluators to interactively
execute RBAC RAG searches, trigger autonomous agent tools, and inspect HITL approvals.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.core.config import ClearanceTier, Department
from src.core.security import EnterpriseUser
from src.agent.engine import AutonomousEnterpriseAgent
from src.agent.hitl import HumanInTheLoopManager
from src.rag.engine import EnterpriseRAGEngine


def interactive_session():
    print("=" * 70)
    print("  DATHEON ENTERPRISE FORWARD DEPLOYED ENGINEERING (FDE) CLI")
    print("=" * 70)
    print("Select Demo Persona:")
    print("  1. Alex Mercer     [Engineering | Clearance: L2_RESTRICTED]")
    print("  2. Sarah Jenkins   [Finance     | Clearance: L3_CONFIDENTIAL]")
    print("  3. David Chen      [HR          | Clearance: L3_CONFIDENTIAL]")
    print("  4. Junior Intern   [Cross-Func  | Clearance: L1_PUBLIC]")
    print("=" * 70)

    choice = input("Enter persona choice (1-4, default 1): ").strip() or "1"
    personas = {
        "1": EnterpriseUser(user_id="USR-ENG-4401", name="Alex Mercer", department=Department.ENGINEERING, clearance=ClearanceTier.L2_RESTRICTED),
        "2": EnterpriseUser(user_id="USR-FIN-9901", name="Sarah Jenkins", department=Department.FINANCE, clearance=ClearanceTier.L3_CONFIDENTIAL),
        "3": EnterpriseUser(user_id="USR-HR-2010", name="David Chen", department=Department.HR, clearance=ClearanceTier.L3_CONFIDENTIAL),
        "4": EnterpriseUser(user_id="USR-PUB-0012", name="Junior Intern", department=Department.CROSS_FUNCTIONAL, clearance=ClearanceTier.L1_PUBLIC),
    }
    user = personas.get(choice, personas["1"])
    print(f"\n[+] Authenticated as: {user.name} ({user.user_id})")
    print(f"    Department: {user.department.value.upper()} | Clearance: {user.clearance.value}")

    rag = EnterpriseRAGEngine()
    agent = AutonomousEnterpriseAgent()
    hitl = HumanInTheLoopManager.get_instance()

    while True:
        print("\n" + "-" * 70)
        print("Select Action:")
        print("  [R] RAG Knowledge Query (RBAC & Citations)")
        print("  [A] Autonomous Agent Task (ERP/CRM Orchestration)")
        print("  [H] View / Approve Pending HITL Actions")
        print("  [Q] Quit")
        action = input("Select [R/A/H/Q]: ").strip().upper()

        if action == "Q":
            print("Exiting Datheon FDE CLI. Goodbye.")
            break

        elif action == "R":
            query = input("\nEnter enterprise search query: ").strip()
            if not query:
                continue
            print(f"\n[*] Executing RAG retrieval for clearance {user.clearance.value}...")
            resp = rag.query(user=user, query_text=query)
            print("\n[ANSWER]:")
            print(resp.answer)
            print(f"\n[METRICS]: Latency: {resp.latency_ms:.2f} ms | Groundedness: {resp.groundedness_score*100:.1f}% | Chunks: {resp.chunks_retrieved}")
            if resp.citations:
                print("\n[VERIFIED CITATIONS]:")
                for c in resp.citations:
                    print(f"  * {c['citation_tag']}")
                    print(f"    Excerpt: \"{c['excerpt']}\"")

        elif action == "A":
            prompt = input("\nEnter agent objective/command: ").strip()
            if not prompt:
                continue
            print("\n[*] Initializing autonomous agent Thought-Action-Observation cycle...")
            result = agent.run(user=user, objective=prompt)
            print(f"\n[AGENT STATUS]: {result.status}")
            print("\n[REASONING TRACE]:")
            for step in result.steps:
                print(step.format_console())
            print("\n[FINAL OUTCOME]:")
            print(result.final_output)

        elif action == "H":
            pending = hitl.list_pending_actions()
            print(f"\n[*] Pending HITL Actions in Queue: {len(pending)}")
            for item in pending:
                print(f"\n  Action ID: {item['action_id']} | Tool: {item['tool_name']}")
                print(f"  Reason:    {item['reason']}")
                print(f"  Token:     {item['confirmation_token']}")
                print(f"  Payload:   {item['action_payload']}")

            if pending:
                act_id = input("\nEnter Action ID to resolve (or enter to cancel): ").strip()
                if act_id:
                    matched = [p for p in pending if p["action_id"] == act_id]
                    if matched:
                        token = matched[0]["confirmation_token"]
                        verdict = input("Approve action? [Y/N]: ").strip().upper() == "Y"
                        res = hitl.confirm_action(action_id=act_id, token=token, approver=user, approved=verdict)
                        print("\n[RESOLUTION RESULT]:", json.dumps(res, indent=2))
                    else:
                        print("Invalid Action ID.")


if __name__ == "__main__":
    interactive_session()
