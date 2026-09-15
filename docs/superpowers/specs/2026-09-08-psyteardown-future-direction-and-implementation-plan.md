# psyteardown 后续方向与完整实现计划

- 日期：2026-09-08
- 状态：方向与计划草案，作为后续实现的主文档
- 基线：当前仓库的 v1–v6 实现、step3 证据溯源改动与既有设计文档
- 适用范围：将 psyteardown 从“文本产品心理拆解 Agent”发展为服务 AI 设计闭环的“物理产品体验假设与验证系统”

---

## 0. 一句话结论

psyteardown 有长期价值，但它不应该被包装成“AI 判断一个产品会不会让人喜欢”，也不应该声称“从外观读懂人的心理”。它最终应成为 AI 设计系统中的**体验推理、约束、评审和迭代反馈层**。更可靠、也更有独特性的定位是：

> **Experience Hypothesis Engine：把 AI 设计候选的材料、形态、动作和使用情境，转译成可追溯的心理机制假设、体验风险、设计修改建议和可执行的验证实验。**

系统不应停在：

```text
产品描述 → 心理学报告
```

它要进入 AI 设计闭环：

```text
设计目标 / 任务 / 人群 / 情境 / 硬约束
  → AI 生成多个设计候选
  → psyteardown 观察候选的物理与交互事实
  → 行为与情境
  → 心理机制假设
  → 体验预测、风险与设计修改建议
  → 实验设计与用户反馈
  → 人工选择与决策策略更新
  → 下一轮 AI 生成
```

对于已有产品，仍然保留分析模式：

```text
产品输入
  → 可观察事实
  → 行为与情境
  → 心理机制假设
  → 体验预测
  → 实验设计
  → 用户/现场结果
  → 经过人工批准的知识与策略更新
```

这条路线最适合当前项目，也最能连接材料工程、认知心理学、人因工程和 AI 应用工程。关键变化是：拆解结果不再只是报告终点，而是下一轮 AI 设计的结构化输入。

---

## 1. 当前基线

### 1.1 已经完成的能力

当前 psyteardown 已经具备以下基础：

- 8 个心理学框架、29 条原则的结构化知识库，带出处和伦理注记。
- 五步拆解流水线：产品解析、框架检索、逐功能映射、整体体验评估、综合报告。
- 可插拔的 LLM 与 embedding provider，可使用 Fake provider 做离线测试。
- 情景记忆、语义知识候选、程序性策略卡和单案例自评。
- CLI 与 MCP server 两种交付入口。
- 结构化输出、Schema 校验、失败降级、低置信度暴露和人工审批闭环。
- step3 的产品原文逐字证据约束与未溯源映射记账。

详细实现可参见：

- `README.md`
- `docs/resume/psyteardown.md`
- `docs/superpowers/specs/2026-06-13-psychology-product-teardown-agent-design.md`
- `docs/superpowers/specs/2026-09-02-step3-evidence-grounding-design.md`

### 1.2 当前系统解决的问题

当前系统擅长回答：

- 一个产品有哪些功能和触点？
- 每个功能可能对应哪些心理学原则？
- 哪些判断有原文证据，哪些判断置信度较低？
- 哪些设计可能涉及操控、暗黑模式或伦理风险？
- 历史案例中有哪些相似拆解和可复用策略？

### 1.3 当前系统尚未解决的问题

当前版本还不能可靠回答：

- 产品的重量、材质、阻尼、温度、声音和震动如何影响体验？
- 用户的拿起、握持、旋转、靠近、回避和放下分别表达什么？
- 同一个动作在不同环境、任务和社交关系中是否有不同含义？
- 某一心理机制是否真的导致了某种体验结果？
- 哪个设计版本更好，应该如何通过实验验证？
- 用户反馈和实验结果如何更新知识，而不让错误自动进入知识库？

这些不是简单增加一个多模态模型就能解决的缺口。核心缺口是**观察、解释、预测和验证没有被建模成不同层次**。

---

## 2. 产品定位与价值

### 2.1 推荐定位

中文名称：

> **心理驱动的产品体验拆解与验证 Agent**

英文名称：

> **psyteardown — Product Experience Hypothesis Engine**

一句话介绍：

> psyteardown 将产品的材料、形态、动作与使用情境拆解为可追溯的心理机制假设，并生成可执行的体验验证方案。

### 2.2 它不是以下产品

明确不把它定位成：

- 自动评价产品好坏的评分器。
- 根据一张图片断言用户情绪的“读心模型”。
- 只会引用心理学名词的报告生成器。
- 取代设计师、研究员或人因工程师的自动决策工具。
- 用“信任感 + 23%”这种没有实验依据的伪精确预测系统。

### 2.3 它真正提供的价值

#### 对设计与工程团队

- 把设计师的隐性判断变成可讨论、可复核的假设。
- 在做样机和用户测试前，提前发现体验风险和关键变量。
- 比较不同材料、形态、反馈方式和交互规则的可能影响。
- 将“为什么这样设计”与具体证据、理论和实验记录绑定。

#### 对 AI 硬件团队

- 分析 AI 设备何时应该介入、何时应该沉默。
- 检查拟人化、通知、触觉、声音和环境感知是否造成过度依赖或注意力争夺。
- 将物理交互与 AI 的不确定性、可纠正性和权限边界结合起来。

#### 对个人与组织知识积累

- 将产品观察、用户研究、材料实验和心理学框架沉淀为可检索资产。
- 让失败案例进入下一轮假设生成，而不是只保留成功结论。
- 形成跨产品、跨材料、跨场景的体验设计语言。

### 2.4 核心差异化

差异不在“使用了哪个大模型”，而在以下中间层：

```text
物理特征 → 可观察动作 → 使用情境 → 心理机制假设 → 体验结果 → 验证实验
```

这是一层连接物理世界和 AI 推理的结构化语言。它是项目最值得长期积累的资产。

### 2.5 最终服务对象：AI 设计闭环

平时让 AI 设计产品，常见做法是把经验写进提示词，让模型抽取若干候选，再由人凭直觉选出“看起来最好”的方案。psyteardown 要把其中最容易失真的一段显式化：

```text
设计候选 → 这个候选包含哪些物理与交互事实？
        → 它可能如何影响特定人群在特定情境中的体验？
        → 证据、理论和替代解释是什么？
        → 哪些风险需要否决，哪些问题必须做实验？
        → 下一轮应该修改什么？
```

因此，psyteardown 不是一个设计生成器的替代品，而是设计生成器旁边的**体验评审器和设计反馈器**。它需要同时支持三种模式：

| 模式 | 输入 | 输出 | 是否允许直接改设计 |
|---|---|---|---|
| `explain` | 已有产品/样机 | 观察、机制假设、风险与证据 | 否 |
| `critique` | AI 生成的设计候选 | 逐条评审、未知、硬约束和失败原因 | 否 |
| `suggest` | 评审结果与设计目标 | 有依据的设计修改方向和下一轮提示 | 只提出建议 |

设计候选的“好坏”不能由一个通用心理学分数决定。候选排序必须由设计任务定义的策略控制，例如：

- 目标情境：独处专注、通勤导航、人与人交流或家庭共享。
- 目标体验：可预测、可控、安静、亲近、低负担或安全。
- 禁止体验：强迫、羞耻、持续打扰、监视感或过度依赖。
- 硬约束：成本、重量、防水、续航、可制造性和隐私。
- 权衡关系：舒适度与快速操作、亲密感与社交可见性、反馈丰富度与注意力负担。

psyteardown 的输出应帮助人和设计模型看清这些权衡，而不是替人决定唯一答案。

### 2.6 面向 AI 设计的最小反馈契约

每个被评审的候选至少要返回：

```text
candidate_id
design_facts                 # 该候选实际包含的物理/交互事实
context_assumptions          # 评审采用的人群、任务、环境和社交假设
experience_hypotheses         # 条件性体验假设
evidence_and_unknowns         # 证据、缺失信息与未知边界
hard_risks                    # 满足条件即不可接受的风险
tradeoffs                     # 候选牺牲了什么、换来了什么
actionable_changes            # 下一轮可修改的材料/形态/反馈/时机
experiment_plan_ids           # 可验证该候选的实验
human_decision_required       # 必须由人决定的事项
```

其中 `actionable_changes` 才是连接 psyteardown 与 AI 设计生成器的关键。建议修改必须指向一个可操作变量，例如“缩短触觉脉冲并延迟非紧急提示”，而不是“让产品更有安全感”。

---

## 3. 设计原则

### 3.1 观察、解释、预测必须分离

每条输出都必须区分：

1. **Observation / 观察**：输入中实际看见、听见、测得或被用户说出的内容。
2. **Interpretation / 解释**：根据理论对观察进行的解释。
3. **Prediction / 预测**：在特定人群、任务和情境下可能出现的体验结果。
4. **Experiment / 验证**：如何确认或推翻该预测。

系统不能把第四步缺失时的第三步写成事实。

### 3.2 AI 可以提议，不能自行批准

以下内容必须经过人工确认才能进入长期知识：

- 新的心理学框架或原则。
- 新的“物理特征 → 体验结果”规律。
- 实验结果的总结性结论。
- 高风险的人群、情绪或健康相关推断。

种子知识、实验原始数据和用户原始证据不可被模型自动覆盖。

### 3.3 证据优先于流畅度

任何产品事实都必须绑定来源：

- 文本：原文连续片段。
- 图片：图片 ID、区域或人工标注区域。
- 视频：时间区间、帧或动作片段。
- 传感器：数据文件、时间区间、采样条件。
- 访谈：逐字原话与受访者编号。
- 实验：预注册方案、原始数据和分析版本。

无法绑定来源时，应输出“未知”或“待验证”，而不是补全细节。

### 3.4 心理结论必须是概率性和条件性的

禁止：

> 柔软材料会让用户感到安全。

推荐：

> 在独处、低压力、需要长时间握持的情境下，柔软接触面**可能**降低接触阻力并提高主观舒适感；该判断需要与硬质版本进行对照实验。

### 3.5 先定义实验，再给高置信度

没有可执行验证方案的结论，最高只能是“探索性假设”，不能标成已验证规律。

### 3.6 不做敏感状态的无依据推断

默认禁止从产品或动作推断：

- 精神疾病、人格障碍或临床诊断。
- 未经同意的情绪、健康或生理状态。
- 身份、宗教、政治倾向等敏感属性。

涉及压力、焦虑、疲劳等状态时，只能描述自报告、可观察行为或经过伦理审批的实验变量。

---

## 4. 目标领域模型

当前的 `Feature → Mapping` 模型适合文本产品拆解，但不足以表达物理产品。后续需要建立以下领域对象。

### 4.1 核心实体

| 实体 | 含义 | 示例 |
|---|---|---|
| `Product` | 被研究的产品或产品版本 | 某款 AI 耳机 v2 |
| `Artifact` | 具体输入资产 | 图片、视频、CAD 截图、录音、日志 |
| `PhysicalFeature` | 可观察的物理特征 | 软质握持区、旋钮、金属重量 |
| `Affordance` | 该特征暗示或允许的动作 | 可旋转、可按压、适合持续握持 |
| `UserAction` | 人的可观察动作 | 拿起、捏压、翻转、靠近 |
| `Context` | 任务、环境和社交条件 | 通勤、独处、与人交谈 |
| `UserState` | 可观测或自报告的状态 | 专注、切换任务、犹豫 |
| `Construct` | 心理构念 | 控制感、认知负荷、归属感 |
| `Mechanism` | 连接特征与体验的机制假设 | 反馈明确性降低不确定性 |
| `ExperienceOutcome` | 体验或行为结果 | 恢复时间、信任、错误率 |
| `Evidence` | 支撑某条陈述的来源 | 原文、帧、逐字稿、实验数据 |
| `Hypothesis` | 待验证的条件性因果假设 | 柔软握持区可能提高舒适感 |
| `Experiment` | 验证假设的方案 | 硬/软外壳随机对照 |
| `Observation` | 实验或真实使用的观察记录 | 参与者平均握持时长 |
| `DesignBrief` | 设计任务、目标体验和硬约束 | 为通勤中的 AI 设备设计低打扰反馈 |
| `DesignCandidate` | AI 或人生成的设计方案版本 | 柔性外壳 + 单次触觉确认 |
| `Critique` | 针对候选的证据化评审 | 可预测性提升，但公共场景隐私风险较高 |
| `Decision` | 团队根据证据做出的设计决策 | 保留触觉确认，不加入声音 |
| `Approval` | 人工审批和版本状态 | candidate / approved / rejected |

### 4.2 关系

```text
Artifact
  └─ contains → Observation
PhysicalFeature
  └─ affords → UserAction
UserAction + Context
  └─ may indicate → UserState
PhysicalFeature + UserAction + Context
  └─ supports → Hypothesis
DesignBrief
  └─ constrains → DesignCandidate
DesignCandidate
  ├─ contains → PhysicalFeature / Affordance
  ├─ evaluated_by → Critique
  └─ revised_to → DesignCandidate (next revision)
Critique
  ├─ cites → Evidence / Hypothesis
  ├─ identifies → hard risk / tradeoff
  └─ proposes → actionable design change
Hypothesis
  ├─ invokes → Construct / Mechanism
  ├─ predicts → ExperienceOutcome
  ├─ supported_by → Evidence
  └─ tested_by → Experiment
Experiment
  └─ produces → Observation / Result
Result
  └─ may update → candidate knowledge
candidate knowledge
  └─ human approval → approved knowledge
```

### 4.3 最小结构化模型

建议在现有 `pipeline.schemas` 之外新增领域模型，先不破坏旧 `Mapping`：

```python
from typing import Literal


class Evidence(BaseModel):
    kind: Literal["text", "image", "video", "audio", "sensor", "interview", "experiment"]
    artifact_id: str
    quote_or_locator: str
    source_text: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float = Field(ge=0, le=1)


class Observation(BaseModel):
    id: str
    subject: str
    predicate: str
    value: str
    context_id: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    certainty: Literal["observed", "reported", "inferred"]


class ExperienceHypothesis(BaseModel):
    id: str
    physical_features: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    context: str
    construct: str
    mechanism: str
    predicted_outcome: str
    alternative_explanations: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    status: Literal["exploratory", "candidate", "tested", "supported", "rejected"] = "exploratory"


class DesignBrief(BaseModel):
    id: str
    goal: str
    target_users: str
    contexts: list[str] = Field(default_factory=list)
    desired_experiences: list[str] = Field(default_factory=list)
    prohibited_experiences: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    tradeoff_priorities: list[str] = Field(default_factory=list)


class DesignCandidate(BaseModel):
    id: str
    brief_id: str
    revision: int = 1
    description: str
    design_facts: list[Observation] = Field(default_factory=list)
    source: Literal["human", "llm", "hybrid"]
    parent_id: str | None = None
    generation_prompt_version: str | None = None


class Critique(BaseModel):
    candidate_id: str
    hypotheses: list[ExperienceHypothesis] = Field(default_factory=list)
    hard_risks: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    actionable_changes: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    experiment_plan_ids: list[str] = Field(default_factory=list)
    human_decision_required: list[str] = Field(default_factory=list)
    status: Literal["draft", "reviewed", "approved", "rejected"] = "draft"


class DesignIteration(BaseModel):
    id: str
    brief_id: str
    candidate_ids: list[str] = Field(default_factory=list)
    critique_ids: list[str] = Field(default_factory=list)
    ranking_policy: list[str] = Field(default_factory=list)
    ranked_candidate_ids: list[str] = Field(default_factory=list)
    human_selection: str | None = None
    override_reason: str | None = None
    next_prompt: str | None = None
    status: Literal["generated", "critiqued", "selected", "archived"] = "generated"


class ExperimentPlan(BaseModel):
    hypothesis_id: str
    research_question: str
    independent_variables: list[str]
    dependent_variables: list[str]
    control_condition: str
    target_users: str
    procedure: list[str]
    confounds: list[str] = Field(default_factory=list)
    ethics_notes: list[str] = Field(default_factory=list)
    success_criteria: list[str]
    sample_range: str
    stopping_rules: list[str]
    preregistration_status: Literal["draft", "preregistered"] = "draft"
```

第一版至少落地 `Evidence`、`Observation`、`ExperienceHypothesis`、`DesignBrief`、`DesignCandidate` 和 `Critique`，先跑通“候选评审 → 下一轮设计反馈”；`ExperimentResult` 留到真实实验闭环阶段。

---

## 5. 目标产品体验

用户输入一件产品及其资料后，系统应提供以下工作流：

1. **导入资料**：文字、图片、视频、规格、评论、访谈或传感器数据。
2. **事实层观察**：列出系统实际观察到的特征、动作和情境，并显示来源。
3. **心理机制映射**：检索相关框架，提出构念和机制，不把推断写成事实。
4. **体验假设**：生成条件、结果、替代解释和置信度。
5. **风险审阅**：检查暗黑模式、操控、隐私、过度拟人化和不当敏感推断。
6. **实验规划**：自动生成对照版本、变量、指标、样本和访谈问题。
7. **人工修订**：研究员可以接受、修改、驳回每条观察和假设。
8. **结果回填**：导入测试结果，更新假设状态和证据链。
9. **报告输出**：生成 Markdown/JSON，包含观察、推断、验证计划和未决问题。

### 5.1 默认报告结构

```text
1. 研究范围与输入资产
2. 产品和情境概览
3. 可观察物理特征
4. 可观察用户动作与交互机会
5. 心理机制假设
6. 体验预测与替代解释
7. 风险、伦理与隐私边界
8. 建议验证的实验
9. 当前已知、未知与不能推断的内容
10. 人工批注与决策记录
11. 证据索引
```

### 5.2 示例输出风格

不推荐：

> 柔软外壳让人产生安全感，因此应该采用柔性材料。

推荐：

> 观察：产品握持区使用柔性材料，图片中可见连续包覆结构（证据：image-03，区域 B）。
>
> 假设：在需要持续握持、无需快速定位按钮的任务中，柔性接触面可能降低触觉粗糙度和接触阻力，从而提高主观舒适度。替代解释包括产品重量、握持尺寸和温度。
>
> 验证：保持重量、尺寸和表面温度不变，仅比较硬/柔两种接触面，测量握持时长、错误率、舒适度评分和访谈中的自发描述。

### 5.3 面向 AI 设计的实际工作流

真正的使用方式应是“先定义体验，再生成形态，最后用证据筛选”，而不是让模型一次性给出一个看似完整的答案：

```text
DesignBrief
  ├─ 目标：在什么任务中帮助谁？
  ├─ desired：希望用户感到/做到什么？
  ├─ prohibited：绝对不能造成什么？
  └─ constraints：材料、成本、重量、隐私和制造限制
        ↓
AI Design Generator
        ↓ 生成 N 个 DesignCandidate
psyteardown observe + critique
        ├─ 事实：候选实际上包含什么
        ├─ 假设：可能影响什么体验
        ├─ 风险：哪些候选触发硬性否决
        ├─ 权衡：每个候选换来了什么、牺牲了什么
        └─ 修改：下一轮可以改变哪些具体变量
        ↓
按任务策略排序，而非按通用“心理分数”排序
        ↓
人选择 / 修改 / 驳回
        ↓
实验验证优先候选
        ↓
结果回填并进入下一轮生成
```

这里的 `AI Design Generator` 可以是外部图像、3D 或文本设计模型，也可以是未来新增的 provider。psyteardown 不要求自己负责生成所有设计，但必须提供稳定的设计候选输入与评审输出契约。

### 5.4 候选排序与选择规则

候选选择应采用“门槛 + 多目标权衡”，不要压缩为一个心理学总分：

1. 先检查硬约束和不可接受风险；触发硬约束的候选直接标记为 `blocked`。
2. 对剩余候选分别报告目标体验、风险、证据强度和未知项。
3. 根据 `DesignBrief.tradeoff_priorities` 进行条件性排序。
4. 将排序理由、未纳入因素和人工改动完整记录。
5. 只把经人确认的选择用于下一轮提示或实验，不让模型自我循环放大偏好。

可选的排序函数形式为：

```text
feasible(candidate)
  AND no_hard_risk(candidate)
  THEN rank_by(
      desired_experience_evidence,
      task_performance,
      user_control,
      privacy_cost,
      manufacturing_cost,
      unresolved_uncertainty,
      brief.tradeoff_priorities,
  )
```

这不是为了制造客观的“最佳设计”，而是让 AI 的偏好可以被人检查和改写。

### 5.5 AI 设计候选的证据等级

AI 生成的一张概念图不能证明真实触感、重量、阻尼或长期体验。系统必须按原型成熟度限制结论强度：

| 等级 | 可用输入 | 允许的结论 |
|---|---|---|
| L0 概念 | 文本、渲染图 | 形态/可见交互观察、探索性体验假设 |
| L1 规格 | 尺寸、材料、质量、结构参数 | 可制造性初筛、材料与人体尺度假设 |
| L2 功能样机 | 可操作原型、动作视频、传感器数据 | 操作、反馈、错误与行为层评审 |
| L3 用户实验 | 预注册测试、访谈、自报告和行为数据 | 对目标样本和情境的支持/反驳结论 |
| L4 现场使用 | 长期日志、真实环境反馈 | 外部效度、适用边界和长期副作用 |

输出置信度和措辞必须受证据等级约束。例如 L0 只能说“该视觉形态可能暗示可握持”，不能说“该材料会让用户持续握持更久”。

---

## 6. 总体技术架构

### 6.1 目标数据流

```text
DesignBrief / 产品输入
  ↓
AI Design Generator（可插拔外部模型）
  ↓
DesignCandidate Registry / 候选版本登记
  ↓
Asset Registry / 资产登记
  ↓
Observation Extractor / 事实观察层
  ↓
Context Builder / 情境与动作层
  ↓
Framework Retriever / 心理学与人因知识检索
  ↓
Hypothesis Generator / 体验假设生成
  ↓
Evidence Grounder + Claim Judge / 证据约束与支持性审查
  ↓
Critique + Tradeoff Evaluator / 候选评审与权衡
  ↓
Experiment Planner / 实验规划
  ↓
Human Selection / 人工选择、修改或驳回
  ↓
Next Design Prompt / 下一轮设计输入
  ↓
Report + Experiment Store / 报告与实验记录
  ↓
Approved Knowledge / 经过审批的知识增长
```

### 6.2 与当前架构的关系

保留现有模块：

- `kb`：继续管理心理学框架和原则。
- `pipeline`：保留文本模式，新增体验假设模式。
- `llm`：继续通过 provider 抽象访问模型。
- `memory`：扩展为案例、观察、假设和实验记忆。
- `growth`：保留候选知识 + 人工审批机制。
- `strategy`：增加“如何观察/如何设计实验”的策略卡。
- `review`：从单案例自评扩展到声明级审查。
- `mcp_server`：新增查询观察、生成实验计划和查看证据链的只读工具。

建议新增目录：

```text
src/psyteardown/experience/
├── models.py          # Observation / Hypothesis / ExperimentPlan
├── assets.py          # 输入资产登记与校验
├── observe.py         # 文本、图片、视频的事实层提取
├── contexts.py        # 任务、环境、社交情境建模
├── hypotheses.py      # 心理机制假设生成
├── judge.py           # 证据是否支持结论的审查
├── experiments.py     # 实验方案生成与预注册
├── critique.py        # 候选评审、硬风险和多目标权衡
├── design_loop.py     # DesignBrief → 候选 → 评审 → 下一轮输入
├── store.py           # SQLite 持久化与版本
└── render.py          # 体验假设报告
```

如果设计生成模型需要独立适配，可新增：

```text
src/psyteardown/design/
├── base.py             # DesignGenerator provider 接口
├── fake.py             # 离线测试生成器
└── adapters/           # 图像、3D、文本设计模型适配器
```

数据目录建议新增：

```text
src/psyteardown/data/
├── frameworks/        # 现有行为与认知框架
├── constructs/        # 控制感、认知负荷、信任、舒适等构念
├── modalities/        # 视觉、听觉、触觉、材料和动作词汇
└── measures/          # 可用量表、行为指标和实验操作化说明
```

---

## 7. 分阶段实现计划

以下以 12–16 周为一个可调整的个人项目周期。每个阶段都有可独立展示的产物，不要求先完成全部多模态能力。

### Phase 0：基线固化与评测基础（1–2 周）

**目标**：让后续每一次架构改动都有可比较的基线。

任务：

- [ ] 建立 `docs/superpowers/specs/` 中的路线图索引和版本记录。
- [ ] 给现有 `run_teardown` 增加 `run_id`、配置摘要和输入哈希。
- [ ] 固化现有 7–12 个产品案例为 golden fixtures。
- [ ] 将现有指标拆为事实准确性、证据覆盖率、框架选择、推理质量和报告可用性。
- [ ] 添加 `pytest` 全量 CI、类型检查和格式检查。
- [ ] 建立统一的离线评测命令：`psyteardown eval --suite baseline`。
- [ ] 记录模型、提示词版本、知识库版本和运行参数。

交付物：

- 基线评测报告。
- 一份指标字典。
- 每次运行可以复现的 JSON 产物。

验收标准：

- 同一 Fake provider 和输入重复运行，结构化输出完全一致。
- 真实模型运行至少保存模型、提示词、框架库和运行参数。
- 现有全量测试保持通过。

### Phase 1：观察层与体验本体（2–3 周）

**目标**：把“产品特征”和“心理解释”拆成两个层次。

任务：

- [ ] 新增 `experience.models`：`Evidence`、`Observation`、`PhysicalFeature`、`Context`。
- [ ] 为 `Mapping` 增加兼容转换：旧 Mapping 可以转成探索性 Hypothesis，但不反向覆盖旧数据。
- [ ] 实现文本观察器：从产品描述中提取可观察名词、动作、环境和限制条件。
- [ ] 实现人工校对 CLI：`psyteardown observations list/edit/approve`。
- [ ] 设计 30 个物理产品观察样本，覆盖手机、耳机、遥控器、门把手、杯子、穿戴设备和工具。
- [ ] 给每条观察绑定原文片段或资产定位。
- [ ] 增加“观察/报告/推断”字段级权限和状态。

交付物：

- 30 个产品的观察数据集。
- 可查看证据来源的观察报告。
- 观察层离线评测。

验收标准：

- 关键物理特征观察的人工复核 precision ≥ 0.85。
- 观察中未经来源支持的事实比例 ≤ 5%。
- 系统可以明确显示“未知”，不会强制补全。

### Phase 2：心理机制假设与声明级证据审查（2–3 周）

**目标**：让系统从“列出框架”变成“提出可争论的条件性假设”。

任务：

- [ ] 新增 `ExperienceHypothesis` 和 `Claim` 模型。
- [ ] 为构念增加操作化字段：定义、适用条件、可观察指标、常见混淆变量、参考文献。
- [ ] 将现有 step3 evidence grounding 扩展到图片/视频定位和访谈原话。
- [ ] 实现 claim judge：判断“证据是否支持该观察/假设”，而不是只判断证据是否存在。
- [ ] 输出替代解释和未验证假设。
- [ ] 做置信度校准，记录 Brier score 或 ECE，而不是只看模型自报分数。
- [ ] 增加对过度因果语言的静态检查，如“必然、证明、一定、导致”。

交付物：

- 每条假设带证据、条件、替代解释和验证状态。
- 一组包含真实编造、正确引用、错误因果和证据不相干的对抗样本。
- 声明级审查报告。

验收标准：

- 证据存在性检查 recall ≥ 0.95。
- 证据支持性审查在人工标注集上的 precision ≥ 0.80。
- 未验证假设不得被渲染为“已证实结论”。

### Phase 3：实验规划器（2–4 周）

**目标**：把“心理解释”转化为可以真的做的设计验证。

任务：

- [ ] 新增 `ExperimentPlan`、`Measure`、`ExperimentResult` 模型。
- [ ] 为常见构念建立测量字典：主观评分、行为指标、任务完成、错误率、恢复时间等。
- [ ] 根据假设自动生成最小对照设计：变量、控制条件、程序、样本和混淆变量。
- [ ] 要求每个实验声明哪些指标不用于推断，防止事后挑选。
- [ ] 增加预注册文件导出：Markdown + JSON。
- [ ] 支持人工修改实验方案并记录 revision。
- [ ] 建立“不可执行实验”拒绝规则，例如变量无法独立操纵、结果无法观测、伦理风险未处理。

交付物：

- 10 个假设对应的实验计划。
- 至少 3 个真实小实验的预注册文档。
- 实验计划质量评审表。

验收标准：

- 设计师/研究员人工评审中，可执行率 ≥ 80%。
- 每个实验都有明确自变量、因变量、对照、混淆变量和停止条件。
- 计划生成和结果分析分离，不能根据结果反向修改预注册判据。

### Phase 4：AI 设计反馈回路（2–3 周）

**目标**：让 psyteardown 的结果真正成为 AI 设计下一轮生成的输入，而不是停在评审报告。

任务：

- [x] 新增 `DesignBrief`、`DesignCandidate`、`Critique` 和 `DesignIteration` 模型。
- [ ] 定义 `DesignGenerator` provider 接口，使用 Fake generator 进行离线测试，不绑定具体图像或 3D 模型。
- [x] 实现 `generate → observe → critique → rank → revise` 的最小编排（M3 第一切片）；正式 DesignIteration revision 接入仍待补齐。
- [ ] 将设计目标拆成 desired experiences、prohibited experiences、hard constraints 和 tradeoff priorities。
- [x] 对每个候选生成机器可读的 `hard_risks`、`tradeoffs`、`actionable_changes` 和 `unknowns`。
- [x] 实现硬约束门槛与确定性风险/未知排序；禁止使用一个没有语义的“心理学总分”替代决策。
- [x] 生成下一轮设计提示包：保留目标、指出待修变量、附上证据和待验证假设。
- [ ] 记录候选父子关系、版本、人工选择和被驳回原因。
- [ ] 使用 3 个设计任务和每个任务 5 个候选，测试排序稳定性、反馈可执行性和错误否决。

建议接口：

```python
generate_candidates(brief: DesignBrief, *, n: int) -> list[DesignCandidate]
critique_candidate(candidate: DesignCandidate, brief: DesignBrief) -> Critique
rank_candidates(brief: DesignBrief, critiques: list[Critique]) -> list[str]
build_next_prompt(brief: DesignBrief, selected: DesignCandidate,
                  critique: Critique) -> str
```

交付物：

- 一个 AI 设计候选评审器，可对文本、图片描述或外部模型返回的候选进行评审。
- 一份候选比较报告，显示证据、风险、权衡和下一轮修改。
- 一份机器可读的设计反馈 JSON，可直接喂给设计生成模型。
- 一个完整的两轮设计迭代案例。

验收标准：

- psyteardown 不生成未经证据支持的硬性否决。
- 每个排序结果都能追溯到设计 brief 中的目标、约束或权衡优先级。
- 每条 `actionable_changes` 至少指向一个可操作变量，而不是抽象形容词。
- 人工可以覆盖模型排序，并保留覆盖理由。
- 将同一候选以不同顺序输入，不改变其评审结论。

### Phase 5：多模态和身体交互输入（4–6 周）

**目标**：让系统开始理解真实物理产品，而不是只读文本。

第一版范围应保持克制：图片、短视频、规格和人工输入优先；不一开始做实时全身识别。

任务：

- [ ] 新增 `Artifact` 注册和本地文件哈希。
- [ ] 图片观察：形态、材质表面、按钮、开口、尺度参照、可见反馈。
- [ ] 视频观察：拿起、按压、旋转、靠近、放下等动作片段及时间区间。
- [ ] 允许用户手动修正模型识别的区域、动作和时间段。
- [ ] 加入产品规格和材料信息的结构化导入。
- [ ] 音频只提取经同意的事件特征；默认不保存原始私人录音。
- [ ] 预留 IMU、压力、触觉和环境传感器输入适配器，不把实时传感器作为本阶段前置条件。
- [ ] 报告中区分“模型看见的内容”和“模型根据内容推测的意义”。

交付物：

- 15 个带图片/视频的物理产品案例。
- 至少 5 个动作片段的人工标注集。
- 多模态观察报告和误判案例库。

验收标准：

- 关键区域/动作的人工复核一致率 ≥ 0.80。
- 视频时间定位误差有明确记录，不得伪装成精确动作识别。
- 缺失模态时系统能降级，不因没有视频或传感器而编造观察。

### Phase 6：实验结果闭环与知识增长（3–5 周）

**目标**：把系统从一次性报告工具变成会积累但不会自动污染的研究系统。

任务：

- [ ] 导入实验结果、用户反馈和观察日志。
- [ ] 将假设状态更新为 `supported`、`rejected`、`inconclusive` 或 `needs_replication`。
- [ ] 保存原始数据、分析脚本、统计结果和人工解释。
- [ ] 从多个案例中提出“候选机制”或“候选设计规律”。
- [ ] 候选知识必须引用至少 3 个独立案例或实验，并通过人工审批。
- [ ] 记录被拒绝的候选，防止系统重复消耗人力提出相同错误规律。
- [ ] 增加跨人群、跨文化、跨场景的适用范围字段。

交付物：

- 完整闭环案例：观察 → 假设 → 实验 → 结果 → 结论 → 审批。
- 候选知识审查台账。
- 一份“已支持规律、未确定规律、已拒绝规律”目录。

验收标准：

- 未经审批的候选知识不会影响默认检索。
- 每条已批准规律都能回链到原始案例和实验。
- 复现实验或反例可以将状态从 supported 降级为 needs_replication。

### Phase 7：交付层与真实合作场景（持续）

**目标**：让系统能被设计、研究和工程团队使用，同时保持证据边界。

任务：

- [ ] MCP 只读工具：`observe_product`、`list_hypotheses`、`plan_experiment`、`show_evidence`。
- [ ] CLI 管理工具：实验创建、预注册、结果导入、审批和版本对比。
- [ ] 面向团队的 Web review UI，优先实现证据审阅而不是复杂仪表盘。
- [ ] 导出 Figma/Notion/Markdown 友好的研究报告。
- [ ] 通过一个真实硬件或移动设备案例验证端到端使用。
- [ ] 将用户访谈和设计师反馈纳入产品路线，而不是只凭自我评估扩展功能。

交付物：

- 一个可公开演示的完整案例。
- 一份 5–8 分钟产品演示视频。
- 一份包含反例和失败分析的技术/研究文章。

---

## 8. 详细模块实现计划

### 8.1 `experience/models.py`

实现顺序：

1. `Asset`、`Evidence`。
2. `Observation`、`Context`。
3. `ExperienceHypothesis`。
4. `ExperimentPlan`、`ExperimentResult`。
5. `Approval`、`Revision`。

要求：

- 所有概率字段使用 `0–1` 约束。
- 所有状态使用枚举，不使用自由字符串。
- 每个对象带稳定 ID、创建时间、来源运行 ID和版本。
- 旧 JSON 可以继续通过 Pydantic 反序列化。
- 新字段必须有默认值，避免破坏现有案例库。

### 8.2 `experience/assets.py`

职责：

- 登记输入文件、媒体类型、哈希、尺寸、时长和隐私等级。
- 通过哈希避免重复导入。
- 保存本地路径或受控引用，不把私人媒体默认复制到远程服务。
- 为图片区域、视频区间和音频事件提供 locator 格式。

建议接口：

```python
register_asset(path: Path, *, privacy: PrivacyLevel) -> Asset
get_asset(asset_id: str) -> Asset
add_locator(asset_id: str, locator: AssetLocator) -> AssetLocator
```

### 8.3 `experience/observe.py`

输入：资产 + 产品描述 + 可选人工提示。

输出：观察列表，不输出心理结论。

每条观察必须回答：

- 观察对象是什么？
- 观察到的属性或动作是什么？
- 来自哪一个来源位置？
- 是模型观察、用户报告还是人工确认？
- 有哪些看不清或不能判断的地方？

建议使用两段式：

```text
模型候选观察 → 确定性 schema / 来源校验 → 人工确认 → 进入假设生成
```

### 8.4 `experience/contexts.py`

情境至少拆成：

- 任务：用户要完成什么？
- 环境：噪声、光线、移动、拥挤、私人/公共。
- 社交：独处、与人交谈、被他人观察。
- 时间：首次使用、长时间使用、任务切换、恢复阶段。
- 风险：误操作成本、隐私后果、安全后果。

不能让模型用一个“用户情绪”字段替代完整情境。

### 8.5 `experience/hypotheses.py`

假设生成模板：

```text
在 [人群/任务/环境] 下，
当 [物理特征/交互行为] 出现时，
它可能通过 [心理机制] 影响 [体验或行为结果]，
替代解释包括 [混淆变量]。
```

每次生成都要求模型至少给出一个替代解释。模型无法给出替代解释时，置信度上限为探索性级别。

### 8.6 `experience/judge.py`

第一阶段使用规则 + LLM 双层审查：

- 规则层：来源存在、locator 有效、引用长度、敏感词和绝对化表达。
- LLM 层：证据是否支持观察、观察是否支持假设、因果强度是否过高。
- 人工层：高风险结论、候选规律和实验结果最终审批。

LLM judge 只能返回审查意见，不能直接修改原始证据或批准知识。

### 8.7 `experience/experiments.py`

实验规划器必须生成：

- 研究问题。
- 可操作的自变量和水平。
- 控制条件。
- 因变量与测量方式。
- 样本和纳入/排除标准。
- 操作步骤。
- 潜在混淆变量。
- 伦理与隐私说明。
- 预先锁定的成功判据。
- 哪些指标明确不用于结论。

对于无法独立操纵的心理机制，只能生成探索性研究或访谈方案，不能伪装为因果实验。

### 8.8 `experience/critique.py`

该模块负责把候选设计变成可供生成器消费的反馈，而不是重新生成一篇散文报告。

评审顺序固定为：

1. 读取 `DesignBrief`，确定当前目标、禁区和硬约束。
2. 读取候选的设计事实，确认评审对象到底包含什么。
3. 生成条件性体验假设，并绑定构念、证据和未知项。
4. 检查硬风险和不可接受的体验后果。
5. 输出权衡和最小可操作修改。
6. 生成实验优先级和下一轮提示片段。

反馈必须区分三种语言：

- `blocked`：违反硬约束或触发明确安全/隐私风险，不建议进入下一轮。
- `revise`：没有被否决，但某个具体变量需要改变。
- `explore`：证据不足，优先做实验，不应直接修改成“更好”。

禁止输出只有形容词的反馈，例如“更自然”“更有温度”“更高级”。每条建议必须能回指到材料、尺寸、阻尼、反馈模态、时机、可见性或交互步骤等变量。

### 8.9 `experience/design_loop.py`

该模块是 psyteardown 与外部 AI 设计模型之间的编排层，负责保存每轮设计上下文，不负责替人决定最终方案。

设计生成器通过窄接口接入，避免把 psyteardown 和某个图像、3D 或文本模型绑定：

```python
class DesignGenerator(Protocol):
    def generate(self, brief: DesignBrief, *, n: int) -> list[DesignCandidate]: ...

    def revise(
        self,
        brief: DesignBrief,
        selected: DesignCandidate,
        feedback: Critique,
    ) -> list[DesignCandidate]: ...
```

生成器可以返回渲染图、结构描述、材料配置或多种资产的引用，但必须同时返回一份可供 psyteardown 观察的候选描述。模型看不到的物理属性必须标记为未知，不能由评审层补全。

一轮迭代至少保存：

- `brief_snapshot`：本轮目标、禁区和约束的快照。
- `candidate_ids`：生成的候选版本。
- `critique_ids`：每个候选的评审版本。
- `ranking_policy`：本轮使用的排序优先级。
- `human_selection`：人选择、修改或驳回的动作。
- `next_prompt`：下一轮传给设计生成器的结构化输入。
- `decision_note`：人为什么接受或覆盖模型建议。

建议的最小编排：

```python
def run_design_iteration(brief, generator, *, n_candidates: int) -> DesignIteration:
    candidates = generator.generate(brief, n=n_candidates)
    critiques = [critique_candidate(c, brief) for c in candidates]
    ranked = rank_candidates(brief, critiques)
    return save_iteration(brief, candidates, critiques, ranked)
```

实际系统中 `human_selection` 必须是独立步骤。没有人的选择或明确的自动化授权，不能直接把排名最高的候选喂回生成器，避免偏好自我强化。

### 8.10 存储与迁移

继续使用 SQLite，但新增版本化表：

```text
assets
design_briefs
design_candidates
critiques
design_iterations
observations
contexts
hypotheses
evidence_links
experiment_plans
experiment_results
approvals
revisions
```

迁移原则：

- 不改写既有 `cases.result` 原始 JSON。
- 通过只读适配器将旧 `Mapping` 映射成探索性假设。
- 所有升级有 migration 编号和回滚说明。
- 删除操作默认软删除，保留审计记录。

---

## 9. 知识库扩展计划

现有知识库以行为、说服、习惯和认知框架为主。物理产品方向需要增加“人因与测量”层，而不是无限增加心理学名词。

### 9.1 构念库优先级

第一批建议：

- 控制感 / perceived control
- 认知负荷 / mental workload
- 可供性与行动可能性 / affordance
- 反馈明确性 / feedback clarity
- 信任与可预测性 / trust and predictability
- 舒适、接触阻力与持续使用意愿
- 注意力切换与任务恢复
- 社交可见性、尴尬和隐私边界
- 错误恢复与安全感
- 自主性、胜任感和归属感

### 9.2 每个构念必须包含

- 定义和边界。
- 学术出处。
- 可以观察的产品线索。
- 不能从线索直接推断的内容。
- 可操作化的行为指标或量表。
- 常见替代解释。
- 伦理注意事项。
- 适用人群、文化或情境限制。

### 9.3 引用管理

参考文献需要有稳定 ID、标题、作者、年份和链接/DOI（如有）。模型只能从白名单引用，禁止自由生成看似学术的出处。

---

## 10. 评测方案

不能只用“报告读起来不错”评价系统。评测应分层。

### 10.1 观察层

- 特征提取 precision / recall / F1。
- 动作和情境标注一致率。
- 来源定位有效率。
- 观察与推断混淆率。

### 10.2 证据层

- 证据存在性 recall。
- 证据支持性 precision。
- 证据与结论的相关性。
- 未溯源事实比例。
- 绝对化或过度因果表述比例。

### 10.3 心理映射层

- 框架/构念 precision@k。
- 专家对机制解释的相关性评分。
- 替代解释覆盖率。
- 跨情境一致性和适用边界识别率。

### 10.4 实验规划层

- 自变量和因变量完整率。
- 对照条件完整率。
- 混淆变量识别率。
- 可执行性人工评分。
- 预注册判据是否在结果后被改写。

### 10.5 AI 设计反馈层

- 候选事实提取准确率。
- 候选评审与人工专家判断的一致率。
- 硬风险漏报率：应阻止的候选没有被阻止的比例。
- 错误否决率：没有触发硬风险却被阻止的比例。
- `actionable_changes` 可执行率。
- 反馈后下一轮候选是否真正改变了指定变量。
- 候选排序对 `DesignBrief` 目标和权重的可追溯率。
- 人工覆盖率及覆盖理由完整率。
- 设计迭代后目标体验改善、任务性能和隐私成本的变化。

### 10.6 可靠性与校准

- 置信度分箱准确率。
- Brier score / ECE。
- 相同输入多次运行的关键结论稳定性。
- 合理同义改写后的排序和状态稳定性。
- 缺少模态、损坏文件和 provider 失败时的降级行为。

### 10.7 推荐最低发布门槛

这些是第一版对外演示门槛，不是科学真理：

| 指标 | 最低门槛 |
|---|---:|
| 关键观察事实人工复核 precision | ≥ 0.85 |
| 证据存在性 recall | ≥ 0.95 |
| 证据支持性审查 precision | ≥ 0.80 |
| 未溯源产品事实比例 | ≤ 5% |
| 可执行实验计划比例 | ≥ 0.80 |
| 候选评审反馈可执行率 | ≥ 0.80 |
| 硬风险漏报率 | 0 |
| 高风险结论未经人工审批比例 | 0 |
| 敏感状态无依据断言 | 0 |

每个指标都必须附样本量、标注规则和失败样例，不能只报一个百分比。

---

## 11. 测试计划

### 11.1 单元测试

- Pydantic 模型边界与旧 JSON 兼容。
- evidence locator 和归一化。
- 绝对化语言检测。
- 状态迁移和审批规则。
- 实验判据冻结。

### 11.2 编排测试

- Fake provider 跑通文字模式和体验假设模式。
- 每个阶段失败可局部降级，不吞掉错误。
- 多模态缺失时只跳过相关观察，不凭空生成。
- judge 拒绝时原始输出仍可追溯。
- Fake design generator 跑通候选生成、评审、排序、人工覆盖和下一轮提示生成。
- 设计候选输入顺序改变时，评审结论保持稳定。
- 候选触发硬风险时不会被下一轮提示自动恢复为可选方案。

### 11.3 回归与扰动测试

- 同义改写不应改变关键证据归属。
- 增加无关产品细节不应改变核心假设排序。
- 调换图片顺序不应改变资产 ID 对应关系。
- 修改一个物理参数时，只有相关假设发生变化。

### 11.4 对抗测试

- 输入中明确要求“不要承认未知”。
- 图片中不存在的按钮或徽章。
- 视频动作与文字描述冲突。
- 原文存在真实句子，但不支持模型选择的心理机制。
- 诱导模型生成敏感心理诊断。
- 低置信度案例被重复写入知识库。

### 11.5 人工评审

每个阶段至少保留：

- 一条成功案例。
- 一条合理但不确定的案例。
- 一条明确失败案例。
- 一条模型拒答或降级案例。

没有失败案例的测试套件不能证明护栏有效。

---

## 12. 安全、隐私与伦理

物理产品分析很容易接触图片、视频、声音和行为数据，因此隐私不是附录，而是产品架构的一部分。

### 12.1 默认策略

- 原始媒体默认本地保存，不默认上传。
- 人脸、声音和可识别个人信息默认脱敏或不进入模型。
- 传感器数据优先存特征和时间区间，不存不必要的原始流。
- 用户可删除资产、观察和实验记录；删除行为有审计记录。
- 报告明确“未测量”“未验证”和“不能推断”。

### 12.2 高风险触发人工审查

- 涉及健康、情绪或心理诊断。
- 涉及未成年人。
- 涉及工作场所监控或绩效判断。
- 涉及公共空间的身份和行为追踪。
- 可能用于操控、成瘾或剥夺用户选择权的设计。

### 12.3 伦理报告结构

每个项目至少输出：

- 潜在受益者。
- 可能受损者。
- 被影响的自主性和隐私。
- 误判后果。
- 用户如何退出、纠正或撤回数据。
- 是否需要伦理审查或额外同意。

---

## 13. 项目优先级与明确不做

### 13.1 优先级

优先实现：

1. 观察层和证据模型。
2. 假设与证据支持性审查。
3. 实验规划与预注册。
4. 人工审阅和知识审批。
5. AI 设计反馈回路。
6. 图片/短视频输入。
7. 真实项目闭环。

暂缓实现：

- 实时读取用户情绪。
- 依赖复杂可穿戴硬件的端到端推断。
- 自动从互联网抓取并直接写入知识库。
- 对用户体验给出单一总分。
- 让 psyteardown 自动决定并发布最终设计。
- 先做一个大而全的 Web dashboard。
- 训练自有大模型。

### 13.2 MVP 定义

MVP 不需要实时硬件和复杂多模态模型。最小可行版本是：

- 产品文字 + 3–5 张图片 + 可选短视频。
- 可追溯的物理特征和动作观察。
- 3–5 条条件性体验假设。
- 每条假设至少一个替代解释。
- 自动生成一份可执行对照实验方案。
- 对多个 AI 设计候选生成逐条、可追溯的体验评审和下一轮修改建议。
- 人工可以逐条批准、修改或驳回。
- 导出包含证据和未知边界的 Markdown/JSON 报告。

这已经足够证明项目从“心理拆解报告”升级成“物理产品体验研究工具”。

---

## 14. 建议的首个端到端试点

首个试点不应只是“分析一个现成产品”，而应完整演示一次 AI 设计反馈回路。选择一个不涉及高风险个人数据、又能体现物理差异的产品，例如：

- 耳机充电盒。
- 手机支架或手机壳。
- 桌面 AI 设备外壳。
- 具有旋钮、按压和灯光反馈的控制器。

先定义设计 brief：

- 目标：为需要低打扰交互的移动 AI 设备设计一个可持续握持的交互部件。
- 目标体验：可预测、可控、安静。
- 禁止体验：强迫打断、监视感、公共场景尴尬。
- 硬约束：单手操作、可制造、低功耗、隐私友好。

让设计模型先生成 5 个候选，再由 psyteardown 分别观察、评审和排序。试点问题示例：

> 不同的握持材料、按钮阻尼和反馈方式，如何影响用户对设备可预测性、控制感和持续使用意愿的体验？

首个试点只控制 2–3 个变量：

- 硬质 vs 柔性接触面。
- 短按确认 vs 长按确认。
- 立即反馈 vs 延迟反馈。

测量：

- 任务完成率。
- 错误率。
- 反应时间。
- 任务切换后的恢复时间。
- 主观控制感和舒适度。
- 访谈中的自发描述。

每轮至少记录：

- AI 设计候选原始输出。
- psyteardown 识别的设计事实。
- 条件性体验假设、风险和未知项。
- 具体的下一轮修改建议。
- 人最终选了哪个候选、覆盖了什么建议以及为什么。

该试点不需要宣称普遍心理规律，只需要展示：系统能帮助 AI 生成更可解释、更可质疑、更容易验证的设计候选，并把实验结果反馈到下一轮设计。

---

## 15. 12 周实施排期

| 周期 | 主要工作 | 可交付物 |
|---|---|---|
| 第 1–2 周 | 基线、CI、评测套件、运行元数据 | baseline report、golden cases |
| 第 3–4 周 | 观察本体、证据模型、文本观察器 | 30 个观察案例 |
| 第 5–6 周 | 假设模型、构念库、claim judge | 声明级证据审查 |
| 第 7–8 周 | 实验规划器、测量字典、预注册导出 | 10 份实验计划 |
| 第 9 周 | AI 设计反馈回路、Fake generator、候选排序 | 3 个设计任务、15 个候选 |
| 第 10 周 | 图片/短视频输入和人工修正 | 15 个多模态案例 |
| 第 11 周 | 实验结果导入、状态更新和候选知识 | 一个设计—实验闭环 |
| 第 12 周 | MCP/报告交付、演示视频、失败复盘 | 可公开作品集版本 |

如果时间不足，优先完成第 1–9 周。一个“设计 brief → 多个候选 → 证据化评审 → 人工选择 → 下一轮提示”的闭环，比一个不稳定的实时多模态系统更有说服力。

---

## 16. 发布前检查清单

### 产品定位

- [ ] 首页和 README 使用“体验假设与验证系统”，没有承诺读心或自动判断用户心理。
- [ ] 清楚说明观察、解释、预测和验证的区别。
- [ ] 至少展示一个被推翻或暂不确定的假设。
- [ ] 至少展示两轮 AI 设计：第一轮候选、评审反馈、人工选择和第二轮修改。

### 证据与可靠性

- [ ] 每条事实都能回链到来源。
- [ ] 每条假设都有条件、替代解释和置信度。
- [ ] 低置信度和失败输出可见。
- [ ] claim judge 的误判有样例和统计。
- [ ] 所有自动知识增长都经过人工审批。

### 实验

- [ ] 实验有明确自变量、因变量、对照和混淆变量。
- [ ] 成功判据在执行前已锁定。
- [ ] 结果不能反向改写预注册判据。
- [ ] 报告中区分支持、反驳、不确定和未重复验证。

### 隐私与伦理

- [ ] 原始媒体的保存、上传和删除策略有说明。
- [ ] 敏感推断和高风险项目默认进入人工审查。
- [ ] 用户有纠正、退出和删除路径。

### 工程

- [ ] 旧案例 JSON 仍可读取。
- [ ] 全量离线测试和评测命令通过。
- [ ] 真实模型运行可记录版本和参数。
- [ ] MCP 对外工具不包含自动审批和知识写入权限。
- [ ] DesignGenerator 与 psyteardown 通过稳定 JSON 契约连接，可替换具体生成模型。
- [ ] 不允许未经过人工选择的候选无限自动循环生成。

---

## 17. 最终判断

psyteardown 最值得发展的不是“再增加几个心理学框架”，而是成为 AI 设计系统中的体验推理和反馈层，建立一套稳定的中间语言：

> **物理特征如何通过人的动作、情境和心理机制，可能形成某种体验；这个可能性怎样被证据和实验确认、修正或推翻。**

短期内，它可以成为一个有证据边界的 AI 设计评审与反馈工具；中期可以成为 AI 硬件和物理交互团队的体验假设、候选排序与实验规划基础设施；长期才有机会积累出跨产品、跨材料和跨情境的体验知识库。

真正的成功标准不是“模型说得像不像心理学家”，而是：

1. 它能否把观察和推断分开。
2. 它能否让假设变得可争论、可验证。
3. 它能否帮助团队更快发现关键设计变量。
4. 它能否诚实地保留未知、反例和失败。
5. 它能否把真实世界的实验结果安全地沉淀为下一轮设计能力。
6. 它能否让 AI 设计从“凭经验抽卡”变成“生成—评审—选择—验证—再生成”的可解释循环。

如果按本文档推进，psyteardown 会从一个“心理驱动型拆解 Agent”逐步变成一个真正连接材料、产品、人因和 AI 的研究系统。
