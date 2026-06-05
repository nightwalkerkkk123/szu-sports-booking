"""Plan + CriticalPoints for run verification.

Inspired by Webwright's plan.md + critical_points checklist, this module lets
a caller declare a list of *verifiable* expectations (e.g. "login succeeded",
"campus selected") and then check them after a run completes. The result is
persisted to `<run_dir>/plan.md` and `<run_dir>/critical_points.json` and
rendered in the HTML report.

Design goals:
    * Pure data class - no I/O coupling to RunManager (it only knows how to
      save/load JSON/markdown to a directory it is given).
    * Lightweight verification - `status` field is set by the caller, this
      module does not introspect the browser. The actual page-level checks
      live in :class:ooking.client.BookingClient and use the same data
      class as a contract.
    * Round-trip safe - `to_dict` / `from_dict` cover all fields, and an
      empty plan serialises to an empty list (never raises).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class EvidenceType(str, Enum):
    """How the critical point's evidence is verified."""

    SCREENSHOT = "screenshot"  # passes when a screenshot file exists
    TEXT_PRESENT = "text"  # passes when expected_text appears in DOM
    SELECTOR = "selector"  # passes when a CSS selector resolves
    CUSTOM = "custom"  # caller defines a predicate (no auto-check)


class PointStatus(str, Enum):
    """Verification state of a single critical point."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CriticalPoint:
    """A single verifiable expectation for a run.

    Attributes:
        name: Short stable identifier (e.g. `"login_succeeded"`).
        description: Human-readable sentence explaining the expectation.
        evidence_type: One of :class:EvidenceType.
        evidence_value: The value the check uses (screenshot filename,
            expected text, CSS selector, or `None` for `CUSTOM`).
        status: Current verification state.
        evidence_path: Path to screenshot file (set after `SCREENSHOT` check
            succeeds). Relative to the run directory when possible.
        note: Optional free-form note (e.g. failure reason).
        checked_at: ISO timestamp of last status change.
    """

    name: str
    description: str
    evidence_type: EvidenceType = EvidenceType.CUSTOM
    evidence_value: str | None = None
    status: PointStatus = PointStatus.PENDING
    evidence_path: str | None = None
    note: str | None = None
    checked_at: str | None = None

    def mark(self, status: PointStatus, note: str | None = None) -> None:
        """Update status, attach note, and stamp the timestamp."""
        self.status = status
        self.note = note
        self.checked_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-friendly dict."""
        return {
            "name": self.name,
            "description": self.description,
            "evidence_type": self.evidence_type.value,
            "evidence_value": self.evidence_value,
            "status": self.status.value,
            "evidence_path": self.evidence_path,
            "note": self.note,
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CriticalPoint:
        """Inverse of :meth:	o_dict. Tolerates missing fields."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            evidence_type=EvidenceType(data.get("evidence_type", "custom")),
            evidence_value=data.get("evidence_value"),
            status=PointStatus(data.get("status", "pending")),
            evidence_path=data.get("evidence_path"),
            note=data.get("note"),
            checked_at=data.get("checked_at"),
        )


@dataclass
class Plan:
    """A list of :class:CriticalPoint with persistence helpers.

    The plan is mutable until :meth:inalise is called, after which adding
    more points is a no-op (handy for the HTML report which expects a stable
    list once verification begins).
    """

    name: str = "default"
    points: list[CriticalPoint] = field(default_factory=list)
    _finalised: bool = field(default=False, repr=False)

    # ---- mutation ---------------------------------------------------------

    def add(
        self,
        name: str,
        description: str,
        evidence_type: EvidenceType = EvidenceType.CUSTOM,
        evidence_value: str | None = None,
    ) -> CriticalPoint:
        """Append a new critical point. Returns the created point."""
        if self._finalised:
            raise RuntimeError("Plan is finalised; create a new plan instead")
        if any(p.name == name for p in self.points):
            raise ValueError(f"Duplicate critical point name: {name!r}")
        point = CriticalPoint(
            name=name,
            description=description,
            evidence_type=evidence_type,
            evidence_value=evidence_value,
        )
        self.points.append(point)
        return point

    def get(self, name: str) -> CriticalPoint | None:
        """Find a point by name (linear scan; lists are short)."""
        for p in self.points:
            if p.name == name:
                return p
        return None

    def check(self, name: str, status: PointStatus, note: str | None = None) -> None:
        """Update a point's status. No-op if the name is unknown."""
        point = self.get(name)
        if point is None:
            return
        point.mark(status, note)

    def finalise(self) -> None:
        """Lock the plan; further `add` calls will raise."""
        self._finalised = True

    # ---- stats ------------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.points)

    @property
    def passed(self) -> int:
        return sum(1 for p in self.points if p.status == PointStatus.PASSED)

    @property
    def failed(self) -> int:
        return sum(1 for p in self.points if p.status == PointStatus.FAILED)

    @property
    def pending(self) -> int:
        return sum(1 for p in self.points if p.status == PointStatus.PENDING)

    @property
    def is_fully_verified(self) -> bool:
        """True iff every point is PASSED, FAILED, or SKIPPED (no PENDING)."""
        return self.pending == 0

    # ---- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "points": [p.to_dict() for p in self.points],
            "finalised": self._finalised,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        plan = cls(name=data.get("name", "default"))
        for raw in data.get("points", []):
            plan.points.append(CriticalPoint.from_dict(raw))
        plan._finalised = bool(data.get("finalised", False))
        return plan

    def save(self, run_dir: str | Path) -> tuple[Path, Path]:
        """Persist both `plan.md` and `critical_points.json`.

        Returns:
            Tuple of (markdown_path, json_path).
        """
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        md_path = run_dir / "plan.md"
        json_path = run_dir / "critical_points.json"
        md_path.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return md_path, json_path

    @classmethod
    def load(cls, run_dir: str | Path) -> Plan | None:
        """Read back a plan from `<run_dir>/critical_points.json`.

        Returns `None` when the file does not exist (plan was never
        declared for this run). Never raises.
        """
        json_path = Path(run_dir) / "critical_points.json"
        if not json_path.exists():
            return None
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return cls.from_dict(data)

    # ---- rendering --------------------------------------------------------

    def to_markdown(self) -> str:
        """Render the plan as a markdown checklist (the Webwright contract)."""
        lines: list[str] = [
            f"# Plan: {self.name}",
            "",
            f"Total critical points: {self.total}",
            f"Passed: {self.passed} | Failed: {self.failed} | Pending: {self.pending}",
            "",
        ]
        if not self.points:
            lines.append("_No critical points declared._")
            return "\n".join(lines) + "\n"

        for p in self.points:
            mark = {
                PointStatus.PASSED: "[x]",
                PointStatus.FAILED: "[ ]",
                PointStatus.SKIPPED: "[-]",
                PointStatus.PENDING: "[ ]",
            }[p.status]
            lines.append(f"- {mark} **{p.name}** \u2014 {p.description}")
            if p.evidence_type is not EvidenceType.CUSTOM and p.evidence_value:
                lines.append(f"  - evidence: {p.evidence_type.value} = {p.evidence_value}")
            if p.evidence_path:
                lines.append(f"  - file: {p.evidence_path}")
            if p.note:
                lines.append(f"  - note: {p.note}")
        return "\n".join(lines) + "\n"


def default_booking_plan(
    campus: str,
    sport: str,
    time_slot: str,
    date_index: int,
) -> Plan:
    """Build the standard 4-point plan for a booking run.

    The CPs map to the steps in :class:ooking.client.BookingClient:
        1. login_succeeded \u2014 account is logged in.
        2. campus_selected \u2014 the right campus tab is active.
        3. slot_selected \u2014 the right sport + time slot is reachable.
        4. confirm_clean \u2014 the confirm page shows a success marker and
           none of the known failure markers ("\u64cd\u4f5c\u8fc7\u4e8e\u9891\u7e41"
           etc.).
    """
    plan = Plan(name=f"book_{campus}_{sport}")
    plan.add(
        "login_succeeded",
        "Account logged in and is on the booking page",
        EvidenceType.SELECTOR,
        ".user-info, .booking-page, [data-logged-in='true']",
    )
    plan.add(
        "campus_selected",
        f"Campus tab '{campus}' is active",
        EvidenceType.TEXT_PRESENT,
        campus,
    )
    plan.add(
        "slot_selected",
        f"Sport '{sport}' and slot '{time_slot}' (date_index={date_index}) is reachable",
        EvidenceType.TEXT_PRESENT,
        time_slot,
    )
    plan.add(
        "confirm_clean",
        "Confirm page shows a success marker and no failure marker",
        EvidenceType.CUSTOM,
        None,
    )
    return plan
