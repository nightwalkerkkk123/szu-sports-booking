"""Tests for booking.observability.tracer module - Distributed tracing."""


class TestTraceIdGeneration:
    """Test trace_id generation."""

    def test_generate_trace_id_returns_string(self):
        """generate_trace_id() returns a string."""
        from booking.observability.tracer import generate_trace_id

        trace_id = generate_trace_id()
        assert isinstance(trace_id, str)

    def test_generate_trace_id_is_unique(self):
        """generate_trace_id() returns unique values."""
        from booking.observability.tracer import generate_trace_id

        ids = [generate_trace_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestTraceContext:
    """Test trace context management."""

    def test_trace_context_has_trace_id(self):
        """TraceContext has trace_id."""
        from booking.observability.tracer import TraceContext, generate_trace_id

        trace_id = generate_trace_id()
        ctx = TraceContext(trace_id)
        assert ctx.trace_id == trace_id

    def test_trace_context_has_start_time(self):
        """TraceContext has start_time."""
        import time

        from booking.observability.tracer import TraceContext, generate_trace_id

        start = time.time()
        ctx = TraceContext(generate_trace_id())
        assert ctx.start_time >= start

    def test_trace_context_can_add_tag(self):
        """TraceContext can add tags."""
        from booking.observability.tracer import TraceContext, generate_trace_id

        ctx = TraceContext(generate_trace_id())
        ctx.tag("user", "test_user")
        assert ctx.tags["user"] == "test_user"

    def test_trace_context_can_add_event(self):
        """TraceContext can add events."""
        from booking.observability.tracer import TraceContext, generate_trace_id

        ctx = TraceContext(generate_trace_id())
        ctx.event("login_attempt")
        assert len(ctx.events) == 1


class TestTraceContextDuration:
    """Test duration calculation."""

    def test_duration_is_elapsed_time(self):
        """duration property returns elapsed time in ms."""
        import time

        from booking.observability.tracer import TraceContext, generate_trace_id

        ctx = TraceContext(generate_trace_id())
        time.sleep(0.01)  # 10ms
        duration = ctx.duration
        assert duration >= 10  # At least 10ms
        assert duration < 1000  # But less than 1 second


class TestTracer:
    """Test Tracer class."""

    def test_tracer_creates_context(self):
        """Tracer.start() creates a TraceContext."""
        from booking.observability.tracer import Tracer

        tracer = Tracer()
        ctx = tracer.start()
        assert ctx is not None
        assert ctx.trace_id is not None

    def test_tracer_creates_unique_trace_ids(self):
        """Tracer.start() creates unique trace_ids."""
        from booking.observability.tracer import Tracer

        tracer = Tracer()
        ctx1 = tracer.start()
        ctx2 = tracer.start()
        assert ctx1.trace_id != ctx2.trace_id

    def test_tracer_can_set_active_context(self):
        """Tracer can set active context."""
        from booking.observability.tracer import TraceContext, Tracer, generate_trace_id

        tracer = Tracer()
        ctx = TraceContext(generate_trace_id())
        tracer.set_context(ctx)
        assert tracer.get_context() == ctx

    def test_tracer_clear_context(self):
        """Tracer.clear_context() clears active context."""
        from booking.observability.tracer import Tracer

        tracer = Tracer()
        tracer.start()
        tracer.clear_context()
        assert tracer.get_context() is None
