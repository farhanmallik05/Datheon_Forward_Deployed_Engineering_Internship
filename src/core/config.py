"""Enterprise configuration and runtime settings.

Engineered to support 12-factor configuration via environment variables
and .env files with strict Pydantic v2 validation.
"""
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClearanceTier(str, Enum):
    """Security clearance classifications for corporate documents and identities."""
    L1_PUBLIC = "L1_PUBLIC"              # Unrestricted company-wide & public documentation
    L2_RESTRICTED = "L2_RESTRICTED"      # Departmental internal operational records
    L3_CONFIDENTIAL = "L3_CONFIDENTIAL"  # Sensitive executive, legal, audit, or compensation data

    @property
    def level(self) -> int:
        """Numeric rank for clearance comparisons."""
        mapping = {
            ClearanceTier.L1_PUBLIC: 1,
            ClearanceTier.L2_RESTRICTED: 2,
            ClearanceTier.L3_CONFIDENTIAL: 3,
        }
        return mapping[self]

    def allows(self, required_tier: "ClearanceTier") -> bool:
        """Determines if this clearance level is permitted to access the required tier."""
        return self.level >= required_tier.level


class Department(str, Enum):
    """Corporate organizational units for tenant isolation."""
    ENGINEERING = "engineering"
    FINANCE = "finance"
    HR = "hr"
    LEGAL = "legal"
    EXECUTIVE = "executive"
    CROSS_FUNCTIONAL = "cross_functional"


class Settings(BaseSettings):
    """Application-wide settings validated at runtime startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General Platform Identifiers
    APP_NAME: str = "Datheon Enterprise FDE Platform"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="production", description="Environment: development, staging, production")
    LOG_LEVEL: str = Field(default="INFO", description="Logging verbosity level")

    # Networking & VPC Config
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(
        default="datheon_vpc_hardened_secret_key_884920261028",
        description="Master secret key for JWT and HMAC generation",
    )
    ADMIN_API_KEY: str = Field(
        default="fde_admin_secops_token_9934",
        description="Default administrative API key for ingestion pipelines",
    )

    # Vector Storage Engine
    VECTOR_STORE_BACKEND: str = Field(
        default="memory",
        description="Vector database backend: 'memory', 'qdrant', or 'chroma'",
    )
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "datheon_enterprise_knowledge"
    VECTOR_DIMENSION: int = 384  # MiniLM-L6-v2 embedding dimension

    # Embeddings & Reranking Models
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    ENABLE_CROSS_ENCODER_RERANKER: bool = True
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    MAX_CHUNK_TOKENS: int = 500
    CHUNK_OVERLAP_TOKENS: int = 50

    # RAG Retrieval & Hallucination Guardrail Policies
    DEFAULT_RETRIEVAL_TOP_K: int = 8
    RERANK_TOP_K: int = 4
    SIMILARITY_THRESHOLD: float = 0.35
    STRICT_CITATION_GUARDRAIL: bool = True
    MIN_CITATION_CONFIDENCE: float = 0.70

    # Enterprise ERP/CRM Autonomous Agent Policies
    AGENT_MAX_ITERATIONS: int = 6
    AGENT_TEMPERATURE: float = 0.0
    HITL_APPROVAL_TIMEOUT_SECONDS: int = 3600
    HITL_HMAC_SECRET: str = "datheon_hitl_cryptographic_audit_secret_2026"

    # Directory Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MOCK_DB_PATH: Path = DATA_DIR / "mock_erp_db.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton getter for application configuration."""
    return Settings()
