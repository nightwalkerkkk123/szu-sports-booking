"""Tests for booking.observability.metrics module - Metrics collection."""


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_collector_has_counters(self):
        """Collector has counters dict."""
        from booking.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        assert hasattr(collector, "counters")
        assert isinstance(collector.counters, dict)

    def test_collector_has_gauges(self):
        """Collector has gauges dict."""
        from booking.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        assert hasattr(collector, "gauges")
        assert isinstance(collector.gauges, dict)

    def test_collector_has_histograms(self):
        """Collector has histograms dict."""
        from booking.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        assert hasattr(collector, "histograms")
        assert isinstance(collector.histograms, dict)


class TestCounter:
    """Test counter metric."""

    def test_counter_starts_at_zero(self):
        """Counter starts at 0."""
        from booking.observability.metrics import Counter

        counter = Counter("test_counter")
        assert counter.value == 0

    def test_counter_increments(self):
        """Counter increments by 1 by default."""
        from booking.observability.metrics import Counter

        counter = Counter("test_counter")
        counter.increment()
        assert counter.value == 1

    def test_counter_increments_by_amount(self):
        """Counter increments by specified amount."""
        from booking.observability.metrics import Counter

        counter = Counter("test_counter")
        counter.increment(5)
        assert counter.value == 5

    def test_counter_decrements(self):
        """Counter decrements."""
        from booking.observability.metrics import Counter

        counter = Counter("test_counter", value=10)
        counter.decrement(3)
        assert counter.value == 7


class TestGauge:
    """Test gauge metric."""

    def test_gauge_starts_at_zero(self):
        """Gauge starts at 0."""
        from booking.observability.metrics import Gauge

        gauge = Gauge("test_gauge")
        assert gauge.value == 0

    def test_gauge_can_set_value(self):
        """Gauge can be set to a value."""
        from booking.observability.metrics import Gauge

        gauge = Gauge("test_gauge")
        gauge.set(42)
        assert gauge.value == 42


class TestHistogram:
    """Test histogram metric."""

    def test_histogram_records_value(self):
        """Histogram records values."""
        from booking.observability.metrics import Histogram

        hist = Histogram("test_histogram")
        hist.record(1.5)
        assert len(hist.values) == 1

    def test_histogram_calculates_mean(self):
        """Histogram calculates mean."""
        from booking.observability.metrics import Histogram

        hist = Histogram("test_histogram")
        hist.record(1.0)
        hist.record(3.0)
        assert hist.mean == 2.0


class TestMetricsSnapshot:
    """Test metrics snapshot."""

    def test_snapshot_contains_all_metrics(self):
        """Snapshot contains counters, gauges, histograms."""
        from booking.observability.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.counter("requests").increment()
        collector.gauge("memory").set(100)

        snapshot = collector.snapshot()
        assert "counters" in snapshot
        assert "gauges" in snapshot
        assert "histograms" in snapshot
