"""Smoke test for the three HTTPBackend implementations.

This test exercises each backend against tls.peet.ws, which echoes back the
TLS and HTTP-2 fingerprint it observed. The test does not assert on
fingerprint correctness (we cannot run a full reference comparison in CI);
it only verifies that:
  1. Each backend returns a 200 with a parseable JSON body.
  2. The `backend` field is set to the expected name.
  3. Body extraction works (not empty).

Run:  pytest tests/smoke/test_infra_backends.py -v
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest

# Make src/ importable when running this file directly.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from booking.infra import (  # noqa: E402
    CurlCffiBackend,
    HttpxBackend,
    FingerprintComposer,
    SurfProxyBackend,
)


PROBE_URL = "https://tls.peet.ws/api/all"


def _surf_proxy_alive() -> bool:
    """Best-effort check that the surf-proxy Go process is running."""
    try:
        with socket.create_connection(("127.0.0.1", 9876), timeout=0.5):
            return True
    except OSError:
        return False


def test_httpx_backend_reaches_public_endpoint():
    """HttpxBackend (no fingerprint) should still get a 200."""
    backend = HttpxBackend()
    try:
        resp = backend.request("GET", PROBE_URL, timeout=15.0)
    finally:
        backend.close()
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.error}"
    assert resp.backend == "httpx"
    body = resp.json
    assert isinstance(body, dict)
    assert "tls" in body


def test_curl_cffi_backend_reaches_public_endpoint():
    """CurlCffiBackend should impersonate Chrome and get a 200."""
    backend = CurlCffiBackend(fingerprint=FingerprintComposer())
    try:
        resp = backend.request("GET", PROBE_URL, timeout=15.0)
    finally:
        backend.close()
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.error}"
    assert resp.backend == "curl_cffi"
    body = resp.json
    assert isinstance(body, dict)
    # curl_cffi impersonates chrome 131 by default; we just want the field.
    assert "user_agent" in body


@pytest.mark.skipif(
    not _surf_proxy_alive(),
    reason="surf-proxy Go process not running on 127.0.0.1:9876",
)
def test_surf_proxy_backend_reaches_public_endpoint():
    """SurfProxyBackend should go through the Go process and get a 200."""
    backend = SurfProxyBackend(fingerprint=FingerprintComposer())
    try:
        # Health check explicitly so we can give a clear failure mode.
        assert backend.health(), "surf-proxy /health did not return 200"
        resp = backend.request("GET", PROBE_URL, timeout=20.0)
    finally:
        backend.close()
    assert resp.status_code == 200, f"got {resp.status_code}: {resp.error}"
    assert resp.backend == "surf_proxy"
    body = resp.json
    assert isinstance(body, dict)
    # surf ships a Chrome fingerprint, so user_agent must be present.
    assert "user_agent" in body
    assert "Chrome" in body["user_agent"]


def test_fingerprint_composer_merges_caller_headers():
    """FingerprintComposer should layer caller headers on top of base + fingerprint fields."""
    fp = FingerprintComposer(chrome_version="148", platform="macOS")
    out = fp.compose(
        method="POST",
        url="https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do",
        headers={"Cookie": "MOD_AUTH_CAS=xxx", "X-Custom": "yes"},
    )
    # Base fields present
    assert out["Origin"] == "https://ehall.szu.edu.cn"
    assert out["X-Requested-With"] == "XMLHttpRequest"
    # Caller headers preserved
    assert out["Cookie"] == "MOD_AUTH_CAS=xxx"
    assert out["X-Custom"] == "yes"
    # Fingerprint fields consistent
    assert "Chrome/148.0.0.0" in out["User-Agent"]
    assert "Chrome" in out["sec-ch-ua"]
    assert out["sec-ch-ua-platform"] == '"macOS"'
    assert out["sec-ch-ua-mobile"] == "?0"


def test_fingerprint_composer_rejects_caller_override_of_fingerprint():
    """Caller should not be able to override UA/sec-ch-ua — keeps the fingerprint stable."""
    fp = FingerprintComposer(chrome_version="148")
    out = fp.compose(
        method="GET",
        url="https://example.com",
        headers={"User-Agent": "BannedBot/1.0"},
    )
    # The fingerprint's value wins, not the caller's.
    assert "Chrome/148" in out["User-Agent"]
    assert "BannedBot" not in out["User-Agent"]
