"""RiskScorer: aggregate anti-bot signals from HTTP responses into a 0-100 score.

The score answers one question: "How likely is it that the server thinks
we are a bot?". The RiskRouter (router.py) decides what to do with the
answer; the score itself is just a number plus the list of reasons.

Signals we look for (with weights):

  +50  - "操作过于频繁" / E111080000000 in body  (rate-limit lockout)
  +40  - 403 Forbidden with empty / opaque body  (silent block)
  +30  - 401 Unauthorized with no Set-Cookie       (session rejected)
  +30  - 302 redirect to a CAPTCHA/login page     (challenge triggered)
  +25  - 200 OK with empty body where we expected JSON  (degraded response)
  +20  - Response latency < 50 ms                  (suspiciously fast)
  +15  - 5xx server error                          (server-side issue, not us)
  +10  - Same backend / same path 3rd failure in a row  (pattern)
  -10  - 200 OK with non-empty JSON body and Set-Cookie (looks healthy)

The score is clamped to [0, 100]. A score of 70 is the "suspect" threshold;
90 is the "definitely blocked" threshold at which the BrowserEscapeHatch
should be triggered.

The scorer is intentionally stateless beyond the rolling failure counter;
a fresh scorer instance starts at zero. The router can construct one per
session, or one shared across the process, depending on what it wants to
track.
"""
from __future__ import annotations

import logging
import re
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from .backends import HttpResponse

logger = logging.getLogger("booking.infra.risk_scorer")


# Substrings that we treat as anti-bot / rate-limit indicators. They have
# been observed in SZU responses during the curl_cffi rate-limit incident.
_KNOWN_RATE_LIMIT_BODY_FRAGMENTS: tuple[str, ...] = (
    "操作过于频繁",
    "E111080000000",
    "访问频率过快",
    "请稍后再试",
    "too many requests",
    "rate limit",
)

# Regex for the SZU error-code pattern: an E followed by digits inside the
# JSON body. Matches e.g. "E111080000000" or "code\":\"E030180000001\"".
_SZU_ERROR_CODE_RE = re.compile(r'"code"\s*:\s*"(E\d{10,})"')

# When the server replies with a redirect, this is what we look for in the
# Location header to decide whether it is a challenge redirect.
_CHALLENGE_PATH_HINTS: tuple[str, ...] = (
    "/captcha",
    "/verify",
    "/challenge",
    "/antibot",
    "/authserver/login",
)


# Public dataclass for the result of one observation. RiskRouter consumes
# this to decide what to do.
@dataclass(frozen=True)
class RiskSignals:
    """A snapshot of observed risk.

    Attributes:
        score: 0-100, higher = more likely to be blocked.
        reasons: human-readable explanations, one per signal that fired.
        suspect: True if score >= SUSPECT_THRESHOLD.
        blocked: True if score >= BLOCKED_THRESHOLD.
    """

    score: int
    reasons: tuple[str, ...] = ()
    suspect: bool = False
    blocked: bool = False

    def __str__(self) -> str:  # pragma: no cover - debug only
        if not self.reasons:
            return f"risk={self.score} (clean)"
        return f"risk={self.score} ({'; '.join(self.reasons)})"


# Thresholds are class-level constants so other modules can reference them
# without poking at private state.
SUSPECT_THRESHOLD = 70
BLOCKED_THRESHOLD = 90


class RiskScorer:
    """Observe HTTP responses and produce a rolling 0-100 risk score.

    The scorer keeps a small rolling window of recent observations (the
    last `window` responses) so that repeated soft signals accumulate
    rather than being instantly forgotten. The window is what makes
    "same backend failed 3x in a row" a meaningful signal.

    Usage:
        scorer = RiskScorer()
        for response in responses:
            signals = scorer.observe(response)
            if signals.blocked:
                ...
    """

    def __init__(self, window: int = 10):
        if window < 1:
            raise ValueError("window must be >= 1")
        self._window: int = window
        self._recent: deque[int] = deque(maxlen=window)
        self._recent_reasons: deque[tuple[str, ...]] = deque(maxlen=window)
        self._same_path_streak: int = 0
        self._last_path: str | None = None

    # --- public API ------------------------------------------------------

    def observe(self, response: HttpResponse, path: str | None = None) -> RiskSignals:
        """Record one response and return the updated risk snapshot.

        Args:
            response: the response we just got.
            path: optional path label for the "same path failed N times"
                  signal. If omitted, that signal is not used.
        """
        score, reasons = self._score(response, path)
        self._recent.append(score)
        self._recent_reasons.append(reasons)
        return RiskSignals(
            score=self._aggregate(),
            reasons=tuple(self._collect_reasons()),
            suspect=self._aggregate() >= SUSPECT_THRESHOLD,
            blocked=self._aggregate() >= BLOCKED_THRESHOLD,
        )

    def reset(self) -> None:
        """Clear all history. Use between unrelated sessions."""
        self._recent.clear()
        self._recent_reasons.clear()
        self._same_path_streak = 0
        self._last_path = None

    @property
    def score(self) -> int:
        """Current aggregate score without observing a new response."""
        return self._aggregate()

    # --- internals -------------------------------------------------------

    def _aggregate(self) -> int:
        if not self._recent:
            return 0
        # Use the max of the window so a single 50-signal can be enough to
        # tip us into "suspect" even if it's surrounded by clean 0s. This
        # matches how anti-bot systems behave: the trigger is local in
        # time, the recovery is slow.
        peak = max(self._recent)
        # But also pull in the rolling sum of the second-most-recent half,
        # so a slow accumulation matters too.
        recent_half = list(self._recent)[len(self._recent) // 2 :]
        if recent_half:
            accumulation = sum(recent_half) // max(1, len(recent_half))
        else:
            accumulation = 0
        combined = max(peak, accumulation)
        return max(0, min(100, combined))

    def _collect_reasons(self) -> Iterable[str]:
        # Keep the most recent distinct reasons; max 6 to keep output readable.
        seen: set[str] = set()
        out: list[str] = []
        for reasons in reversed(self._recent_reasons):
            for r in reasons:
                if r in seen:
                    continue
                seen.add(r)
                out.append(r)
                if len(out) >= 6:
                    return out
        return out

    # --- one-shot scoring ------------------------------------------------

    def _score(self, response: HttpResponse, path: str | None) -> tuple[int, tuple[str, ...]]:
        """Return (delta_to_window, reasons) for one response.

        The caller is responsible for putting the delta into the window.
        We do not return a final score here so that we can implement
        the per-observation contribution separately from the aggregation
        logic.
        """
        deltas: list[tuple[int, str]] = []

        # Transport-level failure
        if response.status_code == 0 or response.error:
            deltas.append((25, f"transport-error: {response.error or 'no status'}"))

        # HTTP 401 / 403 with no session cookies → likely session rejection
        if response.status_code in (401, 403):
            cookie_count = sum(1 for k in response.headers if k.lower() == "set-cookie")
            if cookie_count == 0:
                weight = 40 if response.status_code == 403 else 30
                deltas.append((weight, f"http-{response.status_code} with no set-cookie"))

        # Server-side 5xx
        if 500 <= response.status_code < 600:
            deltas.append((15, f"http-{response.status_code}"))

        # Body-based signals
        body = response.body or ""
        body_lower = body.lower()

        for fragment in _KNOWN_RATE_LIMIT_BODY_FRAGMENTS:
            if fragment.lower() in body_lower:
                deltas.append((50, f"rate-limit fragment: {fragment!r}"))
                break

        # Bare E-code in the body, even if no human text matches.
        if _SZU_ERROR_CODE_RE.search(body):
            # We only count this if the body did not already trigger the
            # human-readable fragment check (avoid double-counting).
            if not any(frag.lower() in body_lower for frag in _KNOWN_RATE_LIMIT_BODY_FRAGMENTS):
                deltas.append((40, "SZU error code (E-prefixed) in body"))

        # Empty body where we'd expect data: 200 OK with empty body and
        # content-length 0 / not present is suspicious on read endpoints.
        if response.status_code == 200 and not body:
            # But only flag if it isn't a known-empty response (204, etc).
            # We treat 200 with empty body as a soft signal, not a hard one.
            deltas.append((20, "200 OK with empty body"))

        # 302 redirect to challenge page
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "") or response.headers.get("location", "")
            if any(hint in location for hint in _CHALLENGE_PATH_HINTS):
                deltas.append((30, f"redirect to challenge: {location[:80]}"))

        # Suspiciously fast response: under 50 ms is not human.
        if 0 < response.elapsed_ms < 50 and response.status_code >= 200:
            deltas.append((20, f"fast response: {response.elapsed_ms}ms"))

        # Healthy response: 200 with JSON body and a Set-Cookie header.
        # Apply a small negative to encourage recovery.
        # The catch: this should NOT fire if the body itself contains an
        # error code or rate-limit fragment, because then the JSON is
        # well-formed but the response is hostile.
        already_hostile = any(label.startswith(
            ("rate-limit", "SZU error", "http-403", "http-401", "redirect to challenge")
        ) for _, label in deltas)
        if (
            response.status_code == 200
            and body
            and response.json is not None
            and not already_hostile
        ):
            deltas.append((-10, "healthy JSON response"))

        # Same path failing repeatedly.
        if path is not None:
            if self._last_path == path and (response.status_code >= 400 or response.error):
                self._same_path_streak += 1
                if self._same_path_streak >= 3:
                    deltas.append((10, f"same path failed {self._same_path_streak}x"))
            else:
                self._same_path_streak = 0
            self._last_path = path

        if not deltas:
            return 0, ()
        # Sum, clamp to [0, 100] for the per-observation contribution.
        # The aggregator will then combine with the window.
        total = sum(d[0] for d in deltas)
        total = max(0, min(100, total))
        return total, tuple(d[1] for d in deltas)
