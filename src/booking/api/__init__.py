"""API booking module - direct backend API calls."""

from .client import ApiClient
from .cookie_extractor import extract_cookies_from_browser, extract_cookies_from_page
from .cookie_manager import CookieManager
from .errors import (
    ApiError,
    AuthenticationError,
    BookingError,
    NetworkError,
    SessionExpiredError,
    ValidationError,
)
from .flow import ApiBookingFlow
from .models import BookingRecord, BookingRequest, BookingResponse, TimeSlot, Venue
from .session import SessionManager

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
    "BookingRecord",
    # Errors
    "ApiError",
    "AuthenticationError",
    "NetworkError",
    "BookingError",
    "ValidationError",
    "SessionExpiredError",
]
