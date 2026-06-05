"""Tests for booking.account module - Account management."""

from datetime import datetime, timedelta


class TestAccountStatus:
    """Test AccountStatus enum."""

    def test_account_status_values(self):
        """All account statuses exist."""
        from booking.account import AccountStatus

        assert AccountStatus.AVAILABLE.value == "AVAILABLE"
        assert AccountStatus.IN_USE.value == "IN_USE"
        assert AccountStatus.COOLDOWN.value == "COOLDOWN"
        assert AccountStatus.DISABLED.value == "DISABLED"
        assert AccountStatus.LOCKED.value == "LOCKED"


class TestAccountCreation:
    """Test Account creation."""

    def test_account_has_username_password(self):
        """Account stores username and password."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        assert account.username == "test_user"
        assert account.password == "test_pass"

    def test_account_default_status_available(self):
        """New accounts have AVAILABLE status by default."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")
        assert account.status == AccountStatus.AVAILABLE

    def test_account_default_priority_one(self):
        """New accounts have priority 1 by default."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        assert account.priority == 1

    def test_account_consecutive_failures_zero(self):
        """New accounts have 0 consecutive failures."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        assert account.consecutive_failures == 0


class TestAccountAvailability:
    """Test Account availability logic."""

    def test_available_account_is_available(self):
        """AVAILABLE account returns True for is_available()."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")
        assert account.status == AccountStatus.AVAILABLE
        assert account.is_available() is True

    def test_in_use_account_not_available(self):
        """IN_USE account returns False for is_available()."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")
        account.status = AccountStatus.IN_USE
        assert account.is_available() is False

    def test_disabled_account_not_available(self):
        """DISABLED account returns False for is_available()."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")
        account.status = AccountStatus.DISABLED
        assert account.is_available() is False

    def test_locked_account_not_available(self):
        """LOCKED account returns False for is_available()."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")
        account.status = AccountStatus.LOCKED
        assert account.is_available() is False

    def test_cooldown_account_not_available_until_expired(self):
        """COOLDOWN account is not available until cooldown expires."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")
        account.status = AccountStatus.COOLDOWN
        account.cooldown_until = datetime.now() + timedelta(minutes=5)

        # Should not be available while in cooldown
        assert account.is_available() is False

        # After cooldown expires
        account.cooldown_until = datetime.now() - timedelta(minutes=1)
        assert account.is_available() is True


class TestAccountFailureTracking:
    """Test Account failure tracking."""

    def test_mark_failure_increments_count(self):
        """mark_failure() increments consecutive_failures."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        assert account.consecutive_failures == 0

        account.mark_failure()
        assert account.consecutive_failures == 1

        account.mark_failure()
        assert account.consecutive_failures == 2

    def test_mark_failure_triggers_cooldown_at_3(self):
        """mark_failure() triggers COOLDOWN after 3 consecutive failures."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")

        account.mark_failure()
        account.mark_failure()
        assert account.status == AccountStatus.AVAILABLE

        account.mark_failure()  # 3rd failure
        assert account.status == AccountStatus.COOLDOWN
        assert account.cooldown_until is not None

    def test_mark_success_resets_failures(self):
        """mark_success() resets consecutive_failures to 0."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        account.consecutive_failures = 5

        account.mark_success()
        assert account.consecutive_failures == 0

    def test_mark_success_sets_available_status(self):
        """mark_success() sets status to AVAILABLE."""
        from booking.account import Account, AccountStatus

        account = Account(username="test_user", password="test_pass")
        account.status = AccountStatus.COOLDOWN
        account.cooldown_until = datetime.now() + timedelta(minutes=5)

        account.mark_success()
        assert account.status == AccountStatus.AVAILABLE
        assert account.cooldown_until is None


class TestAccountCredentials:
    """Test Account credentials property."""

    def test_credentials_returns_tuple(self):
        """credentials property returns (username, password) tuple."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        credentials = account.credentials

        assert isinstance(credentials, tuple)
        assert len(credentials) == 2
        assert credentials == ("test_user", "test_pass")


class TestAccountMetadata:
    """Test Account metadata."""

    def test_account_has_metadata_dict(self):
        """Account has metadata dict for extensibility."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        assert isinstance(account.metadata, dict)

    def test_account_metadata_can_store_custom_data(self):
        """Account metadata can store custom key-value pairs."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        account.metadata["priority"] = 2
        account.metadata["notes"] = "test account"

        assert account.metadata["priority"] == 2
        assert account.metadata["notes"] == "test account"


class TestAccountLastUsed:
    """Test Account last_used timestamp."""

    def test_last_used_initially_none(self):
        """New account has last_used=None."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        assert account.last_used is None

    def test_mark_success_sets_last_used(self):
        """mark_success() sets last_used to current time."""
        from booking.account import Account

        account = Account(username="test_user", password="test_pass")
        assert account.last_used is None

        account.mark_success()
        assert account.last_used is not None
        assert isinstance(account.last_used, datetime)
