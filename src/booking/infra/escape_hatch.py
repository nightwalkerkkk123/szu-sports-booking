"""BrowserEscapeHatch: last-resort UI booking when HTTP path is blocked.

When the BackendRouter's risk score crosses the BLOCKED threshold, the
HTTP path is effectively dead. The escape hatch calls the existing UI
booking client (CloakBrowser / Playwright) to do the same booking through
real browser automation.

The escape hatch is intentionally a thin layer. It does not retry, it
does not handle UI errors specially, and it does not own any state.
The orchestrator that holds both the router and the UI client is
responsible for calling us at the right time and reacting to the result.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from .risk_scorer import BLOCKED_THRESHOLD
from .router import BackendRouter

logger = logging.getLogger("booking.infra.escape_hatch")


class _UIBooker(Protocol):
    """Protocol for whatever UI-side booking client we delegate to.

    Defining a Protocol here (rather than importing BookingClient) keeps
    infra/ decoupled from the booking module. The orchestrator wires
    the real BookingClient at construction time.
    """

    def book(self, date: str, time_slot: str, sport: str, campus: str, name: str | None = None) -> dict:
        ...


@dataclass(frozen=True)
class EscapeHatchResult:
    """What the escape hatch did.

    Attributes:
        invoked: True if the UI was actually called.
        reason: human-readable explanation of the decision.
        ui_result: Whatever the UI booker returned. None if not invoked.
    """

    invoked: bool
    reason: str
    ui_result: dict | None = None


class BrowserEscapeHatch:
    """Decide whether to invoke the UI booker, and invoke it.

    Usage:
        hatch = BrowserEscapeHatch(ui_booker=BookingClient(), router=router)
        result = hatch.maybe_escape(
            date="2026-05-28", time_slot="19:00-20:00",
            sport="网球", campus="粤海校区", name="王子豪",
        )
        if result.invoked:
            ... handle UI result ...
    """

    def __init__(
        self,
        ui_booker: _UIBooker,
        router: BackendRouter,
        blocked_threshold: int = BLOCKED_THRESHOLD,
    ):
        self._ui = ui_booker
        self._router = router
        self._threshold = blocked_threshold

    def should_escape(self) -> bool:
        """Return True if the router's last signals justify UI escape."""
        sig = self._router.last_signals
        if sig is None:
            return False
        return sig.score >= self._threshold

    def maybe_escape(
        self,
        date: str,
        time_slot: str,
        sport: str = "网球",
        campus: str = "粤海校区",
        name: str | None = None,
    ) -> EscapeHatchResult:
        """If risk is blocked, call the UI booker. Otherwise do nothing.

        This is a single-shot decision: it does not loop, does not poll
        the router repeatedly. The caller is expected to make one
        booking attempt via the router, observe the result, and then
        call maybe_escape() if needed.
        """
        sig = self._router.last_signals
        if sig is None:
            return EscapeHatchResult(
                invoked=False,
                reason="no router signals yet; cannot decide",
            )
        if sig.score < self._threshold:
            return EscapeHatchResult(
                invoked=False,
                reason=f"risk={sig.score} below blocked threshold {self._threshold}",
            )

        logger.warning(
            "invoking UI escape hatch (risk=%d reasons=%s)",
            sig.score, sig.reasons,
        )
        try:
            ui_result = self._ui.book(
                date=date, time_slot=time_slot, sport=sport, campus=campus, name=name,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("UI escape hatch failed: %s", e)
            return EscapeHatchResult(
                invoked=True,
                reason=f"UI raised: {e}",
                ui_result=None,
            )
        return EscapeHatchResult(
            invoked=True,
            reason=f"risk={sig.score} >= {self._threshold}, UI booking attempted",
            ui_result=ui_result,
        )
