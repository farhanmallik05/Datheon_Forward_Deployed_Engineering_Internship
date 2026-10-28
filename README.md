# Datheon Forward Deployed Engineering (FDE) Platform
### Enterprise AI Integration, Multi-Tenant RBAC RAG, Autonomous ERP/CRM Agent & VPC Microservice

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Hardened%20VPC-2496ED.svg?logo=docker)](https://www.docker.com/)
[![Prometheus](https://img.shields.io/badge/Prometheus-Telemetry-E6522C.svg?logo=prometheus)](https://prometheus.io/)
[![Directorate Tests](https://img.shields.io/badge/3--Pass%20Audit-100%25%20Passing%20(21%2F21)-success.svg)](scripts/verify_all.py)

---

## 📌 Executive Overview

The **Datheon Forward Deployed Engineering (FDE) Platform** is an enterprise-grade AI integration system engineered to bridge messy, unstructured legacy corporate data with deterministic Large Language Models, autonomous business transaction agents, and private cloud Virtual Private Cloud (VPC) deployments.

This repository fulfills **all four tasks** outlined in the **Datheon Forward Deployed Engineering Internship Task Pack**:
1. **Task 1: Client Legacy Data Ingestion & Vector ETL Pipeline**
2. **Task 2: Enterprise Multi-Tenant RAG with Role-Based Access Control (RBAC)**
3. **Task 3: Autonomous Field Agent: Enterprise ERP/CRM Tool Orchestration**
4. **Task 4: Client VPC Deployment: Dockerized Microservice & Latency Benchmarks**

---

## 🏗️ Architecture & Component Topology

```
+-----------------------------------------------------------------------------------+
|                            CLIENT VPC PRIVATE ENVIRONMENT                         |
|                                                                                   |
|  +--------------------+        +---------------------+      +------------------+  |
|  |  Ingress Gateway / | -----> |  RBAC Security &    | ---> | Hardened FastAPI |  |
|  |   Reverse Proxy    |        |  Clearance Filter   |      |  Microservice    |  |
|  +--------------------+        +---------------------+      +--------+---------+  |
|                                                                      |            |
|       +------------------------------+-------------------------------+            |
|       |                              |                               |            |
|       v                              v                               v            |
|  +------------------+      +-------------------+           +-------------------+  |
|  |   TASK 1: ETL    |      |   TASK 2: RAG     |           |  TASK 3: FIELD    |  |
|  | Vector Pipeline  |      | Enterprise Engine |           | Autonomous Agent  |  |
|  | - PDF/CSV/MD Ext |      | - Query Rewriter  |           | - ReAct Planner   |  |
|  | - Semantic Chunk |      | - RBAC Retriever  |           | - Pydantic Valid  |  |
|  | - Lineage Meta   |      | - Cross-Encoder   |           | - ERP/CRM Tools   |  |
|  | - MiniLM Embed   |      | - Citation Guard  |           | - HITL HMAC Gate  |  |
|  +--------+---------+      +---------+---------+           +---------+---------+  |
|           |                          |                               |            |
|           +-----------------+--------+                               |            |
|                             |                                        v            |
|                             v                              +-------------------+  |
|                    +------------------+                    | Mock ERP/CRM ACID |  |
|                    | Vector Store     |                    | Store (SAP /      |  |
|                    | (Qdrant / Memory |                    | Salesforce Mock)  |  |
|                    | Cosine Index)    |                    +-------------------+  |
|                    +--------+---------+                                           |
|                             |                                                     |
|                             v                                                     |
|                    +------------------+                                           |
|                    | Prometheus       |                                           |
|                    | Telemetry Scrape |                                           |
|                    | (:8000/metrics)  |                                           |
|                    +------------------+                                           |
+-----------------------------------------------------------------------------------+
```

---

## 🚀 Tasks Breakdown & Deliverables

### Task 1: Client Legacy Data Ingestion & Vector ETL Pipeline
- **Multi-Format Extraction**: Custom extractors parsing corporate PDFs (`pypdf`), tabular accounting logs (`CSV`), and technical architecture specs (`Markdown` with YAML frontmatter).
- **Structure-Aware Chunking**: Preserves 1-indexed page numbers, CSV row indices, section headings, and department lineage.
- **Batch Vector Embeddings**: 384-dimensional dense semantic representations using `sentence-transformers/all-MiniLM-L6-v2` with LRU in-memory hashing cache and air-gapped VPC dense vector fallback.
- **Pluggable Vector Storage**: Normalized cosine index supporting both in-memory VPC execution and clustered Qdrant deployment.
- **Benchmark**: Ingests multi-format corpus at **47.05 chunks/second** (13.44 docs/second).

### Task 2: Multi-Tenant RAG with Role-Based Access Control (RBAC)
- **Tenant Isolation**: Strict departmental barriers separating `Finance`, `Engineering`, `HR`, and `Legal`.
- **Clearance Tiers**: Evaluates mathematical hierarchy (`L1_PUBLIC` $\subset$ `L2_RESTRICTED` $\subset$ `L3_CONFIDENTIAL`).
- **Contextual Query Rewriting**: Resolves conversational pronouns and supplements corporate domain terminology (`ASC 606`, `SOX 404`, `CIDR`, `Token Bucket`).
- **Cross-Encoder Precision Reranking**: Re-scores semantic passages using cross-attention alignment.
- **Anti-Hallucination Citation Guardrail**: Audits numerical entities and requires verifiable page citations (e.g. `[Source: Q3_Financial_Audit_Report.pdf, Page 1]`). Ungrounded claims are blocked or sanitized.

### Task 3: Autonomous Field Agent (Enterprise ERP/CRM Orchestration)
- **ReAct Reasoning Loop**: Displays step-by-step **Thought $\to$ Action $\to$ Observation** cycles.
- **Mock ERP/CRM Layer**: Transactional ACID JSON database simulating SAP inventory, Salesforce CRM deals, and ServiceNow ITSM tickets.
- **Self-Healing & Validation**: Pydantic v2 input schemas with exponential backoff retries (`with_retry`).
- **Human-In-The-Loop (HITL) Cryptographic Gate**: Sensitive transactions (purchase orders $\ge \$50,000$, lead closure, wire disbursements) trigger automated execution pause, generating a SHA-256 HMAC authorization token that requires officer sign-off via `/api/v1/agent/confirm-action`.

### Task 4: Client VPC Deployment & Telemetry
- **Hardened Dockerization**: Multi-stage build running under non-privileged system user (`datheon`, UID 10001).
- **Docker Compose VPC Stack**: Includes FastAPI service, Qdrant cluster, and Prometheus scraper over private bridge network `10.180.20.0/24`.
- **Health Probes**: Liveness (`/healthz`, `/livez`) and readiness (`/readyz`) probes.
- **Prometheus Telemetry**: Real-time metric series exposed at `/metrics` tracking request latency, token counts, error rates, and HITL queue size.
- **Latency Benchmark**: Median p50 RAG response of **83.06 ms** with 100% request success rate.

---

## 📊 Measured Benchmark Summary

Empirically validated via `scripts/run_etl_benchmark.py` and `scripts/run_latency_benchmark.py`:

| Component / Metric | Measured Performance | Success Rate | Notes |
| :--- | :---: | :---: | :--- |
| **ETL Ingestion Rate** | **47.05 chunks/sec** | 100% | 21 chunks in 0.4488s across 6 legacy files |
| **Filtered Vector Search** | **5.89 ms – 12.11 ms** | 100% | Cosine similarity with RBAC metadata filtering |
| **Liveness Probe (`/healthz`)** | **1.39 ms (p50)** | 100% | Kubernetes/ALB health check target |
| **Readiness Probe (`/readyz`)** | **1.51 ms (p50)** | 100% | Validates vector store and DB connectivity |
| **Mock ERP Query** | **1.65 ms (p50)** | 100% | Instantaneous inventory SKU lookup |
| **Autonomous Agent Turn** | **5.24 ms (p50)** | 100% | ReAct cycle execution time |
| **Prometheus Scrape (`/metrics`)** | **4.49 ms (p50)** | 100% | Sub-5ms exposition generation |
| **End-to-End RAG Query** | **83.06 ms (p50)** | 100% | Includes query rewrite, retrieval, rerank & guardrail |

---

## 🛠️ Installation & Quickstart

### Prerequisites
- Python 3.11, 3.12, or 3.13
- Git
- Docker & Docker Compose (for VPC container deployment)

### Local Environment Setup
```bash
# 1. Clone the repository
git clone https://github.com/your-username/Datheon_Forward_Deployed_Engineering_Internship.git
cd Datheon_Forward_Deployed_Engineering_Internship

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic corporate documents & mock ERP database
python scripts/generate_synthetic_data.py

# 4. Run the 3-Pass Master Verification Suite
python scripts/verify_all.py
```

### Docker VPC Deployment
```bash
# Launch hardened microservice, Qdrant vector database, and Prometheus scraper
docker compose up --build -d

# Verify container health
curl -f http://localhost:8000/healthz
curl -f http://localhost:8000/readyz

# Inspect Swagger OpenAPI Documentation
open http://localhost:8000/docs
```

---

## 💻 Interactive CLI Demonstrator

Run the real-time interactive terminal demonstrator to test RBAC RAG and Autonomous Agent workflows across different employee personas:

```bash
python scripts/interactive_cli.py
```

### Sample CLI Demonstration Session:
```text
======================================================================
  DATHEON ENTERPRISE FORWARD DEPLOYED ENGINEERING (FDE) CLI
======================================================================
Select Demo Persona:
  1. Alex Mercer     [Engineering | Clearance: L2_RESTRICTED]
  2. Sarah Jenkins   [Finance     | Clearance: L3_CONFIDENTIAL]
  3. David Chen      [HR          | Clearance: L3_CONFIDENTIAL]
  4. Junior Intern   [Cross-Func  | Clearance: L1_PUBLIC]
======================================================================

Select Action:
  [R] RAG Knowledge Query (RBAC & Citations)
  [A] Autonomous Agent Task (ERP/CRM Orchestration)
  [H] View / Approve Pending HITL Actions
  [Q] Quit
```

---

## 🧪 3-Pass Verification & Testing

The repository incorporates an automated 3-pass verification runner (`scripts/verify_all.py`):
```bash
python scripts/verify_all.py
```

- **Pass 1: Architecture & Extraction Audit**: Verifies PDF page numbers, CSV row tracking, Markdown frontmatter, semantic chunking, and mock ERP transactions (`8/8 passed`).
- **Pass 2: RBAC Boundaries & Guardrails Audit**: Audits department isolation, clearance enforcement, cross-encoder reranking, and citation anti-hallucination verification (`8/8 passed`).
- **Pass 3: End-to-End Service & Latency Benchmark**: Tests FastAPI endpoints, Prometheus metrics emission, and executes 170+ concurrent request latency benchmarks (`5/5 passed + 100% benchmark success`).

---

## 📚 Technical Documentation Directory

- [Architecture Deep-Dive & Topology](docs/ARCHITECTURE.md)
- [Enterprise Client Integration & VPC Manual](docs/CLIENT_INTEGRATION_GUIDE.md)
- [Performance & Latency Benchmark Report](docs/BENCHMARK_REPORT.md)
- [LinkedIn Demo Script & Walkthrough Guide](docs/LINKEDIN_DEMO_WALKTHROUGH.md)

---

## ⚖️ License & Accreditation

Developed for the **Datheon Forward Deployed Engineering (FDE) Internship**. Code licensed under the Apache 2.0 License.

