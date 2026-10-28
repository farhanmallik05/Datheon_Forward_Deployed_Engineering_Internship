# Datheon Enterprise FDE Platform: Performance & Latency Benchmark Report
### Directorate Evaluation Verification Data

---

## 1. Executive Summary

This report presents empirical performance measurements collected from the automated benchmark suite (`scripts/run_etl_benchmark.py` and `scripts/run_latency_benchmark.py`) on the Datheon Enterprise Forward Deployed Engineering (FDE) platform.

All four assignments from the internship syllabus were evaluated under enterprise load conditions:
- **Task 1: ETL Pipeline Ingestion Rate**: **47.05 chunks/second** (13.44 documents/second).
- **Task 2: RBAC Retrieval Latency**: **5.89 ms – 12.11 ms** per filtered query.
- **Task 3: Autonomous Agent Tool Cycle Latency**: **5.24 ms** median (p50).
- **Task 4: Microservice End-to-End RAG Query**: **83.06 ms** median (p50) with 100% request success rate.

---

## 2. Task 1: Vector ETL Pipeline Batch Ingestion

### Ingestion Throughput & Token Volume
- **Total Documents Ingested**: 6 corporate files (PDFs, CSVs, Markdown)
- **Total Semantic Chunks Created**: 21 chunks
- **Total Word Tokens Processed**: 1,185 tokens
- **Batch Processing Elapsed Time**: **0.4488 seconds**
- **Throughput (Chunks)**: **47.05 chunks/second**
- **Throughput (Documents)**: **13.44 documents/second**

### Corpus Tenancy & Clearance Distribution
```
Department Breakdown:
  - ENGINEERING    : 11 chunks (52.4%)
  - FINANCE        : 5 chunks (23.8%)
  - HR             : 3 chunks (14.3%)
  - LEGAL          : 2 chunks (9.5%)

Clearance Classification Breakdown:
  - L1_PUBLIC      : 4 chunks (19.0%)
  - L2_RESTRICTED  : 10 chunks (47.6%)
  - L3_CONFIDENTIAL: 7 chunks (33.3%)
```

### Retrieval Latency by Department
| Query Target | Department | Clearance | Retrieval Latency | Cosine Score | Ground Truth Matched |
| :--- | :--- | :--- | :---: | :---: | :---: |
| Q3 Consolidated Revenue | Finance | `L3_CONFIDENTIAL` | **12.11 ms** | 0.6363 | **PASS** (`$48.6M`) |
| Token Bucket Rate Limits | Engineering | `L1_PUBLIC` | **8.40 ms** | 0.7128 | **PASS** (`500 req/min`) |
| Executive Bonus Multiplier | HR | `L3_CONFIDENTIAL` | **6.40 ms** | 0.5537 | **PASS** (`35% ARR`) |
| Trade Secret Terms | Legal | `L2_RESTRICTED` | **5.89 ms** | 0.6023 | **PASS** (`5 years`) |

---

## 3. Task 4: Microservice Latency & VPC Telemetry

Measurements obtained over repeated test client cycles simulating concurrent VPC traffic.

| Endpoint | Method | Iterations | Success Rate | p50 (ms) | p90 (ms) | p95 (ms) | p99 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `/healthz` (Liveness) | GET | 50 | 100.0% | **1.39 ms** | 1.98 ms | 2.16 ms | 2.93 ms |
| `/readyz` (VPC Readiness) | GET | 30 | 100.0% | **1.51 ms** | 2.28 ms | 2.58 ms | 2.91 ms |
| `/api/v1/erp/inventory/{sku}` | GET | 40 | 100.0% | **1.65 ms** | 2.50 ms | 2.71 ms | 2.75 ms |
| `/api/v1/agent/chat` | POST | 10 | 100.0% | **5.24 ms** | 17.85 ms | 17.85 ms | 17.85 ms |
| `/metrics` (Prometheus) | GET | 25 | 100.0% | **4.49 ms** | 4.84 ms | 5.06 ms | 5.94 ms |
| `/api/v1/rag/query` | POST | 15 | 100.0% | **83.06 ms** | 95.62 ms | 4,730 ms* | 4,730 ms* |

*\*Note: p95/p99 on the first RAG query includes one-time cold-start model weight loading into GPU/CPU memory; all warm subsequent queries execute in 64ms – 95ms.*

---

## 4. Security & Isolation Verification Evidence

The negative test matrix (`tests/test_security_leakage.py`) executed cross-tenant penetration tests:
1. **Clearance Barrier Audit**: An `L1_PUBLIC` principal querying for `L3_CONFIDENTIAL` financial audit reports received **0 leaked documents** (100% blocked).
2. **Department Isolation Audit**: An `ENGINEERING` engineer with `L3` clearance querying for `HR` executive payroll was restricted strictly to the engineering domain.
3. **HITL Tampering Audit**: Submitting a forged or modified HMAC token for sensitive purchase orders resulted in an immediate `400 Bad Request` rejection with cryptographic error alert.
4. **Unauthorized Approval Audit**: An `L1` user attempting to approve an executive purchase order was blocked with `403 Forbidden` (`RBACAccessDeniedError`).
