# 错误码说明

## 错误码列表

### 登录错误

| 错误码 | 说明 | 可重试 | 需切换账号 | 需截图 |
|--------|------|--------|-----------|--------|
| LOGIN_FAILED | 登录失败 | ✅ | ❌ | ✅ |
| LOGIN_TIMEOUT | 登录超时 | ✅ | ❌ | ✅ |
| PASSWORD_INCORRECT | 密码错误 | ❌ | ✅ | ❌ |

### 账号错误

| 错误码 | 说明 | 可重试 | 需切换账号 | 需截图 |
|--------|------|--------|-----------|--------|
| ACCOUNT_LOCKED | 账号被锁定 | ❌ | ✅ | ✅ |
| ACCOUNT_DISABLED | 账号被禁用 | ❌ | ✅ | ❌ |
| CAPTCHA_REQUIRED | 需要验证码 | ❌ | ✅ | ✅ |

### 页面错误

| 错误码 | 说明 | 可重试 | 需切换账号 | 需截图 |
|--------|------|--------|-----------|--------|
| PAGE_LOAD_TIMEOUT | 页面加载超时 | ✅ | ❌ | ✅ |
| ELEMENT_NOT_FOUND | 元素未找到 | ✅ | ❌ | ✅ |
| ELEMENT_NOT_CLICKABLE | 元素无法点击 | ✅ | ❌ | ✅ |

### 预约错误

| 错误码 | 说明 | 可重试 | 需切换账号 | 需截图 |
|--------|------|--------|-----------|--------|
| NO_AVAILABLE_SLOT | 无可用时间段 | ✅ | ❌ | ❌ |
| SLOT_ALREADY_TAKEN | 时间段已被抢 | ✅ | ❌ | ❌ |
| SUBMIT_FAILED | 提交失败 | ✅ | ❌ | ✅ |
| SUBMIT_TIMEOUT | 提交超时 | ✅ | ❌ | ✅ |

### 系统错误

| 错误码 | 说明 | 可重试 | 需切换账号 | 需截图 |
|--------|------|--------|-----------|--------|
| NETWORK_ERROR | 网络错误 | ✅ | ❌ | ❌ |
| BROWSER_CRASHED | 浏览器崩溃 | ✅ | ❌ | ✅ |
| UNKNOWN_ERROR | 未知错误 | ❌ | ❌ | ✅ |

---

## 错误处理策略

### 可重试错误 (is_retryable=True)

以下错误会自动重试：
- `PAGE_LOAD_TIMEOUT` - 等待后重试
- `NETWORK_ERROR` - 短暂等待后重试
- `NO_AVAILABLE_SLOT` - 稍后重试

### 不可重试错误 (is_retryable=False)

以下错误应立即停止并切换账号：
- `CAPTCHA_REQUIRED` - 验证码无法自动处理
- `ACCOUNT_LOCKED` - 账号被锁定
- `PASSWORD_INCORRECT` - 密码错误

---

## 使用示例

```python
from booking.errors import ErrorCode, ERROR_MAP

# 获取错误信息
info = ERROR_MAP[ErrorCode.LOGIN_FAILED]
print(f"错误信息: {info.message}")
print(f"处理提示: {info.hint}")

# 判断是否应重试
if info.is_retryable:
    # 执行重试逻辑
    pass
```