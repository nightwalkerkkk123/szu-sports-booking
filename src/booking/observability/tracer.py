"""Distributed tracing for booking system."""
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def generate_trace_id() -> str:
    """Generate a unique trace ID.

    Returns:
        A unique string identifier for the trace.
    """
    return str(uuid.uuid4())


@dataclass
class TraceContext:
    """Context for a single trace/span."""

    trace_id: str
    start_time: float = field(default_factory=time.time)
    tags: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def tag(self, key: str, value: Any) -> None:
        """Add a tag to the trace."""
        self.tags[key] = value

    def event(self, name: str, **kwargs: Any) -> None:
        """Add an event to the trace."""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            **kwargs,
        })

    @property
    def duration(self) -> int:
        """Get elapsed time in milliseconds."""
        return int((time.time() - self.start_time) * 1000)


class Tracer:
    """Tracer for creating and managing trace contexts."""

    def __init__(self):
        """Initialize tracer."""
        self._context: TraceContext | None = None

    def start(self) -> TraceContext:
        """Start a new trace.

        Returns:
            A new TraceContext with a unique trace_id.
        """
        trace_id = generate_trace_id()
        self._context = TraceContext(trace_id)
        return self._context

    def set_context(self, context: TraceContext) -> None:
        """Set the active trace context."""
        self._context = context

    def get_context(self) -> TraceContext | None:
        """Get the active trace context."""
        return self._context

    def clear_context(self) -> None:
        """Clear the active trace context."""
        self._context = None


# Global tracer instance
_tracer = Tracer()


def get_tracer() -> Tracer:
    """Get the global tracer instance.

    Returns:
        The global Tracer instance.
    """
    return _tracer


def query_trace(trace_id: str, log_dir: str = "logs/booking") -> dict[str, Any] | None:
    """Query a trace from log files by trace_id.

    Args:
        trace_id: The trace ID to search for
        log_dir: Directory containing log files

    Returns:
        A dictionary with trace info, or None if not found
    """
    log_path = Path(log_dir) / "booking.json.log"
    if not log_path.exists():
        return None

    entries = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("trace_id") == trace_id:
                    entries.append(data)
            except json.JSONDecodeError:
                continue

    if not entries:
        return None

    return {
        "trace_id": trace_id,
        "entries": entries,
        "count": len(entries),
    }


def print_trace(trace_id: str, log_dir: str = "logs/booking") -> None:
    """Print a trace in human-readable format.

    Args:
        trace_id: The trace ID to display
        log_dir: Directory containing log files
    """
    trace = query_trace(trace_id, log_dir)

    if not trace:
        print(f"Trace {trace_id} not found")
        return

    print("=" * 60)
    print(f"Trace: {trace_id}")
    print("=" * 60)
    print(f"Total entries: {trace['count']}")
    print()

    for entry in trace["entries"]:
        timestamp = entry.get("timestamp", "")
        level = entry.get("level", "")
        message = entry.get("message", "")

        print(f"[{level}] {message}")

        # Print extra fields
        extras = {k: v for k, v in entry.items()
                  if k not in ("timestamp", "level", "logger", "message", "trace_id")}
        if extras:
            for k, v in extras.items():
                print(f"         {k}: {v}")
        print()