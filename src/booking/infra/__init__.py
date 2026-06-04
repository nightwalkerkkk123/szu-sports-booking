"""Infrastructure layer for the booking system.

This package is the seam between the application logic (src/booking/api/) and
the network. The HTTPBackend interface lets us swap transport implementations
(curl_cffi, surf-proxy, plain httpx) without changing the call sites.

Public entry points:
    HTTPBackend           - the transport interface
    HttpResponse          - normalized response value
    BackendUnavailable    - raised when a backend can't even attempt a request
    CurlCffiBackend       - default backend, Chrome TLS via curl_cffi
    SurfProxyBackend      - Chrome TLS via the surf-proxy Go process
    HttpxBackend          - no fingerprint, useful for fallback / debugging
    FingerprintComposer   - single source of truth for Chrome headers
    RiskScorer            - aggregate risk signals from responses
    AccountRateLimiter    - per-account token bucket + cooldown
    BackendRouter         - strategy + fallback chain
    BrowserEscapeHatch    - last-resort UI booking when HTTP fails
"""
from .backends import (
    HTTPBackend,
    HttpResponse,
    BackendUnavailable,
    CurlCffiBackend,
    SurfProxyBackend,
    HttpxBackend,
)
from .fingerprint import FingerprintComposer, DEFAULT_CHROME_VERSION
from .risk_scorer import (
    RiskScorer,
    RiskSignals,
    SUSPECT_THRESHOLD,
    BLOCKED_THRESHOLD,
)
from .rate_limiter import AccountRateLimiter, RateLimitState, RouteDecision as RateLimitDecision
from .router import BackendRouter, RouteDecision
from .escape_hatch import BrowserEscapeHatch, EscapeHatchResult

__all__ = [
    # Backends
    "HTTPBackend",
    "HttpResponse",
    "BackendUnavailable",
    "CurlCffiBackend",
    "SurfProxyBackend",
    "HttpxBackend",
    # Fingerprint
    "FingerprintComposer",
    "DEFAULT_CHROME_VERSION",
    # Risk
    "RiskScorer",
    "RiskSignals",
    "SUSPECT_THRESHOLD",
    "BLOCKED_THRESHOLD",
    # Rate limiting
    "AccountRateLimiter",
    "RateLimitState",
    "RateLimitDecision",
    # Routing
    "BackendRouter",
    "RouteDecision",
    # Escape hatch
    "BrowserEscapeHatch",
    "EscapeHatchResult",
]
