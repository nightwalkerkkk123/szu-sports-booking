"""Tests for booking.config module - Configuration management."""

from pathlib import Path

import pytest


class TestConfigLoad:
    """Test Config loading from various sources."""

    def test_load_reads_yaml_file(self, sample_config_yaml, mock_env):
        """Config loads values from YAML file."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from booking.config import Config

        config = Config.load(sample_config_yaml)
        assert config.venue_url == "https://test.example.com"
        assert config.default_campus == "粤海校区"

    def test_load_returns_config_object(self, sample_config_yaml, mock_env):
        """Config.load returns a Config instance."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from booking.config import Config

        config = Config.load(sample_config_yaml)
        assert isinstance(config, Config)


class TestConfigDefaults:
    """Test Config default values."""

    def test_default_venue_url(self, mock_env):
        """Default venue URL is set."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from booking.config import Config

        config = Config.from_defaults()
        assert config.venue_url is not None
        assert "ehall.szu.edu.cn" in config.venue_url

    def test_default_retry_values(self, mock_env):
        """Default retry values are set."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from booking.config import Config

        config = Config.from_defaults()
        assert config.retry_max_attempts >= 1
        assert config.retry_base_delay >= 0.1


class TestConfigEnvOverride:
    """Test environment variable override."""

    def test_env_overrides_log_level(self, monkeypatch, sample_config_yaml):
        """环境变量覆盖日志级别"""
        from booking.config import Config

        monkeypatch.setenv("SZU_LOG_LEVEL", "debug")
        config = Config.load(sample_config_yaml)
        assert config.log_level == "debug"


class TestConfigMergeRegression:
    """Regression tests for config merge bugs."""

    def test_accounts_survive_env_merge(self, temp_dir, monkeypatch):
        """Bug: from_env() 空列表覆盖 yaml 的 accounts。
        修复后 accounts 应该保留 yaml 中的值。"""
        from booking.config import Config

        config_path = temp_dir / "with_accounts.yaml"
        config_path.write_text(
            """
booking:
  default_campus: "粤海校区"
  default_sport: "网球"
accounts:
  - username: "2023150090"
    default_campus: "丽湖校区"
    default_sport: "羽毛球"
""",
            encoding="utf-8",
        )
        # env 会创建空的 default Config（accounts=[]），
        # 修复后应该不覆盖 yaml 的 accounts
        config = Config.load(str(config_path))
        assert len(config.accounts) == 1
        assert config.accounts[0]["username"] == "2023150090"
        assert config.accounts[0]["default_sport"] == "羽毛球"


class TestConfigValidation:
    """Test Config validation."""

    def test_load_with_invalid_path_uses_defaults(self, mock_env):
        """Loading non-existent config file uses defaults instead of raising."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from booking.config import Config

        # Config.load() should NOT raise, it should use defaults when file doesn't exist
        config = Config.load("/nonexistent/path/config.yaml")
        assert isinstance(config, Config)
        assert config.default_campus == "粤海校区"  # Default value

    def test_config_has_required_fields(self, mock_env):
        """Config has all required fields."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from booking.config import Config

        config = Config.from_defaults()
        assert hasattr(config, "venue_url")
        assert hasattr(config, "default_campus")
        assert hasattr(config, "default_sport")
        assert hasattr(config, "default_date_index")
        assert hasattr(config, "default_time_slot")
        assert hasattr(config, "retry_max_attempts")
        assert hasattr(config, "log_level")


class TestConfigDataclass:
    """Test Config as a dataclass."""

    def test_config_is_dataclass(self, mock_env):
        """Config is a dataclass."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from dataclasses import is_dataclass

        from booking.config import Config

        assert is_dataclass(Config)

    def test_config_immutable(self, mock_env):
        """Config instances cannot be modified after creation."""
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from booking.config import Config

        config = Config.from_defaults()
        with pytest.raises(Exception):  # frozen dataclass should raise  # noqa: B017
            config.default_campus = "changed"
