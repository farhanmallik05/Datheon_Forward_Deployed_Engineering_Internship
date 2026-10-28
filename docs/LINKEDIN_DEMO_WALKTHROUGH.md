# LinkedIn Project Walkthrough & Video Demonstration Guide
### Datheon Forward Deployed Engineering (FDE) Internship

---

## 1. LinkedIn Post Copy (Ready to Publish)

Copy and paste this post to LinkedIn upon pushing your repository. Be sure to tag **@Datheon** to qualify for top-tier Letter of Recommendation (LOR) review and verifiable QR credential issuance!

---

### [Copy Text Below]

🚀 Excited to announce the completion of the **Forward Deployed Engineering (FDE) Internship** with **@Datheon**!

As AI transitions from consumer chatbots to mission-critical enterprise environments, the real engineering challenge is bridging messy, legacy corporate data with deterministic Large Language Models, private cloud VPCs, and strict operational security.

Over this intensive engineering track, I architected and implemented all 4 production-grade tasks for enterprise deployment:

🔹 **Task 1: Legacy Data Ingestion & Vector ETL Pipeline**
Built a multi-format ingestion pipeline (PDFs, CSVs, Markdown) with semantic chunking and 100% metadata preservation (department tenancy, access tiers, and page lineage). Benchmarked at **47.05 chunks/second** indexing into cosine vector storage.

🔹 **Task 2: Multi-Tenant Enterprise RAG with Strict RBAC & Guardrails**
Engineered an isolated retrieval pipeline enforcing 3 clearance tiers (`L1_PUBLIC`, `L2_RESTRICTED`, `L3_CONFIDENTIAL`). Implemented domain query re-writing, Cross-Encoder reranking, and an anti-hallucination citation guardrail that verifies exact page citations (`[Source: Q3_Financial_Audit_Report.pdf, Page 1]`) and prevents cross-department data leaks.

🔹 **Task 3: Autonomous Field Agent (ERP/CRM Tool Orchestration)**
Constructed an autonomous function-calling agent displaying full Thought-Action-Observation cycles. Bound the agent to mock enterprise SAP/Salesforce/ServiceNow APIs with Pydantic validation loops and exponential backoff retries. Implemented a **Human-In-The-Loop (HITL)** cryptographic HMAC confirmation gate before high-value write operations (e.g., purchase orders $\ge \$50,000$).

🔹 **Task 4: Hardened Client VPC Deployment & Telemetry**
Containerized the platform into a hardened Docker microservice with non-root security contexts (`UID 10001`), Docker Compose bridge networking (`10.180.20.0/24`), `/healthz` & `/readyz` probes, and live Prometheus metric collectors at `/metrics` (p50 query latency of **83.06 ms**).

✅ Verified with a **3-Pass automated test suite** (21/21 passing tests covering unit logic, negative security boundary audits, and end-to-end latency benchmarks).

📂 **Public GitHub Repository**: https://github.com/farhanmallik05/Datheon_Forward_Deployed_Engineering_Internship
🌐 **Live Interactive Showcase**: https://datheon-fde-platform.netlify.app
🎥 **Live Video Walkthrough**: [Link to your Loom / YouTube demo (Optional)]

Huge thanks to the **@Datheon** Directorate team for designing a curriculum that reflects real-world Forward Deployed Engineering at tier-one enterprise tech companies!

#Datheon #ForwardDeployedEngineer #EnterpriseAI #RAG #AIArchitecture #Docker #FastAPI #MachineLearning #SystemDesign #OpenSource #VPC

---

## 2. Video Demonstration Script (3-5 Minutes)

Use this script when recording your screen (via Loom, OBS, or QuickTime):

### Scene 1: Introduction (0:00 - 0:45)
- **Visual**: Show GitHub repository README and `docs/ARCHITECTURE.md`.
- **Talking Points**:
  - "Hello! Today I'm presenting my Forward Deployed Engineering project for Datheon. Forward deployed engineers turn foundational AI models into robust, secure, and operational client solutions."
  - "I've completed all four tasks: the Vector ETL pipeline, the multi-tenant RBAC RAG service with citation verification, the autonomous ERP/CRM tool agent with Human-in-the-Loop gating, and the containerized VPC microservice with Prometheus telemetry."

### Scene 2: Task 1 - Vector ETL Pipeline (0:45 - 1:30)
- **Visual**: Run `python scripts/run_etl_benchmark.py` in your terminal.
- **Talking Points**:
  - "Here in Task 1, our ETL pipeline ingests unstructured legacy files—multi-page PDF audit reports, CSV vendor invoices, and Markdown architecture specs."
  - "Notice how the batch ingestion completes in 0.45 seconds at over 47 chunks per second, maintaining full metadata lineage including department tenancy, access tier, and 1-indexed page citations."

### Scene 3: Task 2 & Task 3 - Interactive CLI Demo (1:30 - 3:00)
- **Visual**: Launch `python scripts/interactive_cli.py`.
- **Step A: RAG with Clearance Enforcement**:
  - Select Persona 1 (Alex Mercer - Engineering L2).
  - Search: *"What is the token bucket rate limit?"* $\to$ Shows answer with exact citation `[Source: api_rate_limiting_spec.md, Section 2]`.
  - Try searching for Finance audit margins $\to$ Shows `Access Denied: Zero documents in your clearance boundary`.
  - Switch to Persona 2 (Sarah Jenkins - Finance L3) $\to$ Shows revenue answer citing `[Source: Q3_Financial_Audit_Report.pdf, Page 1]`.
- **Step B: Autonomous Field Agent & HITL**:
  - Enter Agent Task: *"Check inventory for SKU-H100-80G and order $145,000 from NVIDIA Cloud Compute."*
  - Point out the terminal displaying **Thought $\to$ Action $\to$ Observation**.
  - Show how the agent executes the inventory check, but when it attempts the $145,000 purchase order, the **Human-in-the-Loop (HITL)** security gate halts execution!
  - Point out the generated cryptographic HMAC confirmation token.
  - Switch to Action [H] in CLI and authorize the pending action with the token $\to$ Show transaction mutation executed with audit log entry.

### Scene 4: Task 4 - Hardened Microservice & Prometheus Telemetry (3:00 - 4:00)
- **Visual**: Show Docker Compose configuration, FastAPI Swagger UI at `http://localhost:8000/docs`, and `/metrics` endpoint.
- **Talking Points**:
  - "The service is hardened for private VPC subnets with health probes at `/healthz` and `/readyz`."
  - "At `/metrics`, Prometheus scrapes real-time counters and latency histograms for HTTP traffic, RAG queries, and agent tool executions."

### Scene 5: 3-Pass Verification & Conclusion (4:00 - 4:30)
- **Visual**: Run `python scripts/verify_all.py` showing all 3 passes passing.
- **Talking Points**:
  - "Finally, our 3-pass verification suite audits architecture unit tests, security boundary negative tests, and latency benchmarks in under 95 seconds with 100% pass rates."
  - "Thank you to the Datheon Technical Directorate for this challenge!"

