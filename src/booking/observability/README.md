# observability

可观测性模块：日志、追踪、指标、报告。

## 架构

```
observability/
├── __init__.py
├── logger.py           # Logger（结构化日志、JSON/文本双格式）
├── tracer.py           # Tracer（trace_id 追踪、日志关联）
├── metrics.py          # MetricsCollector（Counter/Gauge/Histogram）
├── reporter.py         # Reporter（预约报告摘要）
├── run_manager.py      # RunManager（Run 隔离目录 + SQLite 索引）
├── report_generator.py # HTML 报告生成（含自动打开浏览器）
├── step_tracker.py     # StepTracker（步骤追踪 + 摘要报告）
└── trace_viewer.py     # Trace HTML 查看器
```

## 使用示例

### Logger

```python
from booking.observability import Logger, get_logger

logger = Logger("booking")
logger.info("预约开始", trace_id="abc-123")
```

### Tracer

```python
from booking.observability import Tracer, get_tracer

tracer = get_tracer()
ctx = tracer.start()
ctx.tag("user", "test_user")
ctx.event("login_attempt")
```

### Metrics

```python
from booking.observability import get_metrics

metrics = get_metrics()
metrics.counter("booking_attempts").increment()
metrics.histogram("booking_duration").record(1500)
```

### Reporter

```python
from booking.observability import Reporter

reporter = Reporter()
summary = reporter.get_summary(days=7)
print(f"成功率: {summary['success_rate']}")
```

## 全局实例

每个模块都提供 `get_*()` 函数获取全局实例：
- `get_logger(name)`
- `get_tracer()`
- `get_metrics()`

## 日志格式

日志支持 JSON 格式输出到文件，结构化字段包括：
- `timestamp`
- `level`
- `logger`
- `message`
- `trace_id`（注入）
- 其他自定义字段

## 注意事项

- **不得输出敏感信息**（密码、Cookie、Token）
- 日志文件位于 `logs/` 目录
- trace_id 用于关联一次完整的预约流程