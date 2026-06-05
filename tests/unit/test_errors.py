"""Tests for booking.errors module - ErrorCode and ERROR_MAP."""

from booking.errors import ERROR_MAP, ErrorCode, ErrorInfo


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_code_has_login_category(self):
        """Login error codes exist."""
        assert ErrorCode.LOGIN_FAILED is not None
        assert ErrorCode.LOGIN_TIMEOUT is not None
        assert ErrorCode.PASSWORD_INCORRECT is not None

    def test_error_code_has_account_category(self):
        """Account error codes exist."""
        assert ErrorCode.ACCOUNT_LOCKED is not None
        assert ErrorCode.CAPTCHA_REQUIRED is not None

    def test_error_code_has_page_category(self):
        """Page error codes exist."""
        assert ErrorCode.PAGE_LOAD_TIMEOUT is not None
        assert ErrorCode.ELEMENT_NOT_FOUND is not None

    def test_error_code_has_booking_category(self):
        """Booking error codes exist."""
        assert ErrorCode.NO_AVAILABLE_SLOT is not None
        assert ErrorCode.SUBMIT_FAILED is not None

    def test_error_code_has_system_category(self):
        """System error codes exist."""
        assert ErrorCode.NETWORK_ERROR is not None
        assert ErrorCode.BROWSER_CRASHED is not None
        assert ErrorCode.UNKNOWN_ERROR is not None

    def test_error_code_values_are_strings(self):
        """All error code values are uppercase strings."""
        for code in ErrorCode:
            assert isinstance(code.value, str)
            assert code.value.isupper()


class TestErrorInfo:
    """Test ErrorInfo dataclass."""

    def test_error_info_has_required_fields(self):
        """ErrorInfo has all required fields."""
        info = ErrorInfo(
            code=ErrorCode.LOGIN_FAILED,
            message="Login failed",
            is_retryable=True,
            should_switch_account=False,
            should_screenshot=True,
            should_alert=False,
            hint="Check credentials",
        )
        assert info.code == ErrorCode.LOGIN_FAILED
        assert info.message == "Login failed"
        assert info.is_retryable is True
        assert info.should_switch_account is False
        assert info.should_screenshot is True
        assert info.should_alert is False
        assert info.hint == "Check credentials"


class TestErrorMap:
    """Test ERROR_MAP."""

    def test_error_map_contains_all_error_codes(self):
        """ERROR_MAP contains entries for all ErrorCode values."""
        for code in ErrorCode:
            assert code in ERROR_MAP, f"Missing entry for {code.name}"

    def test_error_map_login_failed_is_retryable(self):
        """LOGIN_FAILED is retryable."""
        info = ERROR_MAP[ErrorCode.LOGIN_FAILED]
        assert info.is_retryable is True
        assert info.should_switch_account is False
        assert info.should_screenshot is True

    def test_error_map_captcha_not_retryable(self):
        """CAPTCHA_REQUIRED is not retryable."""
        info = ERROR_MAP[ErrorCode.CAPTCHA_REQUIRED]
        assert info.is_retryable is False
        assert info.should_switch_account is True
        assert info.should_alert is True

    def test_error_map_no_available_slot_is_retryable(self):
        """NO_AVAILABLE_SLOT is retryable."""
        info = ERROR_MAP[ErrorCode.NO_AVAILABLE_SLOT]
        assert info.is_retryable is True
        assert info.should_switch_account is False
        assert info.should_screenshot is False

    def test_error_map_all_entries_have_hints(self):
        """All ERROR_MAP entries have non-empty hints."""
        for code, info in ERROR_MAP.items():
            assert info.hint, f"Missing hint for {code.name}"
            assert len(info.hint) > 0, f"Empty hint for {code.name}"
