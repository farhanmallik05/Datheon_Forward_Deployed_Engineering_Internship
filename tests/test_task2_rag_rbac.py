"""Unit and integration tests for Task 2: Enterprise Multi-Tenant RAG with RBAC."""
import pytest
from src.core.config import ClearanceTier, Department
from src.rag.engine import EnterpriseRAGEngine
from src.rag.guardrails import HallucinationGuardrail
from src.rag.query_rewriter import EnterpriseQueryRewriter
from src.rag.rbac_retriever import RBACRetriever, RetrievedChunk
from src.rag.reranker import CrossEncoderReranker


def test_query_rewriter_domain_expansion():
    rewriter = EnterpriseQueryRewriter()
    res = rewriter.rewrite("What is the Q3 revenue guidance?")
    assert "revenue" in res.expanded_query.lower()
    assert res.inferred_department == Department.FINANCE
    assert "ASC 606" in res.expanded_query or "margin" in res.expanded_query


def test_rbac_clearance_enforcement(vector_store, embedder, user_pub_l1, user_fin_l3):
    retriever = RBACRetriever(vector_store=vector_store, embedder=embedder)

    # 1. L1 Public User querying confidential finance audit report
    chunks_l1 = retriever.retrieve(
        user=user_pub_l1,
        query="Datheon Q3 consolidated revenue and internal SOX 404 controls",
        target_department=Department.FINANCE,
    )
    # L1 user should receive ZERO L3 documents
    assert all(c.metadata.clearance != ClearanceTier.L3_CONFIDENTIAL for c in chunks_l1)

    # 2. L3 Finance Officer querying same topic
    chunks_l3 = retriever.retrieve(
        user=user_fin_l3,
        query="Datheon Q3 consolidated revenue and internal SOX 404 controls",
        target_department=Department.FINANCE,
    )
    assert len(chunks_l3) > 0
    assert any("$48.6M" in c.text for c in chunks_l3)
    assert any(c.metadata.page_number == 1 for c in chunks_l3)


def test_department_tenant_isolation(vector_store, embedder, user_eng_l2):
    retriever = RBACRetriever(vector_store=vector_store, embedder=embedder)

    # Engineering user attempts to retrieve HR confidential executive bonuses
    chunks = retriever.retrieve(
        user=user_eng_l2,
        query="Executive salary bands and equity acceleration double trigger",
        target_department=Department.HR,
    )
    # Target department should be overridden to caller department (Engineering)
    assert all(c.metadata.department != Department.HR for c in chunks)


def test_hallucination_guardrail_citation_verification():
    from src.etl.extractors import DocumentMetadata
    guardrail = HallucinationGuardrail()

    meta = DocumentMetadata(
        doc_id="DOC-1",
        source_file="Q3_Financial_Audit_Report.pdf",
        department=Department.FINANCE,
        clearance=ClearanceTier.L3_CONFIDENTIAL,
        date="2026-10-28",
        page_number=1,
    )
    chunk = RetrievedChunk(
        chunk_id="c1",
        text="Datheon achieved consolidated revenue of $48.6M in Q3 2026.",
        metadata=meta,
        similarity_score=0.9,
    )

    # 1. Valid Grounded Answer with exact page citation
    valid_answer = "Datheon achieved consolidated revenue of $48.6M in Q3 2026. [Source: Q3_Financial_Audit_Report.pdf, Page 1]"
    res_valid = guardrail.verify(valid_answer, [chunk])
    assert res_valid.is_valid is True
    assert res_valid.groundedness_score >= 0.70
    assert len(res_valid.citations) == 1
    assert res_valid.citations[0].page_number == 1

    # 2. Hallucinated Answer with invented monetary figure ($990M)
    hallucinated_answer = "Datheon achieved consolidated revenue of $990M with $500M in profits. [Source: Q3_Financial_Audit_Report.pdf, Page 1]"
    res_hallucinated = guardrail.verify(hallucinated_answer, [chunk])
    assert res_hallucinated.is_valid is False
    assert len(res_hallucinated.hallucinated_claims) > 0


def test_end_to_end_rag_engine(vector_store, embedder, user_fin_l3):
    retriever = RBACRetriever(vector_store=vector_store, embedder=embedder)
    rag = EnterpriseRAGEngine(retriever=retriever)

    resp = rag.query(
        user=user_fin_l3,
        query_text="What was the operating margin and revenue in Q3 2026?",
    )
    assert resp.chunks_retrieved > 0
    assert len(resp.citations) > 0
    assert "Page" in resp.citations[0]["citation_tag"]
    assert resp.is_grounded is True
    assert resp.latency_ms > 0
