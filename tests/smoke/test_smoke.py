"""Smoke tests for booking system - End-to-end verification."""
import pytest


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

    def test_validate_config_command_exists(self):
        """validate-config command exists and works."""
        from click.testing import CliRunner
        from booking.cli import validate_config
        import tempfile
        import os

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.yaml")
            with open(config_path, "w") as f:
                f.write("""
booking:
  venue_url: "https://test.example.com"
  default_campus: "粤海校区"
  default_sport: "网球"
  default_date_index: 0
  default_time_slot: "19:00-20:00"
""")
            result = runner.invoke(validate_config, ["--config", config_path])
            assert result.exit_code == 0
            assert "配置有效" in result.output


class TestObservabilitySmoke:
    """Smoke tests for observability components."""

    def test_logger_can_be_created(self):
        """Logger can be instantiated."""
        from booking.observability import Logger

        logger = Logger("test_smoke", level="info")
        assert logger.name == "test_smoke"

    def test_tracer_can_create_context(self):
        """Tracer can start a trace."""
        from booking.observability import Tracer

        tracer = Tracer()
        ctx = tracer.start()
        assert ctx is not None
        assert ctx.trace_id is not None

    def test_metrics_can_collect(self):
        """Metrics collector can record data."""
        from booking.observability import MetricsCollector

        collector = MetricsCollector()
        collector.counter("test").increment()
        assert collector.counter("test").value == 1


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
        from booking.errors import ErrorCode, ERROR_MAP

        assert ErrorCode.LOGIN_FAILED in ERROR_MAP
        info = ERROR_MAP[ErrorCode.LOGIN_FAILED]
        assert info.is_retryable is True

    def test_retry_policy_exists(self):
        """RetryPolicy can be instantiated."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_database_can_be_created(self):
        """Database can be instantiated."""
        from booking.database import Database
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = Database(db_path)
            assert db is not None


class TestModuleIntegration:
    """Integration smoke tests for module interactions."""

    def test_account_manager_works(self):
        """AccountManager can manage accounts."""
        from booking.account import AccountManager

        manager = AccountManager()
        account = manager.add_account("user1", "pass1")
        assert manager.get_account_by_username("user1") is not None

    def test_retry_policy_respects_error_map(self):
        """RetryPolicy checks error retryability."""
        from booking.retry import RetryPolicy
        from booking.errors import ErrorCode

        policy = RetryPolicy()
        # CAPTCHA_REQUIRED is not retryable
        assert policy.should_retry(ErrorCode.CAPTCHA_REQUIRED, 0) is False
        # LOGIN_FAILED is retryable
        assert policy.should_retry(ErrorCode.LOGIN_FAILED, 0) is True

    def test_observability_integration(self):
        """Logger and Tracer can work together."""
        from booking.observability import Logger, Tracer

        logger = Logger("integration_test")
        tracer = Tracer()

        ctx = tracer.start()
        logger.inject_trace_id(ctx.trace_id)

        assert tracer.get_context() is not None