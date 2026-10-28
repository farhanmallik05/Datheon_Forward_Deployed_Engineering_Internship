"""Enterprise Vector ETL Pipeline orchestrator.

Coordinates multi-format document extraction, semantic chunking, batch vector embedding,
and metadata indexing into the vector store while recording telemetry metrics.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from src.core.config import ClearanceTier, Department, get_settings
from src.core.logger import get_logger
from src.core.telemetry import TelemetryMetrics
from src.etl.embedder import EnterpriseEmbedder
from src.etl.extractors import DocumentChunk, ExtractorFactory
from src.etl.splitters import SemanticChunker
from src.etl.vector_store import BaseVectorStore, VectorStoreFactory

logger = get_logger("etl.pipeline")


@dataclass
class IngestionReport:
    """Detailed summary of an ETL ingestion batch execution."""
    total_documents: int = 0
    total_chunks: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0
    throughput_docs_per_sec: float = 0.0
    throughput_chunks_per_sec: float = 0.0
    department_counts: Dict[str, int] = field(default_factory=dict)
    clearance_counts: Dict[str, int] = field(default_factory=dict)
    processed_files: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "duration_seconds": round(self.duration_seconds, 3),
            "throughput_docs_per_sec": round(self.throughput_docs_per_sec, 2),
            "throughput_chunks_per_sec": round(self.throughput_chunks_per_sec, 2),
            "department_counts": self.department_counts,
            "clearance_counts": self.clearance_counts,
            "processed_files": self.processed_files,
        }


class VectorETLPipeline:
    """End-to-end automated pipeline for enterprise legacy document ingestion."""

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedder: Optional[EnterpriseEmbedder] = None,
        chunker: Optional[SemanticChunker] = None,
    ):
        self.vector_store = vector_store or VectorStoreFactory.get_vector_store()
        self.embedder = embedder or EnterpriseEmbedder()
        self.chunker = chunker or SemanticChunker()

    def ingest_files(
        self,
        file_paths: List[Path],
        override_department: Optional[Department] = None,
        override_clearance: Optional[ClearanceTier] = None,
        batch_size: int = 32,
    ) -> IngestionReport:
        """Processes a list of files through extraction, chunking, embedding, and indexing."""
        start_time = time.time()
        report = IngestionReport()
        all_chunks: List[DocumentChunk] = []

        logger.info("Initiating ETL batch ingestion for %d target files", len(file_paths))

        for fpath in file_paths:
            path = Path(fpath)
            if not path.is_file():
                continue

            try:
                extractor = ExtractorFactory.get_extractor(path)
                raw_chunks = extractor.extract(
                    path,
                    override_department=override_department,
                    override_clearance=override_clearance,
                )
                refined_chunks = self.chunker.chunk(raw_chunks)
                all_chunks.extend(refined_chunks)

                report.total_documents += 1
                report.processed_files.append(path.name)
            except Exception as e:
                logger.error("Error processing file %s: %s", path.name, str(e))

        if not all_chunks:
            logger.warning("No chunks generated from specified files.")
            report.duration_seconds = time.time() - start_time
            return report

        # Extract texts for batch embedding
        texts = [c.text for c in all_chunks]
        total_tokens = sum(c.token_count for c in all_chunks)
        report.total_chunks = len(all_chunks)
        report.total_tokens = total_tokens

        logger.info("Computing dense embeddings for %d semantic chunks...", len(all_chunks))
        embeddings = self.embedder.embed_texts(texts, batch_size=batch_size)

        logger.info("Upserting vectors into target enterprise vector index...")
        self.vector_store.upsert(all_chunks, embeddings)

        # Compute breakdown stats
        for chunk in all_chunks:
            dept_key = chunk.metadata.department.value
            clear_key = chunk.metadata.clearance.value
            report.department_counts[dept_key] = report.department_counts.get(dept_key, 0) + 1
            report.clearance_counts[clear_key] = report.clearance_counts.get(clear_key, 0) + 1

        duration = time.time() - start_time
        report.duration_seconds = duration
        if duration > 0:
            report.throughput_docs_per_sec = report.total_documents / duration
            report.throughput_chunks_per_sec = report.total_chunks / duration

        # Telemetry metrics emission
        TelemetryMetrics.record_etl_run(
            docs_count=report.total_documents,
            chunks_count=report.total_chunks,
            department=override_department.value if override_department else "multi",
            duration_sec=duration,
        )

        logger.info(
            "ETL ingestion completed: %d documents, %d chunks, %.2f s (%.1f chunks/sec)",
            report.total_documents,
            report.total_chunks,
            duration,
            report.throughput_chunks_per_sec,
        )
        return report

    def ingest_directory(
        self,
        directory_path: Path,
        recursive: bool = True,
        batch_size: int = 32,
    ) -> IngestionReport:
        """Recursively discovers and ingests all supported legacy documents in a directory."""
        dir_path = Path(directory_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Target directory does not exist: {dir_path}")

        pattern = "**/*" if recursive else "*"
        supported_exts = {".pdf", ".csv", ".md", ".txt"}
        candidate_files = [p for p in dir_path.glob(pattern) if p.is_file() and p.suffix.lower() in supported_exts]

        return self.ingest_files(candidate_files, batch_size=batch_size)

