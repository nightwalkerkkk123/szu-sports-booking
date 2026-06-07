"""Unit tests for RiskScorer.

Run:  pytest tests/unit/test_risk_scorer.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from booking.infra.backends import HttpResponse  # noqa: E402
from booking.infra.risk_scorer import (  # noqa: E402
    BLOCKED_THRESHOLD,
    SUSPECT_THRESHOLD,
    RiskScorer,
)


def _resp(**kw) -> HttpResponse:
    """Helper: build an HttpResponse with sensible defaults."""
    return HttpResponse(
        status_code=kw.get("status_code", 200),
        headers=kw.get("headers", {}),
        body=kw.get("body", ""),
        elapsed_ms=kw.get("elapsed_ms", 100),
        backend=kw.get("backend", "test"),
        error=kw.get("error"),
    )


# --- baseline -------------------------------------------------------------


def test_clean_response_stays_low():
    """A 200 JSON response should produce a small (or zero) score."""
    s = RiskScorer()
    out = s.observe(_resp(status_code=200, body='{"ok":true}'))
    assert out.score < SUSPECT_THRESHOLD
    assert not out.suspect
    assert not out.blocked


# --- hard signals ---------------------------------------------------------


def test_rate_limit_body_fragments_trigger_high_score():
    """The literal '操作过于频繁' string should fire the +50 signal."""
    s = RiskScorer()
    out = s.observe(_resp(status_code=200, body='{"msg":"操作过于频繁","code":"E111080000000"}'))
    # +50 from the fragment, plus +40 from the SZU error code, but we
    # dedupe so we don't double-count. So the contribution is +50 per
    # observation, and the aggregate is 50.
    assert out.score >= 50
    assert any("rate-limit" in r for r in out.reasons)


def test_rate_limit_plus_other_signal_hits_suspect_threshold():
    """Rate-limit alone is +50; combine with an empty-body or 5xx to hit 70."""
    s = RiskScorer()
    out = s.observe(
        _resp(
            status_code=200,
            body='{"msg":"操作过于频繁","code":"E111080000000"}',  # +50
            elapsed_ms=10,  # +20 fast
        )
    )
    # 50 + 20 = 70 -> SUSPECT threshold reached.
    assert out.score >= SUSPECT_THRESHOLD
    assert out.suspect


def test_403_with_no_set_cookie_is_suspect():
    s = RiskScorer()
    out = s.observe(_resp(status_code=403, headers={}, body="forbidden"))
    assert out.score >= 40
    assert any("403" in r for r in out.reasons)


def test_401_with_no_set_cookie_triggers_signal():
    s = RiskScorer()
    out = s.observe(_resp(status_code=401, headers={}, body=""))
    assert out.score >= 30
    assert any("401" in r for r in out.reasons)


def test_redirect_to_captcha_path_triggers_signal():
    s = RiskScorer()
    out = s.observe(
        _resp(
            status_code=302,
            headers={"Location": "https://example.com/captcha?token=abc"},
        )
    )
    assert any("challenge" in r for r in out.reasons)


def test_5xx_triggers_soft_signal():
    s = RiskScorer()
    out = s.observe(_resp(status_code=500, body="oops"))
    assert any("500" in r for r in out.reasons)


def test_fast_response_triggers_signal():
    s = RiskScorer()
    out = s.observe(_resp(status_code=200, body="hi", elapsed_ms=10))
    assert any("fast" in r for r in out.reasons)


def test_empty_body_on_200_triggers_signal():
    s = RiskScorer()
    out = s.observe(_resp(status_code=200, body=""))
    assert any("empty body" in r for r in out.reasons)


# --- aggregation ---------------------------------------------------------


def test_repeated_failures_accumulate():
    """Same path failing 3+ times should trip the streak signal."""
    s = RiskScorer()
    for _ in range(3):
        s.observe(_resp(status_code=500, body=""), path="/x")
    # Third observation should include the streak signal in reasons.
    assert any("failed" in r for r in s.observe(_resp(status_code=500, body=""), path="/x").reasons)


def test_blocked_threshold_uses_max_not_average():
    """A single huge signal should be enough to trip BLOCKED, even if
    the rolling average is low because of recent good observations."""
    s = RiskScorer()
    # Healthy history
    for _ in range(5):
        s.observe(_resp(status_code=200, body='{"ok":1}'))
    # One catastrophic response
    out = s.observe(
        _resp(
            status_code=403,
            headers={},
            body='{"msg":"操作过于频繁","code":"E111080000000"}',
        )
    )
    assert out.score >= BLOCKED_THRESHOLD, f"score={out.score}, expected >= {BLOCKED_THRESHOLD}"
    assert out.blocked


def test_reset_clears_state():
    s = RiskScorer()
    for _ in range(5):
        s.observe(_resp(status_code=403, headers={}, body="操作过于频繁"))
    assert s.score >= SUSPECT_THRESHOLD
    s.reset()
    assert s.score == 0


def test_score_clamps_to_100():
    """A pathological response with every signal firing should be clamped."""
    s = RiskScorer()
    out = s.observe(
        _resp(
            status_code=403,
            headers={},
            body="操作过于频繁 E111080000000",
            elapsed_ms=1,
            error="also transport error",
        )
    )
    assert 0 <= out.score <= 100


# --- healthy response counterweight --------------------------------------


def test_healthy_response_subtracts():
    """A healthy JSON response should apply a -10 negative delta."""
    s = RiskScorer()
    # Build up some risk
    s.observe(_resp(status_code=403, body="操作过于频繁"))
    before = s.score
    # Now a healthy one
    s.observe(_resp(status_code=200, body='{"ok":1}'))
    # Score should not grow.
    assert s.score <= before
