# psyteardown 平台化重点交接

更新时间：2026-09-14

## 一句话结论

三个 Transit Anchor round 已完成设计迭代闭环，但整个项目还没有完成。后续重点从继续打磨单个产品的 Blender 视觉轮次，转向把 `psyteardown` 建设为可复用的体验研究与 AI 设计反馈平台。

Transit Anchor 应作为第一个垂直试点、回归 fixture 和平台演示案例，而不是继续承载所有平台能力的专用逻辑。

## 当前总体位置

```text
文本产品心理拆解基础能力
  → 体验设计 brief 与场景建模
  → 结构化设计候选与 VariablePatch 迭代
  → Blender 派生几何与人工确认
  → 虚拟预检、策略 replay、验证协议
  → 当前：通用平台层建设入口
  → 观察/证据/体验假设/评审
  → 实验规划与 AI 设计反馈
  → 多模态输入与实验结果知识增长
```

当前不是 prototype validated、supported 或 production-ready 阶段，而是：

> Transit Anchor：`geometry_ready / design-review confirmed / physical validation pending`
> psyteardown 平台：已有垂直设计与证据工作流基础，正在补通用体验推理层

## Transit Anchor 当前基线

权威数据库：

`output/experience/transit-anchor-complete-r2/case.db`

当前 Round 3：

- candidate：`scaffold-r1-1.iter-d53a8eee13e0.iter-0f812cd910ad.iter-820dc8412b30.iter-2b03a1ce1ad7.r1`
- model：`scaffold-r1-1.model.r17`
- stage：`geometry_ready`
- confirmed DesignToolRun：`design-tool-run-85d5cebcd5f9.r2`
- prototype runs：`0`
- measurement observations：`0`
- evidence reviews：`0`
- evidence level：`none`

三个 round 的设计结果已保存为历史 revision，不应删除或覆盖。Round 2 和 Round 3 的完成记录分别为：

- `output/experience/transit-anchor-strap-release-r1/round2-completion.md`
- `output/experience/transit-anchor-round3-r1/round3-completion.md`

这些记录、Blender 资产、virtual preflight 和 scenario replay 都不能替代真实样机证据。

## 平台当前已经具备的能力

- 原有文本产品心理拆解、框架检索、证据约束和报告输出。
- `DesignBrief`、`DesignCandidate`、`VariablePatch` 和 `ProgressiveDesignModel`。
- 参数化 parent/child revision 链和 stale revision 保护。
- `ScenarioPolicy` 与确定性 scenario replay。
- Blender provider、设计工具请求/结果、人工确认和 derived asset provenance。
- `ExternalAsset`、`ObservationDraft`、`PrototypeRun`、`MeasurementObservation`、`EvidenceReview`。
- 虚拟工程预检和 portfolio 投影。
- SQLite revision、domain event 和 audit event 存储。

## 平台当前缺口

通用体验研究中间层还不完整，主要缺少：

- 通用 `Evidence` 模型。
- 通用 `Observation` 模型。
- 条件性的 `ExperienceHypothesis` 模型。
- 通用候选 `Critique` 模型。
- `DesignBrief → Candidate → Critique → Rank → Revise` 的通用编排。
- 声明级证据支持审查和过强因果语言检查。
- 将观察、假设和实验计划跨产品复用的能力。

现有的样机证据模型解决的是“真实运行之后如何导入和人工确认测量”，不能替代通用的“产品资料如何变成可追溯观察和体验假设”。

## 下一阶段：平台 M1

### 目标

让任意物理产品能够走通：

```text
产品资料
  → 可追溯观察
  → 条件性体验假设
  → 证据、未知与替代解释
  → 风险评审
  → 可执行验证方案
```

### 实施范围

1. 在 `src/psyteardown/experience/models.py` 增加或整理：
   - `Evidence`
   - `Observation`
   - `ExperienceHypothesis`
   - `Critique`
   - 必要的 `Context` / `PhysicalFeature` 轻量结构

2. 每条观察必须能绑定来源：
   - 文本连续引用
   - 图片区域
   - 视频时间段
   - 传感器文件
   - 访谈原话
   - 实验记录

3. 明确区分：
   - `observed`
   - `reported`
   - `inferred`
   - `exploratory`
   - `tested`
   - `supported`
   - `rejected`

4. 每条体验假设至少包含：
   - 目标人群
   - 任务、环境和社交条件
   - 物理特征或用户动作
   - 心理构念与可能机制
   - 预测结果
   - 至少一个替代解释
   - 当前证据和未知项
   - 验证方式

5. 增加确定性审查规则：
   - 无来源的内容不能成为观察事实。
   - 观察不能直接渲染成用户心理结论。
   - 禁止把“必然、证明、一定导致”等过强表达作为已验证结论。
   - 没有真实实验不能标记为 `supported`。
   - Blender、GLB、PNG 只能作为设计观察来源，不能作为物理性能证据。

6. 为 M1 增加 SQLite 持久化、服务层、CLI 和测试。

### M1 验收标准

- Transit Anchor 和至少一个非穿戴产品都能生成结构化观察。
- 每条观察有来源、确定性和未知边界。
- 每条体验假设有条件、替代解释和验证方式。
- 人工可以确认、修改或驳回观察/假设。
- 未经人工确认的假设不会进入长期知识或默认检索。
- 可导出 Markdown 和 JSON。
- 现有 Round 1/2/3 数据库和全量测试不回归。

## 后续平台路线

### M2：实验规划器

将体验假设转为：

- 自变量和水平
- 对照条件
- 因变量和测量方法
- 样本范围
- 混淆变量
- 停止条件
- 预注册 Markdown/JSON

### M3：AI 设计反馈回路

实现：

```text
DesignBrief
  → 生成多个候选
  → 观察候选事实
  → 体验评审
  → 硬风险筛选
  → 基于目标/约束/权衡排序
  → 人工选择
  → 下一轮设计提示
```

每条 `actionable_change` 必须指向可操作变量，例如材料、尺寸、阻尼、反馈模态、反馈时机、可见状态或交互步骤；不能只输出“更自然”“更有安全感”。

### M4：图片和短视频观察

优先支持图片区域、材质/按钮/结构观察，以及拿起、按压、旋转等短动作片段；允许人工修正；缺失模态时明确降级，不补全不可见事实。

### M5：实验结果和知识增长

```text
真实实验结果
  → 假设状态更新
  → supported / rejected / inconclusive / needs_replication
  → 人工审批
  → 跨案例候选规律
  → 下一轮设计反馈
```

未经人工审批的候选规律不能影响默认知识库。反例和复现实验可以将已有结论降级。

## Transit Anchor 在平台中的用法

Transit Anchor 后续主要承担四个角色：

1. 回归 fixture：验证 revision、证据边界和隐私护栏不被破坏。
2. 端到端 demo：展示 brief、候选、patch、几何、协议和报告如何串起来。
3. 观察/假设样本：将 Round 3 的 private haptic、safe-boundary pulse 和 bystander state edge 转成通用对象。
4. 未来真实实验案例：有真实 device build 后，再导入 `PrototypeRun` 和 `MeasurementObservation`。

不要为了证明平台能力而伪造 Transit Anchor 的样机、参与者、测量或隐私结果。

## 明确暂缓

- 不继续做没有证据支撑的 Round 4 视觉美化。
- 不做实时用户情绪或健康状态判断。
- 不让模型自动批准设计、实验结果或候选规律。
- 不用一个“心理学总分”替代多目标设计决策。
- 不把 Blender/GLB/PNG 或 virtual preflight 提升为 prototype evidence。
- 不先做复杂 Web dashboard。
- 不先训练自有大模型。

## 推荐下一次开发任务

直接实现平台 M1 的第一切片：

1. `Evidence` / `Observation` / `ExperienceHypothesis` / `Critique` 数据模型。
2. revision-safe SQLite repository 映射。
3. 确定性 evidence/claim 检查器。
4. Transit Anchor fixture 和一个非穿戴产品 fixture。
5. 单元测试、CLI 输出和 Markdown/JSON 报告。

完成 M1 后，再进入实验规划器和 AI 设计反馈回路；不要先扩展更多产品视觉资产。

## 回归要求

每次平台化改动后至少运行：

```powershell
pytest -q
```

当前基线：`345 passed, 2 skipped`。

任何后续交接都必须继续明确：

- Transit Anchor 当前 revision 和 parent lineage。
- `PrototypeRun`、`MeasurementObservation`、`EvidenceReview` 数量。
- evidence level。
- 哪些内容是 declared、derived、observed、supported 或未知。

## M1 完成记录（2026-09-14）

M1 第一切片已落地并通过全量回归：`349 passed, 2 skipped`。新增通用
`Context`、`PhysicalFeature`、`Evidence`、`Observation`、
`ExperienceHypothesis`、`Critique`，以及 SQLite revision 映射、确定性 claim
检查器、`research-import` / `research-export` CLI。Transit Anchor 与电热水壶
fixture 分别位于 `examples/m1-transit-anchor-research.json` 和
`examples/m1-kettle-research.json`。这些 fixture 只表达 declared/design
observation，不生成样机或参与者证据。

## M2 开始记录（2026-09-14）

已开始实验规划器切片：`ExperimentVariable`、`MeasureSpec`、`SamplePlan`、
`StoppingRule` 扩展 `ExperimentPlan`，并新增
`build_experiment_plan`、`preregister_plan`、Markdown/JSON 导出与
`experiment-plan` / `experiment-preregister` CLI。规划器从条件性
`ExperienceHypothesis` 生成对照条件、自变量/水平、因变量、样本范围、混淆
变量、停止条件、成功判据和伦理备注；默认状态为 `draft`，只有人工调用
`preregister_plan` 后才创建 `preregistered` revision。M2 计划本身不产生实验
结果，不会把 hypothesis 标记为 `supported`。

下一步应补齐：与 `HypothesisBinding` / `AnalysisFamily` 的正式绑定、预注册
字段级 amendment 审查，以及真实实验结果导入前的分析协议检查。继续保持
Transit Anchor 当前 `geometry_ready / design-review confirmed /
physical validation pending` 基线不变。

## M3 开始与第一切片记录（2026-09-14）

M3 AI 设计反馈回路第一切片已完成：`generate_candidates`、
`critique_candidate`、`rank_candidates`、`select_feedback_candidate`、
`build_next_prompt` 和 `run_feedback_loop` 已实现。候选事实从
`DeclaredFact.source_locator` 生成 Evidence/Observation，体验结论保持为
`exploratory` Hypothesis；硬风险、未知项、权衡和可操作变量修改均在
Critique 中保留。排序只使用确定性风险/未知/可操作性规则和 candidate ID，
不生成无语义的心理学总分。

`design-feedback` CLI 会把候选与 Critique 保存到 SQLite 并导出机器可读反馈
JSON；`design-feedback-select` 需要显式人工选择，随后才生成带
`parent_candidate_revision_id`、目标、未知和 `do_not_claim` 护栏的下一轮
prompt，并持久化 `DesignFeedbackSelection`。系统不会在生成或排序阶段自动
批准候选，也不会把 hypothesis 标记为 `supported`。

M3 当前仍需继续补齐：将反馈选择接入完整 `DesignIteration` / `SelectionDecision`
revision 链，支持基于确认 VariablePatch 的第二轮候选生成，以及跨候选报告和
人工覆盖理由导出。所有 M3 改动后继续运行 `pytest -q`。
