# Product Studio 当前状态

- 快照日期：2026-09-20
- 当前阶段：Phase A — 决策范围校准，A3 暂停
- 当前工作包：新旧 ADR 权威范围校正（已完成）；A3 不继续扩展
- 下一步：重新确认首条用户切片及 A1/A2 原型的字段、人工确认与存储边界，然后再恢复 A3
- 最近完整测试：`pytest -q`，438 passed、2 skipped、1 warning（ADR 校正后；A3 草稿无 HTTP 测试覆盖）

## 一句话状态

仓库已经具备经过测试的 Python/Pydantic 可信研发内核；新写的 ProductProject、四个上位对象、Application Service 和 InMemory/SQLite 实现通过了相应代码测试，但只是尚未经过首条真实用户闭环验证的探索性实现。A3 FastAPI 代码已写入一部分，却未通过启动与 HTTP 集成测试：当前环境的 FastAPI 0.115.6 与 Starlette 1.3.1 组合在 APIRouter 初始化时报错。Web 工作空间、可恢复生成 Job、隔离代码执行和产品预览均未实现。

## 已验证的软件基线

| 能力区域 | 当前事实 | 证据位置 | 状态 |
|---|---|---|---|
| 拆解与知识内核 | 具备心理框架、五步流水线、grounding、记忆、策略与自评模块 | `src/psyteardown/{kb,pipeline,memory,growth,strategy,review}` 与对应测试 | verified |
| 体验与证据内核 | 具备 Evidence、Observation、ExperienceHypothesis、设计候选、实验与反馈模型 | `src/psyteardown/experience/` 与 `tests/experience/` | verified |
| revision 与依赖传播 | 具备 SQLite 持久化、revision、依赖图以及 stale/invalidation 语义 | experience repositories/sqlite/service 与测试 | verified |
| 工程与质量边界 | 具备工程对象、工具请求/结果分离、质量和发布 Gate；没有真实工具结果就不会提升声明 | experience engineering/quality/tool modules 与测试 | verified |
| 自动化入口 | CLI 与 MCP 共享现有应用/编排能力；MCP 主要用于读取和草稿 | `src/psyteardown/cli.py`、`src/psyteardown/mcp_server/` | verified |
| Product Studio 上位领域原型 | 四对象不可变 revision、人工确认/授权门和直接 revision 影响计算；字段和门槛尚待确认 | `src/psyteardown/product/`、`tests/product/` | prototype tested |
| Product 项目应用层原型 | 独立聚合、命令、expected revision、事件/审计/impact、双 adapter 和重启恢复；架构尚待确认 | `src/psyteardown/product/{commands,service,repositories,sqlite}.py`、`tests/product/test_service.py` | prototype tested |
| A3 HTTP 草稿 | 已有路由、DTO、app factory 和依赖声明；当前依赖组合下无法启动 | `src/psyteardown/api/`、`pyproject.toml` | unverified / paused |
| 回归基线 | 当前完整测试通过，但没有 API 启动或 HTTP 集成测试 | 2026-09-20 `pytest -q`：438 passed、2 skipped | A1/A2 covered; A3 unverified |

## Product Studio 能力差距

| 工作流 | 目标 | 当前状态 | 最近下一步 |
|---|---|---|---|
| 上位产品模型 | ProductIntent、ProblemModel、OutcomeContract、ProductThesis 均可版本化、纠正和追溯 | prototype tested, decisions open | 对照具体用户流程验证最小字段与确认边界 |
| 项目应用层 | 用 Domain Command 和 `expected_revision` 编排上位对象 | prototype tested, architecture open | 验证是否需要独立聚合及 `product_*` 持久化 |
| FastAPI API | `/api/v1` 提供稳定命令/读取入口 | draft / paused | 先解决版本兼容及领域决策，再完成 HTTP 测试 |
| Web Product Studio | 五区工作空间共享同一项目 revision 上下文 | not started | A4 建立 React/TypeScript/Vite 壳 |
| 对话到结构化状态 | 模型 proposal 经人确认后成为领域 revision | not started | 先用 fake provider 走通 proposal/confirm |
| 持久化长任务 | Job 可暂停、恢复、取消、限预算并处理 stale input | partial foundation | 盘点现有持久化能力后补 Product Studio Job |
| 隔离生成与运行 | 在受限 workspace 构建、测试和运行生成的 Web 产品 | not started | Phase B 前锁定本地沙箱 ADR |
| 浏览器验证 | Playwright 覆盖启动、关键任务、错误态和基础可访问性 | not started | 与首个生成模板一起实现 |
| 预览与反馈 | 用户直接使用产品，反馈锚定页面、任务和 revision | not started | Phase B 实现 |
| 导出与交付 | 导出源码、构建物、验证结果、未知和交付说明 | existing lower-level export only | Phase B 建立 Product Program bundle |
| 真实结果验证 | 现实任务、用户报告和测量保持来源与证据边界 | lower-level model exists | Phase C 接入 Product Studio 闭环 |

`partial foundation` 只表示旧内核存在可复用构件，不表示 Product Studio 已经提供该用户能力。

## 当前证据边界

- 当前版本不能称为 Product Studio；用户仍不能通过 Web 工作空间从模糊意图获得可运行产品。
- Transit Anchor 仍是 `geometry_ready / design-review confirmed / physical validation pending`。
- 当前 `PrototypeRun=0`、`MeasurementObservation=0`、`EvidenceReview=0`，证据等级仍为 `none`。
- Blender、GLB、PNG、virtual preflight 和 scenario replay 是设计或派生材料，不是舒适、安全、可靠、可制造、合规或可发布证据。
- 自动化测试证明的是代码在覆盖范围内的行为，不证明产品给真实用户带来了目标结果。

## 当前约束与风险

1. Product 上位域暂时复用 `experience.models` 的 frozen/revision/event 基础类型；这是原型取舍，不是已确认的长期架构。
2. 第一条纵向切片的具体目标用户与现实问题尚未选定；在 Phase B 开始前必须选定，否则测试只能验证框架，不能验证产品价值。
3. `pyproject.toml` 已加入 FastAPI/Uvicorn 依赖和 API 启动入口，但本机 FastAPI/Starlette 组合不兼容；HTTP 功能不能标为可用。前端与 Playwright 尚无依赖。
4. 旧 ADR 在既有内核范围内才可能有效；新平台方向以 North Star 为准，新增字段、人工 Gate、聚合和存储选择须重新确认。
5. 全量测试仍有 1 条 Pydantic 字段遮蔽 warning；A3 尚未完成启动与 HTTP 验证。

## 下一次状态更新的触发条件

恢复并完成 A3 之前，先完成以下检查：

- 选择具体首条用户场景，检查 A1/A2 原型是否回答真实用户问题；
- 对照 North Star §17 恢复四对象最小字段、人工确认范围等待决问题；
- 解决 FastAPI/Starlette 版本冲突，并验证现有 A3 草稿是否仍适用。

A3 真正完成时至少应出现：

- FastAPI 应用入口、lifespan 和 repository 注入；
- `/api/v1/projects` 的最小 create/read 与四对象 proposal/confirm/disposition command endpoints；
- transport DTO/OpenAPI 与领域 snapshot/Command DTO 的边界；
- revision conflict、domain gate、validation 和 not-found 的稳定错误格式；
- 耗时动作不在同步写端点执行，并预留 `job_id` 语义；
- HTTP 集成测试使用临时 SQLite，重启后读取结果一致。
