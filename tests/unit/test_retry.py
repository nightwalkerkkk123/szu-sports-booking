"""Tests for booking.retry module - Retry policy and strategies."""

import pytest


class TestRetryStrategy:
    """Test RetryStrategy enum."""

    def test_retry_strategy_values(self):
        """All retry strategies exist."""
        from booking.retry import RetryStrategy

        assert RetryStrategy.IMMEDIATE.value == "IMMEDIATE"
        assert RetryStrategy.LINEAR_BACKOFF.value == "LINEAR_BACKOFF"
        assert RetryStrategy.EXPONENTIAL_BACKOFF.value == "EXPONENTIAL_BACKOFF"


class TestRetryPolicy:
    """Test RetryPolicy dataclass."""

    def test_retry_policy_has_default_values(self):
        """RetryPolicy has sensible defaults."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 30.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_retry_policy_custom_values(self):
        """RetryPolicy accepts custom values."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy(
            max_attempts=5, base_delay=2.0, max_delay=60.0, strategy=RetryStrategy.LINEAR_BACKOFF
        )
        assert policy.max_attempts == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 60.0
        assert policy.strategy == RetryStrategy.LINEAR_BACKOFF


class TestShouldRetry:
    """Test should_retry logic."""

    def test_should_retry_returns_false_when_max_attempts_reached(self):
        """should_retry returns False when attempt >= max_attempts."""
        from booking.errors import ErrorCode
        from booking.retry import RetryPolicy

        policy = RetryPolicy(max_attempts=3)

        # At attempt 3 (0-indexed), should return False
        result = policy.should_retry(ErrorCode.LOGIN_FAILED, attempt=3)
        assert result is False

    def test_should_retry_returns_true_for_retryable_error(self):
        """should_retry returns True for retryable error codes."""
        from booking.errors import ErrorCode
        from booking.retry import RetryPolicy

        policy = RetryPolicy(max_attempts=3)

        # LOGIN_FAILED is retryable
        result = policy.should_retry(ErrorCode.LOGIN_FAILED, attempt=0)
        assert result is True

    def test_should_retry_returns_false_for_non_retryable_error(self):
        """should_retry returns False for non-retryable error codes."""
        from booking.errors import ErrorCode
        from booking.retry import RetryPolicy

        policy = RetryPolicy(max_attempts=3)

        # CAPTCHA_REQUIRED is not retryable
        result = policy.should_retry(ErrorCode.CAPTCHA_REQUIRED, attempt=0)
        assert result is False

    def test_should_retry_returns_false_for_known_non_retryable_error(self):
        """should_retry returns False for error codes marked non-retryable."""
        from booking.errors import ErrorCode
        from booking.retry import RetryPolicy

        policy = RetryPolicy(max_attempts=3)

        # UNKNOWN_ERROR is marked non-retryable in ERROR_MAP
        result = policy.should_retry(ErrorCode.UNKNOWN_ERROR, attempt=0)
        assert result is False


class TestGetDelay:
    """Test get_delay calculations."""

    def test_get_delay_immediate_returns_zero(self):
        """IMMEDIATE strategy returns 0 delay."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy(strategy=RetryStrategy.IMMEDIATE)

        assert policy.get_delay(attempt=0) == 0
        assert policy.get_delay(attempt=1) == 0
        assert policy.get_delay(attempt=5) == 0

    def test_get_delay_linear_returns_attempt_times_base(self):
        """LINEAR_BACKOFF strategy returns base_delay * attempt."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy(strategy=RetryStrategy.LINEAR_BACKOFF, base_delay=2.0)

        assert policy.get_delay(attempt=0) == 0
        assert policy.get_delay(attempt=1) == 2.0
        assert policy.get_delay(attempt=3) == 6.0

    def test_get_delay_exponential_returns_capped_exponential(self):
        """EXPONENTIAL_BACKOFF strategy returns capped exponential delay."""
        from booking.retry import RetryPolicy, RetryStrategy

        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF, base_delay=1.0, max_delay=30.0
        )

        # attempt=0: 1.0 * 2^0 = 1.0
        assert policy.get_delay(attempt=0) == 1.0
        # attempt=1: 1.0 * 2^1 = 2.0
        assert policy.get_delay(attempt=1) == 2.0
        # attempt=2: 1.0 * 2^2 = 4.0
        assert policy.get_delay(attempt=2) == 4.0
        # attempt=3: 1.0 * 2^3 = 8.0
        assert policy.get_delay(attempt=3) == 8.0
        # attempt=10: would be 1024, but capped at 30
        assert policy.get_delay(attempt=10) == 30.0


class TestRetryWithPolicy:
    """Test retry_with_policy decorator/function."""

    def test_successful_call_returns_result(self):
        """Successful function call returns result without retrying."""
        from booking.errors import ErrorCode
        from booking.retry import RetryPolicy, retry_with_policy

        policy = RetryPolicy(max_attempts=3)

        def success_func():
            return "success"

        result = retry_with_policy(success_func, policy, ErrorCode.LOGIN_FAILED)
        assert result == "success"

    def test_retries_on_retryable_error(self):
        """Retries when should_retry returns True."""
        from booking.errors import ErrorCode
        from booking.retry import BookingError, RetryPolicy, retry_with_policy

        policy = RetryPolicy(max_attempts=3, base_delay=0.01)

        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise BookingError(ErrorCode.LOGIN_FAILED)
            return "success"

        result = retry_with_policy(flaky_func, policy, ErrorCode.LOGIN_FAILED)
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_attempts(self):
        """Raises after exhausting max_attempts."""
        from booking.errors import ErrorCode
        from booking.retry import BookingError, RetryPolicy, retry_with_policy

        policy = RetryPolicy(max_attempts=3, base_delay=0.01)

        def always_fail():
            raise BookingError(ErrorCode.LOGIN_FAILED)

        with pytest.raises(BookingError) as exc_info:
            retry_with_policy(always_fail, policy, ErrorCode.LOGIN_FAILED)

        assert exc_info.value.error_code == ErrorCode.LOGIN_FAILED

    def test_raises_immediately_on_non_retryable_error(self):
        """Raises immediately for non-retryable errors without retrying."""
        from booking.errors import ErrorCode
        from booking.retry import BookingError, RetryPolicy, retry_with_policy

        policy = RetryPolicy(max_attempts=3, base_delay=0.01)

        call_count = 0

        def captcha_error():
            nonlocal call_count
            call_count += 1
            raise BookingError(ErrorCode.CAPTCHA_REQUIRED)

        with pytest.raises(BookingError) as exc_info:
            retry_with_policy(captcha_error, policy, ErrorCode.CAPTCHA_REQUIRED)

        assert exc_info.value.error_code == ErrorCode.CAPTCHA_REQUIRED
        assert call_count == 1  # Only called once, not retried


class TestBookingError:
    """Test BookingError exception class."""

    def test_booking_error_has_error_code(self):
        """BookingError stores error code."""
        from booking.errors import ErrorCode
        from booking.retry import BookingError

        error = BookingError(ErrorCode.LOGIN_FAILED)
        assert error.error_code == ErrorCode.LOGIN_FAILED

    def test_booking_error_is_runtime_error(self):
        """BookingError is a RuntimeError."""
        from booking.errors import ErrorCode
        from booking.retry import BookingError

        error = BookingError(ErrorCode.LOGIN_FAILED)
        assert isinstance(error, RuntimeError)

    def test_booking_error_message_contains_code(self):
        """BookingError message contains error code value."""
        from booking.errors import ErrorCode
        from booking.retry import BookingError

        error = BookingError(ErrorCode.PAGE_LOAD_TIMEOUT)
        assert "PAGE_LOAD_TIMEOUT" in str(error)
