"""Tests for the Plan / CriticalPoint observability module."""

import pytest

from booking.observability.plan import (
    CriticalPoint,
    EvidenceType,
    Plan,
    PointStatus,
    default_booking_plan,
)


class TestCriticalPoint:
    """Tests for the CriticalPoint dataclass."""

    def test_defaults(self):
        p = CriticalPoint(name="x", description="y")
        assert p.status is PointStatus.PENDING
        assert p.evidence_type is EvidenceType.CUSTOM
        assert p.evidence_value is None
        assert p.evidence_path is None
        assert p.note is None
        assert p.checked_at is None

    def test_mark_sets_status_and_timestamp(self):
        p = CriticalPoint(name="x", description="y")
        p.mark(PointStatus.PASSED, "looks good")
        assert p.status is PointStatus.PASSED
        assert p.note == "looks good"
        assert p.checked_at is not None
        # Timestamp should be parseable ISO.
        from datetime import datetime

        datetime.fromisoformat(p.checked_at)

    def test_to_from_dict_round_trip(self):
        p = CriticalPoint(
            name="login",
            description="user logged in",
            evidence_type=EvidenceType.SELECTOR,
            evidence_value=".user-info",
        )
        p.mark(PointStatus.PASSED, "ok")
        data = p.to_dict()
        restored = CriticalPoint.from_dict(data)
        assert restored.name == p.name
        assert restored.description == p.description
        assert restored.evidence_type is EvidenceType.SELECTOR
        assert restored.evidence_value == ".user-info"
        assert restored.status is PointStatus.PASSED
        assert restored.note == "ok"
        assert restored.checked_at == p.checked_at


class TestPlan:
    """Tests for the Plan container."""

    def test_add_and_get(self):
        plan = Plan(name="t")
        p = plan.add("cp1", "first", EvidenceType.SELECTOR, ".ok")
        assert p.name == "cp1"
        assert plan.get("cp1") is p
        assert plan.get("missing") is None

    def test_duplicate_name_raises(self):
        plan = Plan(name="t")
        plan.add("dup", "x")
        with pytest.raises(ValueError, match="Duplicate"):
            plan.add("dup", "y")

    def test_check_unknown_name_is_noop(self):
        plan = Plan(name="t")
        plan.check("nope", PointStatus.PASSED)  # no raise
        assert plan.passed == 0

    def test_finalise_locks_plan(self):
        plan = Plan(name="t")
        plan.add("cp1", "x")
        plan.finalise()
        with pytest.raises(RuntimeError, match="finalised"):
            plan.add("cp2", "y")

    def test_stats(self):
        plan = Plan(name="t")
        plan.add("a", "x")
        plan.add("b", "y")
        plan.add("c", "z")
        plan.check("a", PointStatus.PASSED)
        plan.check("b", PointStatus.FAILED)
        assert plan.total == 3
        assert plan.passed == 1
        assert plan.failed == 1
        assert plan.pending == 1
        assert not plan.is_fully_verified
        plan.check("c", PointStatus.SKIPPED)
        assert plan.is_fully_verified

    def test_save_load_round_trip(self, tmp_path):
        plan = Plan(name="roundtrip")
        plan.add("a", "alpha", EvidenceType.TEXT_PRESENT, "hello")
        plan.add("b", "beta", EvidenceType.SELECTOR, ".x")
        plan.check("a", PointStatus.PASSED, "found")

        md_path, json_path = plan.save(tmp_path)
        assert md_path.exists()
        assert json_path.exists()

        loaded = Plan.load(tmp_path)
        assert loaded is not None
        assert loaded.name == "roundtrip"
        assert loaded.total == 2
        assert loaded.passed == 1
        assert loaded.get("a").note == "found"

    def test_load_missing_returns_none(self, tmp_path):
        assert Plan.load(tmp_path) is None

    def test_to_markdown_contains_checklist(self):
        plan = Plan(name="md")
        plan.add("login", "logged in")
        plan.add("campus", "on right campus", EvidenceType.TEXT_PRESENT, "Yuehai")
        plan.check("login", PointStatus.PASSED)
        md = plan.to_markdown()
        assert "# Plan: md" in md
        assert "[x] **login**" in md
        assert "[ ] **campus**" in md
        assert "evidence: text = Yuehai" in md
        assert "Pending: 1" in md

    def test_to_markdown_empty(self):
        plan = Plan(name="empty")
        md = plan.to_markdown()
        assert "No critical points declared" in md


class TestDefaultBookingPlan:
    """Tests for the default critical-points helper."""

    def test_contains_four_standard_points(self):
        plan = default_booking_plan("Yuehai", "tennis", "19:00-20:00", 0)
        names = {p.name for p in plan.points}
        assert names == {"login_succeeded", "campus_selected", "slot_selected", "confirm_clean"}

    def test_uses_campus_and_slot_in_evidence(self):
        plan = default_booking_plan("Lihu", "badminton", "20:00-21:00", 1)
        campus = plan.get("campus_selected")
        assert campus.evidence_value == "Lihu"
        slot = plan.get("slot_selected")
        assert slot.evidence_value == "20:00-21:00"


class TestPlanJsonResilience:
    """Regression: malformed JSON should not crash load()."""

    def test_load_corrupt_json_returns_none(self, tmp_path):
        (tmp_path / "critical_points.json").write_text("not json", encoding="utf-8")
        assert Plan.load(tmp_path) is None
