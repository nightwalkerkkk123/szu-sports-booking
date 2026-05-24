# examples

示例代码，展示如何使用本项目。

## 文件说明

| 文件 | 说明 |
|------|------|
| `dry_run_booking.py` | 模拟预约流程（不访问真实系统） |
| `config.example.yaml` | 配置示例 |

## dry_run_booking.py

演示如何使用 FakeBrowserLifecycle 执行模拟预约流程：

```bash
PYTHONPATH=src python examples/dry_run_booking.py
```

此脚本：
1. 使用 FakeBrowserLifecycle（不启动真实浏览器）
2. 执行完整的预约流程模拟
3. 打印结果

## 添加新示例

添加新示例时：
1. 使用 `FakeBrowserLifecycle` 避免访问真实系统
2. 添加清晰的注释说明
3. 确保示例可以独立运行