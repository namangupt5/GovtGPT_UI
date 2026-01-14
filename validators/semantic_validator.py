"""
Semantic Validator Module
Validates semantic consistency and cross-lingual similarity.
Uses FREE/LOCAL libraries: sentence-transformers, langdetect, pyarabic.
"""

import logging
from typing import Any, Union

from validators.base_validator import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


class SemanticValidator(BaseValidator):
    """
    Validates semantic consistency and cross-lingual similarity.

    Uses:
    - sentence-transformers for multilingual embeddings (FREE/LOCAL)
    - langdetect for language detection (FREE/LOCAL)
    - pyarabic for Arabic text processing (FREE/LOCAL)
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        super().__init__("SemanticValidator")
        self._model_name = model_name
        self._model = None

    def _lazy_load_model(self):
        """Lazy load sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading multilingual model: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

    def validate(
        self,
        prompt: str,
        response: Union[str, Any],  # Can accept ResponseData or string
        min_similarity: float = 0.75,
        **kwargs,
    ) -> ValidationResult:
        """Validate semantic consistency of response."""
        logger.info("Running semantic validation")

        # Handle ResponseData or string
        if hasattr(response, "full_text"):
            response_text = response.full_text
        else:
            response_text = str(response)

        details = {"min_similarity_required": min_similarity, "checks": []}
        errors = []

        # Coherence check
        coherence = self._check_internal_coherence(response_text)
        details["coherence"] = coherence
        details["checks"].append({"coherence": coherence.get("score", 0.5)})

        # Alignment check
        alignment = self._check_prompt_response_alignment(prompt, response_text)
        details["alignment"] = alignment
        details["checks"].append({"alignment": alignment.get("score", 0.5)})

        # Language detection
        lang_info = self._detect_language(response_text)
        details["language"] = lang_info

        # Arabic validation if detected
        if lang_info.get("is_arabic", False):
            arabic_check = self._validate_arabic(response_text)
            details["arabic_validation"] = arabic_check

        # Overall score
        overall_score = (coherence.get("score", 0.5) + alignment.get("score", 0.5)) / 2
        details["overall_score"] = overall_score

        passed = overall_score >= min_similarity

        if not passed:
            if alignment.get("score", 0) < 0.5:
                errors.append(f"Low alignment score: {alignment.get('score', 0):.2f}")

        return self._create_result(
            passed=passed, score=overall_score, threshold=min_similarity, details=details, errors=errors
        )

    def _check_internal_coherence(self, text: str) -> dict[str, Any]:
        """Check internal coherence of text."""
        self._lazy_load_model()

        if self._model is None:
            return {"available": False, "score": 0.5}

        try:
            import re

            import numpy as np

            sentences = re.split(r"[.!?]+", text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

            if len(sentences) < 2:
                return {"available": True, "score": 0.8, "note": "Single sentence"}

            embeddings = self._model.encode(sentences)

            similarities = []
            for i in range(len(embeddings) - 1):
                sim = np.dot(embeddings[i], embeddings[i + 1]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
                )
                similarities.append(float(sim))

            avg_sim = sum(similarities) / len(similarities) if similarities else 0.5
            score = (avg_sim + 1) / 2

            return {"available": True, "score": score, "avg_similarity": avg_sim, "sentence_count": len(sentences)}
        except Exception as e:
            logger.warning(f"Coherence check failed: {e}")
            return {"available": False, "score": 0.5, "error": str(e)}

    def _check_prompt_response_alignment(self, prompt: str, response: str) -> dict[str, Any]:
        """Check semantic alignment between prompt and response."""
        self._lazy_load_model()

        if self._model is None:
            return {"available": False, "score": 0.5}

        try:
            import numpy as np

            embeddings = self._model.encode([prompt, response])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            score = float(max(0, min(1, (similarity + 1) / 2)))

            return {"available": True, "score": score, "raw_similarity": float(similarity)}
        except Exception as e:
            logger.warning(f"Alignment check failed: {e}")
            return {"available": False, "score": 0.5, "error": str(e)}

    def _detect_language(self, text: str) -> dict[str, Any]:
        """Detect language of text."""
        try:
            from langdetect import detect, detect_langs

            lang = detect(text)
            probs = detect_langs(text)

            return {
                "detected": lang,
                "is_arabic": lang == "ar",
                "is_english": lang == "en",
                "confidence": probs[0].prob if probs else 0.0,
            }
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            # Fallback: check for Arabic characters
            arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
            total_alpha = len([c for c in text if c.isalpha()])
            is_arabic = (arabic_chars / total_alpha) > 0.5 if total_alpha > 0 else False
            return {
                "detected": "ar" if is_arabic else "en",
                "is_arabic": is_arabic,
                "is_english": not is_arabic,
                "method": "fallback",
            }

    def _validate_arabic(self, text: str) -> dict[str, Any]:
        """Validate Arabic text using pyarabic."""
        result = {"rtl_correct": True}

        try:
            import pyarabic.araby as araby

            # Check if text contains Arabic
            arabic_text = araby.strip_tashkeel(text)
            is_arabic = araby.is_arabicrange(text)

            # Count Arabic words
            words = text.split()
            arabic_words = [w for w in words if any("\u0600" <= c <= "\u06ff" for c in w)]

            result["arabic_word_count"] = len(arabic_words)
            result["total_words"] = len(words)
            result["arabic_ratio"] = len(arabic_words) / len(words) if words else 0
            result["pyarabic_available"] = True

            return result
        except Exception as e:
            logger.warning(f"Arabic validation failed: {e}")
            result["pyarabic_available"] = False
            result["error"] = str(e)
            return result

    def calculate_cross_lingual_similarity(
        self, text_en: str, text_ar: str, min_similarity: float = 0.8
    ) -> tuple[bool, float, dict]:
        """Calculate semantic similarity between English and Arabic texts."""
        self._lazy_load_model()

        if self._model is None:
            return False, 0.5, {"error": "Model not available"}

        try:
            import numpy as np

            embeddings = self._model.encode([text_en, text_ar])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            score = float((similarity + 1) / 2)
            passed = score >= min_similarity

            return passed, score, {"raw_similarity": float(similarity), "threshold": min_similarity}
        except Exception as e:
            logger.warning(f"Cross-lingual similarity failed: {e}")
            return False, 0.0, {"error": str(e)}
