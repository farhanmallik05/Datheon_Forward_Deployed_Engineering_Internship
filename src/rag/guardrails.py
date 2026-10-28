"""Hallucination detection and citation verification guardrails.

Audits synthesized enterprise answers against retrieved document passages,
verifies page/row citation fidelity, and blocks ungrounded claims.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from src.core.config import get_settings
from src.core.exceptions import HallucinationGuardrailError
from src.core.logger import get_logger
from src.core.telemetry import TelemetryMetrics
from src.rag.rbac_retriever import RetrievedChunk

logger = get_logger("rag.guardrails")


@dataclass
class Citation:
    """Verifiable document citation reference."""
    source_file: str
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    section_title: Optional[str] = None
    excerpt: str = ""
    is_verified: bool = False

    def to_citation_tag(self) -> str:
        if self.page_number is not None:
            return f"[Source: {self.source_file}, Page {self.page_number}]"
        elif self.row_number is not None:
            return f"[Source: {self.source_file}, Row {self.row_number}]"
        elif self.section_title is not None:
            return f"[Source: {self.source_file}, {self.section_title}]"
        return f"[Source: {self.source_file}]"


@dataclass
class GuardrailResult:
    """Evaluation output from the hallucination audit check."""
    is_valid: bool
    groundedness_score: float
    citations: List[Citation] = field(default_factory=list)
    hallucinated_claims: List[str] = field(default_factory=list)
    sanitized_answer: str = ""
    warnings: List[str] = field(default_factory=list)


class HallucinationGuardrail:
    """Enterprise citation verification and anti-hallucination barrier."""

    def __init__(self, min_confidence: float = None, strict_mode: bool = None):
        settings = get_settings()
        self.min_confidence = min_confidence or settings.MIN_CITATION_CONFIDENCE
        self.strict_mode = strict_mode if strict_mode is not None else settings.STRICT_CITATION_GUARDRAIL

    def verify(self, answer: str, context_chunks: List[RetrievedChunk]) -> GuardrailResult:
        """Audits generated answer text against retrieved evidence chunks."""
        if not context_chunks:
            return GuardrailResult(
                is_valid=False,
                groundedness_score=0.0,
                hallucinated_claims=["No supporting context chunks retrieved."],
                sanitized_answer="Access Denied or No Authoritative Records Found in Clearance Boundary.",
                warnings=["Query returned zero verified context chunks."],
            )

        # 1. Parse Citations in the generated text
        # Patterns like: [Source: file.pdf, Page 2], [Page 2], [Source: file.csv, Row 4], [file.md, Section 1]
        citation_pattern = re.compile(
            r"\[(?:Source:\s*)?([A-Za-z0-9_\-\.]+)(?:,\s*(?:Page|Row|Section)?\s*([0-9A-Za-z\s]+))?\]"
        )
        found_matches = citation_pattern.findall(answer)

        verified_citations: List[Citation] = []
        for match in found_matches:
            src_file = match[0].strip()
            loc_str = match[1].strip() if len(match) > 1 and match[1] else None

            # Attempt to locate matching retrieved chunk
            matched_chunk = None
            for chunk in context_chunks:
                if src_file.lower() in chunk.metadata.source_file.lower():
                    # Check page or row match if specified
                    if loc_str:
                        if chunk.metadata.page_number and str(chunk.metadata.page_number) in loc_str:
                            matched_chunk = chunk
                            break
                        elif chunk.metadata.row_number and str(chunk.metadata.row_number) in loc_str:
                            matched_chunk = chunk
                            break
                    else:
                        matched_chunk = chunk
                        break

            if matched_chunk:
                verified_citations.append(
                    Citation(
                        source_file=matched_chunk.metadata.source_file,
                        page_number=matched_chunk.metadata.page_number,
                        row_number=matched_chunk.metadata.row_number,
                        section_title=matched_chunk.metadata.section_title,
                        excerpt=matched_chunk.text[:140] + "...",
                        is_verified=True,
                    )
                )

        # 2. Extract facts and numbers from answer and check against evidence text
        evidence_corpus = " ".join(c.text for c in context_chunks).lower()
        # Strip citation annotations so citation page/row numbers aren't treated as factual claims
        claims_text = citation_pattern.sub("", answer).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", claims_text) if s.strip()]

        grounded_count = 0
        hallucinated_claims: List[str] = []

        for sent in sentences:
            if not sent.strip():
                continue

            # Extract critical numeric and monetary tokens (e.g. $48.6M, 24.8%, 142, 500, etc.)
            numerical_entities = re.findall(r"(?:\$[\d\.]+[MBK%]?|\b\d+(?:\.\d+)?[MBK%]?)", sent)

            # Check if all entities in this sentence exist in the evidence
            sentence_grounded = True
            for entity in numerical_entities:
                norm_entity = entity.lower().replace(",", "")
                # Ignore trivial 1-2 digit integers that might be list bullets or grammar
                if len(norm_entity) <= 1 and norm_entity.isdigit():
                    continue
                if norm_entity not in evidence_corpus and entity.lower() not in evidence_corpus:
                    sentence_grounded = False
                    hallucinated_claims.append(f"Unverified entity '{entity}' in claim: '{sent.strip()}'")

            if sentence_grounded:
                grounded_count += 1

        total_sentences = max(len(sentences), 1)
        groundedness_score = round(grounded_count / total_sentences, 3)

        # Boost groundedness if citations are present and verified (only if zero hallucinated claims)
        if verified_citations and not hallucinated_claims:
            groundedness_score = min(1.0, round(groundedness_score + 0.15, 3))

        is_valid = (groundedness_score >= self.min_confidence) and (len(hallucinated_claims) == 0)

        sanitized_answer = answer
        if not is_valid:
            TelemetryMetrics.record_guardrail_violation("hallucinated_entities_detected")
            logger.warning(
                "Hallucination guardrail flagged response. Groundedness: %.2f, Violations: %d",
                groundedness_score,
                len(hallucinated_claims),
            )
            if self.strict_mode and hallucinated_claims:
                sanitized_answer = (
                    f"{answer}\n\n[GUARDRAIL NOTICE: The above response contains {len(hallucinated_claims)} "
                    f"unverified assertion(s) requiring human audit: {hallucinated_claims[0]}]"
                )

        return GuardrailResult(
            is_valid=is_valid,
            groundedness_score=groundedness_score,
            citations=verified_citations,
            hallucinated_claims=hallucinated_claims,
            sanitized_answer=sanitized_answer,
            warnings=[] if is_valid else ["Low groundedness or unverified claims detected."],
        )
