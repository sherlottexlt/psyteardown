# AI 工程协同研发平台后续开发交接

更新时间：2026-09-16

## 一句话结论

M1、M2、M3 已经完成体验研究、实验规划和设计反馈的确定性闭环。下一阶段不应把系统扩展成几个彼此独立的“专家 Agent”，而应建设一个以工程对象为共享语言、以 revision graph 为记忆、以验证 gate 为控制、以真实测试为裁判的 AI 协同研发系统。

系统的目标不是让 AI 单独证明一个穿戴设备可以量产，而是让 AI 主导方案探索、工程工具编排、证据整理和下一轮变更；由真实工程工具、样机、测量、法规和具名人员完成验证与放行。

## 当前边界

当前平台已经具备：

- 场景、移动状态、注意力和社交暴露建模；
- `DesignBrief`、`DesignCandidate`、`VariablePatch` 和 parent/child revision；
- Blender 派生几何、设计评审和资产 provenance；
- M1 的 `Evidence`、`Observation`、`ExperienceHypothesis`、`Critique`；
- M2 的实验变量、条件快照、分析族、预注册和 analysis protocol gate；
- M3 的多候选生成、风险/未知筛选、人工选择、下一轮 prompt 和第二轮候选生成；
- SQLite revision、domain event、audit event 和人工审批边界。

Transit Anchor 仍保持：

```text
geometry_ready / design-review confirmed / physical validation pending
PrototypeRun = 0
MeasurementObservation = 0
EvidenceReview = 0
evidence level = none
```

因此，Blender、GLB、PNG、virtual preflight 和 scenario replay 仍是设计/策略材料，不是样机证据，也不是制造或认证结论。

## 目标系统

后续系统采用以下闭环：

```text
场景 + 产品用途
  → AI 形成需求与约束假设
  → 工业设计 / 结构 / 材料工艺提出多方案
  → 系统集成检查接口与整体取舍
  → CAD / BOM / CAE / DFM / 人机工程 / 法规评估
  → AI 选择当前证据下最值得验证的方案
  → 样机、实验室、人体与认证测试
  → 人工 EvidenceReview
  → 证据回写需求、风险、假设和 VariablePatch
  → 下一轮设计与工程验证
```

角色之间不直接依赖自然语言对话。每个角色通过带有 revision、依赖、证据、状态和 reviewer 的结构化工程对象交互。

## 角色与职责

### 1. 系统工程角色

输入：场景、产品用途、业务目标、法规市场、成本和维护假设。

输出：`EngineeringRequirement`、验收指标、优先级、硬约束、软目标、风险和未知项。

职责：

- 将“做一个智能穿戴设备”转成可验证需求；
- 区分 must、should、explore；
- 维护需求到设计、测试和证据的 traceability；
- 不能把 AI 生成的默认假设伪装成用户或工程事实。

### 2. 工业设计角色

输入：需求、体验目标、场景、品牌和交互约束。

输出：形态方向、CMF、佩戴关系、状态可见性、交互表面和 `DesignCandidate`/`CADArtifact` 草案。

职责：

- 探索多个可比较方向；
- 保留可达性、可读性、隐私和移动状态下的交互边界；
- 标记尺寸、材质、舒适度等尚未测量的内容。

### 3. 结构工程角色

输入：系统需求、内部器件、工业设计外形、装配和维护约束。

输出：`MechanicalArchitecture`、壳体/骨架/固定/密封/按键结构、`ToleranceStack`、结构风险。

职责：

- 处理堆叠、装配、公差、紧固、拆卸和维修；
- 把结构冲突转成可执行的 VariablePatch 或工程问题；
- 不以渲染图代替 CAD、尺寸和强度证据。

### 4. 材料与工艺角色

输入：接触、强度、热、外观、成本、供应链和制造方式。

输出：`MaterialProcessChoice`、材料牌号、表面处理、注塑/压铸/冲压/包胶等工艺假设、工艺风险。

职责：

- 对材料选择给出依据和待验证项目；
- 检查皮肤接触、汗液、老化、耐磨、阻燃和回收等问题；
- 将双色注塑、纳米注塑、密封、模具和良率风险显式化。

### 5. 系统集成角色

输入：工业设计、结构、材料、电子器件、交互和场景策略。

输出：集成设计、接口矩阵、冲突列表、Pareto 候选和集成决策记录。

职责：

- 检查各专业方案能否组成一个整体；
- 发现 TPU 厚度与按键行程、快拆机构与空间、状态灯与天线等接口冲突；
- 不用单一“心理学总分”掩盖硬约束冲突。

### 6. CAE 编排角色

输入：CAD、材料模型、边界条件、载荷、环境和网格/求解设置。

输出：`CAEAnalysisRun`、原始结果引用、收敛状态、不确定性和解释报告。

职责：

- 编排结构、热、模流、跌落、振动、接触压力等真实工具；
- 检查输入是否足以运行分析；
- 解释结果但不伪造仿真结果；
- 明确仿真结果不能自动替代物理测试。

### 7. DFM / 成本角色

输入：CAD、材料工艺、BOM、供应商和目标成本。

输出：`DFMReview`、制造风险、零件数、装配步骤、成本假设、良率风险和建议变更。

职责：

- 检查壁厚、拔模、分型、进胶、紧固、装配和维修；
- 维护成本/VAVE 取舍；
- 不能在没有供应商数据时承诺成本、产能或良率。

### 8. 人机工程与体验验证角色

输入：佩戴结构、动作序列、目标人群和实验协议。

输出：人体工学风险、`VerificationTestRun`、夹具需求、测量指标和结果解释草案。

职责：

- 验证不同体型、腕围、姿态、汗湿和移动状态；
- 测量压力、滑移、旋转、误触、按压力、触觉检出和取消时间；
- 不将体验假设直接升级为舒适、安全或用户偏好事实。

### 9. 质量 / 法规角色

输入：需求、材料、测试结果、风险记录、适用市场和法规矩阵。

输出：FMEA、合规检查、认证缺口、放行意见和 `ReleaseDecision`。

职责：

- 管理 IP、EMC、跌落、振动、高低温、可靠性和法规证据；
- 对发布、量产和安全承担人工责任；
- 没有完整证据时只能输出 blocked、pending 或 conditional approval。

### 10. AI 工程编排角色

输入：所有当前 revision、依赖图、风险、测试结果和人工决策。

输出：下一步任务、并行任务、冲突报告、`VariablePatch`、变更候选和审查摘要。

职责：

- 判断哪些任务可并行、哪些必须等待前置对象；
- 使依赖输入变化后的旧结果进入 stale；
- 聚合多专业冲突；
- 保持所有结论的 provenance；
- 不替代具名工程师、测试人员、法规人员和最终签字人。

## 共享工程对象

后续开发应把以下对象作为角色之间的正式接口，而不是让 Agent 互相传递长文本：

| 对象 | 用途 |
|---|---|
| `EngineeringRequirement` | 需求、验收指标、优先级、来源和适用范围 |
| `MechanicalArchitecture` | 壳体、骨架、装配、密封、固定和维修结构 |
| `MaterialProcessChoice` | 材料、工艺、表面处理、供应链和验证要求 |
| `CADArtifact` | CAD、工程图、格式、工具版本和输入 revision |
| `BOMRevision` | 零件、材料、数量、供应商、成本和替代料 |
| `ToleranceStack` | 公差链、基准、最坏情况和统计假设 |
| `CAEAnalysisRun` | 分析类型、边界条件、求解器、原始结果和 reviewer |
| `DFMReview` | 可制造性、装配、模具、成本和良率风险 |
| `FMEARevision` | 失效模式、严重度、发生率、可探测性和措施 |
| `VerificationTestRun` | 测试条件、夹具、样本、原始测量和判定 |
| `ManufacturingReadinessReview` | 试产、供应商、良率、质量和产能准备度 |
| `ReleaseDecision` | 发布范围、阻塞项、审批人和有效 revision |

每个对象必须至少记录：

- `revision_id` 和 `parent_revision_id`；
- 创建者、工具/模型版本和时间；
- 输入依赖；
- 原始资产或结果位置；
- 假设、未知和适用范围；
- reviewer、决策和理由；
- 当前状态以及失效条件。

## 依赖图与失效传播

依赖关系示例：

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
  FMEARevision / ReleaseDecision
```

失效传播规则：

1. CAD revision 改变时，依赖它的 BOM、CAE、DFM 和测试计划标记为 `stale`。
2. 材料牌号或工艺改变时，相关热、强度、模流、接触和可靠性结果必须重新检查。
3. 需求验收指标改变时，旧测试结果不能自动满足新需求。
4. 测试夹具、样本或边界条件无效时，结果进入 `invalidated`，不能用于放行。
5. 新证据只能创建新 revision，不能原地覆盖历史结论。

## 状态门

建议把平台工程状态扩展为：

```text
concept_declared
  → experience_reviewed
  → engineering_ready
  → prototype_ready
  → physical_validation
  → compliance_reviewed
  → manufacturing_ready
  → released
```

最低 gate：

| 状态 | 最低证据 |
|---|---|
| `concept_declared` | 场景、用途、初始假设 |
| `experience_reviewed` | M1/M2/M3 评审、风险、未知和人工选择 |
| `engineering_ready` | 结构架构、材料工艺、CAD、关键接口和工程 reviewer |
| `prototype_ready` | BOM、装配方案、制造路径、关键 DFM 通过 |
| `physical_validation` | 样机、测试条件、原始测量和 EvidenceReview |
| `compliance_reviewed` | 适用法规、可靠性和认证证据 |
| `manufacturing_ready` | 试产、良率、供应商、质量和成本审查 |
| `released` | 明确范围、有效 revision、剩余风险和具名批准人 |

任何 AI 输出都不能通过 gate；AI 只能准备 gate 所需材料。Gate 通过必须由具名责任角色批准。

## 决策和冲突规则

### 硬约束优先级

```text
安全 / 法规
  > 核心功能
  > 人机工程
  > 可靠性
  > 可制造性
  > 成本
  > 外观偏好
```

安全、法规和关键功能冲突时，方案阻塞；软目标冲突时，保留多个 Pareto 候选；无法判断时创建人工决策任务。

### 禁止行为

- 不用一个综合分替代多目标工程决策；
- 不把自然语言共识当作工程批准；
- 不把仿真当作测量；
- 不把测量单点当作普遍用户结论；
- 不把 Blender/GLB/PNG 当作制造或物理性能证据；
- 不让 AI 自动批准安全、法规、量产或发布；
- 不因新 revision 删除或覆盖旧 revision。

## 一次完整交互示例：低打扰通勤穿戴设备

1. 系统工程角色把场景转成需求：不依赖持续视觉注意、有明确取消动作、不能泄露内容、需要验证佩戴稳定性和误触率。
2. 工业设计角色提出低轮廓腕戴、佩戴者朝向状态边缘、凹面确认区和独立取消区。
3. 结构角色提出壳体、内部骨架、快拆表带和密封假设，并创建尺寸/公差未知项。
4. 材料工艺角色提出 PC/ABS 主壳、TPU 接触层和内部增强件，同时提出汗液老化、皮肤接触、模具和成本风险。
5. 系统集成角色发现 TPU 厚度影响按键行程、快拆机构挤占内部空间、状态灯可能与天线冲突。
6. CAE、DFM、人机工程角色分别生成仿真、制造和佩戴验证任务。
7. 测试工程角色把风险转成滑移、旋转、按压力、取消时间、触觉检出、汗湿、跌落和温升测试。
8. 人类执行样机和测试，导入原始数据。
9. EvidenceReview 确认数据有效性；AI 比较需求和结果，区分已满足、未满足、变差、无法判断。
10. AI 生成带目标变量、证据引用和验证要求的下一轮 `VariablePatch`，由工程师批准后进入新 revision。

## 后续开发阶段

### P0：工程对象和编排骨架

- 新增上述工程对象及 SQLite registry 映射；
- 实现统一 dependency graph 和 stale/invalidation 传播；
- 实现 `EngineeringOrchestrator` 的任务、依赖、状态和人工 gate；
- 给 M1/M2/M3 对象补工程依赖入口；
- 保持现有 Transit Anchor revision 和测试基线不回归。

### P1：M4 多模态观察

- 图片区域和视频时间段观察；
- `ExternalAsset → ObservationDraft → 人工确认/修改/驳回`；
- 缺失模态显式降级为 `unknown`/`not_observable`；
- 图像和视频不能未经校准生成尺寸、压力、强度或舒适度事实。

### P2：真实样机与验证回流

- Transit Anchor 形成真实样机；
- 导入 `PrototypeRun`、`MeasurementObservation`；
- 用 `EvidenceReview` 确认或驳回测量；
- 将结果绑定到 M2 的 `ConditionSnapshot`、`AnalysisFamily` 和 `HypothesisBinding`；
- 通过 analysis protocol gate 后再允许 hypothesis 状态变化。

### P3：CAD/CAE/DFM 工具适配

- CAD 参数和工程图适配；
- Moldflow、结构/热仿真和可靠性工具调用；
- BOM、材料、供应商和成本数据接入；
- 原始工具结果和 AI 解释分开保存；
- 仿真和工程结论必须有人审查。

### P4：制造、法规和质量闭环

- FMEA、DVP&R、试产、良率、可靠性和认证对象；
- `ManufacturingReadinessReview` 和 `ReleaseDecision`；
- 发布 gate、变更单、供应商变更和售后问题回流；
- 未满足关键 gate 时只能输出 blocked/conditional 状态。

### P5：跨案例知识增长

- 真实实验和工程证据更新 hypothesis 状态；
- 生成跨案例规律候选；
- 去重、冲突、反例和复现检查；
- 人工批准后才进入默认知识库；
- 未批准规律不能影响默认设计排序。

## AI 能做与不能做

### AI 可以做

- 从场景和用途生成需求、约束和默认假设；
- 生成和比较多个工业设计、结构、材料和交互方案；
- 编排 CAD/CAE/DFM/测试工具；
- 自动整理 BOM、FMEA、验证计划和差异报告草案；
- 发现接口冲突、风险、未知和设计回归；
- 汇总真实测试结果并提出下一轮变更；
- 维护 traceability、revision、依赖和审计记录。

### AI 不能单独做

- 证明结构可制造、可靠、舒适或安全；
- 证明 IP、EMC、跌落、振动、热和寿命要求达标；
- 代替真实样机、测试设备、参与者和认证实验室；
- 从渲染图推断真实尺寸、重量、压力、寿命或用户偏好；
- 自动批准量产、法规、医疗、安全或产品发布；
- 在缺少供应商和工艺数据时保证成本、良率和交付。

## 验收标准

后续平台阶段完成的最低判断标准：

1. 给定场景和产品用途，系统能生成带假设、来源和验收指标的需求集。
2. 多个角色可以并行提出方案，但输出都落在正式工程对象上。
3. CAD、材料、BOM、CAE、DFM 和测试之间存在可查询的 revision 依赖链。
4. 上游 revision 变化会使下游过期结果自动进入 stale 或 invalidated。
5. AI 能生成下一步任务和变更，但不能绕过人工 gate。
6. 真实测量可以回写需求、风险、假设和下一轮 `VariablePatch`。
7. 任何“满足要求”的结论都能追溯到原始数据、工具版本、适用条件和具名 reviewer。
8. Transit Anchor 的历史 revision、`PrototypeRun`、`MeasurementObservation`、`EvidenceReview` 和 evidence level 不被伪造或覆盖。

## 交接结论

项目的正确定位是：

> 一个以场景为输入、以工程对象为共享语言、以 revision graph 为记忆、以验证 gate 为控制、以真实测试为裁判的 AI 辅助移动与穿戴设备研发平台。

AI 是高频探索者、工程工具编排者、证据整理者和变更建议者；系统工程、结构、材料、测试、质量、法规和制造人员仍然拥有相应领域的验证权与最终责任。

## 2026-09-17 继续实施状态

本次接续完成并验证了 P0–P5 闭环的本地实现，并新增 MCP 只读 `engineering_status` 和 `engineering_traceability` 工具。它们与 CLI 共享 SQLite revision 数据，只返回状态/追溯投影，不执行工程软件、不评审证据、不推进 gate。

当前尚未完成的是外部真实资源：Transit Anchor 实物样机与测量、真实 CAD/CAE/DFM/BOM 工具与供应商数据、认证实验室、以及可选 Web 操作台。在这些数据和具名 reviewer 进入前，系统只能输出 `pending`/`blocked`/`conditional`，不宣称可制造、合规、量产或发布。

CLI 边界已进一步收紧：原始 App/数字服务拆解先进入 `DigitalExperienceDiscovery`，经具名 reviewer 的 `DiscoveryTriageDecision` 逐条分流后，只有设备交互候选才可投影到工程 intake；`engineering-init-from-teardown` 仅作为迁移兼容入口隐藏保留。Typer 继续承担可复现本地命令，MCP 继续承担只读查询，未来多人审查可在相同 Coordinator 之上增加 Web/API。

最新验证：`406 passed, 2 skipped` 。
