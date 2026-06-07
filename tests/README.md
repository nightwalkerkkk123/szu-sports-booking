# tests

## 测试分层

| 目录 | 标记 | 作用 | 外部依赖 |
|------|------|------|----------|
| `unit/` | `@pytest.mark.unit` | 测试单个模块，不访问外部系统 | 无 |
| `integration/` | `@pytest.mark.integration` | 测试模块协作，使用 stub/fake | 无 |
| `smoke/` | `@pytest.mark.smoke` | 测试核心链路，验证整体流程 | 无 |
| `real_env/` | `@pytest.mark.real_env` | 真实环境测试（需手动启用） | 深圳大学内网 |

---

## 运行测试

```bash
# 所有测试（排除真实环境）
make test

# 单元测试
make test-unit

# 集成测试
make test-integration

# 冒烟测试
make test-smoke

# 带覆盖率
make cov
```

---

## 规则

1. **默认测试不得访问真实深圳大学内部网**
2. 真实环境测试必须使用 `@pytest.mark.real_env` 标记
3. 新增功能必须至少新增单元测试
4. 修改预约主流程必须新增或更新 smoke test
5. 测试通过命令：`make test`
6. Agent 不得默认运行 real_env 测试

---

## Fixtures

测试 fixtures 位于 `tests/conftest.py` 和 `tests/fixtures/`：

| Fixture | 用途 |
|---------|------|
| `temp_dir` | 临时目录 |
| `config_path` | 临时配置文件 |
| `mock_env` | Mock 环境变量 |

---

## 添加新测试

1. 单元测试 → `tests/unit/test_<module>.py`
2. 集成测试 → `tests/integration/test_<feature>.py`
3. 冒烟测试 → `tests/smoke/test_smoke.py`

---

## 测试文件清单

| 测试文件 | 被测模块 | 测试数 |
|----------|----------|--------|
| test_matchers.py | matchers/* | 37 |
| test_pool.py | pool.py | 36 |
| test_browser.py | browser/* | 25 |
| test_chain_builder.py | chain_builder.py | 22 |
| test_step_builder.py | step_builder.py | 20 |
| test_account.py | account.py | 19 |
| test_run_manager.py | run_manager.py | 19 |
| test_selectors.py | selectors/* | 18 |
| test_step_tracker.py | step_tracker.py | 17 |
| test_retry.py | retry.py | 17 |
| test_plan.py | plan.py | 15 |
| test_risk_scorer.py | risk_scorer.py | 14 |
| test_client.py | client.py | 14 |
| test_confirm_page.py | selectors/confirm_page.py | 13 |
| test_errors.py | errors.py | 12 |
| test_smoke.py | 冒烟测试 | 11 |
| test_integration.py | 集成测试 | 11 |
| test_cli.py | cli.py | 11 |
| test_config.py | config.py | 10 |
| test_router.py | router.py | 9 |
| test_report_generator.py | report_generator.py | 9 |
| test_rate_limiter.py | rate_limiter.py | 8 |
| test_database.py | database.py | 8 |
| test_logger.py | logger.py | 8 |
| test_login_page.py | selectors/login_page.py | 6 |
| test_escape_hatch.py | escape_hatch | 5 |
| test_render_log_html.py | render_log_html | 4 |
| test_campus_page.py | selectors/campus_page.py | 4 |
| test_sport_page.py | selectors/sport_page.py | 4 |
| test_infra_backends.py | infra backends | 3 |
| **总计** | | **409** |

## 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| account.py | 80% |
| config.py | 80% |
| errors.py | 90% |
| retry.py | 80% |
| database.py | 70% |
| cli.py | 60% |
| observability/* | 70% |
| **总体** | **65%** |