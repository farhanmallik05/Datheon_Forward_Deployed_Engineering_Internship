"""Contextual query rewriter and disambiguation engine.

Expands ambiguous multi-turn user queries, resolves conversational pronouns,
and enriches queries with enterprise domain keywords for high-recall vector retrieval.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from src.core.config import Department
from src.core.logger import get_logger

logger = get_logger("rag.rewriter")


@dataclass
class RewrittenQuery:
    """Output structure of the enterprise query rewrite stage."""
    original_query: str
    expanded_query: str
    inferred_department: Optional[Department] = None
    extracted_entities: List[str] = field(default_factory=list)


class EnterpriseQueryRewriter:
    """Rule-based and semantic query expansion engine for corporate domain inquiries."""

    # Enterprise synonym and domain concept graph
    DOMAIN_EXPANSIONS: Dict[str, List[str]] = {
        "revenue": ["consolidated revenue", "operating margin", "ASC 606", "Q3", "gross receipts"],
        "sox": ["Sarbanes-Oxley", "Section 404", "internal financial controls", "audit deficiency"],
        "bonus": ["executive compensation", "salary bands", "performance multiplier", "E1", "E2", "severance"],
        "severance": ["accelerated vesting", "double trigger", "change of control", "equity cliff"],
        "nda": ["mutual non-disclosure agreement", "trade secrets", "confidential information", "Delaware"],
        "vpc": ["network topology", "CIDR block", "subnets", "Transit Gateway", "bastion host"],
        "rate limit": ["token bucket", "burst quota", "HTTP 429", "tier limits", "requests per minute"],
        "invoice": ["vendor payment", "PO number", "accounts payable", "reconciliation"],
    }

    DEPARTMENT_KEYWORDS: Dict[Department, List[str]] = {
        Department.FINANCE: ["revenue", "sox", "margin", "audit", "invoice", "vendor", "capex", "depreciation", "tax"],
        Department.HR: ["compensation", "salary", "bonus", "severance", "equity", "vesting", "employee", "handbook"],
        Department.LEGAL: ["nda", "confidentiality", "governing law", "trade secret", "agreement", "delaware", "breach"],
        Department.ENGINEERING: ["vpc", "cidr", "subnet", "rate limit", "token bucket", "gateway", "bastion", "api"],
    }

    def rewrite(self, query: str, conversation_context: Optional[str] = None) -> RewrittenQuery:
        """Expands raw input query with domain terms and contextual coreference resolution."""
        clean_query = query.strip()
        lowered = clean_query.lower()

        # 1. Resolve conversational pronouns if context is provided
        expanded_text = clean_query
        if conversation_context and any(pronoun in lowered for pronoun in ["it", "its", "they", "that report", "the document"]):
            expanded_text = f"{conversation_context} - {clean_query}"
            lowered = expanded_text.lower()

        # 2. Extract domain concepts and supplement with technical search terms
        added_terms: List[str] = []
        for keyword, expansions in self.DOMAIN_EXPANSIONS.items():
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                for term in expansions:
                    if term.lower() not in lowered and term not in added_terms:
                        added_terms.append(term)

        # 3. Infer departmental context
        inferred_dept = None
        dept_scores: Dict[Department, int] = {}
        for dept, kw_list in self.DEPARTMENT_KEYWORDS.items():
            score = sum(1 for kw in kw_list if kw in lowered)
            if score > 0:
                dept_scores[dept] = score

        if dept_scores:
            inferred_dept = max(dept_scores, key=dept_scores.get)

        final_expanded_query = clean_query
        if added_terms:
            final_expanded_query = f"{clean_query} ({' '.join(added_terms[:4])})"

        # 4. Extract entities (PO numbers, dollar amounts, document IDs, SKUs)
        entities = re.findall(r"\b(?:PO-\d+|INV-\d+-\d+|SKU-[A-Z0-9-]+|\$\d+(?:\.\d+)?[MBK]?)\b", clean_query)

        logger.debug("Rewrote query '%s' -> '%s' (Inferred Dept: %s)", clean_query, final_expanded_query, inferred_dept)
        return RewrittenQuery(
            original_query=clean_query,
            expanded_query=final_expanded_query,
            inferred_department=inferred_dept,
            extracted_entities=entities,
        )

