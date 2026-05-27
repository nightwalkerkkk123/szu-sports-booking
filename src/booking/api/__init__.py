"""API booking module - direct backend API calls."""

from .client import ApiClient
from .session import SessionManager
from .cookie_manager import CookieManager
from .cookie_extractor import extract_cookies_from_page, extract_cookies_from_browser
from .flow import ApiBookingFlow
from .models import TimeSlot, Venue, BookingRequest, BookingResponse
from .errors import (
    ApiError,
    AuthenticationError,
    NetworkError,
    BookingError,
    ValidationError,
    SessionExpiredError,
)

__all__ = [
    # Core client
    "ApiClient",
    "SessionManager",
    # Cookie management
    "CookieManager",
    "extract_cookies_from_page",
    "extract_cookies_from_browser",
    # High-level flow
    "ApiBookingFlow",
    # Data models
    "TimeSlot",
    "Venue",
    "BookingRequest",
    "BookingResponse",
    # Errors
    "ApiError",
    "AuthenticationError",
    "NetworkError",
    "BookingError",
    "ValidationError",
    "SessionExpiredError",
]