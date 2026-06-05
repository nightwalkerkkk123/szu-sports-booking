"""Chrome browser fingerprint composer.

This is the single place where browser-like request headers are constructed.
Every HTTPBackend that wants to impersonate Chrome pulls headers from here so
we don't end up with three different header strategies drifting apart.

The current ruleset matches Chrome 148 on macOS because that is what the
existing curl_cffi code was producing (we confirmed it in the HAR). Adjust
DEFAULT_CHROME_VERSION if we ever want a different baseline.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

# Chrome version that the fingerprint matches. Surf currently impersonates
# Chrome 144 on Windows by default; if we want to align with what curl_cffi
# is producing we should run a probe (see FingerprintComposer.probe_version).
DEFAULT_CHROME_VERSION = "148"


@dataclass
class FingerprintComposer:
    """Build Chrome-impersonation headers for outgoing requests.

    The composer is stateless beyond the version string, so it is safe to
    share one instance across threads / backends. Construction is cheap
    and the class holds no I/O resources.
    """

    chrome_version: str = DEFAULT_CHROME_VERSION
    platform: str = "macOS"  # matches what we send in sec-ch-ua-platform

    # Headers that are always supplied by the composer, in fixed order.
    # The order matters for fingerprint evasion: some sites (Akamai, DataDome)
    # hash header ordering as part of their JA3+/JA4+ checks.
    _BASE_HEADERS: tuple[tuple[str, str], ...] = (
        ("Accept", "*/*"),
        ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
        ("Accept-Encoding", "gzip, deflate, br, zstd"),
        ("Connection", "keep-alive"),
    )

    def compose(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Return a new dict containing caller headers plus the fingerprint.

        Caller-supplied headers win on conflict for most fields, but for the
        security-sensitive fingerprint fields (sec-ch-ua, User-Agent,
        sec-ch-ua-platform, sec-ch-ua-mobile) the composer keeps its own
        values so the fingerprint stays internally consistent.
        """
        merged: dict[str, str] = {}
        merged.update(self._base_headers(url))
        if headers:
            for k, v in headers.items():
                if k.lower() in self._FINGERPRINT_FIELDS:
                    # Skip caller overrides; the composer owns these.
                    continue
                merged[k] = v
        # Always re-apply fingerprint fields last so order is stable.
        for k, v in self._fingerprint_fields().items():
            merged[k] = v
        return merged

    # --- internal helpers ------------------------------------------------

    _FINGERPRINT_FIELDS = frozenset({
        "user-agent", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
    })

    def _base_headers(self, url: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, v in self._BASE_HEADERS:
            out[k] = v

        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            origin = f"{parsed.scheme}://{parsed.netloc}"
            # Many SZU endpoints expect these.
            out.setdefault("Origin", origin)
            out.setdefault("Referer", origin + "/")

        # X-Requested-With is what the browser sends for XHR. Most SZU
        # endpoints reject requests without it.
        out.setdefault("X-Requested-With", "XMLHttpRequest")
        return out

    def _fingerprint_fields(self) -> dict[str, str]:
        v = self.chrome_version
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{v}.0.0.0 Safari/537.36"
            ),
            "sec-ch-ua": (
                f'"Chromium";v="{v}", "Google Chrome";v="{v}", "Not/A)Brand";v="99"'
            ),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{self.platform}"',
        }


# Read chrome_version from env at import time so production and tests can
# override without changing code. This is intentionally a module-level
# default; the dataclass field can still be set explicitly in code.
_env_version = os.environ.get("SBOOK_CHROME_VERSION")
if _env_version:
    DEFAULT_CHROME_VERSION = _env_version
