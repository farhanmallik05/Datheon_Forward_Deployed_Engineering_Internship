"""Automated Vector ETL Pipeline Batch Ingestion Benchmark.

Evaluates multi-format document extraction, semantic chunk distribution,
embedding latency, vector indexing throughput, and metadata filtering accuracy.
Outputs results to docs/ETL_BENCHMARK_RESULTS.json.
"""
import json
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
from src.core.config import ClearanceTier, Department, get_settings
from src.core.logger import get_logger
from src.etl.embedder import EnterpriseEmbedder
from src.etl.pipeline import VectorETLPipeline
from src.etl.vector_store import InMemoryCosineVectorStore
RAW_DIR = BASE_DIR / "data" / "raw"
DOCS_DIR = BASE_DIR / "docs"


def run_benchmark():
    print("=" * 70)
    print("  DATHEON ENTERPRISE FDE PLATFORM: TASK 1 VECTOR ETL BENCHMARK")
    print("=" * 70)

    settings = get_settings()
    store = InMemoryCosineVectorStore(dimension=settings.VECTOR_DIMENSION)
    embedder = EnterpriseEmbedder()
    pipeline = VectorETLPipeline(vector_store=store, embedder=embedder)

    # 1. Measure Directory Ingestion
    start_ts = time.perf_counter()
    report = pipeline.ingest_directory(RAW_DIR, recursive=True, batch_size=16)
    total_elapsed = time.perf_counter() - start_ts

    print(f"\n[+] Ingestion Complete in {total_elapsed:.4f} seconds")
    print(f"    - Documents Processed: {report.total_documents}")
    print(f"    - Semantic Chunks:     {report.total_chunks}")
    print(f"    - Total Word Tokens:   {report.total_tokens}")
    print(f"    - Ingestion Rate:      {report.throughput_chunks_per_sec:.2f} chunks/sec")
    print(f"    - Indexed Vectors:     {store.count()}")

    print("\n[-] Department Distribution:")
    for dept, count in report.department_counts.items():
        print(f"    * {dept.upper():<16}: {count} chunks")

    print("\n[-] Clearance Tier Distribution:")
    for tier, count in report.clearance_counts.items():
        print(f"    * {tier:<16}: {count} chunks")

    # 2. Metadata Filtering Verification Benchmark
    print("\n[+] Evaluating Metadata-Filtered Vector Retrieval Latency & Boundary...")
    queries = [
        {
            "query": "What was Datheon Q3 consolidated revenue and cloud infrastructure expenditure?",
            "dept": Department.FINANCE,
            "clearance": ClearanceTier.L3_CONFIDENTIAL,
            "expected_keyword": "$48.6M",
        },
        {
            "query": "What is the token bucket rate limit for Tier L1 and Tier L2 users?",
            "dept": Department.ENGINEERING,
            "clearance": ClearanceTier.L1_PUBLIC,
            "expected_keyword": "500 requests",
        },
        {
            "query": "What is the executive bonus multiplier for Band E1 and Band E2?",
            "dept": Department.HR,
            "clearance": ClearanceTier.L3_CONFIDENTIAL,
            "expected_keyword": "35%",
        },
        {
            "query": "What is the duration of trade secret confidentiality under the mutual NDA?",
            "dept": Department.LEGAL,
            "clearance": ClearanceTier.L2_RESTRICTED,
            "expected_keyword": "five (5) years",
        },
    ]

    retrieval_benchmarks = []
    for test in queries:
        t0 = time.perf_counter()
        query_vec = embedder.embed_query(test["query"])
        results = store.search(
            query_vector=query_vec,
            top_k=3,
            department_filter=test["dept"],
            clearance_filter=test["clearance"],
        )
        t_query = (time.perf_counter() - t0) * 1000.0  # ms

        found = any(test["expected_keyword"].lower() in r.text.lower() for r in results)
        retrieval_benchmarks.append({
            "query": test["query"],
            "department": test["dept"].value,
            "clearance": test["clearance"].value,
            "latency_ms": round(t_query, 3),
            "top_k_returned": len(results),
            "ground_truth_matched": found,
            "top_score": round(results[0].score, 4) if results else 0.0,
        })
        status_flag = "[PASS]" if found else "[WARN]"
        print(f"    {status_flag} Dept: {test['dept'].value.upper():<11} | Latency: {t_query:6.2f} ms | Score: {retrieval_benchmarks[-1]['top_score']:.4f} | Matched: {found}")

    # 3. Security Boundary Negative Test (L1 user querying L3 Confidential)
    print("\n[+] Security Clearance Negative Test: L1 Principal querying L3 Finance Report...")
    l1_query_vec = embedder.embed_query("Executive severance schedules and Q3 audit margin")
    l1_results = store.search(
        query_vector=l1_query_vec,
        top_k=5,
        department_filter=Department.FINANCE,
        clearance_filter=ClearanceTier.L1_PUBLIC,  # L1 restricted filter
    )
    # Ensure zero L3 documents leaked
    l3_leaks = [r for r in l1_results if r.metadata.clearance == ClearanceTier.L3_CONFIDENTIAL]
    print(f"    [CHECK] L3 documents retrieved by L1 user: {len(l3_leaks)} (Expected: 0)")
    assert len(l3_leaks) == 0, "Security isolation breach: L3 document returned to L1 clearance user!"

    # Compile Benchmark Summary
    summary = {
        "benchmark_timestamp": "2026-10-28T18:47:00Z",
        "pipeline": {
            "documents_ingested": report.total_documents,
            "chunks_created": report.total_chunks,
            "total_tokens": report.total_tokens,
            "ingestion_duration_sec": round(total_elapsed, 4),
            "chunks_per_sec": round(report.throughput_chunks_per_sec, 2),
            "docs_per_sec": round(report.throughput_docs_per_sec, 2),
        },
        "department_distribution": report.department_counts,
        "clearance_distribution": report.clearance_counts,
        "retrieval_latencies": retrieval_benchmarks,
        "security_isolation_verified": (len(l3_leaks) == 0),
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    bench_file = DOCS_DIR / "ETL_BENCHMARK_RESULTS.json"
    with open(bench_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[+] Detailed benchmark metrics saved to: {bench_file}")
    print("=" * 70)
    return summary


if __name__ == "__main__":
    run_benchmark()
