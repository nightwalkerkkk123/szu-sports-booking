## 改动内容

[简要描述本次改动]

## 修改原因

[为什么需要这个改动]

## 涉及模块

- [ ] booking client (client.py)
- [ ] account (account.py, pool.py)
- [ ] config (config.py)
- [ ] errors (errors.py)
- [ ] retry (retry.py)
- [ ] database (database.py)
- [ ] cli (cli.py)
- [ ] selectors (selectors/)
- [ ] matchers (matchers/)
- [ ] observability (observability/)
- [ ] tests
- [ ] docs

## 是否涉及真实内部网访问

- [ ] 否
- [ ] 是，已标记为 `real_env`

## 是否涉及真实副作用操作

- [ ] 否
- [ ] 是，已加入用户确认机制

## 是否涉及敏感信息

- [ ] 否
- [ ] 是，已脱敏

## 测试

- [ ] `make lint`
- [ ] `make test`
- [ ] `make ci`

## 回滚方式

[如何回滚本次改动]

---

**检查清单：**
- [ ] 代码遵循 AGENTS.md 规则
- [ ] 新增错误码已更新 errors.py
- [ ] 新增配置项已更新 .env.example
- [ ] 选择器变更集中在 selectors/
- [ ] 测试覆盖率未下降