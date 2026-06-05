---
name: szu-sports-booking
version: 2.0.0
description: "深圳大学体育场馆预约自动化工具。当用户想要预约深大体育场馆（羽毛球、网球、乒乓球等场地）、查询空闲场地、“抢场地”、“预约场馆”、“订场”等需求时使用。默认走 HTTP API 路线（curl_cffi 模拟 Chrome TLS 指纹 + 风险评分 + 速率限制），首次需浏览器登录一次拿 cookie（24h 复用），后续无需浏览器。干跑模式（--dry-run）可只查询不预约。IMPORTANT: 真实预约会占用实际名额，任何情况下都先 dry-run 确认可用性，再用户明确确认，最后才执行真实预约。"
metadata:
  bins: ["python"]
  script: "${SZU_BOOKING_DIR:-.}/src/booking/cli.py"
  category: booking
  tags: [szu, sports, booking, automation, http-api]
---

# szu-sports-booking（深大体育场馆预约）

**⚠️ 安全规则** — 真实预约会占用实际名额。**先 dry-run，再用户确认，最后真实预约。**

## 快速决策

| 用户意图 | 使用 |
|---------|------|
| 查询空闲场地/时段 | `python -m booking.cli api ... --dry-run` (API 模式) |
| 预约单个场地 | `python -m booking.cli api ...` (API 模式) |
| API 临时故障 | 退化到 `python main.py` (浏览器模式,见 [browser-mode.md](references/browser-mode.md)) |

**默认走 API 模式**，浏览器模式仅作为最后备选。

## 3 步确认法 (强制)

### Step 1: dry-run 预览

```bash
cd "$SZU_BOOKING_DIR" || cd .
python -m booking.cli api \
  -u 2023150090 \
  -p "$SZU_PASSWORD_0090" \
  -s 网球 \
  -d 2026-06-06 \
  -t 19:00-20:00 \
  --campus 粤海校区 \
  --dry-run
```

**首次运行** 浏览器会弹出 ehall.szu.edu.cn 登录页，**用户手动完成登录**（正常流程，不绕验证码），cookie 自动保存到 `data/cookies/2023150090.json`。
**后续运行** 复用 cookie，无浏览器弹出。

**输出解读**:
```
✓ 已加载保存的cookie
可预约日期: ['2026-06-05', '2026-06-06', '2026-06-07']
预约日期: 2026-06-06
=== 查询模式: 网球 2026-06-06 ===
时间段: 14 个, 可预约: 4 个
  ✓ 002 - 08:00-09:00(可预约)
  ✗ 003 - 09:00-10:00(已被预约)
场地 (19:00-20:00): 6 个, 可预约: 2 个
  ✓ 网球场1号 (粤海校区) - 19:00-20:00
```

### Step 2: 向用户确认意图

向用户清晰展示:
- "“19:00-20:00” 时段有 2 个可预约场地，是否执行真实预约?"
- 列出候选场地名称

### Step 3: 真实预约 (用户明确确认后)

去掉 `--dry-run` 标志:
```bash
python -m booking.cli api \
  -u 2023150090 \
  -s 网球 \
  -d 2026-06-06 \
  -t 19:00-20:00 \
  --campus 粤海校区
```

**成功标志**:
```
✓ 预约成功! 场地: 网球场1号 (粤海校区)
✓ 预约记录已验证
```

## 配置文件

| 文件 | 用途 | 是否提交 |
|------|------|----------|
| `configs/config.yaml` | 业务配置 (校区/默认项目) | 是 |
| `.env` (或 `configs/.env`) | 密码 (按学号后 4 位命名) | **否** (`.gitignore` 已忽略) |
| `data/cookies/*.json` | 已保存的登录 cookie (24h) | **否** |

**`.env` 格式**:
```bash
SZU_PASSWORD_0090=你的密码   # 0090 = 学号末4位
SZU_PASSWORD=你的密码         # 兑底,SZU_PASSWORD_0090 优先
SZU_LOG_LEVEL=info
```

## 详细参考

按需加载以下文件:

- **[references/api-mode.md](references/api-mode.md)** — API 模式详解 (3 种 backend、风险评分、API 方法)
- **[references/browser-mode.md](references/browser-mode.md)** — 浏览器模式 (main.py,仅备选)
- **[references/sport-codes.md](references/sport-codes.md)** — 运动项目/校区编码表
- **[references/error-handling.md](references/error-handling.md)** — 错误处理与恢复

## 安全规则 (强制)

- ✅ **任何预约必须先 `--dry-run` 预览**
- ✅ **必须获得用户明确确认后才执行真实预约**
- ✅ **密码从 `.env` 读取，不在对话/日志中暴露**
- ✅ **API 模式模拟 Chrome TLS 指纹，不绕过风控**
- ✅ **不实现验证码绕过、风控破解、高频刷取逻辑**
- ❌ **不在没有 dry-run 的情况下直接执行真实预约**
- ❌ **不在用户未明确确认的情况下执行真实预约**
- ❌ **不打印/记录 cookie/密码到日志**
- ❌ **不在单账号下并发多个预约实例**

## 注意事项

1. **时间敏感**: 场馆通常提前 1-2 天开放预约
2. **Cookie 24h 过期**: 失效后需重新浏览器登录一次
3. **同一账号同时只能有一个预约实例在运行** (有 per-account rate limiter)
4. **后端自动 failover**: curl_cffi -> surf-proxy -> httpx
5. **首次配置**: 必须设置 `SZU_BOOKING_DIR` 环境变量指向项目根
