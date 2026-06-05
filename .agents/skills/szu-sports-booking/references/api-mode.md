# API Mode Reference (HTTP API 直接调用)

**推荐路线** — 不启动浏览器，速度快 10-100 倍，自动处理 TLS 指纹和风控信号。

## 入口

`python -m booking.cli api`（项目根目录执行）。

## 核心方法 (`ApiBookingFlow`)

```python
from booking.api import ApiBookingFlow

flow = ApiBookingFlow(username="2023150090", proxy="http://127.0.0.1:7897")
# 1. 加载已保存的 cookie
flow.load_cookies()  # bool: True=已加载且有效
# 2. 若 cookie 失效,浏览器登录
flow.login_with_browser(password="...", name="...")  # 启动 Playwright
# 3. 查询
flow.get_available_dates()  -> list[str]  # ["2026-06-06", "2026-06-07"]
flow.get_time_slots(date, sport, campus)  -> list[TimeSlot]
flow.get_venues(date, time_slot, sport, campus)  -> list[Venue]
# 4. 预约
result = flow.book(date, time_slot, sport, campus, name)
# result = {"success": bool, "venue": str, "verified": bool, "message": str}
# 5. 验证
flow.get_my_bookings(page_size=5)  -> list[BookingRecord]
flow.close()
```

支持 `with` 语法: `with ApiBookingFlow(...) as flow: ...`

## 三种 HTTP Backend (`infra/`)

| Backend | 用途 | 是否模拟 Chrome |
|---------|------|----------------|
| `CurlCffiBackend` | **默认**,Chrome 131 TLS 指纹 | 是 |
| `SurfProxyBackend` | Go 进程 (端口 9876) 转发 curl | 是 |
| `HttpxBackend` | 透传,无指纹,fallback/debug | 否 |

自动 failover 顺序: `CurlCffiBackend` -> `SurfProxyBackend` -> `HttpxBackend`。
如果某个后端被风控拉黑 (RiskScorer 评分高),路由会自动跳过它。

## 风险评分与速率限制

- `RiskScorer` 监控每个后端的 4xx/5xx 比例、空响应、TLS 错误等
- 评分超过 `SUSPECT_THRESHOLD` (默认 70) 时,该后端进入熔断,自动路由到下一后端
- `AccountRateLimiter` 实现 per-account token bucket + 冷却,避免同一账号请求过快

## Cookie 生命周期

- 登录成功后保存到 `data/cookies/<username>.json`
- **24 小时有效**(已延长自 8h)
- 失效时 `load_cookies()` 返回 False,CLI 会提示"未找到 cookie 且未提供密码"

## CLI 参数

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `-u/--username` | 是 | - | 学号 |
| `-p/--password` | 首次 | - | 密码 (cookie 失效时重登) |
| `-s/--sport` | 否 | `网球` | 运动项目,见 [sport-codes.md](sport-codes.md) |
| `-d/--date` | 否 | 明天 | YYYY-MM-DD,默认选可预约列表的第二天 |
| `-t/--time-slot` | 预约时必填 | - | `19:00-20:00` |
| `--campus` | 否 | `粤海校区` | `粤海校区` / `丽湖校区` |
| `--name` | 首次 | - | 姓名 (首次浏览器登录需要) |
| `--dry-run` | 否 | False | 只查询不预约 |
| `--proxy` | 否 | - | HTTP 代理,如 `http://127.0.0.1:7897` |

## 典型输出 (dry-run)

```
✓ 已加载保存的cookie
可预约日期: ['2026-06-05', '2026-06-06', '2026-06-07']
预约日期: 2026-06-06

=== 查询模式: 网球 2026-06-06 ===

时间段: 14 个, 可预约: 4 个
  ✓ 002 - 08:00-09:00(可预约)
  ✗ 003 - 09:00-10:00(已被预约)
  ...

场地 (19:00-20:00): 6 个, 可预约: 2 个
  ✓ 网球场1号 (粤海校区) - 19:00-20:00
  ✗ 网球场2号 (粤海校区) - 19:00-20:00(已被预约)
  ...

预约记录: 3 条, 进行中: 1 条
  ● 网球 | 19:00-20:00 | 待核销
  ○ 羽毛球 | 14:00-15:00 | 已核销
  ...
```

## 典型输出 (真实预约)

```
✓ 已加载保存的cookie
可预约日期: [...]
预约日期: 2026-06-06

=== 预约: 网球 2026-06-06 19:00-20:00 (粤海校区) ===
✓ 预约成功! 场地: 网球场1号 (粤海校区)
✓ 预约记录已验证
```

## 错误处理

详见 [error-handling.md](error-handling.md)。常见:
- `AuthenticationError` / `SessionExpiredError` -> 重新登录 (cookie 失效)
- `NetworkError` -> 网络问题,稍后重试
- `BookingError(code=...)` -> 业务错误,详见 `src/booking/api/errors.py`

## 与浏览器模式对比

| 维度 | API 模式 (推荐) | 浏览器模式 (main.py) |
|------|----------------|---------------------|
| 速度 | < 2 秒 | 10-30 秒 |
| 资源 | 仅 HTTP | 启动 Chromium |
| 风控 | TLS 指纹 + 风险评分 | Playwright 暴露 |
| 调试 | JSON 响应 | 截图/DOM |
| Cookie 依赖 | 24h 复用 | 每次重登 |
