# PROJECT_INDEX.md

## 项目一句话说明

深圳大学体育场馆预约自动化系统，包含账号管理、预约流程、选择器匹配、重试、日志、Trace、Metrics、CLI 和测试体系。

---

## 目录索引

| 路径 | 作用 | 修改注意事项 |
|------|------|-------------|
| `src/booking/client.py` | 预约核心入口 | 修改后必须跑集成测试 |
| `src/booking/pool.py` | 多账号并发池 | 注意并发安全 |
| `src/booking/account.py` | 账号管理 | 不得记录明文密码 |
| `src/booking/config.py` | 配置管理 | 新配置需更新 `.env.example` |
| `src/booking/errors.py` | 错误码 | 新错误需同步更新 ERRORS.md |
| `src/booking/retry.py` | 重试策略 | 避免无限重试 |
| `src/booking/database.py` | 数据存储 | 修改 schema 需注意迁移 |
| `src/booking/cli.py` | CLI 入口 | 修改后跑 CLI smoke |
| `src/booking/chain_builder.py` | 链式构建器 | 核心接口，谨慎修改 |
| `src/booking/step_builder.py` | 步骤构建器 | 包含重试逻辑 |
| `src/booking/selectors/` | 页面选择器 | **选择器必须集中维护在此** |
| `src/booking/matchers/` | 文本/正则/组合匹配器 | 4个文件：TextMatcher, RegexMatcher, ContainsMatcher, CompositeMatcher |
| `src/booking/observability/` | 日志/Trace/Metrics/RunManager/Report | 8个模块：不得输出敏感信息 |
| `src/booking/browser/` | 浏览器抽象层 | FakeBrowser + CloakBrowser 双实现 |
| `tests/unit/` | 单元测试 | 快速、无外部依赖 |
| `tests/integration/` | 集成测试 | 使用 fake/stub |
| `tests/smoke/` | 冒烟测试 | 默认不访问真实系统 |
| `configs/` | 配置文件 | config.yaml + .env.example |
| `docs/` | 文档 | 改动功能需同步更新 |

---

## 模块依赖图

```
main.py
    └── booking.cli
            └── booking.client (BookingClient)
                    ├── booking.account (AccountManager)
                    ├── booking.chain_builder (Chain)
                    ├── booking.step_builder (StepBuilder)
                    ├── booking.selectors (FlexibleVenueSelector, FlexibleSlotSelector)
                    └── booking.pool (BookingPool)

booking.config ──► booking.errors
        │
        └──► booking.retry ──► booking.errors

booking.observability
    ├── logger.py
    ├── tracer.py
    ├── metrics.py
    ├── reporter.py
    ├── run_manager.py
    ├── report_generator.py
    ├── step_tracker.py
    └── trace_viewer.py
```

---

## 常见任务入口

### 修改预约流程

优先查看：
1. `src/booking/client.py`
2. `src/booking/chain_builder.py`
3. `src/booking/step_builder.py`
4. `src/booking/selectors/`

### 修改账号逻辑

优先查看：
1. `src/booking/account.py`
2. `src/booking/pool.py`
3. `src/booking/config.py`

### 修改可观测性

优先查看：
1. `src/booking/observability/logger.py`
2. `src/booking/observability/tracer.py`
3. `src/booking/observability/metrics.py`
4. `src/booking/observability/reporter.py`

### 修改测试

优先查看：
1. `tests/conftest.py`
2. `tests/unit/`
3. `tests/integration/`
4. `tests/smoke/`

---

## 文件编码规范

- UTF-8
- Python 3.10+
- 行长度：100 字符（ruff 配置）
- 使用类型注解

---

## 外部依赖

- `cloakbrowser` - 浏览器自动化
- `playwright` - Playwright Python 绑定
- `click` - CLI 框架
- `pyyaml` - YAML 配置
- `python-dotenv` - 环境变量
- `pytest` - 测试框架

---

## 环境变量前缀

所有自定义环境变量以 `SZU_` 开头：
- `SZU_ACCOUNTS`
- `SZU_ENV`
- `SZU_LOG_LEVEL`
- `SZU_DEFAULT_CAMPUS`
- `SZU_DEFAULT_SPORT`
- 等等

---

## 数据库

- 类型：SQLite
- 路径：`data/booking.db`
- 表：`booking_records`
- 用途：记录预约历史、计算成功率

---

## CLI 命令

```bash
python main.py --help
python main.py --username XXX --password XXX --campus 粤海校区 --sport 网球 --time-slot 19:00-20:00
```

或使用 CLI 模块：
```bash
PYTHONPATH=src python -m booking.cli --help
```