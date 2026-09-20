# psyteardown — AI Product Studio（开发中）

长期目标是让用户从一个不完整愿望或现实困扰出发，获得可运行、可验证并可持续演化的产品。完整方向见 [AI Product Studio 北极星](docs/superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md)，开发交接从 [Product Studio 开发台账](docs/product-studio/README.md) 开始。

当前**可使用的部分仍是可信研发内核**：文本拆解、结构化体验研究、设计反馈及工程验证边界。新 Product Studio 的领域与持久化代码目前只是已测试原型；Web 工作空间和从模糊意图生成可运行产品的闭环尚未完成。

继续开发前先看 [当前状态](docs/product-studio/CURRENT_STATE.md)、[路线图](docs/product-studio/ROADMAP.md) 和 [决策登记册](docs/product-studio/DECISION_REGISTER.md)。旧 ADR 仅在原体验/工程内核范围内有效，不自动成为新平台决策。

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
暴露工具:teardown / similar / review_case / kb_list / kb_show / memory_stats / engineering_status / engineering_traceability。
工程体验库读取工具:engineering_status / engineering_traceability（只读）。
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

    # App/数字服务拆解 → Discovery 分流；不会直接生成硬件工程要求
    psyteardown discovery import-teardown --db experience.db --input teardown-result.json --discovery-id app-discovery-001
    psyteardown discovery triage --db experience.db --discovery-id app-discovery-001 --decisions triage-decisions.json --reviewer experience-lead-li --rationale "确认 App、跨端和设备交互边界"
    psyteardown discovery project-to-engineering --db experience.db --discovery-id app-discovery-001 --project-id wearable-project --scenario "walking in shared transit" --target-segment "consented adult commuters"

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
- `mcp_server` — 交付层:MCP server(FastMCP/stdio),8 个工具;与 CLI 共享编排
- `experience` — 结构化体验、Discovery 与工程协同域：数字体验发现、DesignBrief、候选、实验、样机证据、工程对象、依赖失效、人工 gate、制造/法规和跨案例知识
- `product` — ProductIntent、ProblemModel、OutcomeContract、ProductThesis 与项目应用服务的探索性原型；字段、确认门和持久化边界待验证
- `api` — FastAPI `/api/v1` 草稿，A3 已暂停；当前环境存在 FastAPI/Starlette 版本冲突，尚未通过启动或 HTTP 集成测试

现有 CLI 仍是旧内核的薄入口。新平台方向见 `docs/superpowers/specs/`，开发状态与历史见 `docs/product-studio/`；`docs/adr/` 是既有内核的历史决策记录，不应直接用于锁定新平台的领域模型。

## 当前状态

### 已完成

- 文本拆解：5 步流水线、8 个心理学框架/29 条原则、案例记忆、向量检索、策略卡、人工审批、MCP 交付层。
- 可信度护栏：Schema 校验、置信度、失败记录、step3 原文 evidence grounding、未溯源 mapping 记账。
- 体验平台 M1：通用 `Evidence` / `Observation` / `ExperienceHypothesis` / `Critique`，确定性 claim 检查、SQLite revision 持久化和研究对象 CLI。
- 体验平台 M2 第一切片：实验变量、测量、样本、停止条件、预注册计划和导出；不会伪造实验结果。
- 体验平台 M3 第一切片：多候选生成、候选 Critique、确定性排序、人工选择和下一轮 prompt。
- Transit Anchor vertical slice：场景策略、参数化 `VariablePatch`、Blender blockout、多视角 review、虚拟预检、scenario replay、portfolio 投影和样机证据导入/人工复核模型。
- 工程协同 P0：正式工程对象、SQLite registry、统一 revision dependency graph、自动 stale/invalidation 传播、并行角色任务和逐级人工状态门。
- 多模态 P1：图片区域、视频时间段、缺失模态显式降级，以及未校准媒体不能生成尺寸/压力/强度/舒适度事实的确定性边界。
- 验证回流 P2：`PrototypeRun → MeasurementObservation → EvidenceReview` 与 `ConditionSnapshot / AnalysisFamily / HypothesisBinding` 的完整 lineage；analysis protocol gate 通过后才允许创建新的 hypothesis revision。
- 工具适配 P3：CAD/CAE/DFM/BOM 固定请求、原始结果、AI 解释与人工审查分离；上游输入变化自动使结果过期。
- 质量与知识 P4/P5：DVP&R、FMEA、试产良率、法规/可靠性、制造准备、发布、工程/供应商/售后变更，以及人工批准后才能进入默认查询的跨案例工程知识。
- Discovery 边界：App/数字服务拆解先进入 `DigitalExperienceDiscovery`，再由具名 reviewer 通过 `DiscoveryTriageDecision` 逐条分流；只有设备交互候选可以进入工程 intake。

### Product Studio 开发状态

- A1/A2：四个上位对象、项目命令、乐观并发及 InMemory/SQLite 持久化有测试覆盖，状态是 `prototype tested`，不是已确认的最终架构。
- A3：FastAPI 路由与 DTO 已有草稿，但当前环境的 FastAPI 0.115.6 与 Starlette 1.3.1 组合在启动时失败；尚无 HTTP 集成测试，工作包已暂停。
- 首条纵向切片的具体用户与问题尚未决定。需先用真实任务检验 A1/A2 的最小字段和人工确认边界，再恢复 A3、建设 Web 工作台。

### 当前边界

- Transit Anchor 当前为 `geometry_ready / design-review confirmed / physical validation pending`。
- 目前 `PrototypeRun=0`、`MeasurementObservation=0`、`EvidenceReview=0`，`evidence level=none`。
- Blender、GLB、PNG 和 virtual preflight 都是 derived/design material，不证明尺寸、舒适度、触觉检出率、稳定性、隐私结果或用户偏好。
- 已具备视觉/视频观察、CAD/CAE/DFM/BOM 的适配与审查边界，但尚未配置真实多模态模型、真实工程工具连接、实体样机数据、认证实验室或 Product Studio Web 工作台。
- 工程对象处于平台能力层；没有真实原始结果、具名 reviewer 和完整 gate 时，系统不会宣称可制造、合规、量产或发布。

### 下一步路线

1. 选定首条数字产品的具体用户和现实问题，用它校准 A1/A2 原型的字段、人工确认门槛与旧内核衔接；不以旧 ADR 的 `accepted` 状态代替新决策。
2. 解决 FastAPI/Starlette 版本冲突，验证 A3 HTTP 契约与 SQLite 重启恢复后再恢复 API 开发。
3. 建立 React/TypeScript Product Studio，走通“模糊意图 → Product Contract → 多个 Product Thesis → 可运行 Web 产品 → 自动测试与修复 → 用户反馈 → 导出”的真实闭环。
4. 保留体验与工程链作为可信研发内核；Transit Anchor 仅是后续硬件 pack 案例，其证据等级须由真实样机、测量和具名 `EvidenceReview` 推进。

### 工程项目 CLI

```powershell
psyteardown engineering-init --db engineering.db --input examples/engineering-intake.json
psyteardown engineering-requirements-review --db engineering.db --project-id wearable-project --reviewer system-engineer-li --rationale "来源和验收条件已复核"
psyteardown engineering-status --db engineering.db --project-id wearable-project
psyteardown engineering-traceability --db engineering.db --project-id wearable-project --format md --out traceability.md
```

App/数字服务拆解不会直接生成硬件工程需求。推荐使用分域 Discovery CLI：

```powershell
psyteardown discovery import-teardown --db experience.db --input teardown-result.json --discovery-id app-discovery-001
psyteardown discovery triage --db experience.db --discovery-id app-discovery-001 --decisions triage-decisions.json --reviewer experience-lead-li --rationale "逐条确认 App、跨端和设备交互边界"
psyteardown discovery project-to-engineering --db experience.db --discovery-id app-discovery-001 --project-id wearable-project --scenario "walking in shared transit" --target-segment "consented adult commuters"
```

拆解首先保存为 `DigitalExperienceDiscovery`，每条信号必须由具名 reviewer 分流；只有 `device_interaction_candidate` 才能进入工程域，而且只生成 `explore`/`draft` 候选。旧的 `engineering-init-from-teardown` 仅作为迁移兼容命令保留，不应用于新项目。

`engineering-gate-review` 接收 `DependencyRef` JSON 数组作为 `--evidence`。Gate 必须逐级推进，AI 默认需求在人工确认前保持 `draft`，任何未批准规律都不会进入默认工程知识查询。

MCP 工程读取工具默认与 `PSYTEARDOWN_STORE` 共享数据库；可用 `PSYTEARDOWN_EXPERIENCE_STORE` 单独指定体验/工程 SQLite 文件。这两个工具只返回状态和追溯投影，不执行工程软件，也不能审批任何 gate。Typer CLI 继续用于可复现的本地批处理、导入导出和具名审查；MCP 用于对话式只读查询与草稿建议；多人逐条分流和 Gate 审批适合后续复用同一 Coordinator 的 Web/API 工作台。

## 仓库范围

仓库提交源代码、测试、知识库、示例输入、架构决策、设计规格和 field-test 文本结果。以下内容默认只保留在本地，不上传：个人简历和求职材料、PDF/PNG 等导出物、Blender/GLB/BLEND 运行目录、SQLite 运行数据库、临时文件和简历生成脚本。

## 后续方向

项目的上位方向是面向个人与企业的 AI Product Studio：用户可以从一个不完整愿望、现实问题、商业目标或进行中的项目开始，平台承担大部分研究、方案搜索、设计、实现、测试和修复工作，最终交付可运行产品以及与关键声明绑定的证据、未知和风险。用户产品形态、交互模式、心理学位置、技术架构和第一条纵向切片见 [`2026-09-20-psyteardown-ai-product-studio-north-star.md`](docs/superpowers/specs/2026-09-20-psyteardown-ai-product-studio-north-star.md)。

现有“产品 Discovery → 体验假设 → 设计反馈 → 工程验证”能力作为可信研发内核继续保留。App/数字服务拆解先产生 `DigitalExperienceDiscovery` 和待分流信号，不能直接成为机械、材料、制造或法规结论。当前实现基线、领域对象、CLI/MCP 边界与工程验收标准见 [`2026-09-08-psyteardown-future-direction-and-implementation-plan.md`](docs/superpowers/specs/2026-09-08-psyteardown-future-direction-and-implementation-plan.md)。

### 当前验证状态

```text
438 passed, 2 skipped, 1 warning（A1/A2 有覆盖；A3 API 未通过启动/HTTP 测试）
```

当前 Transit Anchor 仍为 `geometry_ready / design-review confirmed / physical validation pending`；`PrototypeRun=0`、`MeasurementObservation=0`、`EvidenceReview=0`、`evidence level=none`。因此仓库中的 Blender、GLB、PNG、virtual preflight 和 scenario replay 仍是设计/策略材料，不是样机、认证或制造证据。
