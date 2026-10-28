"""Semantic and structure-aware chunking with metadata preservation.

Splits larger documents into semantically coherent windows while ensuring
tenant boundaries, security clearances, and exact page citations remain intact.
"""
import re
from typing import List
from src.core.config import get_settings
from src.core.logger import get_logger
from src.etl.extractors import DocumentChunk, DocumentMetadata

logger = get_logger("etl.splitters")


class SemanticChunker:
    """Structure-aware semantic chunker that splits text on paragraph/sentence boundaries."""

    def __init__(self, max_tokens: int = None, overlap_tokens: int = None):
        settings = get_settings()
        self.max_tokens = max_tokens or settings.MAX_CHUNK_TOKENS
        self.overlap_tokens = overlap_tokens or settings.CHUNK_OVERLAP_TOKENS

    def chunk(self, raw_chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Processes extracted units, splitting items exceeding max_tokens while preserving metadata."""
        refined_chunks: List[DocumentChunk] = []

        for unit in raw_chunks:
            words = unit.text.split()
            if len(words) <= self.max_tokens:
                unit.token_count = len(words)
                refined_chunks.append(unit)
                continue

            # Need to split into overlapping windows along sentences
            sub_chunks = self._split_text_with_overlap(unit.text, unit.metadata, unit.chunk_id)
            refined_chunks.extend(sub_chunks)

        logger.debug("Transformed %d raw units into %d semantic chunks", len(raw_chunks), len(refined_chunks))
        return refined_chunks

    def _split_text_with_overlap(
        self,
        text: str,
        metadata: DocumentMetadata,
        base_chunk_id: str,
    ) -> List[DocumentChunk]:
        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.?!])\s+", text)
        chunks: List[DocumentChunk] = []
        current_words: List[str] = []
        sub_idx = 1

        for sent in sentences:
            sent_words = sent.split()
            if len(current_words) + len(sent_words) <= self.max_tokens:
                current_words.extend(sent_words)
            else:
                if current_words:
                    chunk_text = " ".join(current_words)
                    new_meta = DocumentMetadata(
                        doc_id=metadata.doc_id,
                        source_file=metadata.source_file,
                        department=metadata.department,
                        clearance=metadata.clearance,
                        date=metadata.date,
                        author=metadata.author,
                        title=metadata.title,
                        file_format=metadata.file_format,
                        page_number=metadata.page_number,
                        row_number=metadata.row_number,
                        section_title=metadata.section_title,
                        custom_attributes=metadata.custom_attributes.copy(),
                    )
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{base_chunk_id}_c{sub_idx}",
                            text=chunk_text,
                            metadata=new_meta,
                            token_count=len(current_words),
                        )
                    )
                    sub_idx += 1
                    # Retain overlap words
                    current_words = current_words[-self.overlap_tokens:] + sent_words if self.overlap_tokens > 0 else sent_words
                else:
                    # Single sentence larger than max_tokens: hard split
                    current_words = sent_words[:self.max_tokens]

        if current_words:
            chunk_text = " ".join(current_words)
            new_meta = DocumentMetadata(
                doc_id=metadata.doc_id,
                source_file=metadata.source_file,
                department=metadata.department,
                clearance=metadata.clearance,
                date=metadata.date,
                author=metadata.author,
                title=metadata.title,
                file_format=metadata.file_format,
                page_number=metadata.page_number,
                row_number=metadata.row_number,
                section_title=metadata.section_title,
                custom_attributes=metadata.custom_attributes.copy(),
            )
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{base_chunk_id}_c{sub_idx}",
                    text=chunk_text,
                    metadata=new_meta,
                    token_count=len(current_words),
                )
            )

        return chunks

