# psyteardown — 心理驱动型产品拆解 Agent(v6)

基于精选心理学框架知识库,把产品文字描述拆解成结构化报告(Markdown / JSON)。
含三层记忆:v2 情景记忆(案例库 + 向量检索)、v3 语义记忆(框架知识增长)、
v4 程序性记忆(拆解策略卡)。v5 元认知自评(单案例自评 + 策略闭环)。v6 交付层(MCP server,Claude 对话中直接调用)。

## 安装

    pip install -e ".[dev]"
    pip install -e ".[embed]"   # 可选:启用向量检索(本地嵌入模型,首次会下载)

## MCP 接入(Claude Code / Claude Desktop)

    pip install -e ".[mcp]"

Claude Code 一条命令接入(环境变量按需增减;store 建议绝对路径):

    claude mcp add psyteardown \
      -e PSYTEARDOWN_LLM=deepseek -e DEEPSEEK_API_KEY=sk-... \
      -e PSYTEARDOWN_EMBED=ollama \
      -e PSYTEARDOWN_STORE=D:/app/app-mental/.psyteardown/cases.db \
      -- psyteardown-mcp

Claude Desktop 在 `claude_desktop_config.json` 的 `mcpServers` 里加:

    "psyteardown": {
      "command": "psyteardown-mcp",
      "env": { "PSYTEARDOWN_LLM": "deepseek", "DEEPSEEK_API_KEY": "sk-...",
               "PSYTEARDOWN_EMBED": "ollama",
               "PSYTEARDOWN_STORE": "D:/app/app-mental/.psyteardown/cases.db" }
    }

对话中即可说「帮我拆解这个产品:……」触发 teardown 工具。
暴露工具:teardown / similar / review_case / kb_list / kb_show / memory_stats。
管理操作(learn / strategize / candidates / strategies 审批)仍走 CLI。

## 用法

    export ANTHROPIC_API_KEY=sk-ant-...
    # 或用 DeepSeek:export DEEPSEEK_API_KEY=sk-... && export PSYTEARDOWN_LLM=deepseek
    #(模型默认 deepseek-chat,可用 DEEPSEEK_MODEL / DEEPSEEK_BASE_URL 覆盖)
    psyteardown analyze --input product.txt --format md  --out report.md
    psyteardown analyze --input product.txt --use-memory          # 注入相似历史案例
    psyteardown analyze --input product.txt --no-save             # 不落盘
    psyteardown similar --input product.txt --top-k 3             # 查相似历史案例
    psyteardown memory stats                                      # 案例库统计
    psyteardown learn                                            # 从案例提炼候选新框架(待审)
    psyteardown candidates list                                  # 列候选
    psyteardown candidates show <id>                             # 看候选详情
    psyteardown candidates approve <id>                          # 批准入库(此后 analyze 生效)
    psyteardown candidates reject <id>                           # 驳回
    psyteardown strategize                                       # 从案例归纳候选策略卡(待审)
    psyteardown reflect --note "社交产品别漏社交证明"             # 复盘蒸馏成候选策略卡
    psyteardown strategies list                                  # 列候选策略卡
    psyteardown strategies show <id>                             # 看详情
    psyteardown strategies approve <id>                          # 批准
    psyteardown strategies reject <id>                           # 驳回
    psyteardown analyze --input product.txt --use-strategies     # 注入已批准策略卡(默认关)
    psyteardown analyze --input product.txt --self-review         # 拆解后追加 LLM 自评(默认关)
    psyteardown review <case_id>                                  # 历史案例补评(覆盖旧自评)
    psyteardown review <case_id> --to-reflect                     # 补评 + 建议直达策略候选
    psyteardown kb list
    psyteardown kb show fogg-behavior-model

案例库默认存于 `./.psyteardown/cases.db`(可用 `--store` 覆盖)。
向量检索默认用本地嵌入模型(需 `pip install -e ".[embed]"`,首次会下载模型);
也可用本地 Ollama 嵌入(零下载,推荐已装 Ollama 者):`set PSYTEARDOWN_EMBED=ollama`
(默认模型 `bge-m3:567m`,服务地址可用 `OLLAMA_HOST` 覆盖);
若嵌入模型不可用(如离线),`analyze` 会跳过案例库并照常产出报告,不会失败。

## 测试

    pytest                       # 全量(冒烟测试默认跳过,不触网、不加载模型)
    PSYTEARDOWN_E2E=1 pytest      # 含真实 Claude + 本地嵌入冒烟

## 架构

- `kb` — 知识库(精选心理学框架,YAML)
- `pipeline` — 5 步拆解流水线
- `llm` — 可插拔 LLM provider(默认 Claude;可选 DeepSeek)
- `report` — Markdown / JSON 渲染
- `embed` — 可插拔嵌入 provider(默认本地 sentence-transformers;可选 Ollama)
- `memory` — 情景记忆:Case 模型、SQLite 案例库、向量检索
- `growth` — 语义记忆:从案例提炼候选新框架,人工审批后回填知识库(种子库永不被动)
- `strategy` — 程序性记忆:从案例/复盘归纳拆解策略卡,人工审批后按步骤注入拆解流程
- `review` — 元认知自评:拆解后批判性质量自评,信号回流 strategize / reflect
- `mcp_server` — 交付层:MCP server(FastMCP/stdio),6 工具;与 CLI 共享编排

CLI 仅为薄入口。设计与规划见 `docs/superpowers/specs/`(v1–v4 设计文档)。
