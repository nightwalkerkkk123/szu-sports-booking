# AGENTS.md






## 项目目标

本仓库是一个深圳大学体育场馆预约自动化项目，目标是将重复、固定、流程化的网页操作封装为可维护、可测试、可观测的工程系统。

**当前核心能力：**
- 多账号管理（AccountManager + BookingPool）
- 体育场馆预约流程（BookingClient，支持干跑模式）
- 灵活选择器匹配（FlexibleSlotSelector, FlexibleVenueSelector）
- 浏览器抽象层（FakeBrowser + CloakBrowser 双实现）
- 文本匹配器（TextMatcher, RegexMatcher, CompositeMatcher）
- 重试策略（RetryPolicy，线性/指数退避）
- 日志、Trace、Metrics、RunManager、ReportGenerator（observability/）
- StepTracker（步骤追踪，已接入 BookingClient）
- CLI 操作（7个命令）
- 并发执行（支持 --all 并发模式 + [任务N] 前缀区分输出）
- confirm() 页面验证（检测"操作过于频繁"等失败提示）
- _is_available() 颜色优先判断（rgb 颜色值 > 子元素类型）
- select_venue() 时间格式过滤（排除 HH:MM-HH:MM 文本）
- 干跑模式与步骤追踪（use_fake_browser + trace_id）
- 测试体系（319 unit + 23 smoke/integration = 342 total passed）

---

## 重要入口

| 文件 | 作用 |
|------|------|
| `src/booking/client.py` | 预约流程主入口，链式调用接口 |
| `src/booking/pool.py` | 多账号并发池 |
| `src/booking/account.py` | 账号管理（Account + AccountManager） |
| `src/booking/config.py` | 配置加载与校验 |
| `src/booking/errors.py` | 错误码定义（14个错误码） |
| `src/booking/retry.py` | 重试策略（RetryPolicy + BookingError） |
| `src/booking/database.py` | SQLite 数据存储 |
| `src/booking/cli.py` | CLI 入口（run, test-login, validate-config, smoke, report, trace, runs） |
| `src/booking/selectors/` | 页面选择器 |
| `src/booking/matchers/` | 文本/正则/组合匹配器 |
| `src/booking/observability/` | Logger, Tracer, Metrics, RunManager, ReportGenerator, StepTracker |
| `src/booking/browser/` | 浏览器抽象层（FakeBrowser + CloakBrowser） |
| `main.py` | 命令行主入口 |

---

## 开发命令

**安装依赖：**
```bash
make install
# 或
uv sync --dev
```

**运行检查：**
```bash
make lint      # ruff check
make format   # ruff format
make test      # pytest (排除 real_env)
make ci        # lint + test
```

**分类测试：**
```bash
make test-unit       # pytest tests/unit/
make test-integration # pytest tests/integration/
make test-smoke      # pytest tests/smoke/
```

**覆盖率：**
```bash
make cov     # pytest --cov=src --cov-report=html
```

---

## 修改规则

1. **修改业务逻辑后，必须新增或更新测试**
2. **不允许在测试中访问真实深圳大学内部网**，除非测试带有 `real_env` 标记
3. **不允许提交真实账号、密码、Cookie、Token**
4. **不允许实现绕过验证码、破解风控、高频访问等逻辑**
5. 新增错误类型时，必须更新 `src/booking/errors.py`
6. 新增配置项时，必须更新 `configs/.env.example` 和 `docs/CONFIG.md`
7. 新增选择器时，必须放入 `src/booking/selectors/`，不要散落在业务代码中
8. 新增浏览器操作时，应优先通过统一浏览器抽象层，不要在业务逻辑中直接依赖 Playwright
9. 涉及真实提交、预约、支付等副作用操作，必须设计用户确认机制
10. **每修复一个 bug，必须补对应的回归测试**。测试要能复现 bug 场景：
    - 用最小用例重现 bug 的触发条件
    - 验证修复后不再出现
    - 测试名标注 `Bug:` 或放入 `*Regression` 测试类
    - 真实浏览器 API 差异类 bug → 补 `FakeBrowserLifecycle` 测试让 mock 行为对齐
    - 配置合并/覆盖类 bug → 补 `TestConfigMergeRegression` 测试
11. 修改完成后至少运行：
    ```bash
    make lint && make test
    ```

---

## 安全边界

**Agent 不得生成或修改以下内容：**
- 绕过验证码的代码
- 破解登录风控的代码
- 高频刷取内部网页面的代码
- 自动提交敏感操作且无用户确认的代码
- 将密码、Cookie、Token 打印到日志中的代码

---

## 推荐工作流

1. 阅读 `PROJECT_INDEX.md` 了解项目索引
2. 阅读相关模块的 README（若有）
3. 修改代码
4. 新增或更新测试
5. 运行 `make ci`
6. 更新文档
7. 提交 PR

---

## 测试标记

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.smoke` - 冒烟测试
- `@pytest.mark.real_env` - 真实环境测试（需手动启用）

**默认运行（不含真实环境）：**
```bash
pytest tests/ -m "not real_env"
```

---

## 快速导航

- [PROJECT_INDEX.md](PROJECT_INDEX.md) - 项目文件索引
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - 架构设计
- [CONFIG.md](docs/CONFIG.md) - 配置说明
- [ERRORS.md](docs/ERRORS.md) - 错误码说明
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) - 开发指南

## 临时文件规范

- 所有一次性脚本、调试脚本、迁移脚本、dump 文件必须放在 tmp/ 目录（仓库根的 tmp/ 已被 .gitignore 忽略，仅本地可见）。
- 命名建议带用途前缀，例如 tmp/patch_<topic>.py、tmp/analyze_<topic>.py、tmp/dump_<date>.json，方便后续定位和清理。
- 禁止在仓库根目录直接创建 patch_*.py / fix_*.py / analyze.py / dump.* 等一次性脚本（这类命名一旦被遗忘就会变成永久噪音）。
- 周期性清理（保留 tmp/ 目录本身）：
  - make tmp-clean — 清空 tmp/ 内容（推荐）
  - git clean -fX tmp/ — 只清 git 标记为 ignored 的本地文件
  - Get-ChildItem tmp -Recurse | Where-Object LastWriteTime -LT (Get-Date).AddDays(-7) | Remove-Item -Recurse -Force — PowerShell 下清理 7 天以上未访问的文件

