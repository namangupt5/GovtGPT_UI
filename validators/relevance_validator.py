"""
Relevance Validator Module
Validates AI response relevance to the prompt.
Uses FREE/LOCAL libraries: sentence-transformers, bert-score.
"""

import logging
from typing import Any, Union

from validators.base_validator import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


class RelevanceValidator(BaseValidator):
    """
    Validates AI response relevance using semantic similarity.

    Uses:
    - sentence-transformers for semantic embeddings (FREE/LOCAL)
    - bert-score for text similarity (FREE/LOCAL)
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        super().__init__("RelevanceValidator")
        self._model_name = model_name
        self._model = None

    def _lazy_load_model(self):
        """Lazy load sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading model: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

    def validate(
        self,
        prompt: str,
        response: Union[str, Any],  # Can accept ResponseData or string
        min_score: float = 0.7,
        **kwargs,
    ) -> ValidationResult:
        """Validate response relevance to prompt."""
        logger.info("Running relevance validation")

        # Handle ResponseData or string
        if hasattr(response, "full_text"):
            response_text = response.full_text
            paragraphs = getattr(response, "paragraphs", [])
            word_count = getattr(response, "word_count", len(response_text.split()))
        else:
            response_text = str(response)
            paragraphs = [p.strip() for p in response_text.split("\n\n") if p.strip()]
            word_count = len(response_text.split())

        details = {
            "min_score_required": min_score,
            "paragraph_count": len(paragraphs),
            "word_count": word_count,
            "checks": [],
        }
        errors = []

        # Semantic similarity
        semantic_score = self._calculate_semantic_similarity(prompt, response_text)
        details["semantic_similarity"] = semantic_score
        details["checks"].append({"semantic": semantic_score})

        # Per-paragraph relevance (if multiple paragraphs)
        if len(paragraphs) > 1:
            para_scores = []
            for i, para in enumerate(paragraphs[:5]):  # Check first 5 paragraphs
                para_score = self._calculate_semantic_similarity(prompt, para)
                para_scores.append({"paragraph": i, "score": para_score})
            details["paragraph_relevance"] = para_scores

        # Keyword coverage
        keyword_score = self._calculate_keyword_coverage(prompt, response_text)
        details["keyword_coverage"] = keyword_score
        details["checks"].append({"keywords": keyword_score})

        # Response length check
        length_score = self._evaluate_response_length(response_text)
        details["length_score"] = length_score

        # Overall score
        overall_score = semantic_score * 0.5 + keyword_score * 0.3 + length_score * 0.2
        details["overall_score"] = overall_score

        passed = overall_score >= min_score

        if not passed:
            if semantic_score < 0.5:
                errors.append(f"Low semantic similarity: {semantic_score:.2f}")
            if keyword_score < 0.3:
                errors.append(f"Low keyword coverage: {keyword_score:.2f}")

        return self._create_result(
            passed=passed, score=overall_score, threshold=min_score, details=details, errors=errors
        )

    def _calculate_semantic_similarity(self, prompt: str, response: str) -> float:
        """Calculate semantic similarity using sentence-transformers."""
        self._lazy_load_model()

        if self._model is None:
            return self._fallback_similarity(prompt, response)

        try:
            import numpy as np

            embeddings = self._model.encode([prompt, response])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(max(0, min(1, (similarity + 1) / 2)))
        except Exception as e:
            logger.warning(f"Semantic similarity failed: {e}")
            return self._fallback_similarity(prompt, response)

    def _fallback_similarity(self, prompt: str, response: str) -> float:
        """Fallback similarity using word overlap."""
        prompt_words = set(prompt.lower().split())
        response_words = set(response.lower().split())
        if not prompt_words:
            return 0.0
        overlap = prompt_words & response_words
        return len(overlap) / len(prompt_words)

    def _calculate_keyword_coverage(self, prompt: str, response: str) -> float:
        """Calculate keyword coverage."""
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "i",
            "me",
            "my",
            "you",
            "your",
            "he",
            "she",
            "it",
            "we",
            "they",
            "what",
            "which",
            "who",
            "how",
            "when",
            "where",
            "why",
            "and",
            "but",
            "if",
            "or",
            "because",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

        prompt_words = set(w.lower() for w in prompt.split() if w.lower() not in stop_words and len(w) > 2)
        response_lower = response.lower()

        if not prompt_words:
            return 0.5

        covered = sum(1 for w in prompt_words if w in response_lower)
        return covered / len(prompt_words)

    def _evaluate_response_length(self, response: str) -> float:
        """Evaluate response length appropriateness."""
        word_count = len(response.split())
        if word_count < 10:
            return 0.3
        elif word_count < 30:
            return 0.6
        elif word_count < 300:
            return 1.0
        else:
            return 0.7
