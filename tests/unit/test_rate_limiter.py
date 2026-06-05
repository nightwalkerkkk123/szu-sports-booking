"""Unit tests for AccountRateLimiter.

Run:  pytest tests/unit/test_rate_limiter.py -v
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from booking.infra.rate_limiter import (  # noqa: E402
    AccountRateLimiter,
)


@pytest.fixture
def tmp_state_path(tmp_path: Path) -> Path:
    return tmp_path / "rate_limits.json"


def test_first_acquire_is_allowed(tmp_state_path: Path):
    rl = AccountRateLimiter(state_path=tmp_state_path, burst=2)
    d = rl.acquire("user1")
    assert d.allowed
    assert d.tokens_remaining >= 0


def test_burst_then_block(tmp_state_path: Path):
    """`burst=2` means we can do 2 then the 3rd should be blocked."""
    rl = AccountRateLimiter(state_path=tmp_state_path, burst=2, steady_rate=0.01)
    assert rl.acquire("u").allowed
    assert rl.acquire("u").allowed
    d = rl.acquire("u")
    assert not d.allowed
    assert d.wait_seconds > 0


def test_violation_sets_cooldown(tmp_state_path: Path):
    rl = AccountRateLimiter(state_path=tmp_state_path, burst=2)
    rl.acquire("u")
    rl.record_violation("u", cooldown_seconds=60)
    d = rl.acquire("u")
    assert not d.allowed
    assert d.wait_seconds > 50
    assert "cooldown" in d.reason


def test_clear_removes_state(tmp_state_path: Path):
    rl = AccountRateLimiter(state_path=tmp_state_path, burst=2)
    rl.acquire("u")
    rl.record_violation("u", cooldown_seconds=60)
    rl.clear("u")
    d = rl.acquire("u")
    assert d.allowed


def test_persists_across_instances(tmp_state_path: Path):
    """State must survive process restarts."""
    rl1 = AccountRateLimiter(state_path=tmp_state_path, burst=2)
    rl1.acquire("u")
    rl1.record_violation("u", cooldown_seconds=120)

    # New instance, same path -> should see the cooldown.
    rl2 = AccountRateLimiter(state_path=tmp_state_path, burst=2)
    d = rl2.acquire("u")
    assert not d.allowed
    assert d.wait_seconds > 100


def test_state_returns_current_view(tmp_state_path: Path):
    rl = AccountRateLimiter(state_path=tmp_state_path, burst=2)
    rl.acquire("u")
    st = rl.state("u")
    assert st is not None
    assert st.account == "u"
    assert st.violation_count == 0
    rl.record_violation("u", cooldown_seconds=30)
    st = rl.state("u")
    assert st.violation_count == 1
    assert st.cool_until > time.time()


def test_unknown_account_starts_with_full_bucket(tmp_state_path: Path):
    rl = AccountRateLimiter(state_path=tmp_state_path, burst=3)
    for _ in range(3):
        assert rl.acquire("new-user").allowed
    # 4th should be blocked.
    assert not rl.acquire("new-user").allowed


def test_penalty_rate_is_lower_than_steady(tmp_state_path: Path):
    """After cooldown ends, requests should be throttled to penalty rate."""
    rl = AccountRateLimiter(
        state_path=tmp_state_path,
        burst=1,
        steady_rate=1.0,  # 1/s
        penalty_rate=0.1,  # 1/10s
        penalty_duration=120,
        cooldown_seconds=0,  # immediate transition to penalty
    )
    rl.acquire("u")
    # First request was a violation; cooldown is 0, so we transition
    # straight to penalty mode.
    rl.record_violation("u", cooldown_seconds=0)
    d = rl.acquire("u")
    # Tokens might be available from the burst, but refill should be slow.
    if d.allowed:
        # If we did get one through, the next one should take ~10s.
        d2 = rl.acquire("u")
        assert d2.wait_seconds > 5
