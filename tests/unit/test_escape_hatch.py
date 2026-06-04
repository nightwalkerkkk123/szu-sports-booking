"""Unit tests for BrowserEscapeHatch.

We use a fake UIBooker (just a class with a `book` method) and a fake
BackendRouter (we set last_signals directly) so the escape hatch is
tested in isolation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from booking.infra.escape_hatch import BrowserEscapeHatch  # noqa: E402
from booking.infra.risk_scorer import RiskSignals, BLOCKED_THRESHOLD  # noqa: E402


class FakeUIBooker:
    def __init__(self, return_value=None, raise_exc=None):
        self.return_value = return_value or {"success": True, "venue": "fake"}
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    def book(self, **kw):
        self.calls.append(kw)
        if self.raise_exc:
            raise self.raise_exc
        return self.return_value


class FakeRouter:
    def __init__(self, signals: RiskSignals | None):
        self._signals = signals

    @property
    def last_signals(self) -> RiskSignals | None:
        return self._signals


def test_no_signals_means_no_escape():
    ui = FakeUIBooker()
    hatch = BrowserEscapeHatch(ui_booker=ui, router=FakeRouter(None))
    out = hatch.maybe_escape(date="2026-05-28", time_slot="19:00-20:00")
    assert not out.invoked
    assert ui.calls == []


def test_low_risk_does_not_escape():
    sig = RiskSignals(score=50, suspect=True, blocked=False)
    ui = FakeUIBooker()
    hatch = BrowserEscapeHatch(ui_booker=ui, router=FakeRouter(sig))
    out = hatch.maybe_escape(date="2026-05-28", time_slot="19:00-20:00")
    assert not out.invoked
    assert "below blocked" in out.reason
    assert ui.calls == []


def test_blocked_risk_invokes_ui():
    sig = RiskSignals(score=95, blocked=True)
    ui = FakeUIBooker(return_value={"success": True, "venue": "网1"})
    hatch = BrowserEscapeHatch(ui_booker=ui, router=FakeRouter(sig))
    out = hatch.maybe_escape(
        date="2026-05-28", time_slot="19:00-20:00", sport="网球", campus="粤海校区", name="张三",
    )
    assert out.invoked
    assert out.ui_result == {"success": True, "venue": "网1"}
    assert ui.calls == [{
        "date": "2026-05-28", "time_slot": "19:00-20:00",
        "sport": "网球", "campus": "粤海校区", "name": "张三",
    }]


def test_ui_exception_is_captured():
    sig = RiskSignals(score=BLOCKED_THRESHOLD, blocked=True)
    ui = FakeUIBooker(raise_exc=RuntimeError("playwright crashed"))
    hatch = BrowserEscapeHatch(ui_booker=ui, router=FakeRouter(sig))
    out = hatch.maybe_escape(date="d", time_slot="t")
    assert out.invoked
    assert out.ui_result is None
    assert "playwright crashed" in out.reason


def test_should_escape_helper():
    sig_blocked = RiskSignals(score=90, blocked=True)
    sig_ok = RiskSignals(score=30)
    sig_none = None

    h1 = BrowserEscapeHatch(ui_booker=FakeUIBooker(), router=FakeRouter(sig_blocked))
    h2 = BrowserEscapeHatch(ui_booker=FakeUIBooker(), router=FakeRouter(sig_ok))
    h3 = BrowserEscapeHatch(ui_booker=FakeUIBooker(), router=FakeRouter(sig_none))

    assert h1.should_escape()
    assert not h2.should_escape()
    assert not h3.should_escape()
