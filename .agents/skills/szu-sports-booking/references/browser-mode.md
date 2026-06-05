# Browser Mode Reference (main.py)

**备选路线** — 启动 Chromium 浏览器,适合需要处理复杂 UI 流程或验证码的极端场景。
**不推荐作为默认**,因 Playwright 指纹易被风控识别。

## 入口

```bash
python main.py [选项]
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--username` | 是 | 学号 |
| `--password` | 是 | 密码 (明文,不推荐) |
| `--campus` | 是 | `粤海校区` / `丽湖校区` |
| `--sport` | 是 | 中文名 (网球/羽毛球...) |
| `--date` | 是 | `0`=今天, `1`=明天, `2`=后天 |
| `--time-slot` | 是 | `14:00-15:00` / `19:00-20:00` |
| `--dry-run` | 否 | 只查询不预约 |

## 何时用浏览器模式

- API 后端临时故障
- 需要处理验证码 (新设备/异常 IP)
- 调试页面结构 (截图/DOM 检查)
- API 模式无法覆盖的边缘情况

## 不推荐的原因

1. Playwright 默认特征 (navigator.webdriver=true 等) 容易被风控识别
2. 启动浏览器慢 (10-30 秒)
3. 资源占用高 (CPU/内存)
4. Cookie 每次会话不同,需重新登录

## 实现模块

- `src/booking/client.py` - `BookingClient` 链式调用
- `src/booking/pool.py` - `BookingPool` 多账号并发
- `src/booking/browser/` - 浏览器抽象层
  - `FakeBrowser` (测试用)
  - `CloakBrowser` (真实浏览器)
- `src/booking/selectors/` - 页面元素选择器

## 推荐迁移到 API 模式

`main.py` 路线保留为向后兼容,**新功能请使用 `python -m booking.cli api`**。
如发现浏览器模式有任何问题,请优先考虑 API 模式能否解决。
