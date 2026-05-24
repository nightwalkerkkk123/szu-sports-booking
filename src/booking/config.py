"""Configuration management for booking system.

Supports multi-level configuration:
1. CLI arguments (highest priority)
2. Environment variables
3. .env file
4. config.yaml
5. Default values (lowest priority)
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import os
import yaml


@dataclass(frozen=True)
class Config:
    """Immutable configuration for the booking system."""

    # Booking settings
    venue_url: str = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do#/sportVenue"
    default_campus: str = "粤海校区"
    default_sport: str = "网球"
    default_date_index: int = 0
    default_time_slot: str = "19:00-20:00"

    # Multi-account settings
    accounts: List[Dict[str, Any]] = field(default_factory=list)

    # Retry settings
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0

    # Logging settings
    log_level: str = "info"
    log_dir: str = "logs"
    log_rotation: str = "daily"
    log_retention_days: int = 7

    # Browser settings
    browser_headless: bool = False
    browser_timeout_ms: int = 30000

    # Observability settings
    trace_enabled: bool = True
    debug_mode: bool = False
    screenshot_on_failure: bool = True

    # Data settings
    data_dir: str = "data"
    db_path: str = "data/booking.db"

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls._merge_data(data)

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量读取运行时配置（仅日志级别、debug 开关等）。

        业务配置（场馆、项目、账号列表）应从 config.yaml 读取。
        密码通过 os.environ 直接读取，不经过 Config。
        """
        data = {
            "logging": {
                "level": os.environ.get("SZU_LOG_LEVEL"),
            },
            "observability": {
                "debug_mode": os.environ.get("SZU_DEBUG_MODE", "false").lower() == "true",
            },
        }

        for section in data:
            data[section] = {k: v for k, v in (data[section] or {}).items() if v is not None}

        return cls._merge_data(data)

    @classmethod
    def load(cls, config_path: str = "configs/config.yaml") -> "Config":
        """
        Load configuration with priority:
        1. Default values
        2. config.yaml
        3. .env file (auto-loaded by python-dotenv)
        4. Environment variables (runtime overrides)
        """
        # Auto-load .env file
        cls._load_dotenv()

        config = cls.from_defaults()

        try:
            yaml_config = cls.from_yaml(config_path)
            config = cls._merge_configs(config, yaml_config)
        except FileNotFoundError:
            pass

        env_config = cls.from_env()
        config = cls._merge_configs(config, env_config)

        return config

    @staticmethod
    def _load_dotenv():
        """自动加载 .env 文件到 os.environ。"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

    @classmethod
    def from_defaults(cls) -> "Config":
        """Create config with default values."""
        return cls()

    @classmethod
    def _merge_data(cls, data: dict) -> "Config":
        """Create Config from dictionary data."""
        kwargs = {}

        # Booking section
        booking = data.get("booking", {})
        kwargs["venue_url"] = booking.get("venue_url", cls.__default_venue_url())
        kwargs["default_campus"] = booking.get("default_campus", "粤海校区")
        kwargs["default_sport"] = booking.get("default_sport", "网球")
        kwargs["default_date_index"] = booking.get("default_date_index", 0)
        kwargs["default_time_slot"] = booking.get("default_time_slot", "19:00-20:00")

        # Accounts section
        kwargs["accounts"] = data.get("accounts") or data.get("booking", {}).get("accounts", [])

        # Retry section
        retry = data.get("retry", {})
        kwargs["retry_max_attempts"] = retry.get("max_attempts", 3)
        kwargs["retry_base_delay"] = retry.get("base_delay_seconds", 1.0)
        kwargs["retry_max_delay"] = retry.get("max_delay", 30.0)

        # Logging section
        logging = data.get("logging", {})
        kwargs["log_level"] = logging.get("level", "info")
        kwargs["log_dir"] = logging.get("dir", "logs")
        kwargs["log_rotation"] = logging.get("rotation", "daily")
        kwargs["log_retention_days"] = logging.get("retention_days", 7)

        # Browser section
        browser = data.get("browser", {})
        kwargs["browser_headless"] = browser.get("headless", False)
        kwargs["browser_timeout_ms"] = browser.get("timeout_ms", 30000)

        # Observability section
        obs = data.get("observability", {})
        kwargs["trace_enabled"] = obs.get("trace_enabled", True)
        kwargs["debug_mode"] = obs.get("debug_mode", False)
        kwargs["screenshot_on_failure"] = obs.get("screenshot_on_failure", True)

        return cls(**kwargs)

    @classmethod
    def _merge_configs(cls, base: "Config", override: "Config") -> "Config":
        """Merge two configs, override takes priority.
        Only takes override value if it differs from the real default.
        """
        import inspect

        default_config = cls.from_defaults()
        kwargs = {}
        for name, value in inspect.signature(cls).parameters.items():
            if value.default is not inspect.Parameter.empty:
                override_value = getattr(override, name)
                default_value = getattr(default_config, name)
                if override_value != default_value:
                    kwargs[name] = override_value
                else:
                    kwargs[name] = getattr(base, name)

        return cls(**kwargs)

    @staticmethod
    def __default_venue_url() -> str:
        """Default venue URL."""
        return "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do#/sportVenue"

    def __repr__(self) -> str:
        """String representation of Config."""
        return (
            f"Config(venue_url={self.venue_url[:50]}..., "
            f"campus={self.default_campus}, "
            f"sport={self.default_sport})"
        )