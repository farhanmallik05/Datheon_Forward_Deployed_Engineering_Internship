"""Role-Based Access Control (RBAC) vector retriever.

Enforces defense-in-depth tenant boundary isolation and clearance tier validation
at both the database index and post-retrieval verification layers.
"""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from src.core.config import ClearanceTier, Department, get_settings
from src.core.logger import get_logger
from src.core.security import EnterpriseUser, can_access_document
from src.etl.embedder import EnterpriseEmbedder
from src.etl.extractors import DocumentMetadata
from src.etl.vector_store import BaseVectorStore, VectorStoreFactory

logger = get_logger("rag.rbac_retriever")


@dataclass
class RetrievedChunk:
    """Document passage validated against caller clearance and department boundary."""
    chunk_id: str
    text: str
    metadata: DocumentMetadata
    similarity_score: float
    rerank_score: float = 0.0

    def to_citation_reference(self) -> str:
        """Formats an enterprise citation tag."""
        if self.metadata.page_number is not None:
            return f"[{self.metadata.source_file}, Page {self.metadata.page_number}]"
        elif self.metadata.row_number is not None:
            return f"[{self.metadata.source_file}, Row {self.metadata.row_number}]"
        elif self.metadata.section_title is not None:
            return f"[{self.metadata.source_file}, {self.metadata.section_title}]"
        return f"[{self.metadata.source_file}]"


class RBACRetriever:
    """Enterprise retriever executing boundary-isolated semantic searches."""

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedder: Optional[EnterpriseEmbedder] = None,
    ):
        self.vector_store = vector_store or VectorStoreFactory.get_vector_store()
        self.embedder = embedder or EnterpriseEmbedder()
        self.settings = get_settings()

    def retrieve(
        self,
        user: EnterpriseUser,
        query: str,
        target_department: Optional[Department] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """Retrieves and strictly verifies semantic candidates matching the user's RBAC profile."""
        k = top_k or self.settings.DEFAULT_RETRIEVAL_TOP_K

        # 1. Determine effective department filter
        if user.is_admin or user.department == Department.EXECUTIVE:
            # Executive/Admin can query target department or cross-functional
            dept_filter = target_department
        else:
            # Standard employees strictly bound to their assigned department
            if target_department and target_department != user.department and target_department not in user.additional_allowed_departments:
                logger.warning(
                    "User %s (Dept: %s) requested cross-tenant search in %s. Overriding to caller department.",
                    user.user_id,
                    user.department.value,
                    target_department.value,
                )
            dept_filter = user.department

        # 2. Embed the query vector
        query_vec = self.embedder.embed_query(query)

        # 3. Vector DB Search with Pre-Filtering
        raw_results = self.vector_store.search(
            query_vector=query_vec,
            top_k=k * 2,  # Fetch pool for defense-in-depth evaluation
            department_filter=dept_filter,
            clearance_filter=user.clearance,
            min_score=self.settings.SIMILARITY_THRESHOLD,
        )

        # 4. Post-Retrieval Defense-in-Depth Verification
        verified_chunks: List[RetrievedChunk] = []
        for res in raw_results:
            meta = res.metadata
            # Strict access check
            if not can_access_document(user, meta.department, meta.clearance):
                logger.critical(
                    "SECURITY BREACH ATTEMPT PREVENTED: User %s (Clearance: %s, Dept: %s) "
                    "was served chunk %s (Clearance: %s, Dept: %s). Discarding immediately.",
                    user.user_id,
                    user.clearance.value,
                    user.department.value,
                    res.chunk_id,
                    meta.clearance.value,
                    meta.department.value,
                )
                continue

            verified_chunks.append(
                RetrievedChunk(
                    chunk_id=res.chunk_id,
                    text=res.text,
                    metadata=meta,
                    similarity_score=res.score,
                )
            )

            if len(verified_chunks) >= k:
                break

        logger.info(
            "Retrieved %d verified chunks for user %s [Dept: %s, Clearance: %s]",
            len(verified_chunks),
            user.user_id,
            user.department.value,
            user.clearance.value,
        )
        return verified_chunks
