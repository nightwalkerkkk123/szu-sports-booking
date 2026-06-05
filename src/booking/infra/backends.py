"""HTTPBackend interface and three concrete implementations.

The interface is intentionally minimal: callers pass method/url/headers/body
and get back an HttpResponse. Cookies, sessions, header fingerprinting, and
proxying are all the backend's problem.

The point of having three backends is to be able to swap transport layers
without touching the application code. SurfProxyBackend talks to a Go
process that uses github.com/enetx/surf for Chrome TLS impersonation;
CurlCffiBackend uses the Python curl_cffi library directly; HttpxBackend
uses httpx with no fingerprinting and is the universal fallback.
"""

from __future__ import annotations

import abc
import json
import logging
import time
from abc import abstractmethod  # noqa: F401
from collections.abc import Mapping
from dataclasses import dataclass, field

import httpx

from .fingerprint import FingerprintComposer

logger = logging.getLogger("booking.infra.backends")


# --- Value objects ---------------------------------------------------------


@dataclass
class HttpResponse:
    """Normalized response from any HTTPBackend.

    Mirrors the shape of the surf-proxy ProxyResponse so we can swap
    backends without the caller caring which one served the request.
    """

    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    proto: str = ""
    elapsed_ms: int = 0
    backend: str = ""
    error: str | None = None

    @property
    def is_ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400

    @property
    def json(self) -> dict | list | None:
        """Try to parse the body as JSON, return None on failure."""
        if not self.body:
            return None
        try:
            return json.loads(self.body)
        except (ValueError, TypeError):
            return None


class BackendUnavailable(Exception):  # noqa: N818
    """Raised when a backend cannot even attempt a request.

    This is distinct from a normal network error: it means the backend
    itself is down (e.g. the surf-proxy Go process is not running).
    The router catches this and falls through to the next backend.
    """


# --- The interface ---------------------------------------------------------


class HTTPBackend(abc.ABC):
    """Abstract HTTP backend.

    Implementations:
        CurlCffiBackend   - default, Chrome TLS via curl_cffi
        SurfProxyBackend  - Chrome TLS via the surf-proxy Go process
        HttpxBackend      - no fingerprint, fallback / debugging
    """

    name: str = "abstract"

    def __init__(
        self,
        fingerprint: FingerprintComposer | None = None,
        proxy: str | None = None,
        default_timeout: float = 30.0,
    ):
        self._fingerprint = fingerprint
        self._proxy = proxy
        self._default_timeout = default_timeout

    @abc.abstractmethod
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        body: str | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Send one HTTP request and return a normalized response.

        Args:
            method: HTTP method (GET, POST, ...).
            url: Full URL including scheme.
            headers: Caller-supplied semantic headers. The backend may
                augment these with a fingerprint if configured.
            body: Request body as a string. Empty string for GET.
            timeout: Override the backend default timeout (seconds).
        """

    def close(self) -> None:  # noqa: B027
        """Release any resources held by the backend. Default: no-op."""


def _merge_fingerprint(
    fingerprint: FingerprintComposer | None,
    method: str,
    url: str,
    caller_headers: Mapping[str, str] | None,
) -> dict[str, str]:
    """Apply the fingerprint composer to caller headers.

    If no fingerprint is configured, return the caller headers as-is.
    """
    base = dict(caller_headers) if caller_headers else {}
    if fingerprint is None:
        return base
    return fingerprint.compose(method=method, url=url, headers=base)


# --- CurlCffiBackend -------------------------------------------------------


class CurlCffiBackend(HTTPBackend):
    """Default backend. Wraps curl_cffi.requests with Chrome TLS impersonation.

    This is the closest drop-in replacement for the legacy code in
    src/booking/api/client.py. The big difference: it goes through
    FingerprintComposer so headers stay consistent with the other backends.
    """

    name = "curl_cffi"

    def __init__(
        self,
        fingerprint: FingerprintComposer | None = None,
        proxy: str | None = None,
        default_timeout: float = 30.0,
        impersonate: str = "chrome",
    ):
        super().__init__(fingerprint=fingerprint, proxy=proxy, default_timeout=default_timeout)
        self._impersonate = impersonate
        # Lazy import so the infra package can be imported without curl_cffi.
        from curl_cffi import requests as cffi_requests

        self._session = cffi_requests.Session(impersonate=impersonate)

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        body: str | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:

        merged = _merge_fingerprint(self._fingerprint, method, url, headers)
        kwargs: dict = {
            "headers": merged,
            "proxy": self._proxy,
            "timeout": timeout or self._default_timeout,
        }

        method_upper = method.upper()
        try:
            start = time.perf_counter()
            if method_upper == "GET":
                resp = self._session.get(url, **kwargs)
            elif method_upper == "POST":
                resp = self._session.post(url, data=body or "", **kwargs)
            elif method_upper == "PUT":
                resp = self._session.put(url, data=body or "", **kwargs)
            elif method_upper == "DELETE":
                resp = self._session.delete(url, **kwargs)
            elif method_upper == "PATCH":
                resp = self._session.patch(url, data=body or "", **kwargs)
            elif method_upper == "HEAD":
                resp = self._session.head(url, **kwargs)
            else:
                return HttpResponse(
                    status_code=0,
                    error=f"unsupported method: {method}",
                    backend=self.name,
                )
            elapsed = (time.perf_counter() - start) * 1000
        except Exception as e:
            return HttpResponse(
                status_code=0,
                error=str(e),
                backend=self.name,
            )

        return HttpResponse(
            status_code=int(getattr(resp, "status_code", 0)),
            headers={k: v for k, v in resp.headers.items() if v},
            body=resp.text or "",
            elapsed_ms=int(elapsed),
            backend=self.name,
        )

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:  # noqa: BLE001
            pass


# --- SurfProxyBackend ------------------------------------------------------


class SurfProxyBackend(HTTPBackend):
    """Talks to the surf-proxy Go process over HTTP.

    The Go process is a long-running daemon that uses github.com/enetx/surf
    to send requests with a Chrome TLS / HTTP-2 fingerprint. This backend
    does the translation: Python dicts in, Go ProxyRequest JSON out, Go
    ProxyResponse JSON back into HttpResponse.

    The backend does a /health probe on first use and remembers the result
    for `cooldown_after_failure` seconds before retrying. While in cooldown
    it raises BackendUnavailable so the router can skip to the next backend
    instead of waiting for a connect error.
    """

    name = "surf_proxy"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:9876",
        fingerprint: FingerprintComposer | None = None,
        proxy: str | None = None,
        default_timeout: float = 30.0,
        cooldown_after_failure: float = 30.0,
    ):
        super().__init__(fingerprint=fingerprint, proxy=proxy, default_timeout=default_timeout)
        self._base_url = base_url.rstrip("/")
        self._cooldown_after_failure = cooldown_after_failure
        self._healthy: bool | None = None
        self._last_failure: float = 0.0
        # Use a shared httpx client for health checks. The Go process is
        # local so this is cheap; we keep it separate from the request
        # path to keep the per-request payload small.
        self._http = httpx.Client(timeout=2.0)

    def health(self) -> bool:
        """Probe the Go process. Result is cached briefly."""
        if self._healthy and (time.time() - self._last_failure) < self._cooldown_after_failure:
            return True
        try:
            r = self._http.get(f"{self._base_url}/health", timeout=2.0)
            self._healthy = r.status_code == 200
        except Exception:  # noqa: BLE001
            self._healthy = False
            self._last_failure = time.time()
        return self._healthy

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        body: str | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        # Cooldown check: if the last health probe failed recently, raise so
        # the router can move on without a connect error.
        if not self._healthy and (time.time() - self._last_failure) < self._cooldown_after_failure:
            raise BackendUnavailable(
                f"surf-proxy is in cooldown ({self._cooldown_after_failure}s after last failure); "
                f"start it with: surf-proxy &"
            )

        merged = _merge_fingerprint(self._fingerprint, method, url, headers)
        payload = {
            "method": method.upper(),
            "url": url,
            "headers": merged,
            "body": body or "",
            "timeout": int(timeout or self._default_timeout),
        }

        try:
            r = self._http.post(
                f"{self._base_url}/proxy",
                json=payload,
                timeout=(timeout or self._default_timeout) + 5.0,
            )
        except httpx.ConnectError as e:
            self._healthy = False
            self._last_failure = time.time()
            raise BackendUnavailable(
                f"surf-proxy not reachable at {self._base_url}: {e}. "
                f"Start it with: cd surf-proxy && SURF_PROXY_PORT=9876 ./surf-proxy &"
            ) from e
        except Exception as e:  # noqa: BLE001
            self._healthy = False
            self._last_failure = time.time()
            return HttpResponse(status_code=0, error=str(e), backend=self.name)

        if r.status_code != 200:
            # The proxy always returns 200 for /proxy regardless of upstream
            # status, but it returns 4xx for bad input. Treat anything non-200
            # as a transport failure and trip the cooldown.
            self._healthy = False
            self._last_failure = time.time()
            return HttpResponse(
                status_code=r.status_code,
                error=f"surf-proxy returned HTTP {r.status_code}: {r.text[:200]}",
                backend=self.name,
            )

        try:
            data = r.json()
        except ValueError as e:
            return HttpResponse(
                status_code=0, error=f"non-json from surf-proxy: {e}", backend=self.name
            )

        # Transport-level error from surf-proxy: status_code==0 with an error field.
        if data.get("status_code", 0) == 0 and data.get("error"):
            return HttpResponse(
                status_code=0,
                error=data["error"],
                elapsed_ms=int(data.get("time_ms", 0)),
                backend=self.name,
            )

        self._healthy = True
        return HttpResponse(
            status_code=int(data.get("status_code", 0)),
            headers=data.get("headers", {}) or {},
            body=data.get("body", "") or "",
            proto=data.get("proto", "") or "",
            elapsed_ms=int(data.get("time_ms", 0)),
            backend=self.name,
        )

    def close(self) -> None:
        try:
            self._http.close()
        except Exception:  # noqa: BLE001
            pass


# --- HttpxBackend ----------------------------------------------------------


class HttpxBackend(HTTPBackend):
    """Plain httpx, no fingerprint impersonation.

    Useful for:
        - reaching internal endpoints that don't fingerprint (cookie health
          checks, debug logging endpoints)
        - fallback when both chrome-impersonating backends are failing
        - testing without a Go process or curl_cffi installed
    """

    name = "httpx"

    def __init__(
        self,
        fingerprint: FingerprintComposer | None = None,
        proxy: str | None = None,
        default_timeout: float = 30.0,
    ):
        super().__init__(fingerprint=fingerprint, proxy=proxy, default_timeout=default_timeout)
        # We deliberately do NOT compose a fingerprint here: the point of
        # HttpxBackend is "send the request as httpx would." Callers that
        # want fingerprints go through CurlCffiBackend or SurfProxyBackend.
        self._client = httpx.Client(
            proxy=proxy,
            timeout=default_timeout,
            follow_redirects=True,
        )

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        body: str | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        merged = dict(headers) if headers else {}
        try:
            start = time.perf_counter()
            resp = self._client.request(
                method=method.upper(),
                url=url,
                headers=merged,
                content=body or None,
                timeout=timeout or self._default_timeout,
            )
            elapsed = (time.perf_counter() - start) * 1000
        except Exception as e:  # noqa: BLE001
            return HttpResponse(status_code=0, error=str(e), backend=self.name)

        return HttpResponse(
            status_code=resp.status_code,
            headers={k: v for k, v in resp.headers.items() if v},
            body=resp.text,
            proto=resp.http_version,
            elapsed_ms=int(elapsed),
            backend=self.name,
        )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass
