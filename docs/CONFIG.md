# 配置说明

## 配置层级（优先级从高到低）

```
CLI 参数 > 环境变量 > .env 文件 > config.yaml > 默认值
```

---

## config.yaml

```yaml
booking:
  venue_url: "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do#/sportVenue"
  default_campus: "粤海校区"
  default_sport: "网球"
  default_date_index: 0
  default_time_slot: "19:00-20:00"

accounts:
  - username: "2023150090"       # 密码从环境变量 SZU_PASSWORD_0090 读取
    default_campus: "粤海校区"    # 可选，覆盖全局
    default_sport: "网球"         # 可选，覆盖全局
    default_time_slot: "19:00-20:00"  # 可选，覆盖全局
  - username: "2023150091"       # 密码从环境变量 SZU_PASSWORD_0091 读取
    default_campus: "丽湖校区"
    default_sport: "羽毛球"
    default_time_slot: "20:00-21:00"

retry:
  max_attempts: 3
  base_delay_seconds: 1.0
  max_delay: 30.0

logging:
  level: "info"
  dir: "logs"
  rotation: "daily"
  retention_days: 7

observability:
  trace_enabled: true
  debug_mode: false
  screenshot_on_failure: true

browser:
  headless: false
  timeout_ms: 30000

data:
  dir: "data"
  db_path: "data/booking.db"
```

---

## 环境变量 (.env)

```bash
# 账号密码（命名约定：SZU_PASSWORD_{学号后4位}）
SZU_PASSWORD_0090=你的密码
SZU_PASSWORD_0091=第二个账号的密码
SZU_PASSWORD=默认密码

# 单账号配置
SZU_USERNAME=你的学号

# 多账号配置（config.yaml 有 accounts 时不使用此项）
# SZU_ACCOUNTS=user1:pass1,user2:pass2

# 环境配置
SZU_ENV=dev
SZU_LOG_LEVEL=info

# 校区和项目
SZU_DEFAULT_CAMPUS=粤海校区
SZU_DEFAULT_SPORT=网球
SZU_DEFAULT_DATE_INDEX=0
SZU_DEFAULT_TIME_SLOT=19:00-20:00

# 浏览器配置
SZU_BROWSER_HEADLESS=false

# 可观测性配置
SZU_TRACE_ENABLED=true
SZU_DEBUG_MODE=false
SZU_SCREENSHOT_ON_FAILURE=true

# 真实环境测试
SZU_REAL_ENV=false
SZU_TEST_USERNAME=your_test_username
SZU_TEST_PASSWORD=your_test_password
```

---

## 配置项说明

### booking

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| venue_url | string | - | 预约页面 URL |
| default_campus | string | "粤海校区" | 默认校区 |
| default_sport | string | "网球" | 默认运动项目 |
| default_date_index | int | 0 | 默认日期索引 (0=今天) |
| default_time_slot | string | "19:00-20:00" | 默认时间段 |

### accounts（多账号+多场馆）

`accounts` 是一个列表，每个元素定义一个账号及其独立的预约配置：

| 配置项 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | ✅ | 学号 |
| default_campus | string | ❌ | 覆盖全局 default_campus |
| default_sport | string | ❌ | 覆盖全局 default_sport |
| default_time_slot | string | ❌ | 覆盖全局 default_time_slot |
| default_date_index | int | ❌ | 覆盖全局 default_date_index |

**密码不在这里配置**，通过环境变量 `SZU_PASSWORD_{学号后4位}` 注入。例如学号 `2023150090` → 环境变量 `SZU_PASSWORD_0090`。

```yaml
accounts:
  - username: "2023150090"
    default_campus: "粤海校区"
    default_sport: "网球"
    default_time_slot: "19:00-20:00"
  - username: "2023150091"
    # 不指定 default_campus/default_sport，使用全局默认值
```

### retry

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| max_attempts | int | 3 | 最大重试次数 |
| base_delay_seconds | float | 1.0 | 基础延迟（秒） |
| max_delay | float | 30.0 | 最大延迟（秒） |

### logging

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| level | string | "info" | 日志级别 (debug/info/warning/error) |
| dir | string | "logs" | 日志目录 |
| rotation | string | "daily" | 轮转策略 |
| retention_days | int | 7 | 保留天数 |

### browser

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| headless | bool | false | 是否隐藏浏览器 |
| timeout_ms | int | 30000 | 超时时间（毫秒） |

---

## 使用示例

```python
from booking.config import Config

# 从文件加载
config = Config.load("configs/config.yaml")

# 使用默认值
config = Config.from_defaults()

# 访问配置
print(config.default_campus)  # 粤海校区
print(config.retry_max_attempts)  # 3
```