# psyteardown 后续方向与完整实现计划

- 初始日期：2026-09-08
- 本次更新：2026-09-18
- 状态：当前架构与后续实施主文档
- 适用范围：从 App/数字服务产品拆解，发展为带体验研究、AI 设计反馈和工程验证边界的协同研发平台

## 0. 当前一句话结论

psyteardown 不是一个“替用户读懂心理”或“自动评价产品好坏”的模型，而是一套把数字产品发现、体验假设、设计候选、工程对象和真实验证连接起来的可追溯系统。

当前正确的分层是：

```text
App / 数字服务描述
  → 原产品拆解（Discovery）
  → DigitalExperienceDiscovery
  → 具名人员逐条分流
  ├─ App 体验问题
  ├─ 跨端验证问题
  ├─ 设备交互候选
  ├─ 延后
  └─ 驳回
        ↓ 仅设备交互候选
Experience / Design / Engineering Intake
  → 多候选设计与工程对象
  → CAD / CAE / DFM / BOM / 样机 / 测量
  → EvidenceReview 与质量 Gate
  → 下一轮变更和经过审批的知识
```

原始产品拆解仍然重要，但它属于 App/数字服务的 Discovery 层，不能直接生成机械、材料、制造、法规或发布结论。

---

## 1. 定位、边界与不做什么

### 1.1 产品定位

推荐名称：

> psyteardown — Product Experience Discovery and Verification Platform

中文描述：

> 面向数字产品、移动交互与穿戴设备研发的体验发现、假设验证和工程协同平台。

系统的长期价值不在于使用哪一个大模型，而在于维护以下中间语言：

```text
产品/服务事实
  → 用户动作与使用情境
  → 体验风险和机制假设
  → 验证问题与可操作变量
  → 设计候选和工程对象
  → 原始测试证据与具名决策
```

### 1.2 明确分层

| 层 | 主要对象 | 可以回答 | 不能声称 |
|---|---|---|---|
| Discovery | `TeardownResult`、`DigitalExperienceDiscovery`、`DigitalExperienceSignal` | App/数字服务有哪些功能、触点、摩擦、机会和伦理信号 | 硬件要求、物理性能、用户普遍偏好 |
| Experience | `Evidence`、`Observation`、`ExperienceHypothesis`、`Critique`、`ExperimentPlan` | 在特定场景下有哪些体验假设和验证问题 | 因果规律已被证明 |
| Design | `DesignBrief`、`DesignCandidate`、`VariablePatch`、`DesignIteration` | 多方案如何比较、哪些变量值得下一轮修改 | 一个综合心理分数代表最佳方案 |
| Engineering | `EngineeringRequirement`、CAD/BOM/CAE/DFM、任务和依赖图 | 工程对象、接口、工具结果和过期传播 | AI 单独批准可制造、可靠、合规或量产 |
| Quality | FMEA、DVP&R、样机、EvidenceReview、MRR、ReleaseDecision | 验证、质量、法规、制造准备和发布状态 | 没有原始证据时放行 |

### 1.3 明确不做

- 不从一张图片推断情绪、人格、健康状态或真实尺寸。
- 不把 App 的心理学拆解自动套成物理产品需求。
- 不用 Blender、GLB、PNG、虚拟预检或场景 replay 代替样机和实验室证据。
- 不用单一“心理学总分”排序设计。
- 不让 AI 自动批准需求、实验、质量、法规、制造或发布 Gate。
- 不让未审批的规律进入默认知识检索或设计排序。
- 不把跨案例相关性包装成普遍因果规律。

---

## 2. 当前已实现基线（截至 2026-09-18）

### 2.1 原始 App/数字产品拆解

已实现：

- 五步流水线：产品解析、框架检索、功能/触点映射、体验评估、摘要。
- 心理学知识库、引用、step3 原文 grounding 和未溯源映射记账。
- Fake/真实 LLM provider、embedding、案例记忆、策略卡、自评和 MCP 文本工具。
- Markdown/JSON 输出、CLI `analyze` 和原有案例管理命令。

这些结果是 Discovery 输入，不是硬件工程事实。

### 2.2 M1/M2/M3 体验研究与设计反馈

已实现：

- `Evidence`、`Observation`、`ExperienceHypothesis`、`Critique`。
- 实验变量、条件快照、分析族、预注册和 analysis protocol gate。
- `DesignBrief`、`DesignCandidate`、`VariablePatch`、parent/child revision。
- 多候选生成、风险/未知筛选、确定性排序、人工选择和下一轮 prompt。
- SQLite revision、domain events、audit events 和人工审批边界。

### 2.3 多模态和样机证据边界

已实现：

- `ExternalAsset → ObservationDraft → 人工确认/修改/驳回`。
- 图片区域、视频时间段、校准状态和来源定位。
- 缺失模态降级为 `unknown`/`not_observable`。
- 未校准媒体不能建立尺寸；设计派生媒体不能建立压力、强度、舒适度或物理测量事实。
- `PrototypeRun → MeasurementObservation → EvidenceReview`。
- EvidenceReview 与 `ConditionSnapshot`、`AnalysisFamily`、`HypothesisBinding` 的 lineage。

### 2.4 工程协同 P0–P5

已实现：

- 正式工程对象：需求、机械架构、材料工艺、CAD、BOM、公差、CAE、DFM、FMEA、DVP&R、验证、试产、法规、MRR、发布、变更和售后问题。
- 统一 registry、revision graph、dependency graph、stale/invalidation 传播。
- 角色任务、依赖检查、冲突分类、逐级人工状态门。
- CAD/CAE/DFM/BOM 工具请求、原始工具结果、AI 解释和人审投影分离。
- 质量/发布 Gate 和跨案例知识候选，未审批知识不会进入默认知识。

### 2.5 Discovery 与工程边界（最新）

已实现：

- `DigitalExperienceDiscovery`：保存 App/数字服务拆解快照。
- `DigitalExperienceSignal`：保存 friction、ethics、opportunity 信号。
- `DiscoveryTriageDecision`：具名 reviewer 逐条路由为 App、跨端、设备交互、延后或驳回。
- `discovery import-teardown`、`discovery triage`、`discovery project-to-engineering`。
- 只有人工路由的 `device_interaction_candidate` 才能进入工程 intake。
- 投影结果仍是 `explore`/`draft`，不会自动成为硬约束。
- 旧 `engineering-init-from-teardown` 仅隐藏保留作迁移兼容，不作为新项目路径。

### 2.6 当前验证与真实边界

当前全量离线测试：

```text
406 passed, 2 skipped
```

Transit Anchor 当前仍为：

```text
geometry_ready / design-review confirmed / physical validation pending
PrototypeRun = 0
MeasurementObservation = 0
EvidenceReview = 0
evidence level = none
```

尚未拥有的不是本地模型，而是真实外部资源：实体样机、测量设备、参与者、真实 CAD/CAE/DFM/BOM 工具、供应商/成本数据、认证实验室和多人 Web 工作台。

---

## 3. 核心数据流与对象关系

### 3.1 Discovery 到工程的安全路径

```text
TeardownResult
  ├─ product profile / App features / touchpoints
  ├─ mappings / grounding stats
  └─ assessment: friction / ethics / opportunities
        ↓
DigitalExperienceDiscovery
  └─ DigitalExperienceSignal[]
        ↓ named human triage
DiscoveryTriageDecision[]
  ├─ app_experience
  ├─ cross_channel_validation
  ├─ device_interaction_candidate
  ├─ deferred
  └─ rejected
        ↓ only device interaction candidates
EngineeringIntake(status=draft)
        ↓ system-engineering review
EngineeringRequirement(status=draft, type=explore)
```

### 3.2 工程依赖图

```text
EngineeringRequirement
  ↓
DesignCandidate / MechanicalArchitecture / MaterialProcessChoice
  ↓
CADArtifact
  ├── BOMRevision
  ├── ToleranceStack
  ├── CAEAnalysisRun
  └── DFMReview
          ↓
VerificationTestRun / PrototypeRun
          ↓
MeasurementObservation / EvidenceReview
          ↓
FMEARevision / DVPRevision / ReleaseDecision
```

### 3.3 所有正式对象的最低 provenance

每个 revision 至少包含：

- `revision_id`、`parent_revision_id`。
- 创建者、时间、工具/模型版本和创建理由。
- 输入依赖和依赖 revision。
- 原始资产、测量或工具结果位置。
- 假设、未知、适用条件和失效条件。
- reviewer、决定、理由和时间。
- 当前状态以及 stale/invalidated 原因。

---

## 4. CLI、MCP 与未来 Web/API

### 4.1 CLI 决策

保留 Typer，不立即替换为 FastAPI 或 Web。CLI 适合：

- 本地批处理和 JSON 导入导出。
- CI、迁移、回放和可复现实验。
- 具名 reviewer 发起的审查命令。
- 无需常驻服务的 SQLite 工作流。

命令按领域演进：

```text
psyteardown
├── teardown       # App/数字服务拆解与案例记忆
├── discovery      # 拆解导入、信号分流、跨端投影
├── experience     # M1/M2/M3、假设、实验、证据
├── design         # 候选、派生资产和迭代
├── engineering    # 需求、依赖、工具和 Gate
├── quality        # FMEA、制造准备和发布
├── memory         # 案例与向量检索
└── strategies     # 策略卡与人工审批
```

当前推荐：

```powershell
psyteardown discovery import-teardown --db experience.db --input teardown-result.json --discovery-id app-discovery-001
psyteardown discovery triage --db experience.db --discovery-id app-discovery-001 --decisions triage-decisions.json --reviewer experience-lead-li --rationale "确认 App、跨端和设备交互边界"
psyteardown discovery project-to-engineering --db experience.db --discovery-id app-discovery-001 --project-id wearable-project --scenario "walking in shared transit" --target-segment "consented adult commuters"
```

旧平铺命令继续作为兼容 wrapper；新功能不得再把业务逻辑写进 CLI 入口。

### 4.2 MCP 决策

MCP 适合对话式查询和草稿建议：

- 原始拆解、知识库和案例查询。
- 工程状态和 traceability 只读投影。
- 未来的发现信号解释和下一步任务建议。

MCP 不得自动批准 Gate、写入默认知识或绕过 reviewer。

### 4.3 Web/API 触发条件

只有出现以下需求时才增加 Web/API：

- 多人并发 review 和权限管理。
- 图片/视频逐条区域审查。
- Dependency Graph 可视化。
- Gate 审批、评论、通知和附件管理。
- 供应商、实验室和外部工具的服务端连接。

Web/API 必须复用 Coordinator 和应用服务，不复制 CLI/MCP 业务逻辑。

---

## 5. 后续实现优先级

### P0（本地已完成，保持回归）

- 工程对象 registry 和 SQLite 映射。
- revision/dependency graph。
- stale/invalidation 传播。
- 任务、冲突和逐级人工 Gate。
- M1/M2/M3 依赖入口。

### P1（本地已完成，真实模型尚未配置）

- 多模态观察草稿、图片区域、视频时间段。
- 缺失模态与物理声明边界。
- 人工确认、修改和驳回。

### P2（本地已完成，等待真实样机）

- PrototypeRun、MeasurementObservation、EvidenceReview。
- 真实测量回写假设和下一轮 VariablePatch。
- 正式分析协议 Gate 后的 hypothesis transition。

### P3（适配边界已完成，等待外部工具）

- CAD/CAE/DFM/BOM 请求和原始结果保存。
- 解释与人审分离。
- 输入 revision 改变后的 stale 传播。

### P4/P5（本地 gate 和对象已完成，等待真实证据）

- FMEA、DVP&R、试产、法规、可靠性、MRR、ReleaseDecision。
- 变更单、供应商变更、售后问题回流。
- 跨案例候选知识、冲突/反例/复现和人工批准。

### P6（下一阶段：Discovery/CLI 收敛）

- 将 `cli.py` 拆成 `cli_commands/teardown.py`、`discovery.py`、`experience.py`、`engineering.py` 等薄模块。
- 为 Discovery triage 增加 JSON schema 示例和可复用报告。
- 为 Discovery signal 增加跨端验证问题对象，而不是用长文本承载。
- 将 App-only、cross-channel、device-interaction 三类输出分别接入对应 coordinator。
- 逐步标记旧直连命令 deprecated，并保持迁移测试。

### P7（真实资源闭环）

- 制作 Transit Anchor 实物样机。
- 导入真实传感器/实验室数据。
- 接入至少一个真实 CAD/CAE/DFM/BOM 适配器。
- 让具名工程、测试、质量和法规人员完成首次完整 Gate。
- 在真实使用前不把任何状态标为 released。

### P8（团队交付）

- Web/API review 工作台。
- 统一身份、权限、审计、附件和评论。
- 多项目、供应商和实验室协作。
- 只读 MCP 与可写 Web 操作的权限分层。

---

## 6. 验证与测试计划

### 6.1 当前必须保持的回归

- 原始 App 拆解和案例库行为不回归。
- M1/M2/M3 全量测试通过。
- Transit Anchor 历史 revision 和 evidence level 不被覆盖。
- SQLite revision、domain event、audit event 可重放。
- 工程对象上游变更可以使下游 stale/invalidated。

### 6.2 Discovery 边界测试

- TeardownResult 只生成 `DigitalExperienceDiscovery`，不直接生成工程需求。
- 未完成逐条 triage 时不能投影工程 intake。
- AI reviewer 不能完成 triage。
- 纯 `app_experience` 信号不能进入工程域。
- `cross_channel_validation` 必须有验证问题。
- 只有 `device_interaction_candidate` 能进入工程域。
- 投影出来的需求只能是 `explore + draft + hard_constraint=false`。
- 旧兼容命令必须标明 deprecated，不能成为新文档推荐路径。

### 6.3 工程与证据测试

- 成功工具结果必须有 hash 地址的原始资产。
- 仿真结果不等同于物理证据。
- 未经 EvidenceReview 的测量不能升级 hypothesis。
- FMEA、DVP&R、法规、MRR、ReleaseDecision 缺一项时不能批准发布。
- 关键 revision 改变后旧结果进入 stale/invalidated。

### 6.4 推荐度量

这些指标用于工程质量监测，不是产品科学真理：

- 观察来源覆盖率。
- 未溯源事实比例。
- App signal 正确分流率。
- 设备交互候选的人工接受率。
- 可执行验证问题比例。
- 关键硬风险漏报率。
- 错误阻塞率。
- reviewer 决策可追溯率。
- 真实测量到需求/假设回写成功率。
- 跨案例知识批准后的复现率。

---

## 7. 首个真实闭环试点

继续使用 Transit Anchor，但把它拆成两个明确入口：

### 7.1 App/服务 Discovery

输入：

- 原产品拆解结果。
- 场景、移动状态、注意力和社交暴露描述。
- App 与设备协同的体验问题。

输出：

- `DigitalExperienceDiscovery`。
- 逐条 `DigitalExperienceSignal`。
- 人工 triage：App、跨端或设备交互。

### 7.2 穿戴设备工程闭环

只使用人工 triage 后的设备交互候选，再进入：

```text
DesignBrief
  → 多个候选
  → 体验评审和 VariablePatch
  → MechanicalArchitecture / MaterialProcessChoice
  → CAD / BOM / DFM / CAE
  → 实物样机
  → 滑移、旋转、按压力、误触、取消时间、触觉检出、汗湿、跌落、温升
  → EvidenceReview
  → FMEA / DVP&R / Compliance / MRR / Release
```

当前必须保持：

```text
PrototypeRun = 0
MeasurementObservation = 0
EvidenceReview = 0
evidence level = none
```

---

## 8. AI 能做与不能做

### AI 可以做

- 从 App/服务描述提取产品画像、触点、摩擦、机会和机制候选。
- 生成 Discovery signal 和待人工 triage 的验证问题草案。
- 生成和比较多种设计、结构、材料和交互方案。
- 编排 CAD/CAE/DFM/测试工具请求。
- 整理 BOM、FMEA、DVP&R、traceability 和差异报告草案。
- 发现接口冲突、风险、未知和设计回归。
- 汇总真实测试结果并提出下一轮变更。
- 维护 revision、dependency、provenance 和审计记录。

### AI 不能单独做

- 把 App 心理分析直接变成硬件或制造要求。
- 证明结构可制造、可靠、舒适、安全或合规。
- 代替样机、测试设备、参与者、工程师、质量人员或认证实验室。
- 从渲染图推断真实尺寸、压力、寿命或用户偏好。
- 自动完成 Discovery triage、工程 Gate 或 ReleaseDecision。
- 在缺少供应商和工艺数据时承诺成本、良率、产能或交付。

---

## 9. 公开演示与交付门槛

### 本地平台门槛

- 全量离线测试通过。
- 旧 CLI 和 JSON 兼容路径有迁移说明。
- Discovery 分流边界有测试。
- 所有工程写操作走 coordinator。
- MCP 不含自动审批权限。

### 真实工程门槛

- 有真实样机和样本。
- 原始测量和 EvidenceReview 可追溯。
- 适用市场法规和可靠性证据明确。
- 供应商、BOM、成本和试产数据具名审查。
- 发布范围、有效 revision、剩余风险和审批人明确。

### 当前不宣称

在真实资源进入之前，项目不宣称：

- 可制造。
- 安全或舒适。
- 达到 IP/EMC/跌落/振动/热/寿命要求。
- 具备量产良率或成本承诺。
- 已完成法规认证或可发布。

---

## 10. 最终判断

项目后续最重要的不是继续堆叠更多 Agent，而是保持三条边界：

1. App 拆解是 Discovery，不是硬件工程事实。
2. 体验假设必须通过条件、证据、替代解释和验证问题表达。
3. 工程和发布结论必须由真实工具、样机、测量、法规和具名 reviewer 完成。

最终目标是：

> 一个以数字产品发现和真实场景为输入、以体验假设和工程对象为共享语言、以 revision graph 为记忆、以验证 Gate 为控制、以真实测试为裁判的 AI 辅助研发平台。

当前最值得继续做的是 Discovery/CLI 收敛和 Transit Anchor 的真实样机闭环，而不是立即更换 CLI 框架或扩展未经验证的自动化 Agent。
