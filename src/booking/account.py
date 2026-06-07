"""Account management for booking system."""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class AccountStatus(Enum):
    """Account status states."""

    AVAILABLE = "AVAILABLE"  # Can be used for booking
    IN_USE = "IN_USE"  # Currently being used
    COOLDOWN = "COOLDOWN"  # Temporarily unavailable due to failures
    DISABLED = "DISABLED"  # Manually disabled
    LOCKED = "LOCKED"  # Locked due to too many failures


@dataclass
class Account:
    """
    Account for booking system.

    Attributes:
        username: Account username (student ID)
        password: Account password
        status: Current account status
        priority: Account priority (higher = used first)
        consecutive_failures: Number of consecutive booking failures
        last_used: Timestamp of last booking attempt
        cooldown_until: Timestamp when cooldown expires
        metadata: Additional account metadata
    """

    username: str
    password: str
    status: AccountStatus = AccountStatus.AVAILABLE
    priority: int = 1
    consecutive_failures: int = 0
    last_used: datetime | None = None
    cooldown_until: datetime | None = None
    metadata: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def is_available(self) -> bool:
        """
        Check if account is available for use.

        Returns:
            True if account can be used for booking, False otherwise.
        """
        with self._lock:
            # Check cooldown expiry first
            if self.cooldown_until and datetime.now() < self.cooldown_until:
                return False

            # Then check status
            if self.status == AccountStatus.COOLDOWN:
                # Cooldown expired, account is available
                return True
            elif self.status != AccountStatus.AVAILABLE:
                return False

            return True

    def mark_failure(self) -> None:
        """
        Mark a booking failure for this account.

        Increments consecutive_failures and triggers cooldown after 3 failures.
        """
        with self._lock:
            self.consecutive_failures += 1

            if self.consecutive_failures >= 3:
                self.status = AccountStatus.COOLDOWN
                self.cooldown_until = datetime.now() + timedelta(minutes=5)

    def mark_success(self) -> None:
        """
        Mark a successful booking for this account.

        Resets consecutive_failures and updates last_used timestamp.
        """
        with self._lock:
            self.consecutive_failures = 0
            self.last_used = datetime.now()
            self.status = AccountStatus.AVAILABLE
            self.cooldown_until = None

    @property
    def credentials(self) -> tuple[str, str]:
        """
        Get account credentials as a tuple.

        Returns:
            Tuple of (username, password).
        """
        return (self.username, self.password)

    def __repr__(self) -> str:
        """String representation of Account."""
        return (
            f"Account(username={self.username}, "
            f"status={self.status.value}, "
            f"failures={self.consecutive_failures})"
        )


class AccountManager:
    """
    Manages multiple accounts for booking.

    Handles account lifecycle, selection, and status tracking.
    """

    def __init__(self):
        """Initialize empty AccountManager."""
        self._accounts: list[Account] = []

    def add_account(self, username: str, password: str, priority: int = 1, **metadata) -> Account:
        """
        Add a new account to the manager.

        Args:
            username: Account username
            password: Account password
            priority: Account priority (higher = used first)
            **metadata: Additional metadata to store with account

        Returns:
            The newly created Account.
        """
        account = Account(
            username=username, password=password, priority=priority, metadata=metadata
        )
        self._accounts.append(account)
        return account

    def get_available_account(self) -> Account | None:
        """
        Get the next available account.

        Returns accounts in priority order (highest first).
        Accounts with COOLDOWN status are skipped.

        Returns:
            The next available Account, or None if no accounts are available.
        """
        available = [acc for acc in self._accounts if acc.is_available()]
        if not available:
            return None

        # Sort by priority (descending)
        available.sort(key=lambda a: a.priority, reverse=True)
        return available[0]

    def get_all_accounts(self) -> list[Account]:
        """Get all accounts."""
        return list(self._accounts)

    def get_account_by_username(self, username: str) -> Account | None:
        """Get account by username."""
        for account in self._accounts:
            if account.username == username:
                return account
        return None

    def remove_account(self, username: str) -> bool:
        """Remove account by username. Returns True if found and removed."""
        for i, account in enumerate(self._accounts):
            if account.username == username:
                del self._accounts[i]
                return True
        return False

    def __len__(self) -> int:
        """Number of accounts."""
        return len(self._accounts)

    def __iter__(self):
        """Iterate over accounts."""
        return iter(self._accounts)
