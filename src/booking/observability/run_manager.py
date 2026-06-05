"""Run manager - manages run lifecycle and isolation."""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from booking.observability.plan import Plan


@dataclass
class RunRecord:
    """Record of a single run."""

    trace_id: str
    run_dir: str
    start_time: str
    end_time: str | None = None
    status: str = "running"  # running, success, failed, cancelled
    campus: str = ""
    sport: str = ""
    dry_run: bool = False
    error_message: str | None = None


class RunManager:
    """Manages run lifecycle with isolated directories."""

    def __init__(self, base_dir: str = "logs/booking/runs"):
        """Initialize run manager.

        Args:
            base_dir: Base directory for all runs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "runs.db"
        self._init_db()
        self._current_run: RunRecord | None = None
        self._logger = logging.getLogger("booking")

    def _init_db(self) -> None:
        """Initialize SQLite database for run index."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    trace_id TEXT PRIMARY KEY,
                    run_dir TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    campus TEXT,
                    sport TEXT,
                    dry_run INTEGER,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_start_time ON runs(start_time)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON runs(status)
            """)

    def start_run(
        self, campus: str = "", sport: str = "", dry_run: bool = False, trace_id: str | None = None
    ) -> RunRecord:
        """Start a new run with isolated directory.

        Args:
            campus: Campus name
            sport: Sport name
            dry_run: Whether this is a dry run
            trace_id: Optional trace ID (generated if not provided)

        Returns:
            RunRecord with run information
        """
        if trace_id is None:
            trace_id = str(uuid.uuid4())

        # Create run directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir_name = f"{timestamp}_{trace_id[:8]}"
        run_dir = self.base_dir / run_dir_name
        run_dir.mkdir(parents=True, exist_ok=True)

        # Standard Webwright-style subdirs: screenshots live alongside plan artifacts
        (run_dir / "screenshots").mkdir(parents=True, exist_ok=True)

        # Create run record
        start_time = datetime.now().isoformat()
        record = RunRecord(
            trace_id=trace_id,
            run_dir=str(run_dir),
            start_time=start_time,
            campus=campus,
            sport=sport,
            dry_run=dry_run,
        )

        # Save to SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (trace_id, run_dir, start_time, status, campus, sport, dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.trace_id,
                    record.run_dir,
                    record.start_time,
                    record.status,
                    record.campus,
                    record.sport,
                    1 if record.dry_run else 0,
                ),
            )

        self._current_run = record
        return record

    def end_run(self, success: bool = True, error_message: str | None = None) -> None:
        """End the current run.

        Args:
            success: Whether the run succeeded
            error_message: Error message if failed
        """
        if self._current_run is None:
            return

        end_time = datetime.now().isoformat()
        status = "success" if success else "failed"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE runs SET end_time = ?, status = ?, error_message = ?
                WHERE trace_id = ?
            """,
                (end_time, status, error_message, self._current_run.trace_id),
            )

        self._current_run.end_time = end_time
        self._current_run.status = status
        self._current_run.error_message = error_message
        self._current_run = None

    @property
    def current_run(self) -> RunRecord | None:
        """Get current run record."""
        return self._current_run

    def log(self, message: str, level: str = "INFO", **kwargs: Any) -> None:
        """Write log entry to current run's log file.

        Args:
            message: Log message
            level: Log level (INFO, WARNING, ERROR)
            **kwargs: Additional fields to log
        """
        if self._current_run is None:
            return

        log_file = Path(self._current_run.run_dir) / "run.json.log"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "trace_id": self._current_run.trace_id,
            "message": message,
            **kwargs,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_step(
        self,
        step_name: str,
        status: str,
        duration_ms: int = 0,
        error: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log step to steps.json.

        Args:
            step_name: Name of the step
            status: Status (started, success, failed, skipped)
            duration_ms: Duration in milliseconds
            error: Error message if failed
            **kwargs: Additional step details
        """
        if self._current_run is None:
            return

        steps_file = Path(self._current_run.run_dir) / "steps.json"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": self._current_run.trace_id,
            "step": step_name,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
            **kwargs,
        }

        # Append to steps file
        steps = []
        if steps_file.exists():
            with open(steps_file, encoding="utf-8") as f:
                steps = json.load(f)
        steps.append(entry)
        with open(steps_file, "w", encoding="utf-8") as f:
            json.dump(steps, f, ensure_ascii=False, indent=2)

    def save_summary(self, summary: dict[str, Any]) -> None:
        """Save run summary to summary.json.

        Args:
            summary: Summary data
        """
        if self._current_run is None:
            return

        summary_file = Path(self._current_run.run_dir) / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    def query_runs(self, status: str | None = None, limit: int = 10, offset: int = 0) -> list[dict]:
        """Query runs from database.

        Args:
            status: Filter by status (success, failed, running)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of run records
        """
        with sqlite3.connect(self.db_path) as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT trace_id, run_dir, start_time, end_time, status,
                           campus, sport, dry_run, error_message
                    FROM runs
                    WHERE status = ?
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                """,
                    (status, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT trace_id, run_dir, start_time, end_time, status,
                           campus, sport, dry_run, error_message
                    FROM runs
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                """,
                    (limit, offset),
                ).fetchall()

            return [
                {
                    "trace_id": row[0],
                    "run_dir": row[1],
                    "start_time": row[2],
                    "end_time": row[3],
                    "status": row[4],
                    "campus": row[5],
                    "sport": row[6],
                    "dry_run": bool(row[7]),
                    "error_message": row[8],
                }
                for row in rows
            ]

    def get_run_by_trace(self, trace_id: str) -> dict | None:
        """Get run by trace_id.

        Args:
            trace_id: Trace ID to search for

        Returns:
            Run record or None
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT trace_id, run_dir, start_time, end_time, status,
                       campus, sport, dry_run, error_message
                FROM runs
                WHERE trace_id = ?
            """,
                (trace_id,),
            ).fetchone()

            if row is None:
                return None

            return {
                "trace_id": row[0],
                "run_dir": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "status": row[4],
                "campus": row[5],
                "sport": row[6],
                "dry_run": bool(row[7]),
                "error_message": row[8],
            }

    def get_run_logs(self, trace_id: str) -> list[dict]:
        """Get all logs for a run.

        Args:
            trace_id: Trace ID

        Returns:
            List of log entries
        """
        run = self.get_run_by_trace(trace_id)
        if run is None:
            return []

        log_file = Path(run["run_dir"]) / "run.json.log"
        if not log_file.exists():
            return []

        logs = []
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    logs.append(json.loads(line))
        return logs

    def get_run_steps(self, trace_id: str) -> list[dict]:
        """Get all steps for a run.

        Args:
            trace_id: Trace ID

        Returns:
            List of step entries
        """
        run = self.get_run_by_trace(trace_id)
        if run is None:
            return []

        steps_file = Path(run["run_dir"]) / "steps.json"
        if not steps_file.exists():
            return []

        with open(steps_file, encoding="utf-8") as f:
            return json.load(f)

    # ---- plan / screenshot integration -----------------------------------

    def get_screenshots_dir(self) -> Path | None:
        """Return the screenshots directory for the active run, or None."""
        if self._current_run is None:
            return None
        return Path(self._current_run.run_dir) / "screenshots"

    def save_plan(self, plan: Plan) -> tuple[Path, Path] | None:
        """Persist a :class:Plan into the active run directory.

        Writes both `plan.md` and `critical_points.json`. Returns
        `(md_path, json_path)` on success, `None` when no run is active.
        The import is local to avoid a circular dependency with `plan.py`.
        """
        if self._current_run is None:
            return None
        return plan.save(self._current_run.run_dir)

    def load_plan(self, trace_id: str | None = None) -> Plan | None:
        """Load a plan from a run directory.

        Args:
            trace_id: Trace ID to look up. If `None`, uses the active run.
        """
        if trace_id is None:
            if self._current_run is None:
                return None
            run_dir = self._current_run.run_dir
        else:
            record = self.get_run_by_trace(trace_id)
            if record is None:
                return None
            run_dir = record["run_dir"]
        from booking.observability.plan import Plan

        return Plan.load(run_dir)


# Global run manager instance
_run_manager: RunManager | None = None


def get_run_manager() -> RunManager:
    """Get the global run manager instance.

    Returns:
        Global RunManager
    """
    global _run_manager
    if _run_manager is None:
        _run_manager = RunManager()
    return _run_manager
