"""
Base Validator Module
Abstract base class for all AI validators.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    validator_name: str
    passed: bool
    score: float = 0.0
    threshold: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "validator": self.validator_name,
            "passed": self.passed,
            "score": self.score,
            "threshold": self.threshold,
            "details": self.details,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp,
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{self.validator_name}: {status} (score: {self.score:.2f}, threshold: {self.threshold:.2f})"


class BaseValidator(ABC):
    """
    Abstract base class for all validators.
    All validators must implement the validate() method.
    """

    def __init__(self, name: str):
        self.name = name
        self._initialized = False

    @abstractmethod
    def validate(self, prompt: str, response: str, **kwargs) -> ValidationResult:
        """
        Validate the AI response.

        Args:
            prompt: The original user prompt
            response: The AI-generated response
            **kwargs: Additional validation parameters

        Returns:
            ValidationResult with pass/fail status and details
        """
        pass

    def _create_result(
        self,
        passed: bool,
        score: float = 0.0,
        threshold: float = 0.0,
        details: dict | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> ValidationResult:
        """Helper to create ValidationResult."""
        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            score=score,
            threshold=threshold,
            details=details or {},
            errors=errors or [],
            warnings=warnings or [],
        )

    def _log_validation(self, result: ValidationResult) -> None:
        """Log validation result."""
        if result.passed:
            logger.info(f"{self.name}: PASSED (score: {result.score:.2f})")
        else:
            logger.warning(f"{self.name}: FAILED (score: {result.score:.2f})")
            for error in result.errors:
                logger.warning(f"  - {error}")
