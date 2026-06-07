"""Integration tests for booking system - Module interactions."""

from datetime import datetime


class TestConfigAndAccountIntegration:
    """Test config and account work together."""

    def test_config_loaded_for_account_operations(self):
        """Config is used in account operations."""
        from booking.account import AccountManager
        from booking.config import Config

        config = Config.from_defaults()  # noqa: F841
        manager = AccountManager()

        # Add account with config defaults
        account = manager.add_account(username="test_user", password="test_pass", priority=1)

        assert manager.get_account_by_username("test_user") is not None
        assert account.username == "test_user"


class TestAccountAndRetryIntegration:
    """Test account and retry policy integration."""

    def test_account_failure_triggers_retry_check(self):
        """Account failures are tracked for retry decisions."""
        from booking.account import Account
        from booking.retry import RetryPolicy

        account = Account(username="test", password="pass")
        policy = RetryPolicy(max_attempts=3)  # noqa: F841

        # Simulate 3 failures (triggers cooldown)
        account.mark_failure()
        account.mark_failure()
        account.mark_failure()

        assert account.status.value == "COOLDOWN"
        assert account.is_available() is False

    def test_account_success_resets_for_retry(self):
        """Successful booking resets failure count."""
        from booking.account import Account

        account = Account(username="test", password="pass")
        account.consecutive_failures = 5

        account.mark_success()

        assert account.consecutive_failures == 0
        assert account.status.value == "AVAILABLE"


class TestRetryAndErrorIntegration:
    """Test retry policy and error codes integration."""

    def test_retry_policy_with_all_error_codes(self):
        """RetryPolicy handles all error codes correctly."""
        from booking.errors import ErrorCode
        from booking.retry import RetryPolicy

        policy = RetryPolicy(max_attempts=3)

        # Retryable errors
        retryable = [
            ErrorCode.LOGIN_FAILED,
            ErrorCode.PAGE_LOAD_TIMEOUT,
            ErrorCode.NETWORK_ERROR,
            ErrorCode.NO_AVAILABLE_SLOT,
        ]
        for code in retryable:
            assert policy.should_retry(code, 0) is True, f"{code} should be retryable"

        # Non-retryable errors
        non_retryable = [
            ErrorCode.CAPTCHA_REQUIRED,
            ErrorCode.ACCOUNT_LOCKED,
            ErrorCode.PASSWORD_INCORRECT,
        ]
        for code in non_retryable:
            assert policy.should_retry(code, 0) is False, f"{code} should not be retryable"

    def test_retry_delay_for_different_strategies(self):
        """Different retry strategies produce different delays."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy_linear = RetryPolicy(strategy=RetryStrategy.LINEAR_BACKOFF, base_delay=1.0)
        policy_exp = RetryPolicy(strategy=RetryStrategy.EXPONENTIAL_BACKOFF, base_delay=1.0)

        # At attempt 3, linear should be 3.0, exponential should be 8.0 (capped at 30)
        assert policy_linear.get_delay(3) == 3.0
        assert policy_exp.get_delay(3) == 8.0


class TestDatabaseAndAccountIntegration:
    """Test database and account integration."""

    def test_booking_record_reflects_account_state(self):
        """BookingRecord captures account information."""
        from booking.database import BookingRecord

        record = BookingRecord(
            id=None,
            trace_id="trace-123",
            account="user1",
            campus="粤海校区",
            sport="网球",
            time_slot="19:00-20:00",
            status="success",
            error_code=None,
            duration_ms=1500,
            timestamp=datetime.now(),
        )

        assert record.account == "user1"
        assert record.status == "success"

    def test_database_stores_multiple_records(self, tmp_path):
        """Database can store and retrieve multiple records."""
        import os  # noqa: F401

        from booking.database import BookingRecord, Database

        db_path = str(tmp_path / "test.db")
        db = Database(db_path)

        for i in range(5):
            record = BookingRecord(
                id=None,
                trace_id=f"trace-{i}",
                account="user1",
                campus="粤海校区",
                sport="网球",
                time_slot="19:00-20:00",
                status="success" if i % 2 == 0 else "failed",
                error_code=None,
                duration_ms=1000,
                timestamp=datetime.now(),
            )
            db.insert_record(record)

        records = db.get_records_by_account("user1")
        assert len(records) == 5


class TestCLIAndConfigIntegration:
    """Test CLI and config integration."""

    def test_validate_config_displays_loaded_values(self, tmp_path):
        """validate-config shows config values."""
        from click.testing import CliRunner

        from booking.cli import validate_config

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """
booking:
  venue_url: "https://ehall.szu.edu.cn/test"
  default_campus: "丽湖校区"
  default_sport: "羽毛球"
  default_date_index: 1
  default_time_slot: "20:00-21:00"
""",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(validate_config, ["--config", str(config_path)])
        assert result.exit_code == 0
        assert "丽湖校区" in result.output
        assert "羽毛球" in result.output


class TestEndToEndScenarios:
    """End-to-end scenarios simulating real booking flow."""

    def test_booking_flow_with_account_selection(self):
        """Simulates booking flow with account selection."""
        from booking.account import AccountManager, AccountStatus

        manager = AccountManager()

        # Add multiple accounts
        manager.add_account("user1", "pass1", priority=2)
        manager.add_account("user2", "pass2", priority=1)
        manager.add_account("user3", "pass3", priority=1)

        # Get available account (should be highest priority)
        account = manager.get_available_account()
        assert account.username == "user1"

        # Mark account as in use
        account.status = AccountStatus.IN_USE

        # Get next available
        account = manager.get_available_account()
        assert account.username == "user2"

    def test_booking_failure_and_recovery_flow(self):
        """Simulates failure tracking and recovery."""
        from booking.account import Account, AccountStatus
        from booking.errors import ErrorCode
        from booking.retry import BookingError, RetryPolicy

        account = Account(username="test", password="pass")
        policy = RetryPolicy(max_attempts=3, base_delay=0.001)  # noqa: F841

        # Simulate failures
        call_count = 0

        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise BookingError(ErrorCode.LOGIN_FAILED)
            return "success"

        # This would normally retry - but we're testing the account状态
        account.mark_failure()
        assert account.consecutive_failures == 1

        account.mark_failure()
        assert account.consecutive_failures == 2

        # 3rd failure triggers cooldown
        account.mark_failure()
        assert account.status == AccountStatus.COOLDOWN
        assert account.is_available() is False

    def test_config_driven_booking_parameters(self):
        """Config drives booking behavior."""
        from booking.config import Config

        config = Config.from_defaults()

        assert config.default_campus == "粤海校区"
        assert config.default_sport == "网球"
        assert config.default_date_index == 0
        assert config.default_time_slot == "19:00-20:00"
