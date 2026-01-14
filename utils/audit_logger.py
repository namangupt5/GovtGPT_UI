"""
Audit Logger Module
Handles audit trail, explainability, and traceability for government-grade compliance.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Data class for individual validation results."""

    validator_name: str
    score: float
    passed: bool
    threshold: float
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AuditEntry:
    """Data class for complete audit trail entry."""

    # Identification
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    test_id: str = ""
    scenario_name: str = ""

    # Timestamps
    start_time: str = ""
    end_time: str = ""
    duration_ms: int = 0

    # Input
    prompt: str = ""
    prompt_language: str = ""
    prompt_hash: str = ""
    prompt_version: str = "1.0"

    # Output
    response: str = ""
    response_hash: str = ""

    # Model Info
    model_name: str = ""
    model_version: str = ""

    # UI Validations
    ui_validations: dict[str, bool] = field(default_factory=dict)
    scroll_validation: bool = False
    loader_validation: bool = False

    # AI Validations
    relevance_score: float = 0.0
    hallucination_score: float = 0.0
    groundedness_score: float = 0.0
    semantic_similarity_score: float = 0.0
    grammar_score: float = 0.0
    grammar_issues: list[str] = field(default_factory=list)

    # Security Validations
    security_passed: bool = True
    toxicity_score: float = 0.0
    prompt_injection_detected: bool = False
    moderation_categories: dict[str, float] = field(default_factory=dict)

    # Overall Result
    overall_passed: bool = False
    failure_reasons: list[str] = field(default_factory=list)

    # Metadata
    environment: str = ""
    browser: str = ""
    viewport: str = ""
    screenshot_path: str = ""

    # Validation Details
    validation_results: list[dict] = field(default_factory=list)


class AuditLogger:
    """
    Audit logger for government-grade traceability and explainability.
    Captures complete test execution details for compliance reporting.
    """

    def __init__(self, output_dir: str | None = None):
        """
        Initialize audit logger.

        Args:
            output_dir: Directory for audit log files
        """
        from utils.config_loader import config

        if output_dir is None:
            output_dir = config.get("reporting.audit.dir", "reports/audit")

        self.output_dir = Path(__file__).parent.parent / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._current_entry: AuditEntry | None = None
        self._session_entries: list[AuditEntry] = []
        self._session_id = str(uuid.uuid4())[:8]

    def start_scenario(self, test_id: str, scenario_name: str, prompt: str, language: str = "en") -> AuditEntry:
        """
        Start tracking a new test scenario.

        Args:
            test_id: Unique test identifier
            scenario_name: Name of the test scenario
            prompt: User prompt being tested
            language: Prompt language code

        Returns:
            New AuditEntry instance
        """
        from utils.config_loader import config

        self._current_entry = AuditEntry(
            test_id=test_id,
            scenario_name=scenario_name,
            prompt=prompt,
            prompt_language=language,
            prompt_hash=self._hash_text(prompt),
            start_time=datetime.utcnow().isoformat(),
            environment=config.get_env("TEST_ENV", "unknown"),
            browser=config.get("browser.type", "chromium"),
        )

        logger.info(f"Started audit for scenario: {scenario_name} (ID: {test_id})")
        return self._current_entry

    def record_response(self, response: str, model_name: str = "", model_version: str = "") -> None:
        """Record AI response details."""
        if self._current_entry:
            self._current_entry.response = response
            self._current_entry.response_hash = self._hash_text(response)
            self._current_entry.model_name = model_name
            self._current_entry.model_version = model_version

    def record_ui_validation(self, validation_name: str, passed: bool) -> None:
        """Record UI validation result."""
        if self._current_entry:
            self._current_entry.ui_validations[validation_name] = passed

    def record_scroll_validation(self, passed: bool) -> None:
        """Record scroll behavior validation result."""
        if self._current_entry:
            self._current_entry.scroll_validation = passed

    def record_loader_validation(self, passed: bool) -> None:
        """Record loader/spinner validation result."""
        if self._current_entry:
            self._current_entry.loader_validation = passed

    def record_validation_result(self, result: ValidationResult) -> None:
        """
        Record an AI validation result.

        Args:
            result: ValidationResult instance
        """
        if not self._current_entry:
            return

        self._current_entry.validation_results.append(asdict(result))

        # Update specific scores based on validator
        validator_map = {
            "relevance": "relevance_score",
            "hallucination": "hallucination_score",
            "groundedness": "groundedness_score",
            "semantic_similarity": "semantic_similarity_score",
            "grammar": "grammar_score",
        }

        for key, attr in validator_map.items():
            if key in result.validator_name.lower():
                setattr(self._current_entry, attr, result.score)
                break

        if not result.passed:
            self._current_entry.failure_reasons.append(
                f"{result.validator_name}: {result.score:.2f} (threshold: {result.threshold})"
            )

    def record_security_result(
        self,
        passed: bool,
        toxicity_score: float = 0.0,
        prompt_injection: bool = False,
        moderation_categories: dict[str, float] | None = None,
    ) -> None:
        """Record security validation results."""
        if self._current_entry:
            self._current_entry.security_passed = passed
            self._current_entry.toxicity_score = toxicity_score
            self._current_entry.prompt_injection_detected = prompt_injection
            self._current_entry.moderation_categories = moderation_categories or {}

            if not passed:
                if prompt_injection:
                    self._current_entry.failure_reasons.append("Prompt injection detected")
                if toxicity_score > 0.1:
                    self._current_entry.failure_reasons.append(f"Toxicity score: {toxicity_score:.2f}")

    def record_grammar_issues(self, issues: list[str], score: float) -> None:
        """Record grammar validation results."""
        if self._current_entry:
            self._current_entry.grammar_issues = issues
            self._current_entry.grammar_score = score

    def set_screenshot(self, path: str) -> None:
        """Set screenshot path for the current entry."""
        if self._current_entry:
            self._current_entry.screenshot_path = path

    def end_scenario(self, overall_passed: bool) -> AuditEntry:
        """
        End tracking for current scenario.

        Args:
            overall_passed: Overall test result

        Returns:
            Completed AuditEntry
        """
        if not self._current_entry:
            raise ValueError("No active scenario to end")

        self._current_entry.end_time = datetime.utcnow().isoformat()
        self._current_entry.overall_passed = overall_passed

        # Calculate duration
        start = datetime.fromisoformat(self._current_entry.start_time)
        end = datetime.fromisoformat(self._current_entry.end_time)
        self._current_entry.duration_ms = int((end - start).total_seconds() * 1000)

        # Save entry
        self._save_entry(self._current_entry)
        self._session_entries.append(self._current_entry)

        completed_entry = self._current_entry
        self._current_entry = None

        logger.info(f"Completed audit for: {completed_entry.scenario_name} - {'PASS' if overall_passed else 'FAIL'}")
        return completed_entry

    def _hash_text(self, text: str) -> str:
        """Generate SHA-256 hash of text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _save_entry(self, entry: AuditEntry) -> None:
        """Save audit entry to file."""
        filename = f"audit_{entry.test_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(entry), f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved audit entry to: {filepath}")

    def generate_session_report(self) -> dict[str, Any]:
        """Generate summary report for current test session."""
        if not self._session_entries:
            return {}

        total = len(self._session_entries)
        passed = sum(1 for e in self._session_entries if e.overall_passed)
        failed = total - passed

        report = {
            "session_id": self._session_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_scenarios": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{(passed / total) * 100:.1f}%",
            },
            "average_scores": {
                "relevance": self._average_score("relevance_score"),
                "hallucination": self._average_score("hallucination_score"),
                "groundedness": self._average_score("groundedness_score"),
                "semantic_similarity": self._average_score("semantic_similarity_score"),
                "grammar": self._average_score("grammar_score"),
            },
            "security_summary": {
                "injection_attempts": sum(1 for e in self._session_entries if e.prompt_injection_detected),
                "security_failures": sum(1 for e in self._session_entries if not e.security_passed),
            },
            "failed_scenarios": [
                {"test_id": e.test_id, "scenario": e.scenario_name, "reasons": e.failure_reasons}
                for e in self._session_entries
                if not e.overall_passed
            ],
        }

        # Save session report
        report_path = self.output_dir / f"session_report_{self._session_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

    def _average_score(self, field_name: str) -> float:
        """Calculate average score for a field."""
        scores = [getattr(e, field_name) for e in self._session_entries if getattr(e, field_name, 0) > 0]
        return round(sum(scores) / len(scores), 3) if scores else 0.0

    def get_current_entry(self) -> AuditEntry | None:
        """Get the current active audit entry."""
        return self._current_entry

    def to_allure_attachment(self) -> str:
        """Generate Allure-compatible attachment content."""
        if not self._current_entry:
            return ""

        return json.dumps(asdict(self._current_entry), indent=2, ensure_ascii=False)
