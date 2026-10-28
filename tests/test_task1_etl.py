"""Unit and integration tests for Task 1: Client Legacy Data Ingestion & Vector ETL Pipeline."""
from pathlib import Path
import numpy as np
import pytest

from src.core.config import ClearanceTier, Department
from src.etl.extractors import CSVExtractor, ExtractorFactory, MarkdownExtractor, PDFExtractor
from src.etl.splitters import SemanticChunker
from src.etl.vector_store import InMemoryCosineVectorStore


def test_pdf_extractor_page_preservation(settings):
    pdf_path = settings.DATA_DIR / "raw" / "finance" / "Q3_Financial_Audit_Report.pdf"
    assert pdf_path.exists(), "Test PDF file missing"

    extractor = PDFExtractor()
    chunks = extractor.extract(pdf_path)

    assert len(chunks) == 3, f"Expected 3 pages in financial audit, got {len(chunks)}"
    assert chunks[0].metadata.page_number == 1
    assert chunks[1].metadata.page_number == 2
    assert chunks[2].metadata.page_number == 3
    assert chunks[0].metadata.department == Department.FINANCE
    assert chunks[0].metadata.clearance == ClearanceTier.L3_CONFIDENTIAL
    assert "$48.6M" in chunks[0].text


def test_csv_extractor_record_lineage(settings):
    csv_path = settings.DATA_DIR / "raw" / "finance" / "vendor_invoices_2026.csv"
    assert csv_path.exists(), "Test CSV file missing"

    extractor = CSVExtractor()
    chunks = extractor.extract(csv_path)

    assert len(chunks) == 6, f"Expected 6 invoice rows, got {len(chunks)}"
    assert chunks[0].metadata.row_number == 1
    assert "INV-2026-901" in chunks[0].text
    assert "NVIDIA Cloud Compute" in chunks[0].text
    assert chunks[0].metadata.department == Department.ENGINEERING
    assert chunks[0].metadata.clearance == ClearanceTier.L2_RESTRICTED


def test_markdown_extractor_sections_and_frontmatter(settings):
    md_path = settings.DATA_DIR / "raw" / "engineering" / "VPC_Network_Architecture_v2.md"
    assert md_path.exists(), "Test Markdown file missing"

    extractor = MarkdownExtractor()
    chunks = extractor.extract(md_path)

    assert len(chunks) >= 3
    assert chunks[0].metadata.doc_id == "ENG-ARCH-VPC-002"
    assert chunks[0].metadata.department == Department.ENGINEERING
    assert chunks[0].metadata.clearance == ClearanceTier.L2_RESTRICTED
    assert any("10.180.0.0/16" in c.text for c in chunks)


def test_semantic_chunker_splitting():
    chunker = SemanticChunker(max_tokens=20, overlap_tokens=5)
    from src.etl.extractors import DocumentChunk, DocumentMetadata

    meta = DocumentMetadata(
        doc_id="TEST-001",
        source_file="test.txt",
        department=Department.ENGINEERING,
        clearance=ClearanceTier.L1_PUBLIC,
        date="2026-10-28",
        page_number=1,
    )
    long_text = (
        "Enterprise forward deployed engineers interface directly with client stakeholders. "
        "They deploy private VPC infrastructure and hardened microservices. "
        "They build semantic search vector pipelines with metadata preservation. "
        "Strict role-based access control prevents cross-tenant data leakage."
    )
    chunk = DocumentChunk(chunk_id="test_c1", text=long_text, metadata=meta)
    sub_chunks = chunker.chunk([chunk])

    assert len(sub_chunks) > 1
    for sc in sub_chunks:
        assert sc.metadata.page_number == 1
        assert sc.metadata.department == Department.ENGINEERING


def test_vector_store_cosine_filtering():
    store = InMemoryCosineVectorStore(dimension=4)
    from src.etl.extractors import DocumentChunk, DocumentMetadata

    meta_l1 = DocumentMetadata(doc_id="D1", source_file="d1.txt", department=Department.ENGINEERING, clearance=ClearanceTier.L1_PUBLIC, date="2026-10-28")
    meta_l3 = DocumentMetadata(doc_id="D2", source_file="d2.txt", department=Department.FINANCE, clearance=ClearanceTier.L3_CONFIDENTIAL, date="2026-10-28")

    c1 = DocumentChunk(chunk_id="c1", text="engineering doc", metadata=meta_l1)
    c2 = DocumentChunk(chunk_id="c2", text="finance confidential", metadata=meta_l3)

    v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

    store.upsert([c1, c2], np.vstack([v1, v2]))

    # Query with L1 clearance - must NOT return L3 chunk (c2)
    results = store.search(query_vector=v2, top_k=5, clearance_filter=ClearanceTier.L1_PUBLIC)
    assert not any(r.chunk_id == "c2" for r in results), "Security leak: L3 document (c2) returned to L1 clearance!"
    assert all(r.metadata.clearance == ClearanceTier.L1_PUBLIC for r in results)

    # Query with L3 clearance in Finance - must return c2
    results_l3 = store.search(query_vector=v2, top_k=5, department_filter=Department.FINANCE, clearance_filter=ClearanceTier.L3_CONFIDENTIAL)
    assert len(results_l3) == 1
    assert results_l3[0].chunk_id == "c2"
