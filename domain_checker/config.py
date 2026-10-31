"""Configuration management."""

import os
import stat
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Config:
    """Application configuration."""

    def __init__(self, config_path: Path | None = None):
        """Initialize configuration.

        Args:
            config_path: Path to config.yaml file. If None, uses config.yaml in current directory.
        """
        self.config_path = config_path or Path("config.yaml")
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from file and environment variables."""
        load_dotenv()

        if self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

        self._override_from_env()

    def _override_from_env(self):
        """Override config values from environment variables."""
        if os.getenv("TRACKER_TYPE"):
            self._ensure_dict("tracker")
            self._config["tracker"]["type"] = os.getenv("TRACKER_TYPE")

        if os.getenv("TRACKER_URL"):
            self._ensure_dict("tracker")
            self._config["tracker"]["url"] = os.getenv("TRACKER_URL")

        if os.getenv("TRACKER_API_KEY"):
            self._ensure_dict("tracker")
            self._config["tracker"]["api_key"] = os.getenv("TRACKER_API_KEY")

        if os.getenv("CUSTOM_HEADER_NAME"):
            self._ensure_dict("tracker", "custom")
            self._config["tracker"]["custom"]["header_name"] = os.getenv(
                "CUSTOM_HEADER_NAME"
            )

        if os.getenv("CUSTOM_DOMAINS_PATH"):
            self._ensure_dict("tracker", "custom")
            self._config["tracker"]["custom"]["domains_path"] = os.getenv(
                "CUSTOM_DOMAINS_PATH"
            )

        if os.getenv("TELEGRAM_BOT_TOKEN"):
            self._ensure_dict("telegram")
            self._config["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")

        if os.getenv("TELEGRAM_CHAT_ID"):
            self._ensure_dict("telegram")
            self._config["telegram"]["chat_id"] = int(os.getenv("TELEGRAM_CHAT_ID"))

        if os.getenv("CHECK_INTERVAL_MINUTES"):
            self._ensure_dict("checker")
            self._config["checker"]["interval_minutes"] = int(
                os.getenv("CHECK_INTERVAL_MINUTES")
            )

        if os.getenv("CONSECUTIVE_FAILURES_THRESHOLD"):
            self._ensure_dict("checker")
            self._config["checker"]["consecutive_failures_threshold"] = int(
                os.getenv("CONSECUTIVE_FAILURES_THRESHOLD")
            )

        if os.getenv("SSL_WARNING_DAYS"):
            self._ensure_dict("checker")
            self._config["checker"]["ssl_warning_days"] = int(
                os.getenv("SSL_WARNING_DAYS")
            )

        if os.getenv("MAX_CONCURRENT_CHECKS"):
            self._ensure_dict("checker")
            self._config["checker"]["max_concurrent_checks"] = int(
                os.getenv("MAX_CONCURRENT_CHECKS")
            )

        if os.getenv("REQUEST_TIMEOUT_SECONDS"):
            self._ensure_dict("checker")
            self._config["checker"]["request_timeout_seconds"] = int(
                os.getenv("REQUEST_TIMEOUT_SECONDS")
            )

        if os.getenv("DATABASE_PATH"):
            self._ensure_dict("database")
            self._config["database"]["path"] = os.getenv("DATABASE_PATH")

    def _ensure_dict(self, *keys):
        """Ensure nested dictionary structure exists."""
        current = self._config
        for key in keys:
            if key not in current:
                current[key] = {}
            current = current[key]

    def save(self):
        """Save configuration to file with secure permissions."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

        # Set file permissions to 600 (read/write for owner only)
        try:
            os.chmod(self.config_path, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, AttributeError):
            # chmod might not be supported on all platforms (e.g., Windows)
            pass

    @property
    def tracker_type(self) -> str:
        """Get tracker type."""
        return self._config.get("tracker", {}).get("type", "")

    @property
    def tracker_url(self) -> str:
        """Get tracker URL."""
        return self._config.get("tracker", {}).get("url", "")

    @property
    def tracker_api_key(self) -> str:
        """Get tracker API key."""
        return self._config.get("tracker", {}).get("api_key", "")

    @property
    def custom_header_name(self) -> str:
        """Get custom tracker header name."""
        return (
            self._config.get("tracker", {})
            .get("custom", {})
            .get("header_name", "Authorization")
        )

    @property
    def custom_domains_path(self) -> str:
        """Get custom tracker domains JSON path."""
        return (
            self._config.get("tracker", {})
            .get("custom", {})
            .get("domains_path", "domains")
        )

    @property
    def telegram_bot_token(self) -> str:
        """Get Telegram bot token."""
        return self._config.get("telegram", {}).get("bot_token", "")

    @property
    def telegram_chat_id(self) -> int:
        """Get Telegram chat ID."""
        return self._config.get("telegram", {}).get("chat_id", 0)

    @property
    def check_interval_minutes(self) -> int:
        """Get check interval in minutes."""
        return self._config.get("checker", {}).get("interval_minutes", 15)

    @property
    def consecutive_failures_threshold(self) -> int:
        """Get consecutive failures threshold."""
        return self._config.get("checker", {}).get("consecutive_failures_threshold", 2)

    @property
    def ssl_warning_days(self) -> int:
        """Get SSL warning days threshold."""
        return self._config.get("checker", {}).get("ssl_warning_days", 7)

    @property
    def max_concurrent_checks(self) -> int:
        """Get max concurrent checks."""
        return self._config.get("checker", {}).get("max_concurrent_checks", 10)

    @property
    def request_timeout_seconds(self) -> int:
        """Get request timeout in seconds."""
        return self._config.get("checker", {}).get("request_timeout_seconds", 10)

    @property
    def database_path(self) -> str:
        """Get database path."""
        return self._config.get("database", {}).get("path", "data/domain_checker.db")

    @property
    def log_level(self) -> str:
        """Get log level."""
        return os.getenv("LOG_LEVEL") or self._config.get("logging", {}).get(
            "level", "INFO"
        )

    @property
    def log_file(self) -> str | None:
        """Get log file path."""
        return os.getenv("LOG_FILE") or self._config.get("logging", {}).get("file")

    @property
    def log_rotation_enabled(self) -> bool:
        """Get log rotation setting."""
        env_val = os.getenv("LOG_ROTATION_ENABLED")
        if env_val:
            return env_val.lower() in ("true", "1", "yes")
        return self._config.get("logging", {}).get("rotation_enabled", True)

    def update(self, config_dict: dict[str, Any]):
        """Update configuration with new values."""
        self._config = config_dict
