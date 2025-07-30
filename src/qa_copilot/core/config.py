import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages configuration for QA Copilot"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config = self._load_config()

    def _get_default_config_path(self) -> Path:
        """Get default configuration path"""
        # Check environment variable first
        if env_path := os.getenv("QA_COPILOT_CONFIG"):
            return Path(env_path)

        # Check common locations
        locations = [
            Path.cwd() / "qa-copilot.yaml",
            Path.cwd() / ".qa-copilot" / "config.yaml",
            Path.home() / ".qa-copilot" / "config.yaml",
        ]

        for location in locations:
            if location.exists():
                return location

        # Return default location
        return Path.home() / ".qa-copilot" / "config.yaml"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.config_path.exists():
            return self._get_default_config()

        with open(self.config_path, 'r') as f:
            if self.config_path.suffix == '.yaml':
                return yaml.safe_load(f)
            elif self.config_path.suffix == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {self.config_path.suffix}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "general": {
                "log_level": "INFO",
                "parallel_execution": True,
                "max_workers": 4,
                "screenshot_on_failure": True,
                "video_recording": False,
            },
            "detector": {
                "strategies": ["dom", "heuristic", "ocr", "ml"],
                "timeout": 30,
                "retry_count": 3,
                "use_ai": False,
            },
            "bdd": {
                "template_path": "templates/bdd",
                "expansion_level": "medium",  # minimal, medium, comprehensive
                "use_ai": False,
            },
            "executor": {
                "default_browser": "chromium",
                "headless": False,
                "slow_mo": 0,
                "viewport": {"width": 1280, "height": 720},
            },
            "analyzer": {
                "capture_screenshots": True,
                "capture_dom": True,
                "use_ai": False,
            },
            "datagen": {
                "locale": "en_US",
                "seed": None,
                "providers": ["faker", "patterns"],
            },
            "reporter": {
                "formats": ["html", "json"],
                "include_screenshots": True,
                "include_logs": True,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self) -> None:
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            if self.config_path.suffix == '.yaml':
                yaml.dump(self._config, f, default_flow_style=False)
            elif self.config_path.suffix == '.json':
                json.dump(self._config, f, indent=2)

    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """Get configuration for a specific module"""
        return self.get(module_name, {})