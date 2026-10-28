"""FastAPI endpoints for Multi-Tenant RBAC RAG query execution."""
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.core.config import Department
from src.core.security import EnterpriseUser, get_authenticated_user
from src.rag.engine import EnterpriseRAGEngine

router = APIRouter(prefix="/api/v1/rag", tags=["Enterprise RAG Service"])

_rag_engine = None


def get_rag_engine() -> EnterpriseRAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = EnterpriseRAGEngine()
    return _rag_engine


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=3, description="User search inquiry")
    target_department: Optional[Department] = Field(default=None, description="Optional target tenant scope")
    conversation_context: Optional[str] = Field(default=None, description="Prior conversation context for coreference")


@router.post("/query", status_code=status.HTTP_200_OK)
def execute_rag_query(
    request: RAGQueryRequest,
    current_user: EnterpriseUser = Depends(get_authenticated_user),
    engine: EnterpriseRAGEngine = Depends(get_rag_engine),
):
    """Executes a secure, boundary-isolated enterprise RAG query with verifiable page citations."""
    response = engine.query(
        user=current_user,
        query_text=request.query,
        target_department=request.target_department,
        conversation_context=request.conversation_context,
    )
    return response.to_dict()
