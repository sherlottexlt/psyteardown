# ADR-0059: 保留 Typer，按领域演进 CLI 边界

状态：accepted

## 背景

项目最初的 CLI 主要服务于文本产品拆解：输入一段 App 描述，调用 LLM，输出 Markdown/JSON 报告。后续加入了 M1/M2/M3 体验研究、设计迭代、样机证据和工程协同对象。若继续把所有命令平铺在一个 CLI 文件中，命令之间会出现错误的领域暗示，例如把 App 拆解直接当成硬件工程输入。

## 决策

暂不替换 Typer。Typer 继续作为本地、可复现、可审计的命令边界；应用服务和 Coordinator 才是业务边界。CLI 按领域逐步增加命令组：

```text
psyteardown
├── teardown       # 原始 App/数字服务拆解与案例记忆
├── discovery      # 拆解导入、信号分流、跨端投影
├── experience     # M1/M2/M3、假设、实验、证据
├── design         # 候选、Blender 派生资产、迭代
├── engineering    # 需求、任务、依赖、工具、状态门
├── quality        # FMEA、DVP&R、制造、发布
├── memory         # 案例与向量检索
└── strategies     # 策略卡与人工审批
```

旧的平铺命令保留兼容期，但新功能必须进入对应命令组。当前已落地 `discovery` 命令组：

```text
discovery import-teardown
discovery triage
discovery project-to-engineering
```

## 边界规则

1. `TeardownResult` 只能先进入 `DigitalExperienceDiscovery`。
2. 每条 `DigitalExperienceSignal` 必须由具名 reviewer 通过 `DiscoveryTriageDecision` 分流。
3. 只有 `device_interaction_candidate` 可以进入工程域；投影结果仍为 `explore`/`draft`。
4. CLI 不绕过 Coordinator 直接修改工程状态或批准 gate。
5. MCP 默认承担对话式查询和草稿建议，不取代具名审批。
6. 未来 Web/API 复用相同 Coordinator，不在 Web、MCP、CLI 各写一套业务逻辑。

## 为什么不立即换成 FastAPI/Web

当前主要问题是领域边界和流程语义，不是命令行框架能力。Typer 已满足 JSON 文件导入导出、CI、迁移脚本、可复现人工审查和测试；多人并发审查、权限、附件预览和图形化依赖图出现后，再在相同应用服务之上增加 HTTP/Web 工作台。

## 后续迁移

- 将 `cli.py` 拆为 `cli_commands/teardown.py`、`discovery.py`、`experience.py`、`engineering.py` 等模块。
- 保留旧命令作为薄 wrapper，并在帮助文本标记迁移目标。
- 为所有写命令使用统一 JSON envelope、错误码和 stdout/stderr 约定。
- 当 Web/API 上线后，CLI、MCP 和 Web 只调用应用服务，不互相调用入口函数。
