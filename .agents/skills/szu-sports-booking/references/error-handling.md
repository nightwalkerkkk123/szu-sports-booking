# Error Handling Reference

## 错误分类

### 1. 认证错误

| 错误 | 触发 | 处理 |
|------|------|------|
| `AuthenticationError` | 用户名/密码错误 | 引导用户检查 `.env` 中的 `SZU_PASSWORD_0090` |
| `SessionExpiredError` | Cookie 过期 (24h+) | 重新提供 `-p` 密码走浏览器登录 |

### 2. 网络错误

| 错误 | 触发 | 处理 |
|------|------|------|
| `NetworkError` | SSL/TLS 指纹失败、连接超时 | 检查网络/代理,稍后重试 |
| `[SSL: UNEXPECTED_EOF_WHILE_READING]` | 沙箱/防火墙阻断 TLS | 切换到 `SurfProxyBackend` 或检查代理 |
| `Connection timed out after 15000ms` | curl_cffi 后端超时 | 切换 backend 或检查网络 |

### 3. 业务错误 (BookingError.code)

| code | 触发 | 处理 |
|------|------|------|
| `VENUE_UNAVAILABLE` | 时段已被抢 | 换时段,dry-run 查可用 |
| `BOOKING_EXISTS` | 当天已有同类预约 | 取消已有或换项目 |
| `QUOTA_EXCEEDED` | 超过单人单日限额 | 取消之前的预约 |
| `INVALID_PARAMS` | 参数不合法 (日期/校区) | 检查日期格式 `YYYY-MM-DD` |
| `SERVER_ERROR` | 5xx 错误 | 稍后重试 |

### 4. 风控/限流 (RiskScorer)

- 表现: 请求偶发 `403` / `503` / 空响应
- 自动处理: `BackendRouter` 检测到后端评分高会跳过该后端,自动 failover
- 用户层: 通常无需介入,如果所有后端都被风控,**停止操作 1-2 小时**

### 5. 浏览器登录错误 (login_with_browser)

| 错误 | 触发 | 处理 |
|------|------|------|
| 验证码出现 | 异常登录地点/IP | 让用户手动完成,不要绕过 |
| 登录失败 | 密码错误 | 检查 `.env` |
| Cookie 提取失败 | 页面结构变化 | 提示用户需要更新 `cookie_extractor.py` |

## 错误恢复流程图

```
尝试 booking api --dry-run
  ├─ NetworkError -> 切换 backend 或代理
  ├─ SessionExpiredError -> 重新 -p 密码登录
  ├─ BookingError -> 换时段/换项目
  └─ 成功 -> 询问用户 -> booking api (无 --dry-run)
       ├─ NetworkError -> 退避重试
       └─ 成功 -> 验证 + 通知
```

## 调试技巧

1. **启用 DEBUG 日志**:
   ```bash
   SZU_LOG_LEVEL=debug python -m booking.cli api -u 2023150090 --dry-run
   ```

2. **查看原始响应** (修改代码临时):
   ```python
   # 在 src/booking/api/client.py 中 _request() 末尾
   import json; print(json.dumps(result, ensure_ascii=False, indent=2))
   ```

3. **测试网络可达性**:
   ```bash
   curl -I https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do
   ```

4. **清空 cookie 强制重登**:
   ```bash
   rm data/cookies/2023150090.json
   ```
