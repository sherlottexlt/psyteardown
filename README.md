# psyteardown — 体验假设与验证 Agent

psyteardown 把产品或设计候选中的可观察事实，连接到人的动作与使用情境、心理机制假设、体验风险、设计修改和验证实验，输出可追溯的 Markdown / JSON 结果。

项目从“心理驱动的产品拆解 Agent”逐步扩展为“产品体验假设与验证系统”，当前同时支持文本拆解和结构化体验设计 vertical slice。

核心原则：观察、解释、预测和验证分开；AI 可以提议，但不能自行批准；Blender/渲染图可以帮助讨论，但不能冒充样机证据。

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

    # 体验设计 / 参数化迭代（拥挤通勤腕戴伴行器示例）
    psyteardown design --input examples/design-request.json --db output/experience/future-wearable.db --out output/experience/future-wearable.md
    psyteardown design-export-request --db output/experience/future-wearable.db --candidate-revision <candidate-revision> --out output/experience/design-tool-request.json
    psyteardown design-attach --provider blender --db output/experience/future-wearable.db --candidate-revision <candidate-revision> --out output/experience/blender-draft.md
    psyteardown design-review --db output/experience/future-wearable.db --run-id <design-tool-run-id> --out output/experience/blender-confirmed.md
    # patches.json 可为 VariablePatch 数组；先生成子候选，再重新生成 blockout
    psyteardown design-iterate --db output/experience/future-wearable.db --candidate-revision <parent-revision> --patches patches.json --provider blender --out output/experience/iteration.md
    psyteardown design-portfolio --db output/experience/future-wearable.db --model-id <model-id> --format md --out docs/portfolio/transit-anchor.md
    psyteardown design-portfolio --db output/experience/future-wearable.db --model-id <model-id> --format json --out docs/portfolio/transit-anchor.json
    # 无真实样机时运行一阶物理预检（数值是假设/估算，永远不是 evidence）
    psyteardown virtual-validate --input examples/transit-anchor-round2-virtual-validation-input.json --out output/experience/transit-anchor-strap-release-r1/virtual-validation-r1.md
    psyteardown scenario-replay --policy output/experience/transit-anchor-strap-release-r1/scenario-policy-r2-replay.json --input examples/transit-anchor-round2-scenario-replay.json --out output/experience/transit-anchor-strap-release-r1/scenario-replay-r2.md
    # 实体样机完成后才填写并导入；模板中的 REPLACE_ME / YYYYMMDD 会被拒绝
    psyteardown prototype-import --db output/experience/future-wearable.db --run run.json --observations observations.json
    psyteardown prototype-review --db output/experience/future-wearable.db --run-id <run-id> --observation <observation-id> --evidence-level observed

参数化迭代不会把渲染图当作人体工学证据：旧 render/geometry 层会重置为 missing，provider 结果默认为 draft，只有 `--confirm` 才推进层级。形态与验证边界见 [`Transit Anchor wrist companion`](docs/design/2026-09-12-transit-anchor-wrist-companion.md)。

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
- `experience` — 结构化体验设计与验证域：DesignBrief、候选、评审、变量迭代、场景策略、实验规划、样机证据、revision/audit

CLI 仅为薄入口。完整设计、架构决策和交接记录见 `docs/superpowers/`、`docs/adr/` 和 `docs/handoff/`。

## 当前状态

### 已完成

- 文本拆解：5 步流水线、8 个心理学框架/29 条原则、案例记忆、向量检索、策略卡、人工审批、MCP 交付层。
- 可信度护栏：Schema 校验、置信度、失败记录、step3 原文 evidence grounding、未溯源 mapping 记账。
- 体验平台 M1：通用 `Evidence` / `Observation` / `ExperienceHypothesis` / `Critique`，确定性 claim 检查、SQLite revision 持久化和研究对象 CLI。
- 体验平台 M2 第一切片：实验变量、测量、样本、停止条件、预注册计划和导出；不会伪造实验结果。
- 体验平台 M3 第一切片：多候选生成、候选 Critique、确定性排序、人工选择和下一轮 prompt。
- Transit Anchor vertical slice：场景策略、参数化 `VariablePatch`、Blender blockout、多视角 review、虚拟预检、scenario replay、portfolio 投影和样机证据导入/人工复核模型。

### 当前边界

- Transit Anchor 当前为 `geometry_ready / design-review confirmed / physical validation pending`。
- 目前 `PrototypeRun=0`、`MeasurementObservation=0`、`EvidenceReview=0`，`evidence level=none`。
- Blender、GLB、PNG 和 virtual preflight 都是 derived/design material，不证明尺寸、舒适度、触觉检出率、稳定性、隐私结果或用户偏好。
- 尚未接入真实视觉/视频观察模型、真实设计生成模型、CAD/工程系统、实体样机数据和 Web 工作台。

### 下一步路线

1. 完成真实样机测量与人工 EvidenceReview，更新 validation status。
2. 将 M3 选择结果接入完整 `DesignIteration` / `SelectionDecision` revision 链和确认后的 VariablePatch。
3. 补齐 M2 的 `HypothesisBinding` / `AnalysisFamily`、条件快照和实验结果导入前的 analysis gate。
4. 再接入图片/短视频观察、真实设计 provider 和可选的 Experience MCP/HTTP 工作台。

## 仓库范围

仓库提交源代码、测试、知识库、示例输入、架构决策、设计规格和 field-test 文本结果。以下内容默认只保留在本地，不上传：个人简历和求职材料、PDF/PNG 等导出物、Blender/GLB/BLEND 运行目录、SQLite 运行数据库、临时文件和简历生成脚本。

## 后续方向

项目后续不止于文本产品心理拆解，计划发展为服务 AI 设计闭环的“心理驱动的产品体验拆解与验证系统”：把 AI 生成候选的物理特征、人的动作和使用情境转译为可追溯的体验假设，输出风险、权衡和下一轮可操作的设计修改，并生成可执行的验证实验。完整定位、领域模型、分阶段实现计划与验收标准见 [`2026-09-08-psyteardown-future-direction-and-implementation-plan.md`](docs/superpowers/specs/2026-09-08-psyteardown-future-direction-and-implementation-plan.md)。
