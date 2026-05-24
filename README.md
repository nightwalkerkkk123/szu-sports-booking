# 深圳大学体育馆预约自动化工具

## 项目概述

基于 **CloakBrowser**（封装 Playwright）的体育馆预约自动化工具，用于自动化登录深圳大学体育场馆预约系统并完成场地预约。

**目标 URL**: `https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do#/sportVenue`

---

## 快速开始

### 安装依赖

```bash
pip install -e .
```

### 配置

**1. 设置密码（.env 环境变量）**

```bash
cp configs/.env.example .env
# 编辑 .env，按学号后4位设置密码：
#   SZU_PASSWORD_0090=你的密码
# 注意：.env 仅存放密码和日志级别，所有业务配置都在 config.yaml
```

**2. 配置账号和场馆（config.yaml）**

```yaml
# configs/config.yaml
accounts:
  - username: "2023150090"
    default_campus: "粤海校区"
    default_sport: "网球"
  - username: "2023150091"
    default_campus: "丽湖校区"    # 不同账号可以抢不同校区和项目
    default_sport: "羽毛球"
```


### 运行

```bash
# 运行预约（默认：串行，成功一个就停）
PYTHONPATH=src python -m booking.cli run

# 并发执行所有账号（适合同一账号抢多个项目）
PYTHONPATH=src python -m booking.cli run --all

# 干跑模式
PYTHONPATH=src python -m booking.cli run --dry-run --all

# 测试登录
PYTHONPATH=src python -m booking.cli test-login -u 你的学号 -p 你的密码

# 查看运行历史
PYTHONPATH=src python -m booking.cli runs

# 生成 HTML 报告
PYTHONPATH=src python -m booking.cli trace --latest
```

---

## 目录结构

```
登录体育馆_cloak/
├── main.py                          # 命令行主入口
├── src/booking/
│   ├── client.py                    # BookingClient（链式调用接口）
│   ├── pool.py                      # BookingPool（多账号并发池）+ AccountSession
│   ├── account.py                   # Account + AccountManager（状态追踪）
│   ├── config.py                    # Config（YAML 配置加载）
│   ├── errors.py                    # ErrorCode（14个错误码）
│   ├── retry.py                     # RetryPolicy（重试策略）
│   ├── database.py                  # Database（SQLite 存储）
│   ├── cli.py                       # CLI 入口（7个命令）
│   ├── chain_builder.py             # Chain（链式选择器）
│   ├── step_builder.py              # StepBuilder（步骤构建）
│   ├── browser/                     # 浏览器抽象层
│   │   ├── lifecycle.py             # BrowserLifecycle 接口
│   │   ├── cloak_adapter.py         # CloakBrowser 真实浏览器
│   │   └── fake_browser.py          # FakeBrowser 测试用
│   ├── selectors/                   # 页面选择器
│   │   ├── slot_selector.py         # FlexibleSlotSelector（含可用性判断）
│   │   └── venue_selector.py        # FlexibleVenueSelector
│   ├── matchers/                    # 匹配器
│   │   ├── text_matcher.py          # TextMatcher 精确匹配
│   │   ├── regex_matcher.py         # RegexMatcher + TimeSlotMatcher
│   │   ├── contains_matcher.py      # ContainsMatcher + Prefix/Suffix
│   │   └── composite_matcher.py     # CompositeMatcher + 工厂函数
│   └── observability/              # 可观测性
│       ├── logger.py                # Logger（结构化日志）
│       ├── tracer.py                # Tracer（分布式追踪）
│       ├── metrics.py               # MetricsCollector（指标收集）
│       ├── run_manager.py           # RunManager（Run 隔离管理）
│       ├── report_generator.py      # HTML 报告生成
│       ├── step_tracker.py          # StepTracker（步骤追踪）
│       ├── reporter.py              # Reporter（预约报告）
│       └── trace_viewer.py          # Trace HTML 查看器
├── configs/
│   ├── config.yaml                  # 业务配置
│   └── .env.example                 # 环境变量模板
├── tests/                           # 315 单元测试全部通过
│   ├── unit/                        # 22个单测文件
│   ├── integration/                 # 集成测试
│   └── smoke/                       # 冒烟测试
└── docs/                            # 架构/配置/开发/错误码文档
```

---

## 核心模块

### BookingClient

统一的链式调用接口，支持干跑模式：

```python
from booking.client import BookingClient

# 真实浏览器
client = BookingClient()

# 干跑模式
client = BookingClient(use_fake_browser=True)

# 链式调用
client.login("username", "password")
client.select_campus("粤海校区")
client.select_sport("网球")
client.select_date(0)
client.select_time_slot("19:00-20:00")
client.confirm()
```

### BookingPool

多账号并发池，支持 `dry_run` 模式：

```python
from booking.pool import BookingPool

pool = BookingPool(max_concurrent=3, dry_run=False)

# 全局默认配置（所有账号共用）
pool.update_config(campus="粤海校区", sport="网球", time_slot="19:00-20:00")

# 添加账号（使用全局配置）
pool.add_account("user1", "pass1", priority=2)

# 添加账号（独立配置覆盖全局），不同账号可抢不同项目
pool.add_account("user2", "pass2",
    config={"default_campus": "丽湖校区", "default_sport": "羽毛球", "default_time_slot": "20:00-21:00"})

# 串行：一个成功就停
result = pool.run_until_success(timeout=300)

# 并发：全部执行
results = pool.run_all(concurrent=True)
```

### AccountManager

多账号管理和状态跟踪（含失败计数、冷却机制）：

```python
from booking.account import AccountManager

manager = AccountManager()
manager.add_account("user1", "pass1", priority=2)
account = manager.get_available_account()
```

### RetryPolicy

```python
from booking.retry import RetryPolicy, RetryStrategy

policy = RetryPolicy(max_attempts=3, base_delay=1.0,
                     strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
```

### ErrorCode

14 个标准错误码（详见 `docs/ERRORS.md`）：

```python
from booking.errors import ErrorCode, ERROR_MAP
info = ERROR_MAP[ErrorCode.LOGIN_FAILED]
print(info.is_retryable)  # True
```

---

## CLI 命令

```bash
booking run                  # 运行预约（串行，成功一个就停）
booking run --all            # 并发执行所有账号
booking run --dry-run --all  # 干跑模式 + 并发
booking test-login           # 测试登录
booking validate-config      # 验证配置
booking smoke                # 运行冒烟测试
booking report               # 生成预约报告
booking trace --latest       # 打开最新 HTML 报告
booking runs                 # 列出运行历史
```

---

## 配置

### config.yaml（所有业务配置）

```yaml
booking:
  venue_url: "https://ehall.szu.edu.cn/..."
  default_campus: "粤海校区"
  default_sport: "网球"
  default_time_slot: "19:00-20:00"

# 多账号+多场馆（密码从环境变量 SZU_PASSWORD_{后4位} 注入）
accounts:
  - username: "2023150090"
    default_campus: "粤海校区"
    default_sport: "网球"
  - username: "2023150091"
    default_campus: "丽湖校区"
    default_sport: "羽毛球"
    default_time_slot: "20:00-21:00"

retry:
  max_attempts: 3
  base_delay_seconds: 1.0

logging:
  level: "info"
  dir: "logs"
```

### .env（仅存放密码和日志级别）

```bash
# 密码注入（命名规则：SZU_PASSWORD_{学号后4位}）
SZU_PASSWORD_0090=你的密码
SZU_PASSWORD=默认密码

# 日志级别（可选，覆盖 config.yaml）
# SZU_LOG_LEVEL=debug
```

---

## 实现细节

### confirm() 预约确认验证

`confirm()` 点击确认按钮后，会读取页面全文并检查响应结果：

```python
# 失败关键词检测
fail_keywords = ["操作过于频繁", "预约失败", "已预约过", "名额已满",
                 "不可预约", "已满员", "已达上限"]

# 成功关键词检测
success_keywords = ["预约成功", "提交成功", "操作成功"]
```

### 时间段可用性判断（_is_available）

采用**颜色优先**策略，rgb 颜色值判断优先于子元素类型：

1. **颜色检查（优先）：** `div.element` 的 style 属性
   - `rgb(134, 144, 156)` = 不可用
   - `rgb(162, 10, 71)` 或 `rgb(29, 33, 41)` = 可用
2. **子元素回退（颜色不明确时）：** `frame-child1`/`rectangle-4` = 可用，`ellipse` = 不可用

### select_venue() 场地过滤

场地和时间段使用相同的 DOM 结构（`div.group-2`），`select_venue()` 通过正则表达式 `\d{2}:\d{2}-\d{2}:\d{2}` 过滤掉时间格式的文本，只保留场地名称。

### [任务N] 并发输出前缀

多账号并发执行时，每个账号的输出带有 `[任务1]`、`[任务2]` 等前缀，方便区分不同账号的执行日志。

### 干跑模式与步骤追踪

```python
# 干跑模式：使用 FakeBrowser，不访问真实系统
client = BookingClient(use_fake_browser=True)

# 步骤追踪：传入 trace_id 启用 StepTracker
client = BookingClient(trace_id="run_20240524_001")

# BookingPool 同样支持
pool = BookingPool(dry_run=True, trace_id="run_20240524_001")
```

---

## 开发

```bash
make install    # 安装依赖
make test       # 运行测试（319 全部通过）
make lint       # 代码检查
make format     # 格式化
```

## 依赖

- Python 3.10+
- cloakbrowser >= 1.0.0
- click >= 8.0.0
- pyyaml >= 6.0.0
- python-dotenv >= 1.0.0
- playwright