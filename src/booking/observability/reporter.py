"""Reporter for generating booking reports."""
from datetime import datetime
from typing import Any

from booking.database import BookingRecord, Database


class Reporter:
    """Generate booking reports from stored data."""

    def __init__(self, db_path: str = "data/booking.db"):
        """Initialize reporter with database."""
        self.db = Database(db_path)

    def record_booking(
        self,
        trace_id: str,
        account: str,
        campus: str,
        sport: str,
        time_slot: str,
        status: str,
        error_code: str | None = None,
        duration_ms: int = 0,
    ) -> None:
        """Record a booking attempt.

        Args:
            trace_id: Unique trace ID for this booking
            account: Account username
            campus: Campus name
            sport: Sport type
            time_slot: Time slot string
            status: "success" or "failed"
            error_code: Error code if failed
            duration_ms: Duration in milliseconds
        """
        record = BookingRecord(
            id=None,
            trace_id=trace_id,
            account=account,
            campus=campus,
            sport=sport,
            time_slot=time_slot,
            status=status,
            error_code=error_code,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
        )
        self.db.insert_record(record)

    def print_summary(self, days: int = 7) -> None:
        """Print a summary report to console."""
        success_rate = self.db.get_success_rate(days)
        recent = self.db.get_recent_records(limit=10)

        print("=" * 50)
        print("预约报告")
        print("=" * 50)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{days}天成功率: {success_rate * 100:.1f}%")
        print(f"最近记录: {len(recent)} 条")

        if recent:
            print("\n最近记录:")
            for record in recent:
                status_icon = "✓" if record.status == "success" else "✗"
                print(f"  {status_icon} {record.account} {record.campus} {record.sport}")

    def get_summary(self, days: int = 7) -> dict[str, Any]:
        """Get summary data as a dictionary."""
        success_rate = self.db.get_success_rate(days)
        recent = self.db.get_recent_records(limit=50)

        success_count = sum(1 for r in recent if r.status == "success")
        failed_count = len(recent) - success_count

        def _format_timestamp(ts: datetime | str) -> str:
            """Format timestamp to ISO string."""
            if isinstance(ts, datetime):
                return ts.isoformat()
            return ts  # Already a string

        return {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "success_rate": success_rate,
            "total_records": len(recent),
            "success_count": success_count,
            "failed_count": failed_count,
            "recent_records": [
                {
                    "trace_id": r.trace_id,
                    "account": r.account,
                    "status": r.status,
                    "timestamp": _format_timestamp(r.timestamp),
                }
                for r in recent[:10]
            ],
        }