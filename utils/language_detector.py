"""
Language Detector Module
Handles language detection and semantic similarity using HuggingFace/Sentence-Transformers.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Language detection and semantic similarity calculator using transformer models.
    Supports multilingual analysis for English and Arabic.
    """

    def __init__(self, model_name: str | None = None):
        """
        Initialize language detector.

        Args:
            model_name: HuggingFace model name for embeddings
        """
        from utils.config_loader import config

        if model_name is None:
            model_name = config.get(
                "ai_validation.semantic_similarity.model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )

        self.model_name = model_name
        self._model = None
        self._language_detector = None

    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading sentence transformer model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise

    def _load_language_detector(self):
        """Lazy load the language detection model."""
        if self._language_detector is None:
            try:
                from langdetect import detect, detect_langs

                self._language_detector = detect
                self._language_detector_probs = detect_langs
            except ImportError:
                logger.warning("langdetect not available, using fallback")
                self._language_detector = self._fallback_detect
                self._language_detector_probs = self._fallback_detect_probs

    def _fallback_detect(self, text: str) -> str:
        """Fallback language detection using character analysis."""
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        total_chars = len([c for c in text if c.isalpha()])

        if total_chars == 0:
            return "en"

        arabic_ratio = arabic_chars / total_chars
        return "ar" if arabic_ratio > 0.5 else "en"

    def _fallback_detect_probs(self, text: str) -> list:
        """Fallback language detection with probabilities."""
        lang = self._fallback_detect(text)

        class LangProb:
            def __init__(self, lang, prob):
                self.lang = lang
                self.prob = prob

        if lang == "ar":
            return [LangProb("ar", 0.9), LangProb("en", 0.1)]
        return [LangProb("en", 0.9), LangProb("ar", 0.1)]

    def detect_language(self, text: str) -> str:
        """
        Detect the primary language of text.

        Args:
            text: Text to analyze

        Returns:
            Language code ('en', 'ar', etc.)
        """
        self._load_language_detector()

        try:
            return self._language_detector(text)
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return self._fallback_detect(text)

    def detect_language_with_confidence(self, text: str) -> tuple[str, float]:
        """
        Detect language with confidence score.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (language_code, confidence)
        """
        self._load_language_detector()

        try:
            probs = self._language_detector_probs(text)
            if probs:
                return probs[0].lang, probs[0].prob
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")

        lang = self._fallback_detect(text)
        return lang, 0.8

    def is_arabic(self, text: str) -> bool:
        """Check if text is primarily Arabic."""
        return self.detect_language(text) == "ar"

    def is_english(self, text: str) -> bool:
        """Check if text is primarily English."""
        return self.detect_language(text) == "en"

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Numpy array of embeddings
        """
        self._load_model()
        return self._model.encode(text, convert_to_numpy=True)

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        Get embedding vectors for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            Numpy array of embeddings (batch)
        """
        self._load_model()
        return self._model.encode(texts, convert_to_numpy=True)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Cosine similarity score (0-1)
        """
        self._load_model()

        embeddings = self._model.encode([text1, text2], convert_to_numpy=True)

        # Calculate cosine similarity
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )

        return float(similarity)

    def calculate_cross_lingual_similarity(self, text_en: str, text_ar: str) -> float:
        """
        Calculate semantic similarity between English and Arabic texts.
        Uses multilingual model for cross-lingual comparison.

        Args:
            text_en: English text
            text_ar: Arabic text

        Returns:
            Cosine similarity score (0-1)
        """
        return self.calculate_similarity(text_en, text_ar)

    def find_most_similar(self, query: str, candidates: list[str]) -> tuple[int, float, str]:
        """
        Find the most similar text from a list of candidates.

        Args:
            query: Query text
            candidates: List of candidate texts

        Returns:
            Tuple of (index, similarity_score, matched_text)
        """
        self._load_model()

        query_embedding = self._model.encode(query, convert_to_numpy=True)
        candidate_embeddings = self._model.encode(candidates, convert_to_numpy=True)

        # Calculate similarities
        similarities = []
        for emb in candidate_embeddings:
            sim = np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            similarities.append(float(sim))

        max_idx = np.argmax(similarities)
        return int(max_idx), similarities[max_idx], candidates[max_idx]

    def validate_response_consistency(
        self, response_en: str, response_ar: str, min_similarity: float = 0.7
    ) -> tuple[bool, float]:
        """
        Validate that English and Arabic responses are semantically consistent.

        Args:
            response_en: English response
            response_ar: Arabic response
            min_similarity: Minimum required similarity score

        Returns:
            Tuple of (is_consistent, similarity_score)
        """
        similarity = self.calculate_cross_lingual_similarity(response_en, response_ar)
        is_consistent = similarity >= min_similarity

        logger.info(f"Cross-lingual consistency: {similarity:.3f} (threshold: {min_similarity})")

        return is_consistent, similarity

    def validate_rtl_text(self, text: str) -> dict:
        """
        Validate RTL (Right-to-Left) text properties for Arabic.

        Args:
            text: Text to validate

        Returns:
            Dictionary with validation results
        """
        result = {
            "is_rtl": False,
            "has_arabic_chars": False,
            "arabic_char_ratio": 0.0,
            "mixed_direction": False,
            "issues": [],
        }

        # Count Arabic characters
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        total_alpha = len([c for c in text if c.isalpha()])

        if total_alpha > 0:
            result["arabic_char_ratio"] = arabic_chars / total_alpha

        result["has_arabic_chars"] = arabic_chars > 0
        result["is_rtl"] = result["arabic_char_ratio"] > 0.5

        # Check for mixed direction issues
        english_chars = sum(1 for c in text if "A" <= c <= "Z" or "a" <= c <= "z")
        if arabic_chars > 0 and english_chars > 0:
            result["mixed_direction"] = True
            if result["arabic_char_ratio"] > 0.3 and result["arabic_char_ratio"] < 0.7:
                result["issues"].append("Significant mixed LTR/RTL content detected")

        return result
