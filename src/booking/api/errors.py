"""API error definitions."""


class ApiError(Exception):
    """API调用异常"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int | None = None,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(f"[{code}] {message}")

    def __repr__(self) -> str:
        return f"ApiError(code={self.code}, message={self.message})"


class AuthenticationError(ApiError):
    """认证失败"""

    def __init__(self, message: str = "认证失败，请重新登录"):
        super().__init__(code="AUTH_FAILED", message=message)


class NetworkError(ApiError):
    """网络请求失败"""

    def __init__(self, message: str = "网络请求失败"):
        super().__init__(code="NETWORK_ERROR", message=message)


class BookingError(ApiError):
    """预约业务错误"""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(code=code, message=message, details=details)


class ValidationError(ApiError):
    """参数校验失败"""

    def __init__(self, message: str):
        super().__init__(code="VALIDATION_ERROR", message=message)


class SessionExpiredError(ApiError):
    """会话过期"""

    def __init__(self, message: str = "会话已过期，请重新登录"):
        super().__init__(code="SESSION_EXPIRED", message=message)
