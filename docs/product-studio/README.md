# Product Studio 开发台账

- 状态：Active
- 建立日期：2026-09-20
- 适用范围：psyteardown 从“可信研发内核”演进为 AI Product Studio 的全部工作
- 上位方向：[`AI Product Studio 北极星与产品形态规格`](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md)
- 既有内核实施基线（仅限其原有范围）：[`未来方向与实施计划`](../superpowers/specs/2026-09-08-psyteardown-future-direction-and-implementation-plan.md)

## 这个目录解决什么问题

大型项目最容易出现的不是“没有文档”，而是状态、计划、决策和历史混在一起，后来无法判断什么已经实现、什么只是设想。本目录是 Product Studio 的长期开发入口，用来回答四个问题：

1. 现在真实具备什么能力；
2. 当前在推进什么，完成门槛是什么；
3. 为什么作出关键选择；
4. 各部分如何随代码、测试和现实证据演变。

本目录不复制所有规格、ADR 或代码说明，而是索引它们并记录项目级演变。旧内核 ADR 不是 Product Studio 的默认决策来源；A1/A2 是待产品验证的实现原型，A3 已暂停。

## 文档地图

| 文档 | 用途 | 更新方式 |
|---|---|---|
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | 当前能力、缺口、验证基线和最近下一步 | 每个实现批次结束时覆盖更新 |
| [`ROADMAP.md`](ROADMAP.md) | 阶段、工作包、依赖与退出门槛 | 计划或优先级变化时更新 |
| [`DECISION_REGISTER.md`](DECISION_REGISTER.md) | North Star 决策、原型假设和待决问题的索引 | 决策、试验结果或范围变化时更新 |
| [`EVOLUTION_LOG.md`](EVOLUTION_LOG.md) | 项目级时间线 | 只在末尾追加，不改写历史 |
| [`architecture/domain-boundaries.md`](architecture/domain-boundaries.md) | Product 上位域与既有研发内核的职责及集成方向 | 边界或跨域写入规则变化时更新 |
| [`workstreams/phase-a-foundation.md`](workstreams/phase-a-foundation.md) | 当前 Phase A 的实施分解和验收条件 | 工作包推进时更新 |
| [`iterations/2026-09-20-project-ledger-bootstrap.md`](iterations/2026-09-20-project-ledger-bootstrap.md) | 第一次实施记录 | 关闭后保持不变；纠错另记 |
| [`iterations/2026-09-20-a1-upper-domain-contracts.md`](iterations/2026-09-20-a1-upper-domain-contracts.md) | A1 上位领域契约实现记录 | 已关闭；保持不变 |
| [`iterations/2026-09-20-a2-project-application-service.md`](iterations/2026-09-20-a2-project-application-service.md) | A2 项目应用服务与持久化记录 | 已关闭；保持不变 |
| [`iterations/2026-09-20-a3-fastapi-shell.md`](iterations/2026-09-20-a3-fastapi-shell.md) | 暂停中的 A3 FastAPI 实施记录 | 恢复开发或确定处置时更新 |
| [`iterations/2026-09-20-adr-scope-correction.md`](iterations/2026-09-20-adr-scope-correction.md) | 新旧 ADR 范围校正与文件清理 | 已关闭；纠错另记 |
| [`templates/iteration-record.md`](templates/iteration-record.md) | 后续实现记录模板 | 仅在记录制度变化时更新 |

后续按需要增加以下内容，而不是预先建立大量空目录：

- `workstreams/`：一个长期工作流一份活文档；
- `iterations/`：一次可验证实现批次一份记录；
- `architecture/`：跨领域才需要说明清楚的系统视图，明确区分现状与设想；
- `operations/`：构建、迁移、部署和恢复手册。

## 事实与权威来源

不同问题使用不同权威来源：

| 问题 | 权威来源 |
|---|---|
| 产品为什么存在、服务谁、不能做什么 | North Star 规格 |
| 新 Product Studio 的已确认方向 | North Star 明确写出的选择；后续需单独确认的新决策记入本目录 |
| 既有研发内核为什么这样实现 | 在其原有范围内适用的 `docs/adr/` 历史记录 |
| 当前探索方案为何如此实现 | iteration 的实施记录与测试，不等同于已确认架构 |
| 当前软件实际上做什么 | 源代码、迁移和自动化测试 |
| 当前能声称什么验证等级 | 原始工具结果、现实证据和具名审查 |
| 项目正在做什么、下一步是什么 | 本目录的状态、路线图和工作记录 |

如果这些来源互相冲突，不要静默选择一个版本：先在实现记录中标出差异，再明确适用范围与后续决策。不能因为旧 ADR 标为 `accepted`，就把它自动升级为新平台约束；也不能因为原型测试通过，就认为产品或架构已获批准。`CURRENT_STATE.md` 只能总结事实，不能把计划写成已实现能力。

## 每个实现批次的维护协议

### 开始前

1. 阅读 North Star、`CURRENT_STATE.md`、`ROADMAP.md` 和本工作包需要的旧内核资料；
2. 在 `iterations/` 新建记录，写清目标、非目标、基线和验收条件；
3. 如果工作涉及新的长期边界，先在 `DECISION_REGISTER.md` 标明待决与暂定方案；只有确定必要性与适用范围后才新增正式决策文件。

### 实施中

1. 记录范围变化、关键权衡和发现的历史债务；
2. 所有“已完成”都必须能链接到代码、测试、迁移、截图或其他可复核证据；
3. 使用 `planned`、`implemented`、`verified`、`blocked`、`unknown` 等明确状态，避免模糊的完成百分比。

### 结束时

1. 运行与风险相称的测试并记录结果；
2. 更新 `CURRENT_STATE.md` 中受影响的事实与缺口；
3. 更新 `ROADMAP.md` 的工作包状态；
4. 将一条摘要追加到 `EVOLUTION_LOG.md`；
5. 关闭本次 iteration 记录，列出遗留项和下一最小工作包。

## 防漂移规则

- 第一条主线始终是“模糊意图到可运行数字产品的完整闭环”，不是继续横向增加旧内核对象。
- 现有 revision、provenance、dependency、stale/invalidation 和 Gate 能力优先复用，不另建平行真相源。
- 聊天和模型输出只是 proposal；确认后的结构化对象与 Domain Command 才能改变项目状态。
- 仿真、渲染、模型自评和自动测试不得冒充真实用户、物理、法规或商业结果。
- 在首条闭环完成前，不引入 North Star 明确排除的基础设施复杂度。
