"""Tests for booking.database module - Local data storage."""
import os
import sqlite3
import pytest
from datetime import datetime, timedelta
from pathlib import Path


class TestDatabaseInit:
    """Test Database initialization."""

    def test_database_creates_tables(self, tmp_path):
        """Database creates required tables on init."""
        from booking.database import Database

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='booking_records'"
            )
            assert cursor.fetchone() is not None

    def test_database_creates_indexes(self, tmp_path):
        """Database creates required indexes."""
        from booking.database import Database

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_trace_id'"
            )
            assert cursor.fetchone() is not None

            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_account'"
            )
            assert cursor.fetchone() is not None


class TestBookingRecord:
    """Test BookingRecord dataclass."""

    def test_booking_record_has_required_fields(self):
        """BookingRecord contains all required fields."""
        from booking.database import BookingRecord

        record = BookingRecord(
            id=None,
            trace_id="trace-123",
            account="user1",
            campus="粤海校区",
            sport="网球",
            time_slot="19:00-20:00",
            status="success",
            error_code=None,
            duration_ms=1500,
            timestamp=datetime.now()
        )

        assert record.trace_id == "trace-123"
        assert record.account == "user1"
        assert record.status == "success"
        assert record.duration_ms == 1500


class TestInsertRecord:
    """Test inserting records."""

    def test_insert_record_saves_to_db(self, tmp_path):
        """insert_record saves record to database."""
        from booking.database import Database, BookingRecord

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        record = BookingRecord(
            id=None,
            trace_id="trace-456",
            account="user2",
            campus="粤海校区",
            sport="羽毛球",
            time_slot="20:00-21:00",
            status="success",
            error_code=None,
            duration_ms=2000,
            timestamp=datetime.now()
        )

        db.insert_record(record)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT * FROM booking_records WHERE trace_id=?", ("trace-456",))
            row = cursor.fetchone()
            assert row is not None
            assert row[2] == "user2"  # account column


class TestGetRecordsByAccount:
    """Test retrieving records by account."""

    def test_get_records_by_account_returns_list(self, tmp_path):
        """get_records_by_account returns list of records."""
        from booking.database import Database, BookingRecord

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        # Insert some records
        for i in range(3):
            record = BookingRecord(
                id=None,
                trace_id=f"trace-{i}",
                account="user3",
                campus="粤海校区",
                sport="网球",
                time_slot="19:00-20:00",
                status="success" if i % 2 == 0 else "failed",
                error_code=None,
                duration_ms=1000,
                timestamp=datetime.now()
            )
            db.insert_record(record)

        records = db.get_records_by_account("user3")

        assert len(records) == 3


class TestGetSuccessRate:
    """Test success rate calculation."""

    def test_get_success_rate_returns_zero_when_no_records(self, tmp_path):
        """get_success_rate returns 0.0 when no records exist."""
        from booking.database import Database

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        rate = db.get_success_rate()
        assert rate == 0.0

    def test_get_success_rate_calculates_correctly(self, tmp_path):
        """get_success_rate calculates success/total correctly."""
        from booking.database import Database, BookingRecord

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        # Insert 2 success, 1 failed
        for status in ["success", "success", "failed"]:
            record = BookingRecord(
                id=None,
                trace_id=f"trace-{status}",
                account="user4",
                campus="粤海校区",
                sport="网球",
                time_slot="19:00-20:00",
                status=status,
                error_code=None,
                duration_ms=1000,
                timestamp=datetime.now()
            )
            db.insert_record(record)

        rate = db.get_success_rate()
        assert rate == pytest.approx(2/3)


class TestGetRecentRecords:
    """Test retrieving recent records."""

    def test_get_recent_records_returns_limited_results(self, tmp_path):
        """get_recent_records respects limit parameter."""
        from booking.database import Database, BookingRecord

        db_path = tmp_path / "test.db"
        db = Database(db_path)

        # Insert 10 records
        for i in range(10):
            record = BookingRecord(
                id=None,
                trace_id=f"trace-{i}",
                account="user5",
                campus="粤海校区",
                sport="网球",
                time_slot="19:00-20:00",
                status="success",
                error_code=None,
                duration_ms=1000,
                timestamp=datetime.now()
            )
            db.insert_record(record)

        recent = db.get_recent_records(limit=5)
        assert len(recent) == 5