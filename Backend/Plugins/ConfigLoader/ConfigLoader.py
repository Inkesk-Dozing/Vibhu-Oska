"""
Vibhu-Oska AI-OS — Configuration Loader
Hierarchical YAML configuration with environment variable overrides.

Config resolution order (last wins):
  1. config/default.yaml          — base defaults
  2. config/{environment}.yaml    — environment-specific overrides
  3. Environment variables         — VIBHU_OSKA__section__key format
  4. .env file                     — local development overrides
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigLoader:
    """
    Singleton configuration manager for the Vibhu-Oska AI-OS.

    Usage:
        config = ConfigLoader.load()
        port = config.get("gateway.port", 8000)
    """

    _instance: ConfigLoader | None = None
    _data: dict[str, Any] = {}

    # ══════════════════════════════════════════════════════════════════════
    # Singleton Access
    # ══════════════════════════════════════════════════════════════════════

    @classmethod
    def load(cls, project_root: Path | None = None) -> ConfigLoader:
        """Load or return the singleton configuration instance."""
        if cls._instance is not None:
            return cls._instance

        instance = cls()
        instance._project_root = project_root or cls._find_project_root()
        instance._load_all()
        cls._instance = instance
        return instance

    @classmethod
    def reload(cls) -> ConfigLoader:
        """Force reload all configuration from disk."""
        cls._instance = None
        return cls.load()

    # ══════════════════════════════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════════════════════════════

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a config value using dot-notation.

        Examples:
            config.get("gateway.port")           → 8000
            config.get("models.router.layers")    → 12
            config.get("nonexistent", "fallback") → "fallback"
        """
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire configuration section as a dictionary."""
        result = self.get(section)
        if isinstance(result, dict):
            return result
        return {}

    @property
    def environment(self) -> str:
        """Current environment name (development, staging, production)."""
        return os.getenv("VIBHU_OSKA_ENV", "development")

    @property
    def project_root(self) -> Path:
        """Absolute path to the project root directory."""
        return self._project_root

    @property
    def data(self) -> dict[str, Any]:
        """Raw configuration dictionary."""
        return self._data.copy()

    # ══════════════════════════════════════════════════════════════════════
    # Internal Loading
    # ══════════════════════════════════════════════════════════════════════

    def _load_all(self) -> None:
        """Execute the full configuration resolution chain."""
        # 1. Load .env file (for local dev)
        env_file = self._project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # 2. Load default.yaml
        config_dir = self._project_root / "config"
        self._data = self._load_yaml(config_dir / "default.yaml")

        # 3. Merge environment-specific overrides
        env_config = self._load_yaml(config_dir / f"{self.environment}.yaml")
        self._deep_merge(self._data, env_config)

        # 4. Apply environment variable overrides
        self._apply_env_overrides()

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a YAML file, returning empty dict if it doesn't exist."""
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}

    def _deep_merge(self, base: dict, override: dict) -> None:
        """Recursively merge override dict into base dict (mutates base)."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self) -> None:
        """
        Apply environment variable overrides.
        Format: VIBHU_OSKA__section__key=value
        Double underscores separate nesting levels.
        """
        prefix = "VIBHU_OSKA__"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split("__")
                self._set_nested(self._data, parts, self._parse_value(value))

    def _set_nested(self, data: dict, keys: list[str], value: Any) -> None:
        """Set a value in a nested dictionary using a list of keys."""
        for key in keys[:-1]:
            data = data.setdefault(key, {})
        data[keys[-1]] = value

    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse string values into appropriate Python types."""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    @staticmethod
    def _find_project_root() -> Path:
        """Walk up from CWD to find the project root (contains pyproject.toml)."""
        current = Path.cwd()
        for parent in [current, *current.parents]:
            if (parent / "pyproject.toml").exists():
                return parent
        # Fallback: assume the Backend's grandparent
        return Path(__file__).resolve().parent.parent.parent

    def __repr__(self) -> str:
        return f"<ConfigLoader env='{self.environment}' root='{self._project_root}'>"
