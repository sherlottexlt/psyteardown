# Iteration：A3 FastAPI `/api/v1` 壳

- 日期：2026-09-20
- 状态：Paused（已有代码草稿；未完成启动和 HTTP 集成验证）
- 路线图工作包：A3
- 类型：API

## 目标

通过本地优先的 FastAPI `/api/v1` 暴露 A2 的项目与四对象命令/查询能力，建立稳定的 transport DTO、错误契约、lifespan Repository 管理和 OpenAPI，为 React Product Studio 提供不会绕过领域层的后端入口。

## 基线

- A2 已完成 ProductApplicationService、InMemory/SQLite adapter 和 ProductProjectView；完整测试 438 passed、2 skipped。
- 环境已有 FastAPI 0.115.6、HTTPX 0.28.1、Uvicorn 0.34.0，但尚未声明为项目依赖。
- North Star §11.1 明确 `/api/v1`、命令写入和 localhost 优先；旧 ADR 0085、0061 只记录旧内核选择，其中 0085 被 North Star 明确引用。

## 范围

- FastAPI app factory、lifespan、SQLite service 注入、健康检查和 `/api/v1` router；
- 项目 create/read/status 与四对象 proposal/confirmation/disposition endpoints；
- HTTP request/response DTO，不把领域 snapshot 直接作为请求模型；
- 统一 request ID 与 validation/not-found/conflict/domain-gate/internal 错误 envelope；
- localhost/testserver Host 限制和 Vite 本地开发 origin 配置；
- OpenAPI 与临时 SQLite HTTP 集成测试，包括重启恢复；
- 声明 FastAPI/Uvicorn/HTTPX 依赖和服务启动入口。

## 非目标

- 不实现 React UI、认证、多租户或互联网部署；
- 不在 HTTP 请求中调用 LLM、执行生成代码或启动长任务；
- 不实现 Job/SSE；
- 不实现 ProductThesis → DesignBrief realization adapter。

## 验收条件

- API 请求经过 transport DTO 后构造既有 Command，路由不直接写 Repository；
- OpenAPI 包含项目与四对象 command schemas；
- HTTP 可走通“项目 → intent confirm → problem confirm → contract confirm → thesis selection”；
- stale expected revision 返回 409 且不写新 revision/event；
- schema validation 返回 422，完整用户输入不出现在错误体；
- 未确认上游触发稳定 domain-gate 错误；未知项目返回 404；
- 同一 SQLite 文件关闭 app、重新创建 app 后可以读取项目视图；
- 完整测试通过并同步项目台账。

## 实施记录

1. 写入 `src/psyteardown/api/` 的 app factory、路由、请求/响应 DTO、错误处理与 SQLite lifespan 草稿，更新 `pyproject.toml` 声明 FastAPI/Uvicorn/HTTPX。
2. 第一次启动检查失败：本机 FastAPI 0.115.6 与 Starlette 1.3.1 在 `APIRouter` 初始化处不兼容；HTTP 路由与 OpenAPI 均未完成运行验证。
3. 用户指出旧 ADR 的适用范围被错误继承，随后确认删除本轮新增七篇 ADR 并暂停 A3；此处保留未验证代码草稿，不将其标记为已交付 API。

## 变更清单

| 区域 | 当前状态 | 证据 |
|---|---|---|
| API 草稿 | app factory、路由与 DTO 文件已存在，启动失败，未有 HTTP 测试 | `src/psyteardown/api/` |
| 依赖声明 | FastAPI/Uvicorn/HTTPX 已写入配置，实际环境组合未兼容 | `pyproject.toml` |

## 决策与偏差

- 薄 HTTP adapter 符合 North Star §11.1 的方向，但具体 DTO/错误映射是未验证原型；原先误标为 accepted 的新 ADR 已删除。

## 验证

- 启动试验：导入并实例化 `create_app()` 失败，`APIRouter` 初始化抛出 `TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'`。
- HTTP 集成测试：尚未创建或运行；本次暂停后不将 A2 的 438 passed 错算为 A3 通过。

## 数据与迁移

- 复用 A2 `product_*` SQLite schema；A3 不新增领域数据表。
- 新增 HTTP 契约但尚无公开发布版本；破坏性变更仍需记录。

## 遗留项与风险

- A4 前需冻结 Product Contract 页面所需的最小 read projection。
- 当前 localhost 限制不是身份认证；任何远程/企业部署前必须加入正式安全边界。
- 恢复 A3 前必须解决 FastAPI/Starlette 依赖版本，并重新验证 A1/A2 原型是否符合首条用户闭环。

## 收尾同步

- [ ] `CURRENT_STATE.md`
- [ ] `ROADMAP.md`
- [ ] `DECISION_REGISTER.md`
- [ ] `EVOLUTION_LOG.md`

## 恢复条件

先明确代表性用户问题，复核四对象最小字段、人工确认范围与聚合/持久化方案，再解决依赖兼容并补齐 HTTP 集成测试；满足后才推进 A4。
