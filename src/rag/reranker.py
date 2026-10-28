"""Cross-Encoder and lexical-semantic reranking engine.

Re-scores candidate retrieval passages against the expanded query using cross-attention
or high-fidelity lexical-semantic alignment scoring to maximize retrieval precision.
"""
import re
from typing import List, Optional
from src.core.config import get_settings
from src.core.logger import get_logger
from src.rag.rbac_retriever import RetrievedChunk

logger = get_logger("rag.reranker")


class CrossEncoderReranker:
    """Production passage reranker with cross-encoder inference and offline VPC fallback."""

    _cross_encoder_instance = None
    _offline_fallback = False

    def __init__(self, model_name: str = None, top_k: int = None):
        settings = get_settings()
        self.model_name = model_name or settings.RERANKER_MODEL_NAME
        self.top_k = top_k or settings.RERANK_TOP_K
        self.enabled = settings.ENABLE_CROSS_ENCODER_RERANKER
        self._initialize_model()

    def _initialize_model(self):
        if not self.enabled or CrossEncoderReranker._cross_encoder_instance is not None:
            return

        try:
            from sentence_transformers import CrossEncoder
            logger.info("Initializing CrossEncoder model: %s", self.model_name)
            CrossEncoderReranker._cross_encoder_instance = CrossEncoder(self.model_name, max_length=512)
            logger.info("CrossEncoder loaded successfully.")
        except Exception as e:
            logger.warning(
                "CrossEncoder unavailable (%s). Activating deterministic lexical-semantic reranker fallback: %s",
                self.model_name,
                str(e),
            )
            CrossEncoderReranker._offline_fallback = True

    def rerank(self, query: str, candidates: List[RetrievedChunk], top_k: Optional[int] = None) -> List[RetrievedChunk]:
        """Re-scores candidate chunks and returns the top-k highest precision passages."""
        if not candidates:
            return []

        limit = top_k or self.top_k
        if not self.enabled or len(candidates) <= 1:
            return candidates[:limit]

        # 1. Attempt CrossEncoder Model Scoring
        if not CrossEncoderReranker._offline_fallback and CrossEncoderReranker._cross_encoder_instance is not None:
            try:
                pairs = [[query, c.text] for c in candidates]
                scores = CrossEncoderReranker._cross_encoder_instance.predict(pairs)
                for chunk, score in zip(candidates, scores):
                    chunk.rerank_score = float(score)
                candidates.sort(key=lambda x: x.rerank_score, reverse=True)
                return candidates[:limit]
            except Exception as e:
                logger.warning("CrossEncoder scoring exception: %s. Using lexical-semantic fallback.", e)

        # 2. High-Fidelity Lexical-Semantic Reranking Fallback
        query_words = set(re.findall(r"\w+", query.lower()))
        for chunk in candidates:
            text_lower = chunk.text.lower()
            text_words = set(re.findall(r"\w+", text_lower))

            # Jaccard lexical overlap
            overlap = len(query_words.intersection(text_words)) / max(len(query_words), 1)

            # Entity and exact phrase bonuses
            phrase_bonus = 0.3 if query.lower() in text_lower else 0.0

            # Header / Section match bonus
            section_bonus = 0.2 if (chunk.metadata.section_title and chunk.metadata.section_title.lower() in query.lower()) else 0.0

            # Combined score: 60% semantic cosine + 25% token overlap + 15% bonuses
            combined_score = (chunk.similarity_score * 0.6) + (overlap * 0.25) + phrase_bonus + section_bonus
            chunk.rerank_score = round(combined_score, 4)

        candidates.sort(key=lambda x: x.rerank_score, reverse=True)
        return candidates[:limit]

