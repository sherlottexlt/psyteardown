# Product Studio 演变日志

本文件记录项目级里程碑，按时间顺序只在末尾追加。早期条目中的新 ADR 与“固定架构”说法已由末尾的 2026-09-20 校正条目撤销；当前真实状态以 `CURRENT_STATE.md` 为准。

## 2026-09-20 — 建立 Product Studio 开发台账

- 触发：确认 [`AI Product Studio 北极星`](../superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md) 是上位产品方向，需要在大型实施过程中保存连续项目记忆。
- 新增：目录入口、当前状态、阶段路线图、决策登记册、Phase A 工作流和 iteration 模板。
- 基线：现有 Python 可信研发内核、CLI/MCP、SQLite revision、体验/工程/质量能力保留；FastAPI、React Product Studio 和上位四对象尚未实现。
- 验证：运行 `pytest -q`，结果为 406 passed、2 skipped、1 warning，用时 20.16 秒。
- 边界：本次只建立开发治理与事实基线，没有修改生产代码，也没有提升任何产品或现实证据等级。
- 下一步：执行 A1，为 ProductIntent、ProblemModel、OutcomeContract 和 ProductThesis 确定最小领域契约与状态转换。
- 详细记录：[`iterations/2026-09-20-project-ledger-bootstrap.md`](iterations/2026-09-20-project-ledger-bootstrap.md)

## 2026-09-20 — A1 上位领域契约落地

- 新增：独立 `psyteardown.product` 上位产品域，包含 ProductIntent、ProblemModel、OutcomeContract、ProductThesis 的不可变 revision snapshot、细粒度值对象和纯状态转换。
- 决策：ADR 0429–0432 固定四对象职责；意图/问题/结果契约必须具名确认，ProductThesis 选择必须有人决定或引用显式授权。
- 护栏：确认后的内容再次修改会回到 proposal；上游 revision 变化只产生 `review_required`/`stale` 影响事实，不改写或删除历史对象。
- 验证：新增 18 个测试；完整 `pytest -q` 为 424 passed、2 skipped、1 warning，用时 19.52 秒。
- 边界：尚无 Product Project Repository、Application Service、SQLite schema、API 或 UI；新增能力是领域层，不代表用户已经能使用 Product Studio。
- 下一步：A2 项目聚合与应用服务，加入 Domain Command、乐观并发、事件/审计和 InMemory/SQLite 持久化。
- 详细记录：[`iterations/2026-09-20-a1-upper-domain-contracts.md`](iterations/2026-09-20-a1-upper-domain-contracts.md)

## 2026-09-20 — A2 项目应用服务与原子持久化

- 新增：最小 ProductProject 生命周期、显式 proposal/confirm/disposition commands、ProductApplicationService 和只读 ProductProjectView。
- 持久化：InMemory 与独立 `product_*` SQLite adapter 共享同一命令路径；事务内检查 `expected_revision` 和父链并保存 current、Domain Event、Audit Event 与 RevisionImpact。
- Gate：ProblemModel、OutcomeContract、ProductThesis 只能引用同项目的 confirmed upstream revision；暂停项目阻止子对象写入。
- 恢复：SQLite 关闭重开后可以恢复 revision chain、current pointers、事件、审计、impact 和完整项目视图。
- 架构：ADR 0433–0434 与 [`architecture/domain-boundaries.md`](architecture/domain-boundaries.md) 固定项目/子聚合及 Product/Experience 边界。
- 验证：Product 测试 32 passed；完整 `pytest -q` 为 438 passed、2 skipped、1 warning，用时 22.29 秒。
- 边界：尚无 HTTP API、Web UI、realization adapter、provider 或异步 Job；A2 不代表用户可通过 Product Studio 完成流程。
- 下一步：A3 FastAPI `/api/v1` 壳和稳定错误/DTO 契约。
- 详细记录：[`iterations/2026-09-20-a2-project-application-service.md`](iterations/2026-09-20-a2-project-application-service.md)

## 2026-09-20 — 校正 ADR 适用范围并暂停 A3

- 发现：前两批 iteration 把旧 Experience 域的 ADR 当作新 Product Studio 的默认约束，又过早给 7 篇新 ADR 标记 `accepted`；A1/A2 的测试仅能证明当前代码行为，不能批准长期架构。
- 处置：删除本轮未提交的 ADR 0429–0435；保留已有 430 篇旧 ADR 作为原适用范围内的历史，不做批量删除。
- 记录：`DECISION_REGISTER.md` 将 North Star 已明确的方向、原型假设与重新开放的问题分开；A1/A2 保留代码和测试，但标为 `prototype tested`。
- 暂停：A3 草稿代码保留，未完成 HTTP 测试；本机 FastAPI 0.115.6 / Starlette 1.3.1 组合启动失败，不能称为可用 API。
- 后续：选定首条代表性用户情境、校准四对象最小字段与人工确认范围，并解决依赖兼容后再决定是否继续 A3。
- 详细记录：[`iterations/2026-09-20-adr-scope-correction.md`](iterations/2026-09-20-adr-scope-correction.md)
