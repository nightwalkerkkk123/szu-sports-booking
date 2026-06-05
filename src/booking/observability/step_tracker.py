"""Step tracking for booking execution."""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Step:
    """A single execution step."""

    name: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "pending"  # pending, running, success, failed, skipped
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "success", error: str | None = None) -> None:
        """Mark step as finished."""
        self.end_time = time.time()
        self.status = status
        self.error = error

    @property
    def duration_ms(self) -> int:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return int((time.time() - self.start_time) * 1000)
        return int((self.end_time - self.start_time) * 1000)


class StepTracker:
    """Track execution steps with timing and status."""

    def __init__(self, trace_id: str):
        """Initialize step tracker.

        Args:
            trace_id: Unique trace ID for this execution
        """
        self.trace_id = trace_id
        self.steps: list[Step] = []
        self._current_step: Step | None = None

    def start_step(self, name: str, details: dict[str, Any] | None = None) -> None:
        """Start a new step.

        Args:
            name: Step name
            details: Additional step details
        """
        step = Step(name=name, details=details or {})
        self.steps.append(step)
        self._current_step = step

    def finish_step(self, status: str = "success", error: str | None = None) -> None:
        """Finish the current step.

        Args:
            status: Step status (success, failed, skipped)
            error: Error message if failed
        """
        if self._current_step:
            self._current_step.finish(status=status, error=error)
            self._current_step = None

    def step_success(self) -> None:
        """Mark current step as successful."""
        self.finish_step(status="success")

    def step_failed(self, error: str) -> None:
        """Mark current step as failed.

        Args:
            error: Error message
        """
        self.finish_step(status="failed", error=error)

    def step_skipped(self) -> None:
        """Mark current step as skipped."""
        self.finish_step(status="skipped")

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary.

        Returns:
            Dictionary with execution summary
        """
        total_duration = sum(s.duration_ms for s in self.steps)
        success_count = sum(1 for s in self.steps if s.status == "success")
        failed_count = sum(1 for s in self.steps if s.status == "failed")
        skipped_count = sum(1 for s in self.steps if s.status == "skipped")

        return {
            "trace_id": self.trace_id,
            "total_steps": len(self.steps),
            "total_duration_ms": total_duration,
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "success_rate": success_count / len(self.steps) if self.steps else 0,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "details": s.details,
                }
                for s in self.steps
            ],
        }

    def print_summary(self) -> None:
        """Print human-readable summary."""
        summary = self.get_summary()

        print()
        print("=" * 60)
        print("执行报告")
        print("=" * 60)
        print(f"Trace ID: {self.trace_id}")
        print(f"总步骤: {summary['total_steps']}")
        print(f"总耗时: {summary['total_duration_ms']}ms")
        print(f"成功率: {summary['success_rate'] * 100:.1f}%")
        print()

        print("步骤详情:")
        print("-" * 60)
        for i, step in enumerate(summary["steps"], 1):
            status_icon = {
                "success": "[OK]",
                "failed": "[X]",
                "skipped": "-",
                "pending": "○",
                "running": "▶",
            }.get(step["status"], "?")

            duration = step["duration_ms"]
            error = f" | 错误: {step['error']}" if step["error"] else ""

            print(f"  {i}. [{status_icon}] {step['name']} ({duration}ms){error}")

            if step["details"]:
                for k, v in step["details"].items():
                    print(f"      {k}: {v}")

        print("-" * 60)
        print()

    def save_report(self, output_dir: str = "logs/booking") -> str:
        """Save report to JSON file.

        Args:
            output_dir: Output directory

        Returns:
            Path to saved report
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_file = output_path / f"report_{self.trace_id[:8]}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.get_summary(), f, ensure_ascii=False, indent=2)

        return str(report_file)


def create_tracker() -> StepTracker:
    """Create a new step tracker with generated trace ID.

    Returns:
        New StepTracker instance
    """
    from booking.observability.tracer import generate_trace_id

    return StepTracker(trace_id=generate_trace_id())
