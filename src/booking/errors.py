"""Error code definitions for booking system."""
from dataclasses import dataclass
from enum import Enum


class ErrorCode(Enum):
    """Standardized error codes for the booking system."""

    # Login errors
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGIN_TIMEOUT = "LOGIN_TIMEOUT"
    PASSWORD_INCORRECT = "PASSWORD_INCORRECT"

    # Account errors
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"

    # Page errors
    PAGE_LOAD_TIMEOUT = "PAGE_LOAD_TIMEOUT"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_NOT_CLICKABLE = "ELEMENT_NOT_CLICKABLE"

    # Booking errors
    NO_AVAILABLE_SLOT = "NO_AVAILABLE_SLOT"
    SLOT_ALREADY_TAKEN = "SLOT_ALREADY_TAKEN"
    SUBMIT_FAILED = "SUBMIT_FAILED"
    SUBMIT_TIMEOUT = "SUBMIT_TIMEOUT"

    # System errors
    NETWORK_ERROR = "NETWORK_ERROR"
    BROWSER_CRASHED = "BROWSER_CRASHED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class ErrorInfo:
    """Information about an error code."""

    code: ErrorCode
    message: str
    is_retryable: bool  # Whether this error can be retried
    should_switch_account: bool  # Whether to switch to another account
    should_screenshot: bool  # Whether to capture a screenshot
    should_alert: bool  # Whether to trigger an alert
    hint: str  # Human-readable hint for handling this error


ERROR_MAP: dict[ErrorCode, ErrorInfo] = {
    # Login errors
    ErrorCode.LOGIN_FAILED: ErrorInfo(
        code=ErrorCode.LOGIN_FAILED,
        message="登录失败",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=False,
        hint="检查账号密码是否正确"
    ),
    ErrorCode.LOGIN_TIMEOUT: ErrorInfo(
        code=ErrorCode.LOGIN_TIMEOUT,
        message="登录超时",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=False,
        hint="网络可能较慢，增加超时时间后重试"
    ),
    ErrorCode.PASSWORD_INCORRECT: ErrorInfo(
        code=ErrorCode.PASSWORD_INCORRECT,
        message="密码错误",
        is_retryable=False,
        should_switch_account=True,
        should_screenshot=False,
        should_alert=True,
        hint="密码错误，切换到其他账号"
    ),

    # Account errors
    ErrorCode.ACCOUNT_LOCKED: ErrorInfo(
        code=ErrorCode.ACCOUNT_LOCKED,
        message="账号被锁定",
        is_retryable=False,
        should_switch_account=True,
        should_screenshot=True,
        should_alert=True,
        hint="账号被锁定，切换到其他账号"
    ),
    ErrorCode.ACCOUNT_DISABLED: ErrorInfo(
        code=ErrorCode.ACCOUNT_DISABLED,
        message="账号被禁用",
        is_retryable=False,
        should_switch_account=True,
        should_screenshot=False,
        should_alert=True,
        hint="账号被禁用，切换到其他账号"
    ),
    ErrorCode.CAPTCHA_REQUIRED: ErrorInfo(
        code=ErrorCode.CAPTCHA_REQUIRED,
        message="需要验证码",
        is_retryable=False,
        should_switch_account=True,
        should_screenshot=True,
        should_alert=True,
        hint="验证码无法自动处理，切换账号或停止任务"
    ),

    # Page errors
    ErrorCode.PAGE_LOAD_TIMEOUT: ErrorInfo(
        code=ErrorCode.PAGE_LOAD_TIMEOUT,
        message="页面加载超时",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=False,
        hint="网络可能较慢，增加超时时间后重试"
    ),
    ErrorCode.ELEMENT_NOT_FOUND: ErrorInfo(
        code=ErrorCode.ELEMENT_NOT_FOUND,
        message="元素未找到",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=False,
        hint="页面结构可能已变化，更新选择器"
    ),
    ErrorCode.ELEMENT_NOT_CLICKABLE: ErrorInfo(
        code=ErrorCode.ELEMENT_NOT_CLICKABLE,
        message="元素无法点击",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=False,
        hint="元素被遮挡或页面正在加载，等待后重试"
    ),

    # Booking errors
    ErrorCode.NO_AVAILABLE_SLOT: ErrorInfo(
        code=ErrorCode.NO_AVAILABLE_SLOT,
        message="无可用时间段",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=False,
        should_alert=False,
        hint="当前时间段已满，可尝试其他时间段"
    ),
    ErrorCode.SLOT_ALREADY_TAKEN: ErrorInfo(
        code=ErrorCode.SLOT_ALREADY_TAKEN,
        message="时间段已被抢",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=False,
        should_alert=False,
        hint="时间段被其他人抢走，尝试其他时间段"
    ),
    ErrorCode.SUBMIT_FAILED: ErrorInfo(
        code=ErrorCode.SUBMIT_FAILED,
        message="提交失败",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=False,
        hint="提交按钮点击失败，重试或截图排查"
    ),
    ErrorCode.SUBMIT_TIMEOUT: ErrorInfo(
        code=ErrorCode.SUBMIT_TIMEOUT,
        message="提交超时",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=False,
        hint="提交响应超时，可能已成功需检查"
    ),

    # System errors
    ErrorCode.NETWORK_ERROR: ErrorInfo(
        code=ErrorCode.NETWORK_ERROR,
        message="网络错误",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=False,
        should_alert=False,
        hint="网络不稳定，等待后重试"
    ),
    ErrorCode.BROWSER_CRASHED: ErrorInfo(
        code=ErrorCode.BROWSER_CRASHED,
        message="浏览器崩溃",
        is_retryable=True,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=True,
        hint="浏览器异常重启，重试任务"
    ),
    ErrorCode.UNKNOWN_ERROR: ErrorInfo(
        code=ErrorCode.UNKNOWN_ERROR,
        message="未知错误",
        is_retryable=False,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=True,
        hint="未知错误，查看日志和截图排查"
    ),
}


def get_error_info(code: ErrorCode) -> ErrorInfo:
    """Get ErrorInfo for an error code."""
    return ERROR_MAP.get(code, ErrorInfo(
        code=code,
        message=code.value,
        is_retryable=False,
        should_switch_account=False,
        should_screenshot=True,
        should_alert=True,
        hint="未知错误码"
    ))
