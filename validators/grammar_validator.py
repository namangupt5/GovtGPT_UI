"""
Grammar Validator Module
Validates AI response grammar, readability, and clarity.
Uses FREE/LOCAL libraries: textstat.
"""

import logging
import re
from typing import Any

from validators.base_validator import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


class GrammarValidator(BaseValidator):
    """
    Validates AI response grammar and readability.

    Uses:
    - textstat for readability analysis (FREE/LOCAL)
    - Basic pattern matching for structure checks
    """

    def __init__(self):
        super().__init__("GrammarValidator")

    def validate(self, prompt: str, response: str, max_errors: int = 3, **kwargs) -> ValidationResult:
        """Validate response grammar and readability."""
        logger.info("Running grammar validation")

        details = {"checks": []}
        errors = []
        warnings = []

        # Readability check
        readability = self._check_readability(response)
        details["readability"] = readability
        details["checks"].append({"readability": readability})

        # Sentence structure check
        structure = self._check_sentence_structure(response)
        details["structure"] = structure
        details["checks"].append({"structure": structure})

        # Basic grammar patterns
        grammar_issues = self._check_basic_grammar(response)
        details["grammar_issues"] = grammar_issues
        details["checks"].append({"grammar_issues": len(grammar_issues)})

        # Calculate score
        readability_score = min(1.0, readability.get("score", 50) / 100)
        structure_score = 1.0 if structure.get("has_complete_sentences", True) else 0.6
        grammar_score = max(0, 1.0 - len(grammar_issues) * 0.1)

        overall_score = readability_score * 0.4 + structure_score * 0.3 + grammar_score * 0.3
        details["overall_score"] = overall_score

        if len(grammar_issues) > max_errors:
            errors.append(f"Too many grammar issues: {len(grammar_issues)}")

        if readability.get("score", 60) < 30:
            warnings.append(f"Low readability: {readability.get('score', 0):.1f}")

        return self._create_result(
            passed=len(errors) == 0 and overall_score >= 0.6,
            score=overall_score,
            threshold=0.6,
            details=details,
            errors=errors,
            warnings=warnings,
        )

    def _check_readability(self, text: str) -> dict[str, Any]:
        """Check readability using textstat."""
        try:
            import textstat

            flesch_score = textstat.flesch_reading_ease(text)
            grade_level = textstat.flesch_kincaid_grade(text)

            if flesch_score >= 80:
                level = "very_easy"
            elif flesch_score >= 60:
                level = "easy"
            elif flesch_score >= 40:
                level = "moderate"
            elif flesch_score >= 20:
                level = "difficult"
            else:
                level = "very_difficult"

            return {"available": True, "score": flesch_score, "grade_level": grade_level, "level": level}
        except Exception as e:
            logger.warning(f"Readability check failed: {e}")
            return {"available": False, "score": 60, "level": "unknown"}

    def _check_sentence_structure(self, text: str) -> dict[str, Any]:
        """Check basic sentence structure."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        result = {"sentence_count": len(sentences), "has_complete_sentences": True, "issues": []}

        if not sentences:
            result["has_complete_sentences"] = False
            result["issues"].append("No complete sentences")
            return result

        incomplete = sum(1 for s in sentences if len(s.split()) < 3)
        very_long = sum(1 for s in sentences if len(s.split()) > 50)

        if incomplete > len(sentences) * 0.3:
            result["has_complete_sentences"] = False
            result["issues"].append(f"Many incomplete sentences: {incomplete}")

        if very_long > 0:
            result["issues"].append(f"Very long sentences: {very_long}")

        result["avg_length"] = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        return result

    def _check_basic_grammar(self, text: str) -> list[dict[str, str]]:
        """Check for common grammar issues using patterns."""
        issues = []

        patterns = [
            (r"\b(i)\b(?!['])", "Lowercase 'i' should be capitalized"),
            (r"\s{2,}", "Multiple consecutive spaces"),
            (r"[.!?]\s*[a-z]", "Sentence starts with lowercase after punctuation"),
            (
                r"\b(dont|cant|wont|isnt|arent|wasnt|werent|hasnt|havent|hadnt|didnt|doesnt)\b",
                "Missing apostrophe in contraction",
            ),
        ]

        for pattern, message in patterns:
            matches = re.findall(pattern, text)
            if matches:
                issues.append({"pattern": pattern, "message": message, "count": len(matches)})

        return issues
