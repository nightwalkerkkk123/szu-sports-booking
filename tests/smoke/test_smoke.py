"""Smoke tests for booking system - End-to-end verification."""


class TestCLISmoke:
    """Smoke tests for CLI commands."""

    def test_cli_can_import(self):
        """CLI module can be imported."""
        from booking.cli import cli

        assert cli is not None

    def test_cli_help_command(self):
        """CLI --help works."""
        from click.testing import CliRunner

        from booking.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "深圳大学体育馆预约工具" in result.output

    def test_validate_config_command_exists(self, tmp_path):
        """validate-config command works with valid config."""
        from click.testing import CliRunner

        from booking.cli import validate_config

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """
booking:
  venue_url: "https://test.example.com"
  default_campus: "粤海校区"
  default_sport: "网球"
  default_date_index: 0
  default_time_slot: "19:00-20:00"
""",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(validate_config, ["--config", str(config_path)])
        assert result.exit_code == 0
        assert "配置有效" in result.output


class TestObservabilitySmoke:
    """Smoke tests for observability components."""

    def test_logger_can_be_created(self):
        """Logger can be instantiated."""
        from booking.observability import Logger

        logger = Logger("test_smoke", level="info")
        assert logger.name == "test_smoke"


class TestCoreModulesSmoke:
    """Smoke tests for core modules."""

    def test_config_loads_defaults(self):
        """Config can load defaults."""
        from booking.config import Config

        config = Config.from_defaults()
        assert config.default_campus == "粤海校区"

    def test_account_can_be_created(self):
        """Account can be instantiated."""
        from booking.account import Account

        account = Account(username="test", password="pass")
        assert account.username == "test"

    def test_errors_have_error_map(self):
        """Error codes have ErrorInfo mapping."""
        from booking.errors import ERROR_MAP, ErrorCode

        assert ErrorCode.LOGIN_FAILED in ERROR_MAP
        info = ERROR_MAP[ErrorCode.LOGIN_FAILED]
        assert info.is_retryable is True

    def test_retry_policy_exists(self):
        """RetryPolicy can be instantiated."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_database_can_be_created(self, tmp_path):
        """Database can be instantiated."""
        from booking.database import Database

        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        assert db is not None


class TestModuleIntegration:
    """Integration smoke tests for module interactions."""

    def test_account_manager_works(self):
        """AccountManager can manage accounts."""
        from booking.account import AccountManager

        manager = AccountManager()
        account = manager.add_account("user1", "pass1")  # noqa: F841
        assert manager.get_account_by_username("user1") is not None

    def test_retry_policy_respects_error_map(self):
        """RetryPolicy checks error retryability."""
        from booking.errors import ErrorCode
        from booking.retry import RetryPolicy

        policy = RetryPolicy()
        # CAPTCHA_REQUIRED is not retryable
        assert policy.should_retry(ErrorCode.CAPTCHA_REQUIRED, 0) is False
        # LOGIN_FAILED is retryable
        assert policy.should_retry(ErrorCode.LOGIN_FAILED, 0) is True
