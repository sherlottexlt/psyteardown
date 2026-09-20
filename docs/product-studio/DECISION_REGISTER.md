# Product Studio 决策登记册

- 建立日期：2026-09-20
- 校正日期：2026-09-20（新旧 ADR 适用范围校正）
- 用途：区分 North Star 已明确的方向、代码原型采用的假设，以及尚需用户场景验证的待决问题

## 权威边界

`docs/adr/` 的旧条目属于它们原本针对的拆解、体验和工程内核；`accepted` 不代表自动适用于新平台。North Star §16 保留旧计划作为可信研发内核基线，§11 只明确重申了部分 API/UI 技术方向。原型代码和测试证明实现行为，不等于产品决策获得批准。2026-09-20 误建的 7 篇新 ADR 已删除，改在本文件记录待验证假设。

## North Star 已明确的方向

| ID | 状态 | 方向 | 来源 | 影响 |
|---|---|---|---|---|
| PS-D001 | accepted | 产品北极星是 AI Product Studio | [North Star §0–2](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 优先走通真实用户结果闭环 |
| PS-D002 | accepted | 主要用户形态是对话驱动、成果物中心的 Web 工作空间；CLI/MCP 是辅助入口 | [North Star §4、§10](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 不以 CLI 流程取代用户主体验 |
| PS-D003 | accepted | 首条完整纵向切片是数字/Web 产品 | [North Star §13](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 硬件和企业能力不并行扩张 |
| PS-D004 | accepted | 旧体验、证据、revision 与工程 Gate 作为可信研发内核保留 | [North Star §0、§9、§16](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 旧内核继续有效，但其原有 ADR 不自动约束新对象 |
| PS-D005 | accepted | 当前阶段采用 React/TypeScript/Vite 与 FastAPI `/api/v1`；领域写逻辑留在 Python | [North Star §11.1](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 技术方向已定，具体 HTTP DTO/错误格式仍需验证 |
| PS-D006 | accepted | 模型输出默认是 proposal，状态由命令与 revision 转换 | [North Star §12.1](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 聊天记录不能充当唯一项目状态 |
| PS-D007 | accepted | 本地第一阶段继续 SQLite、内容寻址资产、持久化单 Worker | [North Star §11.1](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 未决定上位域是否使用独立 `product_*` 表 |
| PS-D009 | accepted | 交付成熟度和证据边界必须显式，不允许伪完成 | [North Star §8](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) | 软件测试、仿真不能证明真实用户结果 |

## 原型假设，不是已接受决策

| ID | 状态 | 当前代码采用的假设 | 证据 | 复核点 |
|---|---|---|---|---|
| PS-H001 | prototype_only | 四对象使用当前不可变字段与 proposed/confirmed 状态机 | [A1 记录](iterations/2026-09-20-a1-upper-domain-contracts.md)、`src/psyteardown/product/models.py` | 最小字段是否足够；哪些字段必须由人确认 |
| PS-H002 | prototype_only | ProblemModel 确认需至少两个竞争解释，OutcomeContract 确认需指标/停止条件等 | [A1 记录](iterations/2026-09-20-a1-upper-domain-contracts.md) | 是否给用户增加不必要的提问与审核成本 |
| PS-H003 | prototype_only | ProductProject 与四对象使用独立 revision 聚合 | [A2 记录](iterations/2026-09-20-a2-project-application-service.md) | 并发和读写边界是否适合首条产品闭环 |
| PS-H004 | prototype_only | 上位域使用独立 `product_*` SQLite 表 | [A2 记录](iterations/2026-09-20-a2-project-application-service.md) | 是否便于复用旧内核并维持一致性 |
| PS-H005 | prototype_only | A1/A2 测试使用手工结构化输入和确定性数据，未接真实模型 | [A1/A2 测试](../../tests/product/test_service.py) | 只能验证代码路径，不能替代模型行为或真实用户闭环 |
| PS-H006 | draft_paused | A3 草稿使用薄 FastAPI command/projection adapter 及一套 HTTP 错误格式 | [A3 记录](iterations/2026-09-20-a3-fastapi-shell.md) | 先解决运行环境兼容，再验证 DTO、HTTP Gate 和可恢复性 |

这些行只说明已经写出什么，不能作为后续工作的强制约束；应先做一条代表性用户流程，再决定保留、修改或移除。

## 当前待决问题

| ID | 状态 | 问题 | 决策时点 |
|---|---|---|---|
| PS-O001 | open | 第一条 vertical slice 的具体目标用户与现实问题是什么？ | 继续扩大领域/API 前优先确认 |
| PS-O002 | reopened | 四个上位对象的最小字段、状态和聚合边界是什么？ | A1 原型校准，A3 恢复前 |
| PS-O003 | reopened | Product Contract 哪些字段必须由人确认，哪些可依据来源/证据推进？ | A1 原型校准，A3 恢复前 |
| PS-O004 | open | 第一版允许生成哪一种 Web 技术模板？ | Phase B 生成器前 |
| PS-O005 | open | 本地代码沙箱的隔离、网络与 Secret 边界是什么？ | 首次执行生成代码前 |
| PS-O006 | open | 模型、工具、重试和自动修复预算是多少？ | 持久化生成 Job 前 |
| PS-O007 | open | 预览反馈采集到什么粒度，如何取得同意？ | 反馈功能前 |
| PS-O008 | open | 哪些实测需求触发 SQLite/单 Worker 迁移？ | 后续架构评审前 |
| PS-O009 | open | 平台名称继续使用 psyteardown 吗？ | 对外试用前 |
| PS-O010 | open | 新对象与旧体验/工程内核如何共享来源、revision 和存储事务？ | 跨域实现前 |

## 记录维护规则

1. 新平台方向优先引用 North Star；旧 ADR 仅在其原范围内引用，并明确是否被 North Star 重申。
2. 可回退的实现先写 iteration 的假设与验证；不因实现先行就把设计标记为 `accepted`。
3. 对影响数据迁移、安全或跨域约束的长期选择，等具体用户场景或原型证据足够时再决定是否编写新 ADR。
4. 不再沿用旧 ADR 递增编号作为新平台实施任务清单；旧文件不批量删除，本次只移除误建的新文件。
