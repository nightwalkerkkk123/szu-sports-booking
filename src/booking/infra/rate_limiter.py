"""Account-level rate limiter with cooldown + persistence.

The RateLimit problem here is two-tier:

  1. Steady state: don't send more than N requests per M seconds per account.
     Without this, even a "well-behaved" client can look like a bot.

  2. Penalty state: after we receive a rate-limit response, back off hard
     for some minutes, then resume at a much lower rate.

We solve both with the same mechanism: a token bucket per account, with a
`cool_until` timestamp that overrides the bucket when set. State is
persisted to data/rate_limits.json so a process restart doesn't reset a
cooldown we earned the hard way.

Usage:

    limiter = AccountRateLimiter()
    decision = limiter.acquire("2023150090")
    if not decision.allowed:
        time.sleep(decision.wait_seconds)
        decision = limiter.acquire("2023150090")
    ... make request ...
    if we_got_rate_limited:
        limiter.record_penalty("2023150090", cooldown_seconds=300)
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("booking.infra.rate_limiter")


# Default policy. The numbers come from the PRD's "Implementation Decisions"
# section. They are intentionally conservative.
DEFAULT_STEADY_RATE = 1.0 / 3.0  # 1 request per 3 seconds
DEFAULT_BURST = 2               # allow short bursts up to 2
DEFAULT_PENALTY_RATE = 1.0 / 10.0  # 1 request per 10 seconds
DEFAULT_PENALTY_DURATION = 30 * 60  # 30 minutes at penalty rate
DEFAULT_COOLDOWN_SECONDS = 5 * 60   # 5 minute hard cooldown after a violation


@dataclass(frozen=True)
class RateLimitState:
    """One account's rate-limit state. Persisted to disk.

    Fields are explicit rather than nested so JSON serialization is
    trivial and the on-disk format is human-readable for debugging.
    """

    account: str
    tokens: float                      # current token-bucket level
    last_refill_at: float              # monotonic-ish timestamp (seconds)
    cool_until: float = 0.0            # 0 = not cooling; > 0 = cool until this time
    penalty_until: float = 0.0         # 0 = not in penalty mode; > 0 = penalty until this time
    violation_count: int = 0           # for diagnostics / future tuning
    last_violation_at: float = 0.0


@dataclass(frozen=True)
class RouteDecision:
    """Result of a rate-limiter acquire() call.

    `wait_seconds` is the time the caller should sleep before retrying.
    `allowed` is False iff the caller should NOT make the request yet.
    """

    allowed: bool
    wait_seconds: float = 0.0
    reason: str = ""
    tokens_remaining: float = 0.0


class AccountRateLimiter:
    """Per-account rate limiter with cooldown + persistence.

    Persistence is on-demand: state changes (acquire, record_penalty) write
    to disk, but the limiter does not start a background thread to flush.
    This keeps the implementation simple and the failure modes obvious.

    All times are in seconds since the unix epoch (time.time()), which is
    what JSON can round-trip without surprising the reader.
    """

    DEFAULT_STATE_PATH = Path("data/rate_limits.json")

    def __init__(
        self,
        state_path: Optional[Path] = None,
        steady_rate: float = DEFAULT_STEADY_RATE,
        burst: int = DEFAULT_BURST,
        penalty_rate: float = DEFAULT_PENALTY_RATE,
        penalty_duration: float = DEFAULT_PENALTY_DURATION,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ):
        self._path = Path(state_path) if state_path else self.DEFAULT_STATE_PATH
        self._steady_rate = steady_rate
        self._burst = burst
        self._penalty_rate = penalty_rate
        self._penalty_duration = penalty_duration
        self._cooldown_seconds = cooldown_seconds
        self._states: dict[str, RateLimitState] = {}
        self._load()

    # --- public API ------------------------------------------------------

    def acquire(self, account: str) -> RouteDecision:
        """Ask permission to send one request for the given account.

        Returns a RouteDecision; if allowed is False, the caller should
        sleep `wait_seconds` and call acquire() again.
        """
        now = time.time()
        st = self._states.get(account) or self._new_state(account, now)

        # Hard cooldown takes priority over everything.
        if st.cool_until > now:
            wait = st.cool_until - now
            return RouteDecision(
                allowed=False,
                wait_seconds=wait,
                reason=f"cooldown for {wait:.0f}s after rate-limit violation",
                tokens_remaining=st.tokens,
            )

        # Refill the bucket. In penalty mode we use the lower rate.
        rate = self._penalty_rate if st.penalty_until > now else self._steady_rate
        elapsed = max(0.0, now - st.last_refill_at)
        new_tokens = min(float(self._burst), st.tokens + elapsed * rate)
        st = RateLimitState(
            account=st.account,
            tokens=new_tokens,
            last_refill_at=now,
            cool_until=st.cool_until,
            penalty_until=st.penalty_until,
            violation_count=st.violation_count,
            last_violation_at=st.last_violation_at,
        )

        if new_tokens < 1.0:
            wait = (1.0 - new_tokens) / rate
            # Stash the (unspent) refill so we don't double-count it.
            self._states[account] = st
            self._save()
            return RouteDecision(
                allowed=False,
                wait_seconds=wait,
                reason=f"bucket empty at {rate:.3f} req/s, wait {wait:.1f}s",
                tokens_remaining=new_tokens,
            )

        # Consume one token and persist.
        st = RateLimitState(
            account=st.account,
            tokens=new_tokens - 1.0,
            last_refill_at=now,
            cool_until=st.cool_until,
            penalty_until=st.penalty_until,
            violation_count=st.violation_count,
            last_violation_at=st.last_violation_at,
        )
        self._states[account] = st
        self._save()
        return RouteDecision(
            allowed=True,
            tokens_remaining=st.tokens,
            reason="ok" + (" (penalty rate)" if st.penalty_until > now else ""),
        )

    def record_violation(self, account: str, cooldown_seconds: Optional[float] = None) -> None:
        """Mark that the server told us to slow down.

        Sets a hard cooldown and switches the bucket to penalty rate for
        `penalty_duration` seconds after the cooldown ends.
        """
        now = time.time()
        st = self._states.get(account) or self._new_state(account, now)
        cd = cooldown_seconds if cooldown_seconds is not None else self._cooldown_seconds
        self._states[account] = RateLimitState(
            account=account,
            tokens=0.0,
            last_refill_at=now,
            cool_until=now + cd,
            penalty_until=now + cd + self._penalty_duration,
            violation_count=st.violation_count + 1,
            last_violation_at=now,
        )
        self._save()
        logger.warning(
            "rate-limit violation for %s: cooldown %.0fs, penalty until %s",
            account, cd,
            time.strftime("%H:%M:%S", time.localtime(now + cd + self._penalty_duration)),
        )

    def clear(self, account: str) -> None:
        """Forget all state for an account."""
        self._states.pop(account, None)
        self._save()

    def state(self, account: str) -> Optional[RateLimitState]:
        """Read-only view of an account's state. Useful for observability."""
        return self._states.get(account)

    # --- internals -------------------------------------------------------

    def _new_state(self, account: str, now: float) -> RateLimitState:
        return RateLimitState(
            account=account,
            tokens=float(self._burst),
            last_refill_at=now,
            cool_until=0.0,
            penalty_until=0.0,
            violation_count=0,
            last_violation_at=0.0,
        )

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            logger.warning("could not read rate-limit state at %s: %s", self._path, e)
            return
        for account, fields in raw.get("states", {}).items():
            try:
                self._states[account] = RateLimitState(
                    account=account,
                    tokens=float(fields.get("tokens", 0.0)),
                    last_refill_at=float(fields.get("last_refill_at", 0.0)),
                    cool_until=float(fields.get("cool_until", 0.0)),
                    penalty_until=float(fields.get("penalty_until", 0.0)),
                    violation_count=int(fields.get("violation_count", 0)),
                    last_violation_at=float(fields.get("last_violation_at", 0.0)),
                )
            except (TypeError, ValueError) as e:
                logger.warning("skipping malformed rate-limit state for %s: %s", account, e)

    def _save(self) -> None:
        # Write atomically: write to a tmp file and rename, so a crash
        # mid-write doesn't corrupt the on-disk state.
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            payload = {
                "states": {
                    acct: {
                        "tokens": st.tokens,
                        "last_refill_at": st.last_refill_at,
                        "cool_until": st.cool_until,
                        "penalty_until": st.penalty_until,
                        "violation_count": st.violation_count,
                        "last_violation_at": st.last_violation_at,
                    }
                    for acct, st in self._states.items()
                }
            }
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError as e:
            logger.warning("could not persist rate-limit state to %s: %s", self._path, e)
