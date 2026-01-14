"""
Configuration Loader Module
Handles loading and merging configuration from YAML files and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


class ConfigLoader:
    """
    Singleton class for loading and managing application configuration.
    Supports environment-specific overrides and .env file loading.
    """

    _instance: Optional["ConfigLoader"] = None
    _config: dict[str, Any] = {}

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._load_environment()
        self._load_config()

    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)

    def _load_config(self) -> None:
        """Load base configuration and environment-specific overrides."""
        config_dir = Path(__file__).parent.parent / "config"

        # Load base config
        base_config_path = config_dir / "config.yaml"
        if base_config_path.exists():
            with open(base_config_path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

        # Load environment-specific config
        env = os.getenv("TEST_ENV", "staging")
        env_config_path = config_dir / "environments" / f"{env}.yaml"

        if env_config_path.exists():
            with open(env_config_path, encoding="utf-8") as f:
                env_config = yaml.safe_load(f) or {}
                self._merge_config(self._config, env_config)

    def _merge_config(self, base: dict, override: dict) -> None:
        """Recursively merge override config into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key in dot notation (e.g., 'browser.headless')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_env(self, key: str, default: str = "") -> str:
        """
        Get environment variable value.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)

    @property
    def base_url(self) -> str:
        """Get application base URL."""
        return self.get_env("UASK_BASE_URL", self.get("application.base_url", ""))

    @property
    def username(self) -> str:
        """Get application username."""
        return self.get_env("UASK_USERNAME", "")

    @property
    def password(self) -> str:
        """Get application password."""
        return self.get_env("UASK_PASSWORD", "")

    @property
    def huggingface_token(self) -> str:
        """Get HuggingFace Hub token (optional, for private models)."""
        return self.get_env("HUGGINGFACE_HUB_TOKEN", "")

    @property
    def browser_config(self) -> dict[str, Any]:
        """Get browser configuration."""
        return self.get("browser", {})

    @property
    def ai_validation_config(self) -> dict[str, Any]:
        """Get AI validation configuration."""
        return self.get("ai_validation", {})

    @property
    def security_config(self) -> dict[str, Any]:
        """Get security validation configuration."""
        return self.get("security", {})

    @property
    def is_headless(self) -> bool:
        """Check if browser should run in headless mode."""
        env_headless = self.get_env("HEADLESS_MODE", "").lower()
        if env_headless:
            return env_headless == "true"
        return self.get("browser.headless", False)

    def reload(self) -> None:
        """Reload configuration from files."""
        self._load_environment()
        self._load_config()

    def to_dict(self) -> dict[str, Any]:
        """Return full configuration as dictionary."""
        return self._config.copy()


# Global config instance
config = ConfigLoader()
