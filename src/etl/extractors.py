"""Multi-format enterprise document extractors with metadata preservation.

Parses unstructured corporate PDFs, CSV tabular logs, and Markdown documentation
while strictly extracting security clearance tiers, department tenancy, page numbers,
and document lineage.
"""
import csv
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import pypdf

from src.core.config import ClearanceTier, Department
from src.core.exceptions import DocumentExtractionError
from src.core.logger import get_logger

logger = get_logger("etl.extractors")


@dataclass
class DocumentMetadata:
    """Enterprise metadata attached to extracted document units."""
    doc_id: str
    source_file: str
    department: Department
    clearance: ClearanceTier
    date: str
    author: Optional[str] = None
    title: Optional[str] = None
    file_format: str = "unknown"
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    section_title: Optional[str] = None
    custom_attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "source_file": self.source_file,
            "department": self.department.value,
            "clearance": self.clearance.value,
            "date": self.date,
            "author": self.author,
            "title": self.title,
            "file_format": self.file_format,
            "page_number": self.page_number,
            "row_number": self.row_number,
            "section_title": self.section_title,
            **self.custom_attributes,
        }


@dataclass
class DocumentChunk:
    """Individual indexable semantic text chunk with full lineage."""
    chunk_id: str
    text: str
    metadata: DocumentMetadata
    token_count: int = 0

    def to_payload(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "token_count": self.token_count,
            "metadata": self.metadata.to_dict(),
        }


class BaseExtractor(ABC):
    """Abstract base class for all legacy format extractors."""

    @abstractmethod
    def extract(
        self,
        file_path: Path,
        override_department: Optional[Department] = None,
        override_clearance: Optional[ClearanceTier] = None,
    ) -> List[DocumentChunk]:
        """Extracts text and metadata units from the given file."""
        pass

    @staticmethod
    def infer_department_from_path(file_path: Path) -> Department:
        """Infers enterprise department from directory structure if available."""
        path_str = str(file_path).lower().replace("\\", "/")
        for dept in Department:
            if f"/{dept.value}/" in path_str or f"\\{dept.value}\\" in path_str:
                return dept
        return Department.CROSS_FUNCTIONAL

    @staticmethod
    def infer_clearance_from_text(text: str) -> ClearanceTier:
        """Scans document header text for clearance markings."""
        upper_text = text.upper()
        if "L3_CONFIDENTIAL" in upper_text or "TIER 3" in upper_text or "TOP SECRET" in upper_text:
            return ClearanceTier.L3_CONFIDENTIAL
        elif "L2_RESTRICTED" in upper_text or "TIER 2" in upper_text or "INTERNAL ONLY" in upper_text:
            return ClearanceTier.L2_RESTRICTED
        elif "L1_PUBLIC" in upper_text or "TIER 1" in upper_text or "PUBLIC" in upper_text:
            return ClearanceTier.L1_PUBLIC
        return ClearanceTier.L2_RESTRICTED


class PDFExtractor(BaseExtractor):
    """Extracts text from multi-page corporate PDFs with page number preservation."""

    def extract(
        self,
        file_path: Path,
        override_department: Optional[Department] = None,
        override_clearance: Optional[ClearanceTier] = None,
    ) -> List[DocumentChunk]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentExtractionError(f"PDF file not found: {file_path}")

        chunks: List[DocumentChunk] = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            doc_id = f"DOC-PDF-{file_path.stem.upper()}"
            dept = override_department or self.infer_department_from_path(file_path)

            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                raw_text = page.extract_text() or ""
                clean_text = re.sub(r"\s+", " ", raw_text).strip()
                if not clean_text:
                    continue

                # Infer clearance from page header or fallback to override
                clearance = override_clearance or self.infer_clearance_from_text(clean_text)

                meta = DocumentMetadata(
                    doc_id=doc_id,
                    source_file=file_path.name,
                    department=dept,
                    clearance=clearance,
                    date="2026-10-28",
                    title=file_path.stem.replace("_", " ").title(),
                    file_format="pdf",
                    page_number=page_num,
                    section_title=f"Page {page_num}",
                )

                chunk = DocumentChunk(
                    chunk_id=f"{doc_id}_p{page_num}",
                    text=clean_text,
                    metadata=meta,
                    token_count=len(clean_text.split()),
                )
                chunks.append(chunk)

            logger.info("Extracted %d pages from PDF %s", len(chunks), file_path.name)
            return chunks
        except Exception as e:
            logger.error("Failed to extract PDF %s: %s", file_path, str(e))
            raise DocumentExtractionError(f"PDF extraction failed for {file_path}: {e}") from e


class CSVExtractor(BaseExtractor):
    """Extracts and serializes structured tabular CSV records into descriptive chunks."""

    def extract(
        self,
        file_path: Path,
        override_department: Optional[Department] = None,
        override_clearance: Optional[ClearanceTier] = None,
    ) -> List[DocumentChunk]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentExtractionError(f"CSV file not found: {file_path}")

        chunks: List[DocumentChunk] = []
        try:
            doc_id = f"DOC-CSV-{file_path.stem.upper()}"
            default_dept = override_department or self.infer_department_from_path(file_path)

            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=1):
                    # Check row-level clearance if present
                    row_clearance_str = row.get("clearance", "").upper()
                    if row_clearance_str and row_clearance_str in ClearanceTier.__members__:
                        clearance = ClearanceTier[row_clearance_str]
                    else:
                        clearance = override_clearance or ClearanceTier.L2_RESTRICTED

                    # Row department
                    row_dept_str = row.get("department", "").lower()
                    try:
                        dept = Department(row_dept_str)
                    except ValueError:
                        dept = default_dept

                    # Format human-readable enterprise record string
                    fields_repr = " | ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in row.items())
                    text_content = f"Record [{file_path.name} Row {row_idx}] - {fields_repr}"

                    meta = DocumentMetadata(
                        doc_id=doc_id,
                        source_file=file_path.name,
                        department=dept,
                        clearance=clearance,
                        date=row.get("date", "2026-10-28"),
                        title=f"{file_path.stem.replace('_', ' ').title()} - Row {row_idx}",
                        file_format="csv",
                        row_number=row_idx,
                        custom_attributes={k: str(v) for k, v in row.items()},
                    )

                    chunk = DocumentChunk(
                        chunk_id=f"{doc_id}_r{row_idx}",
                        text=text_content,
                        metadata=meta,
                        token_count=len(text_content.split()),
                    )
                    chunks.append(chunk)

            logger.info("Extracted %d records from CSV %s", len(chunks), file_path.name)
            return chunks
        except Exception as e:
            logger.error("Failed to extract CSV %s: %s", file_path, str(e))
            raise DocumentExtractionError(f"CSV extraction failed for {file_path}: {e}") from e


class MarkdownExtractor(BaseExtractor):
    """Extracts Markdown documents with YAML frontmatter and section hierarchy awareness."""

    def extract(
        self,
        file_path: Path,
        override_department: Optional[Department] = None,
        override_clearance: Optional[ClearanceTier] = None,
    ) -> List[DocumentChunk]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentExtractionError(f"Markdown file not found: {file_path}")

        chunks: List[DocumentChunk] = []
        try:
            content = file_path.read_text(encoding="utf-8")
            frontmatter_dict: Dict[str, str] = {}
            body = content

            # Parse optional YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    raw_frontmatter = parts[1]
                    body = parts[2].strip()
                    for line in raw_frontmatter.strip().split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            frontmatter_dict[k.strip()] = v.strip().strip('"\'')

            doc_id = frontmatter_dict.get("document_id", f"DOC-MD-{file_path.stem.upper()}")

            # Department resolution
            dept_val = frontmatter_dict.get("department", "").lower()
            try:
                dept = Department(dept_val)
            except ValueError:
                dept = override_department or self.infer_department_from_path(file_path)

            # Clearance resolution
            clearance_val = frontmatter_dict.get("clearance", "").upper()
            try:
                clearance = ClearanceTier[clearance_val]
            except KeyError:
                clearance = override_clearance or self.infer_clearance_from_text(content)

            # Partition body by Markdown headings
            sections = re.split(r"\n(?=#{1,3}\s+)", body)
            for idx, sec in enumerate(sections):
                clean_sec = sec.strip()
                if not clean_sec:
                    continue

                lines = clean_sec.split("\n")
                section_title = lines[0].lstrip("#").strip() if lines[0].startswith("#") else f"Section {idx+1}"

                meta = DocumentMetadata(
                    doc_id=doc_id,
                    source_file=file_path.name,
                    department=dept,
                    clearance=clearance,
                    date=frontmatter_dict.get("date", "2026-10-28"),
                    author=frontmatter_dict.get("author", "Engineering Directorate"),
                    title=frontmatter_dict.get("title", file_path.stem.replace("_", " ").title()),
                    file_format="markdown",
                    section_title=section_title,
                )

                chunk = DocumentChunk(
                    chunk_id=f"{doc_id}_s{idx+1}",
                    text=clean_sec,
                    metadata=meta,
                    token_count=len(clean_sec.split()),
                )
                chunks.append(chunk)

            logger.info("Extracted %d sections from Markdown %s", len(chunks), file_path.name)
            return chunks
        except Exception as e:
            logger.error("Failed to extract Markdown %s: %s", file_path, str(e))
            raise DocumentExtractionError(f"Markdown extraction failed for {file_path}: {e}") from e


class ExtractorFactory:
    """Factory to dispatch appropriate extractor based on file extension."""

    _registry = {
        ".pdf": PDFExtractor,
        ".csv": CSVExtractor,
        ".md": MarkdownExtractor,
        ".txt": MarkdownExtractor,
    }

    @classmethod
    def get_extractor(cls, file_path: Path) -> BaseExtractor:
        ext = file_path.suffix.lower()
        extractor_cls = cls._registry.get(ext)
        if not extractor_cls:
            raise DocumentExtractionError(f"Unsupported document format '{ext}' for file: {file_path}")
        return extractor_cls()
