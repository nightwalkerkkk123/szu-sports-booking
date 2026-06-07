"""Retry policy and strategies for booking system."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from booking.errors import ERROR_MAP, ErrorCode

T = TypeVar("T")


class RetryStrategy(Enum):
    """Retry strategy types."""

    IMMEDIATE = "IMMEDIATE"  # No delay between retries
    LINEAR_BACKOFF = "LINEAR_BACKOFF"  # Linear increase: base_delay * attempt
    EXPONENTIAL_BACKOFF = "EXPONENTIAL_BACKOFF"  # Exponential: base_delay * 2^attempt


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF

    def should_retry(self, error_code: ErrorCode, attempt: int) -> bool:
        """
        Determine if an operation should be retried.

        Args:
            error_code: The error code that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_attempts:
            return False

        error_info = ERROR_MAP.get(error_code)
        if error_info is not None and not error_info.is_retryable:
            return False

        return True

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.LINEAR_BACKOFF:
            return self.base_delay * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return min(self.base_delay * (2**attempt), self.max_delay)
        else:  # IMMEDIATE
            return 0


class BookingError(RuntimeError):
    """Exception raised when a booking operation fails."""

    def __init__(self, error_code: ErrorCode, message: str | None = None):
        self.error_code = error_code
        self.message = message or error_code.value
        super().__init__(self.message)


def retry_with_policy(func: Callable[[], T], policy: RetryPolicy, error_code: ErrorCode) -> T:
    """
    Execute a function with retry policy.

    Args:
        func: Function to execute
        policy: Retry policy to apply
        error_code: Error code to use for retry decisions

    Returns:
        Function result if successful

    Raises:
        BookingError: If all retries are exhausted
    """
    attempt = 0
    last_error: Exception | None = None

    while True:
        try:
            return func()
        except Exception as e:
            if not policy.should_retry(error_code, attempt):
                raise BookingError(error_code) from e

            delay = policy.get_delay(attempt)
            if delay > 0:
                time.sleep(delay)

            attempt += 1
            last_error = e  # noqa: F841
