"""BackendRouter: orchestrate multiple HTTPBackend instances with fallback.

The router is the seam between the application and the transport. The
caller asks for a request to be made; the router picks a backend, makes
the call, observes the response, and decides whether to retry on the same
backend, fall through to the next, or give up.

Selection rules (default):

  1. Walk backends in declared order.
  2. Skip backends that are in circuit-breaker cooldown.
  3. Skip backends whose per-backend risk score is above the suspect
     threshold.
  4. For write methods (POST/PUT/PATCH/DELETE), skip the HttpxBackend
     because it offers no fingerprint and would be a footgun.
  5. Try the chosen backend. If it raises BackendUnavailable OR returns
     a response that the risk scorer tags as `blocked`, fall through
     to the next backend.
  6. The first backend whose response is "good enough" (not blocked) is
     the one whose response we return.

If every backend is exhausted, we return the last response we got. The
caller is expected to check `response.error` and the global risk score.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .backends import (
    BackendUnavailable,
    HTTPBackend,
    HttpResponse,
    HttpxBackend,
)
from .risk_scorer import (
    SUSPECT_THRESHOLD,
    RiskScorer,
    RiskSignals,
)

logger = logging.getLogger("booking.infra.router")


WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class RouteDecision:
    """What the router did on behalf of the caller. For observability."""

    backend_used: str
    attempts: int
    signals: RiskSignals
    fell_back: bool = False


# A request observer is called once per completed backend attempt, with
# the response and the resulting signals. Useful for metrics / logs.
RequestObserver = Callable[[HttpResponse, RiskSignals, str], None]


class BackendRouter:
    """Pick a backend, fall back on failure, observe risk.

    The router owns:
      - The ordered list of backends.
      - A RiskScorer shared across backends (per-account would be
        cleaner, but a single scorer is enough for the current use
        case where one user runs one flow at a time).
      - A circuit breaker per backend (time-based cooldown).

    The router does NOT own the BrowserEscapeHatch. It just exposes a
    `last_signals` so a higher-level orchestrator can decide when to
    invoke the escape hatch.
    """

    def __init__(
        self,
        backends: Sequence[HTTPBackend],
        scorer: RiskScorer | None = None,
        breaker_cooldown: float = 300.0,
        per_backend_suspect_threshold: int = SUSPECT_THRESHOLD,
    ):
        if not backends:
            raise ValueError("BackendRouter requires at least one backend")
        self._backends: list[HTTPBackend] = list(backends)
        self._scorer = scorer or RiskScorer()
        self._breaker_cooldown = breaker_cooldown
        self._per_backend_suspect = per_backend_suspect_threshold
        # Per-backend circuit breaker: backend_name -> cool_until_ts
        self._breaker: dict[str, float] = {}
        # Per-backend risk scorer so one bad backend's signal does not
        # poison the others' view of the world.
        self._per_backend_scorer: dict[str, RiskScorer] = {
            b.name: RiskScorer() for b in self._backends
        }
        self._observers: list[RequestObserver] = []
        self._last_signals: RiskSignals | None = None
        self._last_decision: RouteDecision | None = None

    # --- public API ------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: float | None = None,
        path_label: str | None = None,
    ) -> tuple[HttpResponse, RouteDecision]:
        """Send the request through the fallback chain.

        Returns (response, decision). The response is the last one we
        tried; the decision tells you how many attempts we made and
        whether we fell back.
        """
        method_upper = method.upper()
        is_write = method_upper in WRITE_METHODS
        now = time.time()

        attempts = 0
        last_response: HttpResponse | None = None
        first_attempt_backend: str | None = None
        fell_back = False

        for _idx, backend in enumerate(self._backends):
            # Skip backends in circuit-breaker cooldown.
            if self._breaker.get(backend.name, 0.0) > now:
                logger.debug("skip %s: circuit breaker open", backend.name)
                continue
            # Skip HttpxBackend for writes.
            if is_write and isinstance(backend, HttpxBackend):
                logger.debug("skip %s: not allowed for %s", backend.name, method_upper)
                continue
            # Skip backends whose own risk score is too high.
            backend_score = self._per_backend_scorer[backend.name].score
            if backend_score >= self._per_backend_suspect:
                logger.debug(
                    "skip %s: per-backend risk %d >= %d",
                    backend.name,
                    backend_score,
                    self._per_backend_suspect,
                )
                continue

            attempts += 1
            if first_attempt_backend is None:
                first_attempt_backend = backend.name
            elif first_attempt_backend != backend.name:
                fell_back = True

            try:
                resp = backend.request(
                    method=method_upper,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout=timeout,
                )
            except BackendUnavailable as e:
                logger.warning("backend %s unavailable: %s", backend.name, e)
                self._trip_breaker(backend.name, now)
                last_response = HttpResponse(status_code=0, error=str(e), backend=backend.name)
                continue

            last_response = resp
            # Observe the response on both the per-backend and global scorers.
            signals_b = self._per_backend_scorer[backend.name].observe(resp, path=path_label)
            signals_g = self._scorer.observe(resp, path=path_label)
            self._last_signals = signals_g
            for obs in self._observers:
                try:
                    obs(resp, signals_b, backend.name)
                except Exception as e:  # noqa: BLE001
                    logger.debug("observer raised: %s", e)

            # If the response is healthy, we're done.
            if resp.is_ok and not signals_g.suspect:
                self._last_decision = RouteDecision(
                    backend_used=backend.name,
                    attempts=attempts,
                    signals=signals_g,
                    fell_back=fell_back,
                )
                return resp, self._last_decision

            # If the GLOBAL risk scorer says we're blocked, no point
            # trying other backends with the same request. This is the
            # "abort and call the escape hatch" branch.
            if signals_g.blocked:
                logger.warning(
                    "blocked signal: backend=%s score=%d reasons=%s",
                    backend.name,
                    signals_g.score,
                    signals_g.reasons,
                )
                self._trip_breaker(backend.name, now)
                break

            # Suspect: the response came back but we think we may be
            # detected. Fall through to the next backend and also trip
            # the breaker on this one.
            if signals_g.suspect:
                logger.warning(
                    "suspect signal: backend=%s score=%d reasons=%s; falling back",
                    backend.name,
                    signals_g.score,
                    signals_g.reasons,
                )
                self._trip_breaker(backend.name, now)
                continue

            # Otherwise (4xx, 5xx without rate-limit body, etc.) try the
            # next backend if there is one.
            logger.debug(
                "backend %s returned non-ok (status=%d, score=%d); falling through",
                backend.name,
                resp.status_code,
                signals_g.score,
            )

        # No backend succeeded; return whatever we last got.
        if last_response is None:
            last_response = HttpResponse(
                status_code=0,
                error="all backends skipped (likely circuit breakers open)",
                backend="<none>",
            )
        # If we never picked a backend, first_attempt_backend is None.
        decision = RouteDecision(
            backend_used=last_response.backend or "<none>",
            attempts=attempts,
            signals=self._last_signals or RiskSignals(score=0),
            fell_back=fell_back,
        )
        self._last_decision = decision
        return last_response, decision

    def add_observer(self, observer: RequestObserver) -> None:
        """Subscribe to per-attempt response observations."""
        self._observers.append(observer)

    @property
    def last_signals(self) -> RiskSignals | None:
        return self._last_signals

    @property
    def last_decision(self) -> RouteDecision | None:
        return self._last_decision

    def reset(self) -> None:
        """Clear all scoring / breaker state. Useful between flows."""
        self._scorer.reset()
        for s in self._per_backend_scorer.values():
            s.reset()
        self._breaker.clear()
        self._last_signals = None
        self._last_decision = None

    def close(self) -> None:
        for b in self._backends:
            try:
                b.close()
            except Exception:  # noqa: BLE001
                pass

    # --- internals -------------------------------------------------------

    def _trip_breaker(self, backend_name: str, now: float) -> None:
        self._breaker[backend_name] = now + self._breaker_cooldown
        # When we know a backend is bad, we reset its per-backend risk
        # score so that when the breaker expires we are willing to
        # give it a fresh try. Otherwise the per-backend score and the
        # breaker would both be saying "bad" and we would never
        # recover — we'd need both to clear before trying again.
        scorer = self._per_backend_scorer.get(backend_name)
        if scorer is not None:
            scorer.reset()
        logger.info(
            "circuit breaker tripped for %s, cool until %s",
            backend_name,
            time.strftime("%H:%M:%S", time.localtime(now + self._breaker_cooldown)),
        )
