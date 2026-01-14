"""
Excel Reader Module
Handles reading test data from Excel files using pandas.
SINGLE SOURCE OF TRUTH for test prompts - NO hardcoded prompts allowed.
"""

import logging
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TestPrompt:
    """Data class representing a test prompt from Excel."""

    id: str
    prompt_en: str
    expected_intent: str
    risk_level: str  # High, Medium, Low
    multi_turn: bool
    prompt_ar: str = ""
    notes: str = ""

    @property
    def is_high_risk(self) -> bool:
        return self.risk_level.lower() == "high"

    @property
    def is_medium_risk(self) -> bool:
        return self.risk_level.lower() == "medium"

    @property
    def is_low_risk(self) -> bool:
        return self.risk_level.lower() == "low"

    @property
    def is_multi_turn(self) -> bool:
        return self.multi_turn


class ExcelReader:
    """
    Reader class for loading test data from Excel files.
    This is the SINGLE SOURCE OF TRUTH for all test prompts.
    NO hardcoded prompts in code or feature files.
    """

    def __init__(self, file_path: str | None = None, sheet_name: str = "prompts"):
        """
        Initialize Excel reader.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read
        """
        if file_path is None:
            from utils.config_loader import config

            file_path = config.get("test_data.excel_path", "data/uae_gov_chatbot_prompts.xlsx")

        # Handle both absolute and relative paths
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            self.file_path = Path(__file__).parent.parent / file_path
        else:
            self.file_path = file_path_obj

        self.sheet_name = sheet_name
        self._df: pd.DataFrame | None = None
        self._prompts: list[TestPrompt] = []

    def _load_data(self) -> None:
        """Load data from Excel file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Test data file not found: {self.file_path}")

        logger.info(f"Loading test data from: {self.file_path}")

        self._df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)

        # Normalize column names
        self._df.columns = self._df.columns.str.strip()

        self._parse_prompts()

    def _parse_prompts(self) -> None:
        """Parse DataFrame into TestPrompt objects."""
        self._prompts = []

        for _, row in self._df.iterrows():
            prompt = TestPrompt(
                id=str(row.get("ID", "")).strip(),
                prompt_en=str(row.get("Prompt (EN)", "")).strip(),
                expected_intent=str(row.get("Expected Intent", "")).strip(),
                risk_level=str(row.get("Risk Level", "Low")).strip(),
                multi_turn=bool(row.get("Multi-turn", False)),
                prompt_ar=str(row.get("Prompt (AR)", "")).strip() if "Prompt (AR)" in self._df.columns else "",
                notes=str(row.get("Notes", "")).strip() if "Notes" in self._df.columns else "",
            )
            self._prompts.append(prompt)

        logger.info(f"Loaded {len(self._prompts)} test prompts")

    @property
    def prompts(self) -> list[TestPrompt]:
        """Get all test prompts."""
        if not self._prompts:
            self._load_data()
        return self._prompts

    @property
    def dataframe(self) -> pd.DataFrame:
        """Get raw DataFrame."""
        if self._df is None:
            self._load_data()
        return self._df

    def get_prompt_by_id(self, prompt_id: str) -> TestPrompt | None:
        """Get a specific prompt by ID."""
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt
        return None

    def get_prompts_by_risk(self, risk_level: str) -> list[TestPrompt]:
        """Get prompts filtered by risk level."""
        return [p for p in self.prompts if p.risk_level.lower() == risk_level.lower()]

    def get_high_risk_prompts(self) -> list[TestPrompt]:
        """Get all high-risk prompts."""
        return self.get_prompts_by_risk("high")

    def get_medium_risk_prompts(self) -> list[TestPrompt]:
        """Get all medium-risk prompts."""
        return self.get_prompts_by_risk("medium")

    def get_low_risk_prompts(self) -> list[TestPrompt]:
        """Get all low-risk prompts."""
        return self.get_prompts_by_risk("low")

    def get_multi_turn_prompts(self) -> list[TestPrompt]:
        """Get all multi-turn conversation prompts."""
        return [p for p in self.prompts if p.is_multi_turn]

    def get_prompts_by_intent(self, intent: str) -> list[TestPrompt]:
        """Get prompts filtered by expected intent."""
        return [p for p in self.prompts if intent.lower() in p.expected_intent.lower()]

    def iterate_prompts(self, language: str = "en") -> Generator[dict[str, Any], None, None]:
        """
        Iterate over prompts yielding prompt text and metadata.

        Args:
            language: Language code ('en' or 'ar')

        Yields:
            Dictionary with prompt text and metadata
        """
        for prompt in self.prompts:
            yield {
                "id": prompt.id,
                "prompt": prompt.prompt_en if language == "en" else prompt.prompt_ar,
                "language": language,
                "expected_intent": prompt.expected_intent,
                "risk_level": prompt.risk_level,
                "multi_turn": prompt.multi_turn,
                "notes": prompt.notes,
            }

    def get_prompt_text(self, prompt_id: str, language: str = "en") -> str:
        """Get prompt text by ID and language."""
        prompt = self.get_prompt_by_id(prompt_id)
        if prompt:
            return prompt.prompt_en if language == "en" else prompt.prompt_ar
        return ""

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the test data."""
        return {
            "total_prompts": len(self.prompts),
            "high_risk": len(self.get_high_risk_prompts()),
            "medium_risk": len(self.get_medium_risk_prompts()),
            "low_risk": len(self.get_low_risk_prompts()),
            "multi_turn": len(self.get_multi_turn_prompts()),
            "single_turn": len(self.prompts) - len(self.get_multi_turn_prompts()),
        }

    def reload(self) -> None:
        """Reload data from Excel file."""
        self._df = None
        self._prompts = []
        self._load_data()
