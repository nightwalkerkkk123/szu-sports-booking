"""Observability modules."""
from booking.observability.logger import Logger, get_logger
from booking.observability.tracer import (
    Tracer,
    TraceContext,
    generate_trace_id,
    get_tracer,
)
from booking.observability.metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    get_metrics,
)
from booking.observability.reporter import Reporter
from booking.observability.run_manager import RunManager, RunRecord, get_run_manager
from booking.observability.report_generator import generate_html_report, generate_and_open_report

__all__ = [
    # Logger
    "Logger",
    "get_logger",
    # Tracer
    "Tracer",
    "TraceContext",
    "generate_trace_id",
    "get_tracer",
    # Metrics
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "get_metrics",
    # Reporter
    "Reporter",
    # Run Manager (new)
    "RunManager",
    "RunRecord",
    "get_run_manager",
    # Report Generator (new)
    "generate_html_report",
    "generate_and_open_report",
]
