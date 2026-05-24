# 架构设计

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层                                         │
│                                                                          │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│   │   main.py    │  │  booking cli  │  │   Config     │  │  Database    │ │
│   │  (命令行入口)  │  │  (Click CLI)  │  │  (配置管理)   │  │  (SQLite)    │ │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                              │                  │                │        │
└──────────────────────────────┼──────────────────┼────────────────┼────────┘
                               │                  │                │
                               ▼                  ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            业务层                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                          BookingClient                               │  │
│  │                  (统一链式调用接口 / 预约流程编排)                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│          ┌─────────────────────────┼─────────────────────────┐             │
│          ▼                         ▼                         ▼             │
│   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐     │
│   │  BookingPool │         │ChainBuilder  │         │StepBuilder   │     │
│   │  (多账号池)   │         │ (链式构建)    │         │ (步骤构建)    │     │
│   └──────────────┘         └──────────────┘         └──────────────┘     │
│          │                         │                         │             │
│          ▼                         ▼                         ▼             │
│   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐     │
│   │   Account    │         │    Chain     │         │    Step      │     │
│   │  Management │         │  (执行链)     │         │  (单步执行)   │     │
│   └──────────────┘         └──────────────┘         └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           选择器层                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     FlexibleVenueSelector                             │  │
│  │                 (场地选择：校区 + 运动项目)                              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     FlexibleSlotSelector                              │  │
│  │                   (时间段选择：日期 + 时间)                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           基础设施层                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │    Retry    │  │    Error     │  │   Logger     │  │   Tracer     │   │
│  │   Policy    │  │     Code     │  │  (日志)      │  │  (追踪)      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │   Metrics   │  │  Database    │  │   Config     │                    │
│  │   (指标)     │  │  (存储)      │  │  (配置)      │                    │
│  └──────────────┘  └──────────────┘  └──────────────┘                    │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │  RunManager │  │ ReportGen   │  │ StepTracker │                    │
│  │ (运行隔离)    │  │ (HTML报告)   │  │ (步骤追踪)    │                    │
│  └──────────────┘  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           外部依赖层                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Browser 抽象层                                    │  │
│  │                                                                      │  │
│  │   ┌──────────────────────┐      ┌──────────────────────┐          │  │
│  │   │ CloakBrowserLifecycle │      │ FakeBrowserLifecycle │          │  │
│  │   │   (真实浏览器)         │      │   (测试用模拟)        │          │  │
│  │   └──────────────────────┘      └──────────────────────┘          │  │
│  │                                                                      │  │
│  │                    BrowserLifecycle 接口                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 核心模块

### 1. BookingClient

预约客户端，统一的链式调用接口。

```python
from booking.client import BookingClient

client = BookingClient()
client.login(username, password)
client.select_campus("粤海校区")
client.select_sport("网球")
client.select_date(0)  # 0=今天, 1=明天
client.select_time_slot("19:00-20:00")
client.confirm()
```

**职责：**
- 封装预约完整流程
- 提供链式调用接口
- 管理浏览器生命周期

---

### 2. BookingPool

多账号并发池，管理多账号预约。

```python
from booking.pool import BookingPool

pool = BookingPool()
pool.add_account(username, password, priority=2)
pool.add_account(username2, password2, priority=1)

# 并发执行
results = pool.run_all(
    campus="粤海校区",
    sport="网球",
    date_index=0,
    time_slot="19:00-20:00"
)
```

**职责：**
- 多账号管理
- 并发调度
- 结果汇总

---

### 3. Account / AccountManager

账号抽象和管理。

```python
from booking.account import AccountManager, AccountStatus

manager = AccountManager()
account = manager.add_account(username, password, priority=2)

# 获取可用账号（按优先级排序）
account = manager.get_available_account()

# 状态管理
account.mark_failure()  # 失败计数 +1
account.mark_success()  # 重置失败计数
```

**职责：**
- 账号状态跟踪
- 失败计数和冷却
- 优先级调度

---

### 4. ChainBuilder / StepBuilder

流程构建器，支持链式调用和步骤执行。

```python
from booking.chain_builder import Chain

Chain(page) \
    .click("粤海校区") \
    .wait_for_selector(".sport-list") \
    .click("网球") \
    .wait_for_selector(".date-list") \
    .click("今天")
```

**职责：**
- 链式调用执行
- 步骤组合
- 重试和错误处理

---

### 5. Browser 抽象层

浏览器生命周期抽象，通过接口隔离真实浏览器和测试模拟。

```python
from booking.browser import BrowserLifecycle, CloakBrowserLifecycle, FakeBrowserLifecycle

# 真实浏览器（访问真实系统）
browser = CloakBrowserLifecycle()
browser.launch(headless=False)

# 测试用模拟浏览器（不访问真实系统）
fake_browser = FakeBrowserLifecycle()
fake_browser.launch(headless=True)
```

**模块：**
- `lifecycle.py` - BrowserLifecycle 抽象接口
- `cloak_adapter.py` - CloakBrowserLifecycle 实现（真实 Playwright）
- `fake_browser.py` - FakeBrowserLifecycle 实现（测试用）

**职责：**
- 封装浏览器启动/关闭
- 提供统一的 page 接口
- 支持真实浏览器和模拟浏览器切换

**选择原则：**
- 默认使用 FakeBrowserLifecycle（测试、CI）
- 需要访问真实系统时使用 CloakBrowserLifecycle

---

## 数据流

### 预约流程数据流

```
用户输入
    │
    ▼
main.py / CLI
    │
    ├─── 解析参数 ──────────────────────────────────────────┐
    │                                                        │
    ▼                                                        ▼
Config.load()                                       AccountManager
    │                                             (获取可用账号)
    │                                                        │
    ▼                                                        ▼
BookingClient.login() ◄───────────────────────────── credentials
    │                                           (username, password)
    │
    ├─── 选择校区 ──────────────────────────────────────────┐
    │                                                        │
    ▼                                                        ▼
FlexibleVenueSelector                    CloakBrowser
    │                                    (Playwright)
    ├─── select_campus(campus) ───────────────────────────► │
    │                                                        │
    │                                                        ▼
    │                                              page.click()
    │                                                        │
    ├─── select_sport(sport) ─────────────────────────────► │
    │                                                        │
    ├─── select_date(index) ──────────────────────────────► │
    │                                                        │
    └─── select_time_slot(time) ──────────────────────────► │
                                                             │
                                                             ▼
                                                     预约成功/失败
                                                             │
                    ┌────────────────────────────────────────┼────────────────────────────────────────┐
                    │                                        │                                        │
                    ▼                                        ▼                                        ▼
            Database.insert()                      Account.mark_success()                   Account.mark_failure()
            (记录结果)                              (重置失败计数)                              (失败计数+1)
                    │                                        │                                        │
                    ▼                                        ▼                                        ▼
            BookingRecord                           AccountStatus.AVAILABLE            AccountStatus.COOLDOWN (≥3次)
                                                                                       │
                                                                                       ▼
                                                                          账号进入冷却，切换下一个账号
```

---

### 错误处理数据流

```
异常发生
    │
    ▼
ErrorCode 判定
    │
    ├─── 可重试错误 ──────────────────── RetryPolicy.should_retry()
    │    (LOGIN_FAILED, NETWORK_ERROR)           │
    │                                          ▼
    │                                  RetryPolicy.get_delay()
    │                                          │
    │                                          ▼
    │                                    time.sleep()
    │                                          │
    │                                          ▼
    │                                    重试操作
    │
    ├─── 不可重试错误 ──────────────────── 立即切换账号
    │    (CAPTCHA_REQUIRED,                    │
    │     ACCOUNT_LOCKED)                      ▼
    │                               AccountManager.get_available_account()
    │
    └─── 严重错误 ────────────────────────── 截图 + 告警
         (BROWSER_CRASHED)                    │
                                           ▼
                                    Logger.error() + screenshot
```

---

### 指标收集数据流

```
操作执行
    │
    ▼
MetricsCollector
    │
    ├─── counter("login_attempts").increment()
    │
    ├─── gauge("active_accounts").set(value)
    │
    ├─── histogram("booking_duration").record(ms)
    │
    ▼
Reporter.get_summary()
    │
    ▼
{
    "success_rate": 0.85,
    "total_bookings": 100,
    "failed_bookings": 15,
    ...
}
```

---

## 选择器抽象

### FlexibleVenueSelector

```python
from booking.selectors.venue_selector import FlexibleVenueSelector

venue_selector = FlexibleVenueSelector(page)

# 支持多种匹配方式
venue_selector.select_campus("粤海校区")      # 文本匹配
venue_selector.select_campus(index=0)        # 索引匹配
venue_selector.select_campus(contains="粤海") # 模糊匹配
```

### FlexibleSlotSelector

```python
from booking.selectors.slot_selector import FlexibleSlotSelector

slot_selector = FlexibleSlotSelector(page)

# 选择日期
slot_selector.select_date(0)                # 今天
slot_selector.select_date("2024-05-25")     # 指定日期

# 选择时间段
slot_selector.select_slot("19:00-20:00")     # 精确匹配
slot_selector.select_available()             # 第一个可用
```

---

## 状态机

### Account 状态机

```
                    ┌─────────────────┐
                    │   AVAILABLE     │◄────────────────────────┐
                    │   (可用)        │                          │
                    └────────┬────────┘                          │
                             │                                     │
              mark_failure() │                                     │
                             │                                     │
                             ▼                                     │
                    ┌─────────────────┐                           │
                    │ IN_USE          │                           │
                    │ (使用中)        │                           │
                    └────────┬────────┘                           │
                             │                                     │
                    mark_success() │                                     │
                                     │                                     │
                                     ▼                                     │
                    ┌─────────────────┐    3次失败    ┌─────────────────┐
                    │   AVAILABLE    │◄──────────────│    COOLDOWN    │
                    └─────────────────┘               │    (冷却中)     │
                                                     └────────┬────────┘
                                                              │ cooldown到期
                                                              │
                                                              ▼
                                                     ┌─────────────────┐
                                                     │   AVAILABLE     │
                                                     └─────────────────┘
```

---

## 配置优先级

```
CLI 参数 > 环境变量 > .env > config.yaml > 默认值
```

```python
config = Config.load("configs/config.yaml")

# 所有配置来源按优先级合并
# 1. config.yaml (最低优先级)
# 2. .env 文件
# 3. 环境变量
# 4. CLI 参数 (最高优先级)
```