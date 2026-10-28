"""Enterprise Multi-Tenant RAG Engine with RBAC and citation guardrails.

Orchestrates query rewriting, clearance-filtered vector retrieval, cross-encoder reranking,
factual synthesis with verifiable page citations, and hallucination verification.
"""
import time
from dataclasses import dataclass, field
from typing import List, Optional

from src.core.config import Department, get_settings
from src.core.logger import get_logger
from src.core.security import EnterpriseUser
from src.core.telemetry import TelemetryMetrics
from src.rag.guardrails import Citation, HallucinationGuardrail
from src.rag.query_rewriter import EnterpriseQueryRewriter
from src.rag.rbac_retriever import RBACRetriever, RetrievedChunk
from src.rag.reranker import CrossEncoderReranker

logger = get_logger("rag.engine")


@dataclass
class RAGResponse:
    """Enterprise RAG query response payload."""
    answer: str
    user_id: str
    department: str
    clearance: str
    citations: List[dict] = field(default_factory=list)
    groundedness_score: float = 1.0
    is_grounded: bool = True
    chunks_retrieved: int = 0
    latency_ms: float = 0.0
    hallucination_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "user_id": self.user_id,
            "department": self.department,
            "clearance": self.clearance,
            "citations": self.citations,
            "groundedness_score": self.groundedness_score,
            "is_grounded": self.is_grounded,
            "chunks_retrieved": self.chunks_retrieved,
            "latency_ms": round(self.latency_ms, 2),
            "hallucination_warnings": self.hallucination_warnings,
        }


class EnterpriseRAGEngine:
    """Production-grade RAG service enforcing tenant isolation and citation fidelity."""

    def __init__(
        self,
        retriever: Optional[RBACRetriever] = None,
        rewriter: Optional[EnterpriseQueryRewriter] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        guardrail: Optional[HallucinationGuardrail] = None,
    ):
        self.retriever = retriever or RBACRetriever()
        self.rewriter = rewriter or EnterpriseQueryRewriter()
        self.reranker = reranker or CrossEncoderReranker()
        self.guardrail = guardrail or HallucinationGuardrail()
        self.settings = get_settings()

    def query(
        self,
        user: EnterpriseUser,
        query_text: str,
        target_department: Optional[Department] = None,
        conversation_context: Optional[str] = None,
    ) -> RAGResponse:
        """Executes the full enterprise RAG pipeline for an authenticated principal."""
        start_time = time.perf_counter()

        # Step 1: Query Rewriting and Expansion
        rewritten = self.rewriter.rewrite(query_text, conversation_context)

        # Step 2: RBAC-Gated Vector Retrieval
        target_dept = target_department or rewritten.inferred_department
        retrieved_chunks = self.retriever.retrieve(
            user=user,
            query=rewritten.expanded_query,
            target_department=target_dept,
            top_k=self.settings.DEFAULT_RETRIEVAL_TOP_K,
        )

        if not retrieved_chunks:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RAGResponse(
                answer=(
                    f"Access Denied or No Records Found: No authoritative documents matching your "
                    f"clearance level ({user.clearance.value}) and tenant scope ({user.department.value}) "
                    f"were found for this inquiry."
                ),
                user_id=user.user_id,
                department=user.department.value,
                clearance=user.clearance.value,
                citations=[],
                groundedness_score=1.0,
                is_grounded=True,
                chunks_retrieved=0,
                latency_ms=elapsed_ms,
            )

        # Step 3: Cross-Encoder Precision Reranking
        top_chunks = self.reranker.rerank(
            query=rewritten.expanded_query,
            candidates=retrieved_chunks,
            top_k=self.settings.RERANK_TOP_K,
        )

        # Step 4: Grounded Synthesis with Verifiable Citations
        synthesized_answer = self._synthesize_answer(query_text, top_chunks)

        # Step 5: Hallucination and Citation Guardrail
        guard_res = self.guardrail.verify(synthesized_answer, top_chunks)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Record Telemetry
        TelemetryMetrics.record_rag_query(
            department=user.department.value,
            clearance=user.clearance.value,
            duration_sec=elapsed_ms / 1000.0,
            chunks_count=len(top_chunks),
        )

        citations_payload = [
            {
                "source_file": c.source_file,
                "page_number": c.page_number,
                "row_number": c.row_number,
                "section_title": c.section_title,
                "citation_tag": c.to_citation_tag(),
                "excerpt": c.excerpt,
                "verified": c.is_verified,
            }
            for c in guard_res.citations
        ]

        return RAGResponse(
            answer=guard_res.sanitized_answer,
            user_id=user.user_id,
            department=user.department.value,
            clearance=user.clearance.value,
            citations=citations_payload,
            groundedness_score=guard_res.groundedness_score,
            is_grounded=guard_res.is_valid,
            chunks_retrieved=len(top_chunks),
            latency_ms=elapsed_ms,
            hallucination_warnings=guard_res.warnings,
        )

    def _synthesize_answer(self, query: str, chunks: List[RetrievedChunk]) -> str:
        """Extracts facts from high-scoring chunks and constructs an answer with verifiable page citations."""
        answer_parts = []
        for chunk in chunks:
            citation_tag = chunk.to_citation_reference()
            clean_text = chunk.text.strip()
            # Clean header lines for concise summary
            sentences = [s.strip() for s in clean_text.split(". ") if len(s.strip()) > 20]
            if sentences:
                key_sentence = sentences[0]
                if not key_sentence.endswith("."):
                    key_sentence += "."
                answer_parts.append(f"{key_sentence} [Source: {citation_tag.strip('[]')}]")

        if not answer_parts:
            return "No verifiable factual claims could be synthesized from authorized evidence."

        return " ".join(answer_parts[:3])

