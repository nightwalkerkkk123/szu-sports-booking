"""Unit tests for BackendRouter using fake backends.

These tests do not hit the network. We construct HTTPBackend subclasses
that return canned responses so we can exercise the router's decision
logic in isolation.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from booking.infra.backends import (  # noqa: E402
    BackendUnavailable,
    HTTPBackend,
    HttpResponse,
)
from booking.infra.router import BackendRouter  # noqa: E402


class FakeBackend(HTTPBackend):
    """A backend that returns whatever response you queue up.

    Each call to request() pops the next response from `script`. If a
    script entry is the string "RAISE", the backend raises
    BackendUnavailable instead of returning a response.
    """

    def __init__(self, name: str, script: list):
        super().__init__()
        self.name = name
        self._script = list(script)
        self.calls: list[tuple[str, str]] = []

    def request(self, method, url, headers=None, body=None, timeout=None):
        self.calls.append((method, url))
        if not self._script:
            return HttpResponse(status_code=599, error="script exhausted",
                                backend=self.name)
        nxt = self._script.pop(0)
        if nxt == "RAISE":
            raise BackendUnavailable(f"{self.name} down")
        if isinstance(nxt, Exception):
            raise nxt
        if isinstance(nxt, HttpResponse):
            # Always stamp the backend name so callers can tell which
            # fake produced the response.
            return HttpResponse(
                status_code=nxt.status_code,
                headers=nxt.headers,
                body=nxt.body,
                proto=nxt.proto,
                elapsed_ms=nxt.elapsed_ms,
                backend=self.name,
                error=nxt.error,
            )
        # dict shorthand
        return HttpResponse(backend=self.name, **nxt)


def _ok(body: str = '{"ok":1}', **kw) -> HttpResponse:
    return HttpResponse(status_code=200, body=body, backend="<unset>", **kw)


def _blocked() -> HttpResponse:
    return HttpResponse(
        status_code=200,
        body='{"msg":"操作过于频繁","code":"E111080000000"}',
        elapsed_ms=10,
        backend="<unset>",
    )


# --- basic behavior -------------------------------------------------------


def test_first_backend_succeeds_returns_its_response():
    a = FakeBackend("a", [_ok()])
    b = FakeBackend("b", [_ok()])
    r = BackendRouter([a, b])
    resp, decision = r.request("GET", "https://x")
    assert resp.is_ok
    assert decision.backend_used == "a"
    assert decision.attempts == 1
    assert not decision.fell_back
    assert a.calls == [("GET", "https://x")]
    assert b.calls == []


def test_falls_back_when_first_is_unavailable():
    a = FakeBackend("a", ["RAISE"])
    b = FakeBackend("b", [_ok()])
    r = BackendRouter([a, b])
    resp, decision = r.request("GET", "https://x")
    assert resp.is_ok
    assert decision.backend_used == "b"
    assert decision.fell_back
    assert decision.attempts == 2


def test_falls_back_when_first_returns_blocked():
    """A backend whose response scores 'suspect' or 'blocked' should be skipped."""
    a = FakeBackend("a", [_blocked()])
    b = FakeBackend("b", [_ok()])
    r = BackendRouter([a, b])
    resp, decision = r.request("GET", "https://x")
    assert resp.is_ok
    assert decision.backend_used == "b"
    assert decision.fell_back


def test_all_backends_fail_returns_last_response():
    a = FakeBackend("a", [_blocked()])
    b = FakeBackend("b", [_blocked()])
    r = BackendRouter([a, b])
    resp, decision = r.request("GET", "https://x")
    assert decision.attempts == 2
    # HTTP 200 with a rate-limit body is technically is_ok, but the
    # caller should be able to tell from the global risk signals that
    # the call was effectively a failure.
    assert r.last_signals is not None
    assert r.last_signals.suspect
    # The response body itself should still be the last one we got.
    assert "操作过于频繁" in resp.body


def test_post_skips_httpx_backend():
    """Write methods must not use the no-fingerprint HttpxBackend."""
    from booking.infra.backends import HttpxBackend
    a = FakeBackend("a", [_ok()])
    h = HttpxBackend()  # would 200 but is excluded by the policy
    r = BackendRouter([a, h])
    resp, decision = r.request("POST", "https://x", body="x=1")
    assert decision.backend_used == "a"
    h.close()


# --- circuit breaker ------------------------------------------------------


def test_circuit_breaker_opens_after_blocked():
    a = FakeBackend("a", [_blocked(), _ok(), _ok()])
    r = BackendRouter([a], breaker_cooldown=60)
    # First call: blocked, breaker opens.
    r.request("GET", "https://x/1")
    # Second call: should skip 'a' because breaker is open.
    resp, decision = r.request("GET", "https://x/2")
    # No fallback configured; we get the all-skipped sentinel.
    assert decision.attempts == 0
    assert resp.status_code == 0
    assert "skipped" in (resp.error or "")


def test_breaker_cooldown_expires():
    """After cooldown, the backend is tried again."""
    a = FakeBackend("a", [_blocked(), _ok()])
    r = BackendRouter([a], breaker_cooldown=0.05)  # 50ms
    r.request("GET", "https://x/1")
    import time
    time.sleep(0.1)
    resp, decision = r.request("GET", "https://x/2")
    assert decision.backend_used == "a"


# --- observability --------------------------------------------------------


def test_observer_is_called_per_attempt():
    seen = []
    a = FakeBackend("a", [_ok()])
    b = FakeBackend("b", [_ok()])
    r = BackendRouter([a, b])
    r.add_observer(lambda resp, sig, name: seen.append((name, sig.score)))
    r.request("GET", "https://x")
    # Only 'a' was called, so only one observation.
    assert len(seen) == 1
    assert seen[0][0] == "a"


def test_reset_clears_state():
    a = FakeBackend("a", [_blocked(), _ok()])
    r = BackendRouter([a], breaker_cooldown=60)
    r.request("GET", "https://x/1")
    r.reset()
    # After reset, breaker is cleared, so 'a' is tried again.
    resp, decision = r.request("GET", "https://x/2")
    assert decision.backend_used == "a"
