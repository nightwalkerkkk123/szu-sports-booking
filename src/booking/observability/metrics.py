"""Metrics collection for booking system."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Counter:
    """Counter metric that only goes up."""

    name: str
    value: int = 0

    def increment(self, amount: int = 1) -> None:
        """Increment counter by amount."""
        self.value += amount

    def decrement(self, amount: int = 1) -> None:
        """Decrement counter by amount."""
        self.value -= amount


@dataclass
class Gauge:
    """Gauge metric that can go up or down."""

    name: str
    value: float = 0.0

    def set(self, value: float) -> None:
        """Set gauge to a specific value."""
        self.value = value

    def increment(self, amount: float = 1.0) -> None:
        """Increment gauge by amount."""
        self.value += amount

    def decrement(self, amount: float = 1.0) -> None:
        """Decrement gauge by amount."""
        self.value -= amount


@dataclass
class Histogram:
    """Histogram metric for recording distributions."""

    name: str
    values: list[float] = field(default_factory=list)

    def record(self, value: float) -> None:
        """Record a value."""
        self.values.append(value)

    @property
    def count(self) -> int:
        """Number of recorded values."""
        return len(self.values)

    @property
    def mean(self) -> float:
        """Mean of recorded values."""
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    @property
    def sum(self) -> float:
        """Sum of recorded values."""
        return sum(self.values)


class MetricsCollector:
    """Collector for all metric types."""

    def __init__(self):
        """Initialize metrics collector."""
        self.counters: dict[str, Counter] = {}
        self.gauges: dict[str, Gauge] = {}
        self.histograms: dict[str, Histogram] = {}

    def counter(self, name: str) -> Counter:
        """Get or create a counter."""
        if name not in self.counters:
            self.counters[name] = Counter(name)
        return self.counters[name]

    def gauge(self, name: str) -> Gauge:
        """Get or create a gauge."""
        if name not in self.gauges:
            self.gauges[name] = Gauge(name)
        return self.gauges[name]

    def histogram(self, name: str) -> Histogram:
        """Get or create a histogram."""
        if name not in self.histograms:
            self.histograms[name] = Histogram(name)
        return self.histograms[name]

    def snapshot(self) -> dict[str, Any]:
        """Get a snapshot of all metrics."""
        return {
            "counters": {name: c.value for name, c in self.counters.items()},
            "gauges": {name: g.value for name, g in self.gauges.items()},
            "histograms": {
                name: {"count": h.count, "mean": h.mean, "sum": h.sum}
                for name, h in self.histograms.items()
            },
        }


# Global metrics collector
_collector = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector.

    Returns:
        The global MetricsCollector instance.
    """
    return _collector