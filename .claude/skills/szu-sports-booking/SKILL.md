---
name: szu-sports-booking
version: 1.0.0
description: "深圳大学体育场馆预约自动化工具。帮用户自动化登录并预约体育场地，支持多账号并发、干跑测试模式。"
metadata:
  bins: ["python"]
  script: "E:/szu-sports-booking/main.py"
---

# szu-sports-booking（深大体育馆预约）

**CRITICAL — 真实预约会占用实际名额，调用前必须用户明确确认。**

## 配置

项目位于 `E:/szu-sports-booking/`，配置文件：

- `configs/config.yaml` — 账号、校区、场馆、时间段等业务配置
- `.env` — 密码存储（`SZU_PASSWORD_0090=你的密码`，按学号后4位命名）

## 命令格式

```bash
cd E:/szu-sports-booking
python main.py --username <学号> --password <密码> --campus <校区> --sport <项目> --date <日期> --time-slot <时间段>
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--username` | 学号 | `2023150090` |
| `--password` | 密码 | `11282577` |
| `--campus` | 校区 | `粤海校区` / `丽湖校区` |
| `--sport` | 体育项目 | `网球` / `羽毛球` / `乒乓球` |
| `--date` | 日期索引 | `0`=今天, `1`=明天, `2`=后天 |
| `--time-slot` | 时间段 | `14:00-15:00` / `19:00-20:00` |
| `--dry-run` | 干跑模式（不占名额） | 加在任意位置 |

## 调用流程

### Step 1：查询可用场地（dry-run）

先用干跑模式查询某日期的可用时间段：

```bash
cd E:/szu-sports-booking && python main.py --dry-run --username 2023150090 --password 11282577 --campus 粤海校区 --sport 网球 --date 1 --time-slot 14:00-15:00
```

输出示例：
```
可用时间段 (4/14 个):
  [6] [OK] 14:00-15:00(可预约)
  [7] [OK] 15:00-16:00(可预约)
```

### Step 2：确认用户意图

向用户展示查询结果，明确询问：
- 目标场地是否在列表中
- 确认后去掉 `--dry-run` 执行真实预约

### Step 3：执行预约

去掉 `--dry-run` 即可执行真实预约：

```bash
cd E:/szu-sports-booking && python main.py --username 2023150090 --password 11282577 --campus 粤海校区 --sport 网球 --date 1 --time-slot 14:00-15:00
```

**成功标志**：输出中包含 `[OK] 预约成功（页面确认）`

## 预约成功的标志

- 输出包含 `[OK] 预约成功（页面确认）`
- 日志目录：`logs\booking\runs\<date>_<trace-id>\`

## 注意事项

1. **时间段已被预约**：如果目标时间段显示 `[X]`（已被预约），无法抢到
2. **密码管理**：不要在对话中暴露密码，引导用户配置 `.env` 文件
3. **并发限制**：同一账号同时只能有一个预约实例
4. **时间敏感**：预约系统在特定时间开放，建议提前测试流程

## 错误处理

| 错误 | 原因 | 处理方式 |
|------|------|---------|
| `UnicodeEncodeError` | Windows GBK 终端问题 | 代码已使用 `[OK]`/`[X]` 替代 |
| `选项不可用` | 时间段已被抢 | 换其他时间段 |
| `未找到元素` | 页面结构变化 | 需要更新选择器代码 |
| `登录失败` | 账号密码错误 | 检查凭证 |

## 安全规则

- **禁止在对话中明文输出密码**
- **执行真实预约前必须用户确认**
- **优先使用 `--dry-run` 预览结果**