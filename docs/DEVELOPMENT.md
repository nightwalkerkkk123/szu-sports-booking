# 开发指南

## 环境要求

- Python 3.10+
- uv (包管理工具)

## 安装

```bash
# 安装依赖
make install

# 或手动安装
uv sync --dev
```

## 开发命令

```bash
# 代码检查
make lint

# 格式化代码
make format

# 运行测试
make test

# 运行单元测试
make test-unit

# 运行冒烟测试
make test-smoke

# 生成覆盖率报告
make cov

# 完整 CI 检查
make ci
```

## 测试

```bash
# 所有测试
pytest tests/

# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 冒烟测试
pytest tests/smoke/ -v

# 带覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 代码结构

```
src/booking/
├── client.py          # BookingClient 入口（含 StepTracker 集成）
├── pool.py            # BookingPool + AccountSession
├── account.py         # Account 状态管理（含失败计数、冷却）
├── config.py         # Config（YAML 加载/环境变量合并）
├── errors.py         # ErrorCode（14个错误码）
├── retry.py          # RetryPolicy（线性/指数退避）
├── database.py       # SQLite 数据存储
├── cli.py            # CLI（run/test-login/validate-config/smoke/report/trace/runs）
├── chain_builder.py  # Chain 链式选择器
├── step_builder.py   # StepBuilder 步骤构建（含重试）
├── browser/         # 浏览器抽象层
│   ├── lifecycle.py      # BrowserLifecycle 接口
│   ├── cloak_adapter.py  # CloakBrowser 实现
│   └── fake_browser.py   # FakeBrowser 测试用
├── selectors/        # 页面选择器
│   ├── slot_selector.py  # FlexibleSlotSelector（含可用性判断）
│   └── venue_selector.py # FlexibleVenueSelector
├── matchers/         # 匹配器（4个文件）
│   ├── text_matcher.py
│   ├── regex_matcher.py
│   ├── contains_matcher.py
│   └── composite_matcher.py
└── observability/    # 可观测性（8个模块）
    ├── logger.py          # Logger（结构化日志）
    ├── tracer.py          # Tracer（trace_id 追踪）
    ├── metrics.py         # MetricsCollector（Counter/Gauge/Histogram）
    ├── run_manager.py     # RunManager（Run 隔离 + SQLite 索引）
    ├── report_generator.py # HTML 报告生成
    ├── step_tracker.py    # StepTracker（步骤追踪）
    ├── reporter.py        # Reporter（预约报告）
    └── trace_viewer.py    # Trace HTML 查看器

examples/             # 示例代码
├── dry_run_booking.py

scripts/              # 工具脚本
├── check_repo.py

tests/                # 315 单元测试全部通过
├── unit/             # 22个单测文件
├── integration/      # 集成测试
└── smoke/            # 冒烟测试
```

## 添加新模块

1. 在 `src/booking/` 下创建模块
2. 在 `src/booking/__init__.py` 中导出
3. 编写单元测试
4. 更新本文档

## 提交规范

```bash
git add .
git commit -m "描述"
```

## 工作流

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 编写代码和测试
4. 确保所有测试通过 (`make test`)
5. 提交并 Push
6. 创建 Pull Request