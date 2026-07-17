# 心理驱动型产品拆解 Agent · v6 设计文档

- 日期:2026-07-17
- 状态:已通过设计评审,待用户确认 spec
- 依赖:v1–v5(已合并到 main,实战验证完成)。本文档仅覆盖 **v6**。

---

## 1. 背景与目标

v1–v5 内核(5 步拆解流水线 + 三层记忆 + 元认知自评)已在 5 个真实产品上完成实战验证,但唯一入口是 CLI。v6 开始交付层:把核心能力封装为 **MCP server**,任何支持 MCP 的 Agent(Claude Code、Claude Desktop 等)都能在对话里直接调用——同时兑现最初愿景中的「Skill 封装」与「聊天界面」(在 Claude 里聊天即用)。

### v6 成功标准

1. 新命令 `psyteardown-mcp` 启动 stdio MCP server,暴露 6 个工具:`teardown`、`similar`、`review_case`、`kb_list`、`kb_show`、`memory_stats`。
2. `claude mcp add psyteardown -- psyteardown-mcp` 一条命令接入 Claude Code;对话中"帮我拆解这个产品"即可触发。
3. 配置零新增概念:复用现有环境变量(`PSYTEARDOWN_LLM`、`DEEPSEEK_*`、`ANTHROPIC_API_KEY`、`PSYTEARDOWN_EMBED`、`OLLAMA_HOST`),新增 `PSYTEARDOWN_STORE`(案例库路径,默认 `.psyteardown/cases.db` 与 CLI 一致)。
4. server 层零业务逻辑(与 CLI 同为薄壳);工具函数离线可测(FakeProvider 注入,不启动 MCP server)。
5. 错误以清晰文本返回(MCP 工具错误),不裸抛堆栈。
6. 提取 CLI analyze 的编排逻辑为共享函数,CLI 与 MCP 共用;既有 CLI 测试全部不动、必须全绿(行为回归锁)。

### 明确不做(YAGNI,后置)

- learn/strategize/candidates/strategies 审批类工具(低频管理操作留在 CLI,人工把关不进聊天)
- HTTP/streamable-http 传输、鉴权、多用户(v7 HTTP API 时统一考虑)
- MCP resources/prompts 能力(只用 tools)
- 异步任务、进度通知(拆解 3–15 分钟,同步等待;MCP 客户端超时可配)
- teardown 的 no_save 参数(对话场景积累案例正是价值;补救靠 CLI)

---

## 2. 关键决策(已确认)

| 维度 | 决策 |
|------|------|
| v6 入口 | MCP/Skill 封装(HTTP API、独立聊天界面后置 v7+) |
| 工具粒度 | 核心 6 工具;管理操作留 CLI |
| LLM 调用方 | 工具内部自带 LLM(现有 provider 管道);不用 MCP sampling |
| 长任务 | 同步等待返回完整结果(零状态);不做异步任务 |
| SDK / 传输 | 官方 `mcp` python SDK + FastMCP 装饰器 API + stdio 传输 |
| 返回格式 | 一律人类可读文本/Markdown(结构化 JSON 留给 v7 HTTP API) |

---

## 3. 架构

```
src/psyteardown/
├── mcp_server/                  # 新:MCP 交付层(与 cli.py 平级的薄壳)
│   ├── __init__.py
│   ├── tools.py                 # 6 个工具的纯函数实现(可注入 provider,离线可测)
│   └── server.py                # FastMCP 装配:注册工具 + main() 入口(stdio)
├── cli.py                       # 改:analyze 编排改调 tools.py 共享函数
└── ...                          # 内核(kb/pipeline/llm/embed/memory/growth/strategy/review)全部不动
```

### 关键设计点

- **tools.py 与 server.py 分离**:`tools.py` 是普通同步函数,依赖(LLM provider、嵌入 provider、store 路径)全部参数可注入——测试用 Fake,不需要 MCP 运行时。`server.py` 只做 `@mcp.tool()` 注册 + 从环境变量组装依赖,零业务逻辑。
- **复用而非复制**:CLI `analyze` 命令体内的编排(构建记忆→prior_summary→策略卡→run_teardown→自评→渲染→落盘)提取为 `tools.py` 的共享编排函数;CLI 与 MCP 都调它。提取保持行为逐字节一致,以既有 CLI 测试全绿为回归锁。这同时化解了 v5 评审指出的"analyze 函数逼近提取阈值"。
- **依赖与入口**:`pyproject.toml` 新增可选 extra `mcp = ["mcp"]`;console script `psyteardown-mcp = "psyteardown.mcp_server.server:main"`。未装 mcp 包时运行 `psyteardown-mcp` 给清晰安装提示;核心包 import 不受影响(mcp 只在 server.py 里 import)。
- **store 解析**:`PSYTEARDOWN_STORE` 环境变量,默认 `.psyteardown/cases.db`。MCP server 为长驻进程、工作目录由客户端决定,README 明确建议配绝对路径。

### 数据流(以 teardown 为例)

```
Claude 对话 → MCP tools/call → server.py(env → provider/embed/store)
  → tools.run_teardown_tool()      ← CLI analyze 调同一函数
      → 内核 run_teardown → 自评(可选) → 落盘 → render_markdown
  → 返回 Markdown → Claude 呈现给用户
```

---

## 4. 工具契约

docstring 即 Agent 可见的工具说明,用中文写明何时该用。

| 工具 | 参数 | 返回 |
|---|---|---|
| `teardown` | `description: str`(产品文字描述,必填)、`use_memory: bool=False`、`use_strategies: bool=False`、`self_review: bool=False` | 完整 Markdown 报告(含自评节若开);末尾附「已落盘案例 \<id\>」或降级提示 |
| `similar` | `description: str`、`top_k: int=3` | 文本列表:`分数 产品名 — 一句话(框架)`;空库返回提示文本 |
| `review_case` | `case_id: str` | 自评摘要文本(评分/缺陷/建议);不存在 → 错误文本 |
| `kb_list` | 无 | `id\t名称\t(类别)` 列表(含已批准习得框架) |
| `kb_show` | `framework_id: str` | 框架详情(摘要 + 原则 + 线索);不存在 → 错误文本 |
| `memory_stats` | 无 | `案例数:N` |

### 行为细节

- `teardown` 空描述 → 错误文本「输入为空」;记忆/自评失败 → 优雅降级,提示追加在返回文本末尾(与 CLI stderr 提示同文案)。
- `review_case` 复用 v5 语义:覆盖旧自评、保留向量;LLM 失败 → 错误文本(用户显式要求,不静默)。**不含 --to-reflect**(策略蒸馏属管理操作,留 CLI)。
- `similar`/`teardown --use-memory` 的嵌入维度不匹配(换嵌入模型后旧库)→ 返回既有 MemoryStoreError 的清晰信息。

---

## 5. 测试策略(TDD,全部离线)

- `tools.py`:每工具正常路径 + 边界(空描述、空库、不存在 id);teardown 降级路径(monkeypatch 炸嵌入构建);FakeProvider/FakeEmbeddingProvider + tmp store。
- **CLI 回归锁**:提取共享编排后,`tests/test_cli*.py` 全部不动、必须全绿。
- `server.py`:未装 mcp → `psyteardown-mcp` 报清晰安装提示(monkeypatch import);已装时注册工具数 = 6(读 FastMCP 注册表,不起进程)。不做 MCP 协议级 e2e(SDK 自身已测)。
- 真实接入验证(手动,非测试套件):实现后在 Claude Code 里 `claude mcp add` 实际试用一次 teardown + kb_list。

---

## 6. README 变更

新增「MCP 接入(Claude Code / Claude Desktop)」一节:

- 安装:`pip install -e ".[mcp]"`
- Claude Code:`claude mcp add psyteardown -e PSYTEARDOWN_LLM=deepseek -e DEEPSEEK_API_KEY=... -e PSYTEARDOWN_EMBED=ollama -e PSYTEARDOWN_STORE=<绝对路径> -- psyteardown-mcp`
- Claude Desktop:`claude_desktop_config.json` 配置示例(command + env)
- 说明:管理操作(learn/strategize/审批)仍走 CLI。

---

## 7. 接口预留(v7+)

- FastMCP 切 streamable-http 传输仅一参数之差 → v7 HTTP API 可基于同一 tools.py。
- tools.py 的纯函数契约即未来 HTTP handler 的直接素材。
- 结构化返回(JSON)在 v7 加 `fmt` 参数或独立端点,不动本版文本契约。
