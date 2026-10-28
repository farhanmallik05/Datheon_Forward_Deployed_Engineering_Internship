# Datheon Enterprise Forward Deployed Engineering (FDE) Platform
## System Architecture & Technical Specification

---

## 1. Executive Architectural Overview

The **Datheon Enterprise FDE Platform** bridges legacy corporate unstructured repositories, structured ERP/CRM data stores, and private cloud VPC environments with secure, tenant-isolated Large Language Model (LLM) intelligence.

Built according to production-grade Forward Deployed Engineering standards, the platform enforces strict data boundaries, cryptographic transaction authorization, verifiable page citations, and sub-millisecond telemetry observability.

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT VPC PERIMETER                             |
|                                                                                   |
|  +--------------------+        +---------------------+      +------------------+  |
|  |  Ingress ALB / API | -----> |  RBAC Security &    | ---> | Hardened FastAPI |  |
|  |     Gateway        |        |  Clearance Filter   |      |  Microservice    |  |
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
|                    | Telemetry Metric |                                           |
|                    | Collector (:8000)|                                           |
|                    +------------------+                                           |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Pillars

### Pillar I: Multi-Format Vector ETL Pipeline (Task 1)
- **Extraction Layer**:
  - `PDFExtractor`: Extracts pages via `pypdf`, preserving exact 1-indexed page numbers, headers, and clearance classifications.
  - `CSVExtractor`: Serializes enterprise tabular logs into descriptive semantic records while preserving row indices, PO numbers, and departmental accounts.
  - `MarkdownExtractor`: Parses YAML frontmatter (`document_id`, `department`, `clearance`, `author`, `date`) and splits along heading hierarchies.
- **Semantic Chunking**: Structure-aware token windowing that splits along sentence and paragraph boundaries, maintaining metadata lineage (`doc_id`, `page_number`, `row_number`, `department`, `clearance`).
- **Dense Vector Embedding**: 384-dimensional dense semantic vectors using `sentence-transformers/all-MiniLM-L6-v2` with LRU in-memory hashing cache and air-gapped VPC dense vector fallback.
- **Pluggable Vector Store**:
  - `InMemoryCosineVectorStore`: Zero-dependency, sub-millisecond normalized cosine vector store with strict pre/post filtering.
  - `QdrantVectorStore`: Cluster-grade vector storage with payload indices on `department` and `clearance`.

---

### Pillar II: Multi-Tenant RBAC RAG with Verifiable Citations (Task 2)
- **Contextual Query Rewriter**: Expands raw inquiries with enterprise domain synonyms (`ASC 606`, `SOX 404`, `CIDR`, `mTLS`, `Token Bucket`), infers departmental intent, and resolves conversational pronouns.
- **RBAC Retriever**:
  - Dual-layer defense-in-depth: Enforces clearance and tenancy filters at the vector query level, followed by post-retrieval verification.
  - Clearance hierarchy: `L1_PUBLIC` $\subset$ `L2_RESTRICTED` $\subset$ `L3_CONFIDENTIAL`.
  - Zero cross-tenant leakage between `Finance`, `Engineering`, `HR`, and `Legal`.
- **Cross-Encoder Reranker**: Computes query-passage alignment scores using cross-attention or lexical-semantic ranking to filter out low-relevance candidates.
- **Anti-Hallucination Citation Guardrail**:
  - Extracts numeric and monetary entities (`$48.6M`, `24.8%`, `500 req/min`).
  - Verifies factual ground truth against retrieved passage text.
  - Validates exact page citations (`[Source: filename.pdf, Page X]`) and row citations (`[Source: filename.csv, Row Y]`).
  - Blocks ungrounded statements or injects human-auditable guardrail notices when groundedness falls below threshold (0.70).

---

### Pillar III: Autonomous Field Agent & HITL Orchestration (Task 3)
- **ReAct Execution Engine**: Implements the Thought $\to$ Action $\to$ Observation reasoning loop.
- **Mock ERP/CRM Transactional Layer**: Thread-safe ACID JSON store simulating SAP ERP, Salesforce CRM, and ServiceNow ITSM.
- **Tool Validation & Self-Healing**:
  - All payloads validated with Pydantic v2 schemas (`InventoryLookupSchema`, `LeadStatusUpdateSchema`, `TicketCreateSchema`, `PurchaseOrderCreateSchema`).
  - Transient API failures retried using exponential backoff with jitter (`with_retry`, max 3 attempts).
- **Human-In-The-Loop (HITL) Cryptographic Gate**:
  - High-impact mutations (purchase orders $\ge \$50,000$, lead stage changes to `CLOSED_WON` or `CLOSED_LOST`, wire disbursements) are automatically paused.
  - Computes a SHA-256 HMAC token over `action_id` and canonical payload.
  - Pauses execution and queues the action in `PendingApprovalQueue`.
  - Releases execution only upon secondary officer cryptographic verification via `/api/v1/agent/confirm-action`.

---

### Pillar IV: VPC Hardened Microservice & Prometheus Telemetry (Task 4)
- **FastAPI Core**: Async, non-blocking REST endpoints with automated OpenAPI documentation (`/docs`, `/redoc`).
- **Container Hardening**:
  - Multi-stage Docker build running under non-privileged system user (`datheon`, UID 10001).
  - Health and readiness probes (`/healthz`, `/readyz`, `/livez`).
  - Resource constraints (2.0 CPU, 4GB RAM) and internal VPC bridge network (`10.180.20.0/24`).
- **Telemetry & Observability**:
  - Custom Prometheus metrics exposed at `/metrics`:
    - `datheon_http_requests_total`
    - `datheon_http_request_duration_seconds`
    - `datheon_etl_documents_total`
    - `datheon_etl_chunks_total`
    - `datheon_rag_query_duration_seconds`
    - `datheon_rag_guardrail_blocked_total`
    - `datheon_agent_tool_calls_total`
    - `datheon_agent_hitl_pending_actions`

