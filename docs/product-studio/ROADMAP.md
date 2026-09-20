# Product Studio 路线图

- 基线日期：2026-09-20
- 路线图状态：Phase A 校准中；A3 暂停
- 排序原则：先完成一个可验证的数字产品纵向闭环，再扩展用户类型、基础设施或 realization pack

## 状态图例

| 状态 | 含义 |
|---|---|
| `done` | 验收条件已有可复核证据 |
| `in progress` | 当前正在实施 |
| `ready` | 前置条件满足，可直接开始 |
| `prototype tested` | 实现及测试存在，但字段/架构的产品决策未确认，不能当作阶段正式完成 |
| `paused` | 已明确暂停，不继续投入，保留已写的草稿和待解决问题 |
| `planned` | 已进入路线图，但前置条件尚未满足 |
| `decision required` | 缺少会实质改变实现的产品或架构决策 |

完成度按工作包和退出门槛判断，不使用缺少事实基础的百分比。

## 总体阶段

| 阶段 | 目标结果 | 状态 | 退出门槛摘要 |
|---|---|---|---|
| Phase A | 上位模型和 Product Studio 壳 | paused (decision review) | 可从 Web/API 创建项目、形成并确认 Product Contract，旧内核经应用服务复用 |
| Phase B | 数字产品生成闭环 | planned | 从模糊意图到可运行 Web 产品、自动测试/修复、反馈和导出全链路可演示且可恢复 |
| Phase C | 真实结果验证 | planned | 目标结果有可操作测量，现实观察与 AI/仿真解释严格分层，并能回退产品论点 |
| Phase D | 个人交付与企业治理 | planned | 身份、权限、租户、预算、审计与外部系统集成由真实需求驱动并经过验证 |
| Phase E | Realization Packs | planned | 在数字产品路径验证后，以共享内核增加移动、硬件、服务等独立实现包 |

## Phase A：上位模型和产品壳

### A0 — 建立项目记忆系统

- 状态：`done`
- 产物：本目录的状态、路线图、决策索引、演变日志、工作流计划和记录模板
- 验证：仓库测试基线 406 passed、2 skipped；未修改生产代码

### A1 — 上位领域契约与状态转换（原型）

- 状态：`prototype tested`；字段、状态机和人工确认范围待按 North Star §17 与首条用户场景复核
- 范围：`ProductIntent`、`ProblemModel`、`OutcomeContract`、`ProductThesis`
- 关键产物：
  - 每个对象的职责、最小字段、不变量和 revision 语义；
  - proposal、human confirmation、amendment、supersession 和 invalidation 状态转换；
  - 与 DesignBrief、Discovery、Evidence 和现有 revision/dependency graph 的映射；
  - 原型假设记录与领域单元测试；只有经确认需要时才创建正式决策文档。
- 退出门槛（尚未完成产品验证）：四类对象能通过命令创建/修订；无确认 proposal 不能静默成为权威状态；上游变化的影响可确定性计算，并用具体用户场景检验字段与确认门槛。

### A2 — 项目聚合与应用服务（原型）

- 状态：`prototype tested`；聚合边界和独立 `product_*` 存储待重新确认
- 前置：A1
- 范围：Product Project/Program 的最小聚合边界、命令处理、读模型、Repository 接口和内存/SQLite 适配。
- 退出门槛（尚未完成集成）：同一项目下可追踪四个上位对象；写入支持 `expected_revision`；命令为原子事务边界；旧内核通过明确适配器复用。当前仅完成原型测试，未实现旧内核适配。

### A3 — FastAPI `/api/v1` 壳

- 状态：`paused`；已有部分代码，但 FastAPI 0.115.6 / Starlette 1.3.1 不兼容，且 A1/A2 边界须先校准
- 前置：A1/A2 原型决策复核及运行环境兼容性确认
- 范围：项目资源、命令端点、错误契约、OpenAPI、健康检查和 fake provider 下的集成测试。
- 退出门槛：API 不承载领域写逻辑；并发 revision 冲突可见；耗时动作只返回 Job 引用；客户端类型可由 schema 校验或生成。

### A4 — React/TypeScript/Vite Product Studio 壳

- 状态：`planned`
- 前置：A3 的稳定最小 schema
- 范围：项目主页以及对话、产品契约、工作台、决策、证据五区导航；共享项目 revision 上下文；加载、空、错误和 stale 状态。
- 退出门槛：用户可在浏览器查看并纠正 Product Contract；页面不把聊天消息当作最终项目状态；基础键盘操作和可访问性检查通过。

### A5 — Phase A 薄纵向集成

- 状态：`planned`
- 前置：A1–A4
- 范围：用 fake provider 从一条模糊输入生成结构化 proposal，经人工确认形成 Product Contract，并显示 revision 与未知项。
- 退出门槛：API、UI、SQLite 和领域内核端到端测试通过；失败与重启后不丢失已确认状态；未确认内容保持 proposal。

## Phase B：数字产品闭环

按依赖顺序推进：

1. 选定一类明确目标用户与现实问题，并冻结首条纵向切片的 Outcome Contract；
2. 生成 2–3 个具有真实机制/实现差异的 Product Thesis；
3. 建立受支持的单一 Web 技术模板和内容最小化生成契约；
4. 建立持久化、幂等、可恢复且受预算约束的生成 Job；
5. 在隔离 workspace 中安装依赖、构建并运行产品；
6. 用 Playwright 执行关键任务、错误状态、基础可访问性和视觉回归；
7. 自动定位并修复失败，保留每次尝试和成本；
8. 提供嵌入式预览、revision 差异和页面/任务级反馈锚点；
9. 导出源码、构建物、测试证据、未验证声明和交付说明。

Phase B 开始前必须解决的决策：首个现实问题、允许的生成模板、沙箱边界、模型/工具预算与反馈采集边界。

## Phase C：真实结果验证

- 将 Outcome Contract 的指标转成可执行测量计划；
- 区分运行事件、用户报告、研究观察、模型解释和正式 Evidence Review；
- 支持小规模真实任务试用、同意、撤回和来源追踪；
- 当结果不支持当前方向时，允许回退到 Product Thesis、Outcome Contract 或 ProblemModel；
- 不让软件测试、模拟用户或专家意见冒充真实用户结果。

## Phase D：个人交付与企业治理

- 基于真实使用决定本地个人版、托管版和企业部署的优先级；
- 加入身份、组织、权限、租户隔离、预算、数据政策和审计；
- 接入 Git、工单、数据仓库和部署平台；
- 支持多人评论、通知、冲突处理和具名审批；
- 达到并发与耐久性门槛后再评估 PostgreSQL、对象存储和 Temporal。

## Phase E：Realization Packs

- 数字产品主线验证后，再增加移动应用、硬件/工业设计、服务运营、内容/教育等 pack；
- 每个 pack 复用 Product Intent、Outcome Contract、Evidence 和 revision 内核；
- 每个 pack 单独定义生成器、工具、验证方法和发布 Gate；
- Transit Anchor 作为硬件 pack 的验证案例，不再承担整个平台的产品北极星。

## 暂不进入主线

在 Phase B 闭环通过前，不把以下内容加入当前关键路径：Kubernetes、Kafka、多队列、复杂插件市场、独立 Electron 客户端、任意框架代码生成、大量自治 Agent、无人批准部署，以及与 Python 内核重复的服务端业务逻辑。
