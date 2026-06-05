"""Local data storage using SQLite."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def _register_datetime_adapter() -> None:
    """Register adapter for datetime to avoid deprecation warning."""
    def adapt_datetime(dt: datetime) -> str:
        return dt.isoformat()

    sqlite3.register_adapter(datetime, adapt_datetime)


# Register adapter at module load time
_register_datetime_adapter()


@dataclass
class BookingRecord:
    """Record of a booking attempt."""

    id: int | None
    trace_id: str
    account: str
    campus: str
    sport: str
    time_slot: str
    status: str  # "success" or "failed"
    error_code: str | None
    duration_ms: int
    timestamp: datetime


class Database:
    """SQLite-based data store for booking records."""

    def __init__(self, db_path: str = "data/booking.db"):
        """Initialize database connection and create schema."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS booking_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    account TEXT NOT NULL,
                    campus TEXT,
                    sport TEXT,
                    time_slot TEXT,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    duration_ms INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trace_id ON booking_records(trace_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_account ON booking_records(account)
            """)

    def insert_record(self, record: BookingRecord) -> None:
        """Insert a booking record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO booking_records
                (trace_id, account, campus, sport, time_slot, status, error_code, duration_ms, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.trace_id,
                record.account,
                record.campus,
                record.sport,
                record.time_slot,
                record.status,
                record.error_code,
                record.duration_ms,
                record.timestamp,
            ))

    def get_records_by_account(self, account: str, limit: int = 100) -> list[BookingRecord]:
        """Get booking records for a specific account."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, trace_id, account, campus, sport, time_slot, status, error_code, duration_ms, timestamp
                FROM booking_records
                WHERE account = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (account, limit)).fetchall()
            return [BookingRecord(*row) for row in rows]

    def get_recent_records(self, limit: int = 50) -> list[BookingRecord]:
        """Get most recent booking records."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, trace_id, account, campus, sport, time_slot, status, error_code, duration_ms, timestamp
                FROM booking_records
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [BookingRecord(*row) for row in rows]

    def get_success_rate(self, days: int = 7) -> float:
        """Calculate success rate over the specified number of days."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("""
                SELECT COUNT(*) FROM booking_records
                WHERE timestamp > datetime('now', ?)
            """, (f"-{days} days",)).fetchone()[0]

            if total == 0:
                return 0.0

            success = conn.execute("""
                SELECT COUNT(*) FROM booking_records
                WHERE timestamp > datetime('now', ?) AND status = 'success'
            """, (f"-{days} days",)).fetchone()[0]

            return success / total
