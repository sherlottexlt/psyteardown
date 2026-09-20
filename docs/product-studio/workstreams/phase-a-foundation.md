# Phase A 工作流：上位模型和产品壳

- 状态：Paused（决策范围校准；A3 暂停）
- 开始日期：2026-09-20
- 对应路线图：[`ROADMAP.md`](../ROADMAP.md#phase-a上位模型和产品壳)
- 上位规格：[`North Star §9、§11、§13、§14`](../../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md)

## 目标

建立 Product Studio 的最小可信骨架，使用户能从一条不完整意图开始，在浏览器中查看并纠正结构化理解，经明确确认形成带 revision 的 Product Contract；新能力必须复用现有研发内核，且不把聊天或模型输出当作权威状态。

## 非目标

- 本阶段不生成最终 Web 产品；
- 不执行不受控代码或接入真实部署；
- 不引入多人租户、企业 RBAC、PostgreSQL、Temporal 或插件市场；
- 不扩展硬件 realization pack；
- 不宣称任何真实用户结果。

## 工作包依赖

```text
A0 项目台账（done）
  ↓
A1 上位领域契约（prototype tested，字段/确认范围待复核）
  ↓
A2 项目聚合与应用服务（prototype tested，集成边界待复核）
  ↓
A3 FastAPI API（paused；草稿未通过启动/HTTP 测试） ──┐
  ↓                  │
A4 React Studio 壳   │
  └──────────────┬───┘
                 ↓
          A5 薄纵向集成
```

## A1 设计检查表

四个对象都必须回答：

1. 它拥有而相邻对象不拥有的事实是什么；
2. 哪些字段来自用户陈述、外部证据、AI 推断或人类决定；
3. proposal 如何产生、如何被确认、纠正、替代和拒绝；
4. revision 身份、父 revision、内容 hash 和时间如何记录；
5. 哪些变化会使哪些下游对象 stale，而不是直接删除；
6. 什么条件下对象仍是 draft、可以 confirmed、必须 blocked 或需要重新建模；
7. API DTO 与领域快照怎样分离；
8. 如何在没有真实模型调用的情况下确定性测试。

建议的对象职责边界，当前仅作为设计起点而非已接受 schema：

| 对象 | 负责表达 | 不应负责 |
|---|---|---|
| ProductIntent | 用户想改变的现实、受影响者、价值、明确拒绝项和资源倾向 | 问题成因、具体解决方案或验证结论 |
| ProblemModel | 事实、假设、未知、竞争解释和利益相关方张力 | 将某个产品路径写成既定答案 |
| OutcomeContract | 目标结果、指标、禁止结果、资源边界、停止条件和最低交付成熟度 | 具体界面、技术栈或实现任务 |
| ProductThesis | 机制假设、实现模式、可证伪预测、验证策略和维护代价 | 冒充已验证结果或直接批准发布 |

## A2–A5 当前原型采用的边界（待首条用户切片验证）

以下写/读/存储组织方式部分来自旧内核经验，不因旧 ADR 标为 accepted 就自动成为新平台正式架构。

- 写路径：HTTP/CLI/MCP adapter → application command → domain transition → repository transaction → event/outbox。
- 读路径：可使用页面导向 projection，但 projection 不能写领域状态。
- 并发：所有会改变已存在聚合的命令携带 `expected_revision`。
- 模型：provider 只产生带 provenance 的 proposal DTO；确认命令创建不可变领域 revision。
- 存储：先提供内存适配器做领域测试，再提供 SQLite 适配器；不让 ORM 模型成为领域模型。
- 前端：所有区域共享明确的 project/revision 上下文；stale、unknown、unverified 和 conflict 必须可见。
- 集成：Phase A 使用 fake provider 和结构化文本，避免测试依赖网络、费用或采样波动。

## Phase A 验收场景

```text
Given 一个尚无 Product Contract 的新项目
When 用户提交一条不完整目标
Then 系统保存原始输入并产生 ProductIntent proposal

When 用户纠正并确认关键价值边界
Then 系统通过 Domain Command 创建新的不可变 revision
And 保留 proposal、确认者、时间和来源

When ProblemModel 或 OutcomeContract 的上游事实改变
Then 受影响 ProductThesis/DesignBrief 被标为需要复核或 stale
And 历史 revision 仍可读取

When 两个客户端基于同一旧 revision 写入
Then 后提交者得到显式冲突
And 系统不自动合并价值判断

When 用户打开 Web Studio
Then 对话、产品契约、工作台、决策和证据区域共享同一项目 revision
And 未确认 proposal 与已确认事实具有不同呈现
```

## 风险与提前验证

| 风险 | 最小验证 |
|---|---|
| 四对象边界过细，用户流程被内部模型绑架 | 先用一个端到端 Product Contract projection 驱动 schema |
| 新 revision 系统与旧内核并行 | A1/A2 先验证原型中的 ID/clock/hash/command 行为，再核对旧内核跨域接入是否必要 |
| API DTO 泄漏领域内部复杂度 | 用页面读模型和命令 DTO 契约测试隔离 |
| 前后端同时扩张导致无可运行切片 | 每个工作包保持 fake provider 下可运行，A5 只走一条 happy path 加关键失败路径 |
| 未选真实用例造成抽象设计 | A1 仅建立通用最小契约；Phase B 开始前把 PS-O001 设为硬 Gate |

## 完成定义

Phase A 只有在以下条件同时满足时完成：

- A1–A5 的验收条件均有代码和测试证据；
- 浏览器中可以完成“模糊输入 → proposal → 人工纠正/确认 → Product Contract revision”；
- 关闭/重启后已确认状态仍可恢复；
- revision 冲突、provider 失败、无效 proposal 和 stale input 有显式错误路径；
- README、API schema、当前状态、路线图、决策登记与演变日志同步；
- 未引入 Phase A 非目标，也没有提高未经现实验证的声明。
