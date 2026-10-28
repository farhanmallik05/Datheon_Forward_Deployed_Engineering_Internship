"""Pluggable enterprise vector database integration with cosine similarity indexes.

Provides high-throughput vector storage and retrieval with native metadata filtering,
supporting both Qdrant and high-speed in-memory vector storage.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from src.core.config import ClearanceTier, Department, get_settings
from src.core.logger import get_logger
from src.etl.extractors import DocumentChunk, DocumentMetadata

logger = get_logger("etl.vector_store")


@dataclass
class VectorSearchResult:
    """Standardized search result item returned from vector storage."""
    chunk_id: str
    text: str
    metadata: DocumentMetadata
    score: float

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "score": round(self.score, 4),
            "metadata": self.metadata.to_dict(),
        }


class BaseVectorStore(ABC):
    """Abstract interface defining the enterprise vector storage contract."""

    @abstractmethod
    def upsert(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> int:
        """Indexes document chunks along with their dense vectors."""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        department_filter: Optional[Department] = None,
        clearance_filter: Optional[ClearanceTier] = None,
        min_score: float = 0.0,
    ) -> List[VectorSearchResult]:
        """Searches for nearest semantic neighbors matching tenant and clearance filters."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Returns total indexed vectors."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Wipes the index."""
        pass


class InMemoryCosineVectorStore(BaseVectorStore):
    """High-performance in-memory vector store with cosine indexing and metadata filtering."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.chunks: List[DocumentChunk] = []
        self.vectors: np.ndarray = np.empty((0, dimension), dtype=np.float32)

    def upsert(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> int:
        if len(chunks) == 0:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch between chunks count ({len(chunks)}) and embeddings count ({len(embeddings)})")

        self.chunks.extend(chunks)
        if len(self.vectors) == 0:
            self.vectors = embeddings.astype(np.float32)
        else:
            self.vectors = np.vstack([self.vectors, embeddings.astype(np.float32)])

        logger.info("Upserted %d vectors into InMemoryCosineStore (total: %d)", len(chunks), len(self.chunks))
        return len(chunks)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        department_filter: Optional[Department] = None,
        clearance_filter: Optional[ClearanceTier] = None,
        min_score: float = 0.0,
    ) -> List[VectorSearchResult]:
        if len(self.chunks) == 0:
            return []

        # Ensure normalized query vector
        q_norm = np.linalg.norm(query_vector)
        if q_norm > 0:
            q_vec = query_vector / q_norm
        else:
            q_vec = query_vector

        # Cosine similarity is the dot product of normalized vectors
        scores = np.dot(self.vectors, q_vec)

        # Ranked indices descending
        ranked_indices = np.argsort(scores)[::-1]

        results: List[VectorSearchResult] = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score < min_score:
                continue

            chunk = self.chunks[idx]
            meta = chunk.metadata

            # Metadata filtering: department boundary
            if department_filter and department_filter != Department.CROSS_FUNCTIONAL:
                if meta.department != department_filter and meta.department != Department.CROSS_FUNCTIONAL:
                    continue

            # Metadata filtering: clearance tier (principal clearance must allow doc clearance)
            if clearance_filter:
                if not clearance_filter.allows(meta.clearance):
                    continue

            results.append(
                VectorSearchResult(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    metadata=meta,
                    score=score,
                )
            )

            if len(results) >= top_k:
                break

        return results

    def count(self) -> int:
        return len(self.chunks)

    def clear(self) -> None:
        self.chunks = []
        self.vectors = np.empty((0, self.dimension), dtype=np.float32)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant client integration supporting both local in-memory instances and remote VPC clusters."""

    def __init__(self, collection_name: str = None, host: str = None, port: int = None, in_memory: bool = False):
        settings = get_settings()
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.dimension = settings.VECTOR_DIMENSION

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            if in_memory or settings.VECTOR_STORE_BACKEND == "memory":
                self.client = QdrantClient(":memory:")
                logger.info("Initialized Qdrant in-memory engine")
            else:
                target_host = host or settings.QDRANT_HOST
                target_port = port or settings.QDRANT_PORT
                self.client = QdrantClient(host=target_host, port=target_port, timeout=5.0)
                logger.info("Connected to remote Qdrant cluster at %s:%d", target_host, target_port)

            # Recreate or ensure collection exists
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                )
                # Create payload indexes for metadata filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="department",
                    field_schema="keyword",
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="clearance",
                    field_schema="keyword",
                )
            self._local_chunks: Dict[str, DocumentChunk] = {}
        except Exception as e:
            logger.warning("Failed to initialize Qdrant cluster (%s). Falling back to InMemoryCosineVectorStore.", e)
            self.client = None
            self._fallback = InMemoryCosineVectorStore(self.dimension)

    def upsert(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> int:
        if self.client is None:
            return self._fallback.upsert(chunks, embeddings)

        from qdrant_client.models import PointStruct

        points = []
        for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
            self._local_chunks[chunk.chunk_id] = chunk
            # Hash chunk_id to UUID integer or use int id
            point_id = abs(hash(chunk.chunk_id)) % (2**63 - 1)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vec.tolist(),
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "department": chunk.metadata.department.value,
                        "clearance": chunk.metadata.clearance.value,
                        "metadata": chunk.metadata.to_dict(),
                    },
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info("Upserted %d points to Qdrant collection %s", len(points), self.collection_name)
        return len(points)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        department_filter: Optional[Department] = None,
        clearance_filter: Optional[ClearanceTier] = None,
        min_score: float = 0.0,
    ) -> List[VectorSearchResult]:
        if self.client is None:
            return self._fallback.search(query_vector, top_k, department_filter, clearance_filter, min_score)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        filter_conditions = []
        if department_filter and department_filter != Department.CROSS_FUNCTIONAL:
            filter_conditions.append(
                FieldCondition(key="department", match=MatchValue(value=department_filter.value))
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        search_res = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            query_filter=query_filter,
            limit=top_k * 2,  # Fetch extra to apply clearance level filtering
            score_threshold=min_score,
        )

        results: List[VectorSearchResult] = []
        for hit in search_res:
            payload = hit.payload
            meta_dict = payload.get("metadata", {})
            chunk_dept = Department(payload.get("department", "engineering"))
            chunk_clearance = ClearanceTier(payload.get("clearance", "L2_RESTRICTED"))

            # Clearance check
            if clearance_filter and not clearance_filter.allows(chunk_clearance):
                continue

            meta = DocumentMetadata(
                doc_id=meta_dict.get("doc_id", "DOC-UNKNOWN"),
                source_file=meta_dict.get("source_file", "unknown"),
                department=chunk_dept,
                clearance=chunk_clearance,
                date=meta_dict.get("date", "2026-10-28"),
                author=meta_dict.get("author"),
                title=meta_dict.get("title"),
                file_format=meta_dict.get("file_format", "txt"),
                page_number=meta_dict.get("page_number"),
                row_number=meta_dict.get("row_number"),
                section_title=meta_dict.get("section_title"),
            )

            results.append(
                VectorSearchResult(
                    chunk_id=payload.get("chunk_id", str(hit.id)),
                    text=payload.get("text", ""),
                    metadata=meta,
                    score=float(hit.score),
                )
            )

            if len(results) >= top_k:
                break

        return results

    def count(self) -> int:
        if self.client is None:
            return self._fallback.count()
        info = self.client.get_collection(self.collection_name)
        return info.points_count or 0

    def clear(self) -> None:
        if self.client is None:
            return self._fallback.clear()
        self.client.delete_collection(self.collection_name)
        from qdrant_client.models import Distance, VectorParams
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
        )


class VectorStoreFactory:
    """Instantiates the vector store backend based on runtime settings."""

    _instance = None

    @classmethod
    def get_vector_store(cls, force_recreate: bool = False) -> BaseVectorStore:
        if cls._instance is not None and not force_recreate:
            return cls._instance

        settings = get_settings()
        if settings.VECTOR_STORE_BACKEND.lower() == "qdrant":
            cls._instance = QdrantVectorStore()
        else:
            cls._instance = InMemoryCosineVectorStore(settings.VECTOR_DIMENSION)

        return cls._instance

