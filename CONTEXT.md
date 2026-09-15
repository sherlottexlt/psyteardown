# psyteardown 设计体验评审上下文

本上下文描述 psyteardown 在 AI 物理产品设计流程中的角色、对象和决策边界。

## 语言

**AI 设计生成器（AI Design Generator）**：根据设计目标、使用情境和约束，发散提出一个或多个产品设计候选的外部系统。它负责探索设计空间，不负责决定候选是否被采用。
_避免使用_：最终设计者、自动设计裁判

**设计候选（Design Candidate）**：一个可被讨论、比较、修改或验证的产品设计方案。候选可以是概念级方案，也可以是带规格、样机或真实使用证据的方案。
_避免使用_：设计答案、最佳方案

**体验评审（Experience Critique）**：针对设计候选，基于可观察事实、使用情境和心理机制假设，对可能的体验、风险、权衡和未知项进行结构化分析。
_避免使用_：心理评分、用户喜欢度预测

**设计反馈（Design Feedback）**：由体验评审产生、能够指向具体材料、形态、动作、反馈方式或交互时机的下一轮修改建议。
_避免使用_：泛化建议、审美意见

**人工选择（Human Selection）**：人基于设计目标、评审证据、约束和个人判断，对候选进行接受、修改、驳回或要求验证的决策行为。
_避免使用_：人工兜底、最后点名

**体验评审层（Experience Review Layer）**：连接 AI 设计生成器与人工选择的系统角色，负责观察、提出假设、暴露风险、说明权衡和生成可操作反馈，但不拥有最终采用权。
_避免使用_：自动设计决策器、心理学打分器

**设计证据等级（Design Evidence Level）**：表示一个设计候选当前拥有的可验证证据范围，用来限制评审结论的强度。L0 为概念输入，L1 为带物理规格的候选，L2 为可操作样机，L3 为经过用户实验的候选。
_避免使用_：设计成熟度分数、心理可信度分数

**候选输入契约（Candidate Input Contract）**：设计候选进入体验评审层时必须提供的结构化信息，包括设计描述、交互故事、目标情境和已知未知项；渲染图和规格属于可选证据，不等于真实物理体验。
_避免使用_：一张图、设计 prompt

**设计简报（Design Brief）**：一次设计任务的目标用户、使用情境、期望体验、禁止体验、硬约束和权衡优先级的明确声明。候选评审只在某个设计简报的范围内比较，不产生脱离任务的“最佳设计”。
_避免使用_：需求 prompt、审美偏好

**候选排序（Candidate Ranking）**：在先满足硬约束和风险门槛后，根据设计简报中的目标体验和权衡优先级比较候选的过程。排序不是心理学总分，也不取代人工选择。
_避免使用_：最佳设计评分、自动选型

**评审状态（Critique Status）**：体验评审对候选或候选问题的行动结论。`blocked` 表示触发硬约束或严重风险，`revise` 表示需要修改具体设计变量，`explore` 表示证据不足、应优先验证而非直接断言优劣。
_避免使用_：通过/不通过、好/坏

**可操作修改（Actionable Change）**：能够指向材料、尺寸、形态、阻尼、反馈模态、交互步骤、时机或可见性等具体设计变量的反馈。抽象形容词不构成可操作修改。
_避免使用_：优化体验、增强亲和力

**下一轮设计提示（Next Design Prompt）**：由已确认的设计简报、候选评审反馈和人工选择共同形成，传递给下一轮 AI 设计生成器的结构化输入。未经人工确认的评审草案不能成为下一轮设计约束。
_避免使用_：自动反思、模型自我迭代

**评审回灌（Critique Feedback Injection）**：将人工确认后的评审状态、证据、权衡和可操作修改写入下一轮设计生成上下文的过程。
_避免使用_：自动循环、反馈自学习

**可解释候选排序（Explainable Candidate Ranking）**：在硬约束筛选后，依据设计简报中的目标和权衡优先级展示候选的相对顺序、证据、代价和未知项。排序供人比较，不代表自动采用。
_避免使用_：最佳设计评分、自动选出冠军

**候选偏序（Candidate Partial Order）**：不强制给所有候选排列完整名次，而根据设计简报和证据将候选分为 Preferred、Viable Alternatives、Needs Evidence 和 Blocked，并允许并列或不可比较。
_避免使用_：排行榜、1–N 名次

**体验维度判断（Criterion Assessment）**：候选在某个 DesignBrief 体验维度上的序数判断，取 strong_support、support、neutral、risk、strong_risk 或 unknown，并绑定 ReviewItem 和证据。
_避免使用_：维度分数、心理百分比

**评审项聚合（Review Item Aggregation）**：将人工确认的 ReviewItem 按 DesignBrief 体验维度和确定性规则汇总为 Criterion Assessment 的过程。LLM 可以建议映射，但不能直接决定候选层级。
_避免使用_：模型综合评分、总结打分

**设计一致性（Design Alignment）**：候选的已确认设计事实与 DesignBrief 某个目标体验或约束的结构性一致程度，取 strong_support、support、neutral、risk、strong_risk 或 unknown。它不证明真实用户结果。
_避免使用_：用户体验效果、心理有效性

**结果证据强度（Outcome Evidence Strength）**：支持某个体验结果的实证证据等级，取 none、exploratory、observed、supported 或 replicated。`supported` 至少要求一次预注册实验满足主要指标判据、条件呈现可验证、分析运行可复现且经人工 Result Review；`replicated` 还要求新的参与者样本和新的 AnalysisRun 按相同或兼容协议得到一致方向。该等级独立于设计一致性。
_避免使用_：模型置信度、设计成熟度

**范围排除（Scope Exclusion）**：V1 明确不接受的设计任务类型，例如医疗诊断、儿童心理操控或工作绩效监控。命中范围排除时，项目不能通过普通人工覆盖继续执行。
_避免使用_：高风险提示、低优先级项目

**批准风险规则（Approved Risk Rule）**：经人审查并版本化批准的确定性高风险条件，可与确认事实匹配并触发 blocked。每条规则具有稳定 ID、适用范围、证据要求和解除条件。
_避免使用_：模型风险判断、心理学警告

**风险候选（Risk Candidate）**：LLM 根据 ReviewItem 提出的潜在高风险问题，必须经过人工审查并映射到现有规则或形成候选规则；它本身无权阻断设计候选。
_避免使用_：自动阻断、风险事实

**风险规则候选（Risk Rule Candidate）**：由人或 AI 提出的声明式规则草案，包含条件、证据要求、适用范围和解除条件；只有人工批准后的版本才能被规则引擎执行。
_避免使用_：动态规则、自动安全策略

**重新评审（Re-evaluation）**：使用新的规则、机制库或评审版本，对既有不可变候选事实快照创建新的评审 revision。它不覆盖历史评审。
_避免使用_：自动更新旧结果、回填修改

**反馈效用（Feedback Utility）**：评审反馈是否能被设计者或下一轮生成器理解并转化为具体设计变量的改变，而不是反馈文字是否流畅或听起来专业。
_避免使用_：文案质量、模型自评得分

**设计迭代改善（Design Iteration Improvement）**：在同一设计简报和预先声明的评价维度下，后一轮候选相对于前一轮在约束满足、目标体验、风险或可验证性上的可观察变化。它不等于“后一轮一定更好”。
_避免使用_：自动优化、模型进步

**第一版产品范围（V1 Product Scope）**：AI 移动设备及其配件，包括桌面 AI 设备、耳机盒、手机壳、可握持控制器和随身交互物件。第一版候选输入由文本描述、2D 渲染图、交互故事和已知规格构成。
_避免使用_：通用物理产品平台、全量多模态产品分析

**第一版体验主题（V1 Experience Themes）**：低打扰、控制感、可预测性、隐私边界、握持体验与反馈方式。这些主题用于约束第一版构念库和评审数据集。
_避免使用_：所有心理状态、通用用户喜欢度

**情境化介入（Contextual Intervention）**：AI 设备根据用户当前任务、环境、社交状态和设备关系，决定是否介入、何时介入以及使用何种反馈模态的设计问题。第一版以注意力任务中的情境化介入为核心场景。
_避免使用_：智能提醒、主动服务

**介入变量（Intervention Variables）**：第一版可被评审和修改的具体设计变量，包括反馈模态、反馈时机、确认动作、设备可见性、介入强度和撤销/延后机制。
_避免使用_：交互体验、智能程度

**第一版最小可行产品（V1 MVP）**：不依赖真实硬件的两轮 AI 设计反馈闭环。输入为设计简报和多个包含文本、2D 图像、交互故事及已知规格的候选；输出为体验评审、人工选择、下一轮反馈候选和一份可执行实验计划。
_避免使用_：硬件原型、完整产品

**L2 物理验证**：在可操作样机上验证触觉、握持、反馈可辨识性和现场介入效果的后续阶段，不属于 V1 MVP 的必要条件。
_避免使用_：MVP 必须接硬件

**体验领域（Experience Domain）**：负责 AI 物理产品设计候选的观察、体验假设、评审、人工选择、设计反馈和实验规划的新领域模块。它与现有文本拆解 `pipeline` 并存，不直接重写旧流程。
_避免使用_：新版 pipeline、pipeline v2

**旧流程适配器（Legacy Pipeline Adapter）**：将现有文本拆解产物（例如 `Mapping`）转换为体验领域可读取的探索性观察或假设，但不修改旧案例的原始结果。
_避免使用_：数据迁移覆盖、旧模型重写

**评审项（Review Item）**：针对一个设计候选中的单个物理/交互事实，在特定情境下形成的一组证据、体验假设、风险、权衡、状态和可操作修改。它是体验评审的最小可追踪、可人工确认和可实验验证单位。
_避免使用_：评价点、意见条目

**候选级评审（Candidate Critique）**：一个设计候选下所有评审项的汇总，包括整体风险、权衡、排序信息和下一轮反馈摘要；它不能替代评审项的证据链。
_避免使用_：总评、心理总分

**分层证据（Layered Evidence）**：按来源和证明能力区分的证据结构，包括设计事实证据、使用情境证据、心理/人因机制证据和真实结果证据。不同证据等级只能支持相应强度的评审结论。
_避免使用_：证据分数、模型依据

**设计事实（Design Fact）**：候选输入中可以直接观察或由规格明确声明的产品属性、交互步骤或反馈行为。设计事实不等于用户体验结果。
_避免使用_：设计意图、心理事实

**体验预测（Experience Prediction）**：在指定用户、任务和环境条件下，对候选可能造成的体验或行为结果的条件性推断。没有真实结果证据时，它必须保持为预测或假设。
_避免使用_：体验结论、用户一定会

**机制卡（Mechanism Card）**：心理/人因知识库中的可复用知识单元，包含机制定义、适用条件、反例、可观察线索、混淆变量、可测指标和伦理风险；机制卡不规定固定产品形态。
_避免使用_：设计配方、心理学组件

**设计启发式（Design Heuristic）**：从特定 DesignBrief、设计案例或实验中归纳的、带适用情境和证据范围的设计经验。它不能被当作普遍心理机制或固定设计配方。
_避免使用_：心理规律、最佳实践

**V1 机制范围（V1 Mechanism Set）**：第一版默认启用的八类机制：注意力切换与打断成本、认知负荷、控制感/可撤销性/可恢复性、反馈明确性与可预测性、介入显著性与信号发现、可供性与动作映射、隐私边界与社交可接受性、自动化信任与依赖校准。说服和上瘾类框架默认只用于风险审查。
_避免使用_：全量心理学知识库、正向设计配方

**V1 候选规模（V1 Candidate Batch）**：每个 DesignBrief 第一轮生成 5 个候选，人工选择 1–2 个方向，第二轮为每个选定方向生成 3 个变体。该规模用于验证候选比较和反馈闭环，不代表生产环境的搜索上限。
_避免使用_：穷举搜索、最佳方案搜索

**候选发散矩阵（Candidate Divergence Matrix）**：在生成前声明候选应探索的介入变量和策略方向，例如反馈模态、介入时机、确认动作、设备可见性和介入强度。它用于检验候选是否有真实设计差异，不是审美随机化。
_避免使用_：随机抽卡、风格变化

**设计策略方向（Design Strategy Direction）**：候选针对 DesignBrief 选择的一组权衡优先级，例如低打扰优先、可发现性优先、用户控制优先、隐私优先或紧急场景优先。
_避免使用_：模型风格、候选标签

**生成无效（Generation Invalid）**：候选在进入事实确认前缺少必填输入、资产损坏、与冻结简报不匹配，或违反可直接确定的生成约束，因此不能进入正式评审。它不同于事实冻结后由体验、安全或隐私规则触发的 blocked。
_避免使用_：低质量候选、评审不通过

**生成约束（Generation Constraint）**：候选导入时即可确定的形式或规格要求，例如必填交互故事、重量上限、资产格式或策略方向。违反它会产生 generation_invalid。
_避免使用_：体验风险、心理约束

**体验/安全约束（Experience/Safety Constraint）**：需要在候选事实确认并绑定使用情境后判断的隐私、安全、控制权或体验边界。命中批准规则时会产生 blocked。
_避免使用_：输入校验、生成格式

**材料体验变量（Material Experience Variable）**：候选中可声明、比较和验证的材料/物理属性，包括表面柔顺性、纹理、接触热感、质量分布、握持几何、按键阻力和触觉传递。它们用于形成体验假设，不等于工程性能结论。
_避免使用_：材料好坏、用户触感事实

**材料声明一致性评审（Material Claim Review）**：检查候选的材料声明是否完整、是否与使用情境明显冲突、是否足以支持体验假设，以及还需要哪些样机或实验数据。它不包含工程仿真、寿命、精确成本、工艺或认证判断。
_避免使用_：材料工程验证、可制造性认证

**材料属性卡（Material Property Card）**：描述一种可测物理属性、单位、测量方法、适用条件、典型范围和来源的知识单元。它不包含用户心理结果或固定设计建议。
_避免使用_：材料体验卡、材料心理标签

**材料属性目录（Material Property Catalog）**：由版本化材料属性卡组成的独立知识库，通过 ExperienceHypothesis 与机制卡和体验结果关联。
_避免使用_：心理机制库、材料选型器

**材料属性候选（Material Property Candidate）**：AI 从候选声明、可信材料文档或真实测量记录中提取的结构化属性草案。候选必须经过单位、条件、来源和人工确认后才能成为材料属性卡。
_避免使用_：自动材料数据、模型补全值

**V1 种子阻断规则（V1 Seed Blocking Rules）**：第一版默认启用的六类窄规则：公共场景默认外放私人内容、持续感知但缺少可见状态和快速关闭、非紧急主动介入不可撤销、不确定用户状态推断被伪装为事实且不可纠正、非必要私人原始数据未经授权离开本地、安全关键任务中的非紧急强制介入。
_避免使用_：通用伦理评分、所有体验风险

**事件紧急等级（Event Criticality）**：由冻结 DesignBrief 中人工批准的事件分类表赋予的 critical、important 或 routine 等级。AI 不能自行提升事件等级。
_避免使用_：模型认为重要、通知优先级

**最低必要介入（Minimum Necessary Intervention）**：即使事件为 critical，也只使用当前情境下足以让用户安全感知和响应的最低介入强度，而不是默认采用最强声音、视觉或触觉反馈。
_避免使用_：紧急就全力提醒、最高优先级打断

**情境推断声明（Context Inference Declaration）**：设计候选关于设备将如何推断用户任务、环境或社交状态的结构化声明，包括推断状态、置信度、信号来源、用户纠正方式、低置信度降级和误判后果。V1 评审该声明，不实现识别模型。
_避免使用_：用户状态事实、情绪识别结果

**介入许可（Intervention Permission）**：某个情境推断在指定置信度、事件紧急等级和用户授权下，最多允许触发何种反馈模态与介入强度的声明。它不能由 AI 在运行时自行扩大。
_避免使用_：模型觉得可以提醒、自动权限

**情境误判成本（Context Misclassification Cost）**：情境推断发生 false positive 或 false negative 时，对任务连续性、隐私、安全和用户控制造成的具体后果。
_避免使用_：模型误差、准确率损失

**视觉观察器（Vision Observer）**：从候选图片中生成 Observation Draft 的模型角色，只描述可见事实和不可观察项，不生成心理体验结论。
_避免使用_：多模态评审模型、视觉理解器

**评审推理器（Review Reasoner）**：基于冻结候选事实、DesignBrief 和机制卡生成 ReviewItem Draft 的模型角色，不补充未确认设计事实，也不决定最终候选层级。
_避免使用_：自动产品设计师、心理裁判

**声明审查器（Claim Judge）**：检查 ReviewItem 中证据支持性、因果强度和证据等级越界的模型角色。它不能修改原始证据、自动确认评审项或触发 blocked。
_避免使用_：真相模型、自动审批器

**发散缺口（Divergence Gap）**：候选批次未覆盖发散矩阵要求的关键变量或设计策略方向。合法候选仍可保存和查看，但批次在补齐前不能进入正式跨候选比较。
_避免使用_：候选太少、设计不够好

**机制冲突（Mechanism Tension）**：同一候选在不同情境或目标下同时支持彼此牵制的体验机制，例如即时反馈提高可发现性却增加注意力负担。冲突必须显式呈现为权衡，不能被压缩成单一心理分数。
_避免使用_：模型矛盾、平均心理效果

**情境化权衡（Contextual Tradeoff）**：在明确用户、任务、环境和设计简报优先级后，对一个候选获得的体验收益与承担的成本进行并列说明。权衡不是“平均分”，而是支持人工选择和实验优先级的决策材料。
_避免使用_：综合体验分、总体感觉

**可解除阻断（Unblock Condition）**：一个 `blocked` 评审在何种明确设计修改、情境限制、用户授权或新增证据满足后，可以重新进入评审。它必须与阻断证据和适用范围绑定。
_避免使用_：模型改口、例外处理

**探索项（Explore Item）**：证据不足、机制冲突未解决或多个解释仍然合理的评审项。探索项必须产生下一步验证问题或实验方案，不能作为已证实优点或缺点参与强排序。
_避免使用_：不确定意见、低分项

**验证任务（Validation Task）**：由 `explore` 评审项生成的结构化下一步，包含研究问题、竞争假设、比较条件、测量指标、混淆变量和最低证据要求。验证任务是实验规划的输入，不等于实验已经执行。
_避免使用_：待研究、后续看看

**变量修复追踪（Variable Repair Trace）**：记录一条 `actionable_change` 指定的设计变量，是否在下一轮候选中实际发生了预期改变，以及改变后评审项的状态如何变化。
_避免使用_：模型自评改好了、版本变了

**反馈采用（Feedback Adoption）**：下一轮候选的具体设计变量是否实际响应了上一轮的可操作修改。它与问题是否解决、候选是否整体变好是三个不同判断。
_避免使用_：提示词被看到了、文本变相似

**问题改善（Issue Improvement）**：在指定 ReviewItem 和相同评审条件下，上一轮识别的问题在下一轮是否变为改善、未变、恶化或无法判断。它需要证据或人工评审，不能由“反馈采用”自动推出。
_避免使用_：模型修复成功、分数提升

**人工覆盖（Human Override）**：人对模型评审、候选排序或阻断状态作出的接受、修改、驳回、覆盖或要求补充证据的结构化决策。覆盖保留原模型输出并形成新 revision，必须有理由、作者和时间。
_避免使用_：手动改掉、人工兜底

**覆盖理由（Override Rationale）**：解释人工为什么接受、修改或推翻模型判断的短文本或证据集合，必须能指向设计简报、候选规格、情境差异或新增研究证据。
_避免使用_：备注、个人感觉

**评测标注集（Evaluation Annotation Set）**：由多位具有不同专业背景的标注者，对设计事实、ReviewItem 质量和跨轮反馈结果进行结构化判断的数据集。它用于评测系统，不自动进入生产知识库。
_避免使用_：测试 prompt、专家意见集合

**标注分歧（Annotation Disagreement）**：标注者因设计事实边界、情境适用性、心理机制或风险阈值不同而产生的差异。分歧本身需要保留并分析，不能未经讨论强行平均。
_避免使用_：噪声、谁对谁错

**分歧处置（Disagreement Resolution）**：根据分歧类型采用证据回查、情境拆分、竞争假设或保持未解决的处理过程。处置不等于消除分歧，而是明确下一步如何获得更强证据。
_避免使用_：投票平均、专家拍板

**设计简报快照（Design Brief Snapshot）**：在一轮候选生成前经人确认的 DesignBrief 版本，冻结该轮的目标用户、情境、期望/禁止体验、硬约束和权衡优先级。候选排序和评审只能引用对应快照。
_避免使用_：当前 prompt、临时需求

**简报版本（Brief Revision）**：当设计目标、用户、情境、硬约束或权衡优先级发生变化时创建的新 DesignBrief 版本。不同版本之间的候选排序和迭代结果不能直接比较。
_避免使用_：悄悄改需求、同一任务继续跑

**下一轮设计提示包（Next Design Prompt）**：经人确认后传给 AI 设计生成器的结构化输入，包含冻结的简报快照、选定方向、确认的可操作修改和探索任务。它不是完整评审报告，也不包含未经确认的模型意见。
_避免使用_：把报告塞回 prompt、自动反思文本

**确认反馈（Confirmed Feedback）**：人工明确接受、修改或授权进入下一轮的评审项或可操作修改。只有确认反馈才能影响下一轮设计约束。
_避免使用_：模型建议、候选意见

**设计意图（Design Intent）**：设计者或 AI 生成器声明希望产品实现的体验、行为或关系目标。它描述目标，不证明用户实际感受。
_避免使用_：用户体验、心理事实

**体验结果（Observed Outcome）**：在样机、用户测试或真实使用中实际观察、测量或由参与者报告的结果，必须绑定结果证据和研究条件。
_避免使用_：模型预测、设计效果

**证据冲突（Evidence Conflict）**：两个或多个来源对同一个设计事实、交互行为或规格给出不一致声明的状态。冲突必须被记录、分类和解决或保持未解决，不能被模型静默覆盖。
_避免使用_：模型选择、输入噪声

**不可观察（Not Observable）**：当前证据无法确认某个属性存在或不存在的状态。它不同于“属性不存在”，只能限制评审结论强度。
_避免使用_：没有、模型漏看

**不可变候选版本（Immutable Candidate Revision）**：候选、资产、评审和 DesignBrief 的一次固定快照，创建后不被覆盖；后续变化通过新的 revision 和 parent-child 关系表达。
_避免使用_：更新原候选、覆盖版本

**设计提示包（Design Prompt Package）**：由冻结简报和人工确认反馈生成、用于外部 AI 设计工具的结构化生成输入，可导出为 Markdown 和 JSON。它与生成后的候选输入契约相互独立。
_避免使用_：普通提示词、完整评审报告

**人工导入生成器（Manual Import Generator）**：把外部 AI 设计工具生成的文本、图片、交互故事和规格转换为 DesignCandidate 的适配器。它不负责调用或控制外部生成模型。
_避免使用_：手工设计、无生成器

**声明事实（Declared Fact）**：由候选导入者明确提供的材料、尺寸、重量、交互行为或其他设计属性。声明事实表示设计方案声称包含该属性，不证明它已经在物理样机中实现。
_避免使用_：真实规格、已验证事实

**观察事实（Observed Fact）**：视觉模型或人工从候选资产中直接可见的形态、部件、相对位置或动作线索。观察事实不得扩展到图片无法确认的材料、触感、内部结构或性能。
_避免使用_：模型理解、视觉推理结论

**观察草案（Observation Draft）**：视觉模型从候选资产中提出、尚未经人工确认的观察候选。观察草案不能支持正式 `blocked` 或确定性修改要求。
_避免使用_：视觉事实、自动标注结果

**确认观察（Confirmed Observation）**：经人接受或修订后，可进入 ReviewItem、体验假设和正式评审的观察事实。被驳回或标记不可观察的草案保留用于误差分析。
_避免使用_：模型确认、自动事实

**候选事实冻结（Candidate Facts Frozen）**：候选的声明事实、确认观察、不可观察项和已解决/未解决冲突形成不可变事实快照的状态。只有该状态下的候选可以生成正式 ReviewItem。
_避免使用_：事实大致确认、直接开始分析

**高风险事实（High-Risk Fact）**：会影响隐私、安全、用户控制或 `blocked` 判断的设计事实，例如外放语音、持续监听、不可撤销介入或公开显示个人信息。高风险事实必须逐条人工确认。
_避免使用_：重要事实、模型高置信事实

**审阅工作台（Review Workspace）**：承载 DesignBrief 冻结、候选导入、事实确认、ReviewItem 审阅、候选比较、人工覆盖和下一轮提示确认的本地 Web 界面。它是 V1 的主要人工决策入口。
_避免使用_：管理后台、报告页面

**修订记录（Revision Record）**：领域对象的一次不可变版本，包含父版本、作者、时间和变化原因。对象的当前状态通过 current revision 引用读取，历史版本不被覆盖。
_避免使用_：更新记录、覆盖保存

**审计事件（Audit Event）**：追加记录一次领域动作的时间、操作者、目标和摘要，用于追踪决策过程；系统不依赖重放全部审计事件恢复当前业务状态。
_避免使用_：事件溯源事件、日志文本

**阶段门（Workflow Gate）**：只有前置状态和所需人工确认均满足时才能通过的工作流边界，例如简报冻结、候选事实冻结、评审确认、人工选择和下一轮提示确认。
_避免使用_：流程提示、可选步骤

**领域状态错误（Domain State Error）**：对象因状态或前置条件不满足而拒绝操作时返回的明确错误。系统不能通过自动补齐、静默跳转或覆盖旧版本绕过阶段门。
_避免使用_：接口失败、系统异常

**体验评审流水线（Experience Review Pipeline）**：从冻结候选事实开始，依次执行情境绑定、机制检索、ReviewItem 生成、声明审查、设计反馈和候选汇总的显式多阶段流程。每个阶段保存独立输入、输出和模型版本。
_避免使用_：一个大 prompt、端到端评审

**声明审查（Claim Judge）**：检查 ReviewItem 中的证据是否支持观察和假设、因果措辞是否超过证据等级、是否存在未声明假设的审查步骤。它提出审查结果，不自动批准或改写原始证据。
_避免使用_：模型裁判、事实生成器

**声明审查结果（Claim Judgement）**：对单条 ReviewItem 的 supported、partially_supported、unsupported 或 overclaimed 判断，附带证据与理由。它是人工审阅信号，不是真值或最终裁决。
_避免使用_：事实判决、自动批准

**模型角色隔离（Model Role Isolation）**：即使不同角色复用同一个底层模型，也通过独立调用、不同 system prompt、无共享对话历史和最小必要输入保持职责隔离。
_避免使用_：同一对话多角色、自我反思

**模型步骤尝试（Model Step Attempt）**：一次模型角色对固定输入快照和 prompt 版本的调用记录，包含原始输出、解析结果、校验错误和运行参数。重试创建新尝试，不覆盖旧尝试。
_避免使用_：一次分析、最新模型结果

**首次合法输出（First Valid Output）**：同一模型步骤自动重试过程中，第一个通过 Schema 和确定性证据校验的输出。V1 默认采用它，不在多个合法输出中由模型自选“最佳”。
_避免使用_：最优回答、最终模型意见

**角色随机性策略（Role Sampling Policy）**：根据模型角色职责配置生成随机性；VisionObserver 和 ClaimJudge 优先稳定，ReviewReasoner 允许有限发散。正式评测冻结该策略及其 provider 参数。
_避免使用_：统一 temperature、完全确定性

**正式评测运行（Evaluation Run）**：使用冻结的输入、模型、prompt、采样参数、机制库和规则库版本执行的可比较运行。探索模式输出不能与正式评测结果直接混用。
_避免使用_：随便跑一次、最好的一次

**后台任务（Background Job）**：由本地工作台创建并持久化的耗时模型步骤，具有幂等键、明确状态、进度、尝试次数和错误信息。任务执行与 HTTP 请求生命周期分离。
_避免使用_：后台线程、长请求

**内容寻址资产（Content-Addressed Asset）**：按文件内容 SHA-256 标识并存放的本地原始或派生资产。数据库保存 asset_id、相对路径、来源、隐私等级和父子关系，不保存媒体二进制。
_避免使用_：绝对文件路径、数据库图片字段

**资产定位器（Asset Locator）**：ReviewItem 或 Observation 指向某个资产内具体区域、帧或时间区间的稳定引用，由 asset_id 和定位信息构成。
_避免使用_：截图描述、临时路径

**本地会话（Local Session）**：只允许本机前端访问本地 API 的随机会话令牌边界。它不是多用户身份认证，但用于阻止其他网页未经授权调用本地写接口。
_避免使用_：用户账号、无认证本地服务

**资产传输策略（Asset Transfer Policy）**：按资产隐私等级决定是否允许将原始或派生媒体发送给远程 provider，包括 remote_allowed、confirm_each_run 和 local_only。
_避免使用_：全局上传开关、默认同意

**数据传输清单（Data Transfer Manifest）**：一次远程模型运行实际要发送的 provider、模型、资产、派生版本、文本字段、用途和脱敏状态的不可变记录。没有对应授权时，任务停在 awaiting_consent。
_避免使用_：隐私提示、上传日志

**来源不可用（Source Unavailable）**：原始证据资产已被用户删除或无法访问，但历史 Observation、ReviewItem 和审计记录仍保留的状态。相关结论必须降低可验证性，不能假装证据仍可查看。
_避免使用_：证据不存在、删除评审

**Provider 数据政策（Provider Data Policy）**：远程模型服务关于内容保留、训练使用、区域和删除能力的声明。敏感资产只有在策略明确满足项目要求时才可发送。
_避免使用_：默认隐私、模型安全承诺

**展示包（Showcase Export）**：用于作品集和沟通的轻量导出，包含简报、候选、已确认评审、权衡、人工选择、跨轮变化和实验摘要，默认不包含私人原始资产、完整 prompt、模型原始响应或内部审计。
_避免使用_：完整项目备份、复现包

**可复现项目包（Reproducible Project Bundle）**：用于继续研究和技术审查的版本化导出，包含 manifest、修订记录、经授权资产、事实快照、ReviewItem、规则/机制版本、模型尝试、人工决策、变量追踪和评测配置。
_避免使用_：展示报告、普通压缩包

**预注册实验（Preregistered Experiment）**：在执行前由人锁定研究问题、竞争假设、变量、测量、成功判据、停止规则和不用于推断的指标的实验版本。执行后不能静默修改这些字段。
_避免使用_：实验草案、事后计划

**预注册修订（Preregistration Amendment）**：实验开始前对预注册字段进行版本化修改，保留旧版本、修改原因、时间和批准人，并重新锁定判据和分析结构。
_避免使用_：覆盖预注册、改计划不留痕

**协议偏离（Protocol Deviation）**：实验开始后实际执行与当前预注册不一致的记录，包含偏离字段、原因、发生时间、影响和处理，不修改原预注册。
_避免使用_：实验修正、事后调整

**实验开始事件（Experiment Started Event）**：第一项不可逆的正式用户暴露或数据收集行为发生时发出的 Domain Event，例如首个参与者进入正式任务、首次呈现研究条件、首次写入正式研究数据。它锁定当前预注册版本。
_避免使用_：页面打开、预览、排练

**正式样本（Formal Sample）**：符合预注册纳入/排除条件并进入正式任务、其数据可用于主要/次要分析的参与者集合。招募、筛选和排练不自动属于正式样本。
_避免使用_：所有报名者、测试人员

**参与者状态（Participant Study Status）**：研究参与者在 candidate、screened、enrolled、formal_sample_member、withdrawn、excluded 或 completed 等阶段的状态，按预注册和同意记录转换。
_避免使用_：用户账户状态、数据有无

**退出与缺失分离（Withdrawal-Missing Separation）**：参与者主动退出、筛选排除、任务未完成和单个测量缺失分别记录，不能把任何一种统一编码为 no_response。
_避免使用_：缺失就是拒绝、退出就是无响应

**缺失类型（Missingness Type）**：OutcomeObservation 中对缺失原因的结构化分类，包括 participant_withdrawal、task_abandonment、technical_failure、skipped_by_protocol、no_response 和 not_applicable，影响分析处理但不自动解释为体验方向。
_避免使用_：空值、未完成就是负反馈

**预注册缺失策略（Preregistered Missingness Policy）**：在实验执行前锁定各种缺失类型的分析处理、阈值、排除规则和敏感性分析方式。执行后改变需新分析/预注册 revision。
_避免使用_：结果出来再选缺失处理

**任务完成结果（Task Completion Outcome）**：一次正式任务的结构化结果，包括 completed_successfully、completed_with_assistance、abandoned_by_participant、blocked_by_interface、blocked_by_hardware、blocked_by_protocol、timeout、safety_stop 或 data_unavailable 等类型及原因证据。
_避免使用_：成功/失败二元标签、未完成就是设计失败

**完成原因证据（Completion Cause Evidence）**：支持任务完成/未完成分类的参与者自述、观察记录、系统日志、研究者标注或协议记录。没有足够来源时结果必须为 unknown。
_避免使用_：模型猜失败原因、事后解释

**研究者干预（Researcher Intervention）**：实验过程中研究者对参与者、设备、任务说明或技术问题的帮助、提示、纠正、暂停或安全处置，必须独立记录并按预注册策略处理。
_避免使用_：现场帮忙、无影响提示

**干预后数据（Post-Intervention Data）**：发生研究者干预后收集的任务/体验数据。它不能默认与无干预数据合并，需按干预类型、影响和预注册分析策略处理。
_避免使用_：正常完成数据、可直接比较

**盲法状态（Blinding Status）**：参与者、任务执行者、观察/编码者和分析者对候选条件及假设的知情状态，包括 blinded、partially_blinded、not_feasible 和 unblinded，以及揭盲时间/原因。
_避免使用_：不知道模型答案、默认无偏差

**随机条件标签（Randomized Condition Label）**：与设计语义和候选优劣脱钩的 condition-xx 标签，用于降低参与者、执行者和编码者因名称产生的期待偏差。
_避免使用_：低打扰版、高级版本

**条件分配设计（Condition Allocation Design）**：在预注册中声明采用 within-subject、between-subject 或混合设计，以及条件随机分配、顺序平衡、洗脱和参与者聚类处理方式。
_避免使用_：随意分组、先做再决定

**重复任务聚类（Repeated-Task Clustering）**：同一参与者多次任务/条件数据在分析中按 participant_id 关联处理的规则，避免把重复观测误当独立样本。
_避免使用_：样本量叠加、每次任务一个人

**最小差异实验（Minimal-Difference Experiment）**：围绕一个主要假设，尽量只操纵一个主要 DesignVariable，并保持其他设计、情境和任务条件一致的验证设计。无法做到时必须声明共同变化和组合性结论边界。
_避免使用_：单变量证明、只改一个就一定因果

**组合设计结论（Compositional Design Conclusion）**：多个设计变量同时变化时，只能对该变量组合在指定情境下的整体表现作出的结论，不能归因于其中任一单独变量。
_避免使用_：单因素效果、拆开归因

**多因素实验（Factorial Experiment）**：同时操纵两个或更多 DesignVariable 的实验设计。V1 可保存、导出和导入外部分析，但交互效应默认 exploratory，不能自动拆成单变量因果结论。
_避免使用_：多个 patch 一起就能分别证明

**主要操纵变量（Primary Manipulated Variable）**：ExperimentPlan 中预注册、优先用于解释主要结果的单一 DesignVariable。组合实验可以没有唯一单变量解释，但必须显式标记。
_避免使用_：最重要的模型参数、结果最好的变量

**条件快照（Condition Snapshot）**：实验中一个可呈现条件的不可变版本，绑定候选 revision、结构化变量值、介入序列、场景、资产/样机、说明、环境、随机化角色、同意范围和内容哈希。
_避免使用_：条件名称、可编辑实验配置

**实际呈现条件（Actual Presented Condition）**：参与者实际看到/操作的条件记录，绑定 Condition Snapshot、设备/软件运行日志、校准状态和偏离记录。它是 OutcomeObservation 的条件来源。
_避免使用_：预注册条件、研究者记忆

**条件呈现记录（Condition Presentation Record）**：每次参与者暴露于某实验条件时记录实际 candidate/asset/config hash、设备/软件版本、校准、呈现时间、暴露时长、偏离和验证状态的记录。
_避免使用_：条件名称、实验者回忆

**呈现未验证（Presentation Unverified）**：无法证明参与者实际呈现与 Condition Snapshot 一致的状态。相关结果不能作为主要 Outcome Evidence，只能按预注册策略做 exploratory 或剔除。
_避免使用_：大致呈现、条件默认一致

**最小事件日志（Minimal Event Log）**：只记录条件呈现、反馈、用户响应、技术可靠性、任务边界和研究者干预所需字段的日志，不保存无关长期行为或原始音视频。
_避免使用_：全量行为日志、设备监控

**设备单调时间（Device Monotonic Time）**：设备内不受系统时钟回拨影响的事件顺序时间，用于计算反馈时序、反应时间和延迟；必要时另存 UTC 对齐信息。
_避免使用_：前端显示时间、仅靠墙上时钟

**离线日志缓冲（Offline Log Buffer）**：设备在网络不可用时对最小事件日志进行本地加密、追加式保存，并在恢复后按 sequence 幂等上传的机制。
_避免使用_：实时上传、内存临时日志

**日志完整性不确定（Log Integrity Uncertain）**：事件 sequence 缺失、hash 链冲突、缓冲溢出或时钟质量不足导致无法确认日志完整顺序/内容的状态。相关条件呈现和结果证据需降级。
_避免使用_：日志自动修复、缺一条无影响

**项目日志密钥（Project Log Key）**：由设备安全存储管理、只用于某个研究项目离线事件日志的 AEAD 加密密钥。密钥不写入 SQLite、日志或默认导出包。
_避免使用_：全局日志密钥、固定默认密钥

**密钥版本（Key Version）**：项目日志密钥轮换时递增的标识；旧日志保留其 key_version，新日志使用新版本，不能通过覆盖旧密钥改变历史加密语义。
_避免使用_：密码更新、重新加密覆盖

**密钥不可用（Key Unavailable）**：设备无法从 OS Keychain/Secure Enclave/TPM 解封项目日志密钥的状态。系统保留受保护的本地日志并停止上传，不降级到明文或默认密钥。
_避免使用_：上传失败、自动恢复密钥

**项目恢复密钥（Project Recovery Key）**：用于在受控迁移中解封某项目历史日志密钥、而非直接替代项目密钥的独立密钥包。它与项目包分开保存、加密包裹并受用途/过期/吊销限制。
_避免使用_：项目密码、默认备份密钥

**受控项目迁移（Controlled Project Migration）**：在新设备或新本地项目中导入项目快照、资产和历史日志的手工流程，必须验证 manifest/hash、导入恢复密钥并保留删除/限制状态。
_避免使用_：复制项目文件夹、无审计迁移

**迁移后授权（Post-Migration Authorization）**：项目迁移后对新设备、provider、模型、政策或资产派生版本重新确认的远程传输授权。历史 Consent Record 作为研究用途记录保留，但不等于新设备可发送。
_避免使用_：授权自动继承、迁移即同意

**实例比较（Instance Comparison）**：对不同 Project Instance 的候选、条件或实验结果进行兼容性检查后形成的独立比较 revision，带 comparable、conditionally_comparable 或 not_comparable 状态。
_避免使用_：跨设备直接比、项目合并

**比较兼容性（Comparison Compatibility）**：两个实例在 Brief、场景、候选/条件、变量词汇、机制/规则、协议、分析、样本和资产完整性上的可比较程度。它先于任何统计或体验差异计算。
_避免使用_：相似就能比较、模型判断等价

**条件化比较（Contextual Comparison）**：在部分依赖不同但差异已明确的实例之间进行的描述性比较，只展示方向、条件和限制，不进入正式偏序、启发式支持或因果结论。
_避免使用_：有条件的最佳、近似因果

**复现实验提案（Replication Proposal）**：由条件化比较产生的、要求统一 Brief、场景、条件和协议后重新验证差异的结构化研究提案。
_避免使用_：自动验证、比较结果确认

**可合并（Poolable）**：多个 Project Instance 的结果通过独立 Pooling Compatibility 检查，满足同意、协议、测量、样本和分析要求，可合并到新的 Derived Dataset/AnalysisRun 的状态。它强于 comparable。
_避免使用_：可以比较就能合并、样本直接相加

**实例效应（Instance Effect）**：设备、软件、地点、招募批次、研究者或时间窗口等实例差异对结果的潜在影响。合并分析前必须声明、控制或标记未处理。
_避免使用_：环境噪声、可忽略批次差异

**实例效应状态（Instance Effect Status）**：跨实例结果合并前对实例差异处理程度的分类，包括 controlled、measured、adjusted、suspected 或 unknown。它限制 poolable 资格和结论强度。
_避免使用_：批次差异分数、默认可忽略

**池化审批（Pooling Approval）**：人对满足 Pooling Compatibility 的跨实例结果合并申请进行的结构化批准，绑定分析计划、同意范围、实例效应处理和新数据集/分析版本。
_避免使用_：自动合并、样本相加

**证据强度变更（Evidence Strength Change）**：由人工 Result Review 基于独立复现、样本、协议一致性、跨实例一致性和限制，对 Outcome Evidence Strength 作出的版本化升降记录。池化本身不能触发变更。
_避免使用_：样本更多自动升级、统计显著即证实

**独立经验复现（Independent Empirical Replication）**：在新的参与者集合、新的正式实验运行和新的 AnalysisRun 上，按相同或兼容协议重新检验同一假设；实验室、研究团队或设备型号可以相同，但必须记录并评估 Instance Effect。重复使用参与者、原始数据、模型调用或仅重算统计脚本不构成独立经验复现。
_避免使用_：重复计算、模型重跑、样本相加

**池化提案（Pooling Proposal）**：在 Pooling Approval 前汇总实例、数据集、协议、条件、测量、样本、同意、实例效应、缺失策略、分析计划、收益和风险的结构化申请。
_避免使用_：合并请求、数据拼接

**分层池化（Stratified Pooling）**：经批准后在同一分析框架下保留并报告各实例分层结果的跨实例分析方式，不将实例差异压缩成单一平均结论。
_避免使用_：平均池化、合并后不分组

**撤回优先（Withdrawal Precedence）**：参与者当前的用途撤回、限制或过期状态优先于迁移包中的历史授权；迁移不能恢复已撤回或受限用途。
_避免使用_：旧授权覆盖撤回、迁移恢复权限

**结果审阅（Result Review）**：对实验原始结果、分析版本、预注册判据和限制条件进行人工审阅后，决定假设状态为 supported、rejected、inconclusive 或 needs_replication 的过程。
_避免使用_：模型读结果、自动结论

**确定性分析（Deterministic Analysis）**：由版本化脚本按预注册指标计算描述统计、对照差异、缺失/异常和适用的效应量。它是结果审阅的数值基础，不由模型自由生成。
_避免使用_：LLM 统计、模型读表

**探索性结果（Exploratory Result）**：方向或模式值得继续研究，但样本、设计、预注册或证据强度不足以支持正式结论的结果状态。
_避免使用_：半支持、差不多证明

**设计启发式观察（Heuristic Observation）**：单个案例或实验中的局部、情境绑定观察，只回链原始证据，不作跨案例泛化。
_避免使用_：规律、最佳实践

**设计启发式候选（Design Heuristic Candidate）**：由多个相关案例或较完整实验支持、但仍需边界和人工审查的情境化设计经验。它默认不影响设计生成。
_避免使用_：已验证规律、机制卡

**已批准设计启发式（Approved Design Heuristic）**：满足独立支持、反例/边界、混淆变量和适用范围要求并经人批准的设计经验，只能作为下一轮建议参考，不能替代 DesignBrief 或触发 blocked。其支持资格只能由真人结果提供，至少需要两个独立且达到 `supported` 或更高的经验支持单元，并至少跨越一个 Brief、场景或候选族；专家判断、模拟用户和模型一致性不能单独计为支持案例。
_避免使用_：自动设计规则、心理定律

**启发式支持变量一致性（Heuristic Support Variable Consistency）**：计入同一设计启发式的经验支持单元，必须共享明确的抽象设计变量及其可操作化映射；仅因结果方向相似而把不同操纵变量的实验事后拼接，不构成同一启发式的支持。
_避免使用_：事后归纳同因、组合结果冒充单变量证据

**启发式前瞻性检验（Prospective Heuristic Test）**：在启发式归纳者之外，对已预先锁定的启发式文本、适用范围、变量映射、主要指标和成功判据进行的新案例检验。未完成该检验前，经验只能保持为 `Heuristic Candidate`，不能批准为 `Approved Design Heuristic`。
_避免使用_：事后套用、看完结果再定规则

**启发式前瞻性准入结果（Prospective Heuristic Admission Result）**：启发式前瞻性检验至少达到 `supported` 才能作为批准依据；`observed`、`exploratory`、`needs_replication` 或 `inconclusive` 只能维持 `Heuristic Candidate`，明确冲突则必须创建新 revision 并缩小范围或保留未决。
_避免使用_：一次观察即批准、检验失败仍发布

**批准启发式的反例处置（Approved Heuristic Counterexample Handling）**：批准后的有效反例不删除历史证据；安全、隐私或控制权反例可立即暂停受影响范围的新注入，普通体验反例触发 Evidence Impact Analysis 和待复核状态。复核后只能收窄适用范围、创建新 revision 或废弃，不能静默修正文案维持原批准状态。
_避免使用_：反例覆盖历史、静默改规则

**有效启发式反例（Valid Heuristic Counterexample）**：仅当新结果满足预注册的样本与冲突判据、条件呈现可验证、分析运行可复现，并在启发式声明的适用范围内得出相反方向时，才构成有效反例；低样本、协议偏离、呈现未验证或不可复现的结果只能标记 `needs_replication`/`inconclusive`。
_避免使用_：统计无力即反例、失败运行即推翻

**启发式范围扩张（Heuristic Scope Expansion）**：已批准启发式跨越未声明的任务、用户、设备、场景或风险条件时，只能作为 `validation-only` 参考；新结果不能自动计入原启发式支持或扩大其范围。范围扩张必须创建新启发式 revision，预先锁定新情境、变量映射、主要指标和成功判据，并完成新的前瞻性检验。
_避免使用_：跨场景自动泛化、结果反向扩权

**启发式结果绑定（Heuristic Outcome Binding）**：每个启发式 revision 必须绑定一个明确的结果假设或结果族及其主要指标；多个体验结果分别保存证据绑定。未经联合预注册和组合分析，单一结果的支持不能替其他结果背书，也不能合并成一条多结果因果结论。
_避免使用_：一个结果证明全部体验、事后拼接联合结论

**结果型启发式与机制分离（Outcome Heuristic–Mechanism Separation）**：结果证据稳定但机制未被直接测量或操纵时，仍可批准为结果型设计启发式；机制解释必须标为未验证假设或竞争解释，不能据此创建或升级 Mechanism Card。机制知识需另行经过文献审查或机制层实验。
_避免使用_：结果稳定即机制证实、启发式自动变机制卡

**启发式独立支持单元（Independent Heuristic Support Unit）**：用于启发式资格计数的支持单元必须具有独立参与者集合、独立正式数据生成运行和独立假设检验；同一实验项目内拆分条件、指标、重复分析或 AnalysisRun 不能伪装成多个独立支持单元。
_避免使用_：拆分分析凑复现、同一实验多计数

**启发式外部独立检验（External Independent Heuristic Test）**：同团队的独立复现可以推进 Outcome Evidence Strength，但 Approved Design Heuristic 还必须至少有一次由未参与启发式归纳的外部团队执行，或由结果盲法的独立分析者完成的前瞻性检验；该检验用于降低共同来源偏差，不改变独立复现的定义。
_避免使用_：同团队重复即无偏、换团队即自动可信

**外部检验无力处置（Underpowered External Heuristic Test）**：外部前瞻性检验有效但属于 `inconclusive` 时，不计入启发式支持或反例；未批准的启发式保持 `Heuristic Candidate`，已批准启发式暂停范围扩张和新的资格累积，直至完成足够有力的新外部检验。历史注入、候选和结果保留。
_避免使用_：无力结果即反例、历史启发式自动删除

**外部独立性验证（External Independence Verification）**：启发式外部前瞻性检验必须记录归纳团队与执行/分析团队边界、检验前锁定的启发式与判据、揭盲前结果隔离、沟通/脚本变更审计和独立数据处理。研究者若能在揭盲前影响筛选、清洗或分析，结果标记 `limited_independence`，不得满足启发式批准门槛。
_避免使用_：换机构即独立、口头保证无偏

**结果有效性与独立性分离（Outcome Validity–Independence Separation）**：OutcomeObservation 或 Result Review 的 `supported`/`replicated` 状态与其独立性资格独立记录。`supported + limited_independence` 可以作为有效结果保存和解释，但不能满足 Approved Design Heuristic 的外部独立准入，也不能被结果状态掩盖其独立性限制。
_避免使用_：结果有效即来源独立、supported 覆盖偏差

**协议兼容性判定（Protocol Compatibility Adjudication）**：相同或兼容协议必须由人工依据结构化比较表逐项判定，至少覆盖用户/变体、任务场景与事件等级、canonical DesignVariable 操纵及水平、反馈模态/时机/强度/确认路径、主要测量与时间窗、样本与缺失处理、停止规则及条件呈现/日志要求。主要操纵、主要测量、关键情境或风险边界变化即视为新协议；LLM 仅可提出比较建议。
_避免使用_：指标相同即协议相同、模型自动判兼容

**协议容忍范围事前锁定（Prelocked Protocol Tolerance）**：协议的可容忍变化必须在实验开始前写入并批准的复现计划/预注册中，绑定具体变量、单位、测量方法和上限；开始后不得追加或放宽。未预先声明的变化只能记录为 `protocol_deviation` 并由人工审查，不能直接认定兼容或计入 `replicated`。
_避免使用_：结果后定义容忍、偏离自动兼容

**偏离协议结果与严格复现分离（Deviated Protocol vs Strict Replication）**：未预先声明的协议偏离即使不改变主要假设含义且结果有效，也只能作为偏离协议下的支持/探索证据，不能单独满足严格 `replicated`；偏离不得因结果方向一致而被追认成兼容。
_避免使用_：方向一致即追认兼容、偏离结果单独复现

**严格复现与鲁棒性证据分计（Strict Replication vs Robustness Evidence）**：`replicated` 的资格计数只纳入原协议或事前声明兼容协议下的独立复现；未预声明偏离的有效结果另标 `deviated_protocol_support`，可作为鲁棒性或外部效度证据，但不能增加独立复现计数、弥补严格复现缺口或被简写为额外一次复现。
_避免使用_：偏离结果凑复现、三次结果混称

**同范围复现的边际规则（Within-Scope Replication Marginal Rule）**：达到 `replicated` 后，新增同协议复现只增强该声明范围内的稳定性、精度或限制证据，不自动改变启发式类型、使用优先级、适用范围或 `consider_as_option` 约束。扩大范围或提高使用强度必须创建新启发式 revision，完成针对性前瞻性检验并经人工批准。
_避免使用_：复现次数自动强制化、同场景堆样本即泛化

**同范围证据饱和（Within-Scope Evidence Saturation）**：当新增同协议实验不再改变效应精度、适用范围、反例集合或风险判断时，人工 Result Review 可记录同范围证据已饱和并停止继续复现。该状态不证明普遍有效、不提升结论强度，也不允许扩大范围或改为默认建议；后续优先检验新情境、用户变体、实例效应和反例。
_避免使用_：次数达标即饱和、停止实验即普遍有效

**证据饱和审阅包（Evidence Saturation Review Packet）**：宣布同范围证据饱和必须由非启发式提出者的人工 Result Review 提交结构化证据包，列出严格复现、参与者/协议/实例独立性、效应与不确定性变化、新反例/混淆变量/边界、未覆盖情境及停止理由和后续计划。涉及安全、隐私或控制权时还需风险审阅者共同确认；后续改变结论的新证据只能创建新 revision。
_避免使用_：研究者自报饱和、口头停止复现

**启发式事件触发再验证（Event-Triggered Heuristic Revalidation）**：Approved Design Heuristic 不因固定时间自动过期，但有效反例、关键事实/变量/场景/Brief 修订、协议或主要测量变化、证据撤回或复现链失效、来源纠错及新的安全/隐私/控制权风险会触发 Evidence Impact Analysis。分析期间暂停受影响范围的新注入，历史提示和候选保留；人工复核提醒不自动降低证据等级。
_避免使用_：到期自动失效、提醒即降级

**影响分析期间的范围化使用（Scoped Use During Impact Analysis）**：影响分析未完成时，Approved Design Heuristic 仅可在有依赖链证据证明未受影响的范围内继续以 `consider_as_option` 使用，并引用当前 revision、排除清单和分析状态；边界无法可靠划定时全局暂停，高风险触发可扩大为全局暂停。未受影响不等于已重新验证。
_避免使用_：默认继续全局注入、未受影响即重新验证

**主要声明计算复现（Primary-Claim Computational Reproducibility）**：严格复现只要求主要预注册指标、成功判据和事前锁定的关键派生量在声明容差内重现，状态标记 `analysis_reproducible_for_primary_claim`；次要指标可单独标记不可复现但必须显式降级。主要指标或判据不可重现时不得计入 `replicated`，只能进入 `needs_reanalysis`/`inconclusive`；计算复现资格与真人经验独立性分开记录。
_避免使用_：方向一致代替重算、部分重现冒充完整重现

**次要结果独立证据（Secondary Outcome Independent Evidence）**：主要指标失败不妨碍独立绑定的次要假设形成结果证据，但次要结果不能挽救原主要主张、不能从 exploratory 层级事后升格，也不能直接并入原多结果启发式；要形成新的启发式依据，必须创建独立结果绑定和启发式 revision。
_避免使用_：次要指标挽救主结论、事后升格 exploratory

**多重比较选择性成功（Selective Success Under Multiplicity）**：未在实验开始前锁定分析族、假设层级、比较校正或未校正解释政策的单个有利结果，只能形成 `exploratory` 新假设，不能标记 `supported` 或计入启发式支持；必须以新的参与者和预注册主要假设进行前瞻性验证。
_避免使用_：从八个结果挑一个、人工审批洗成证据

**未校正次要结果资格（Unadjusted Secondary Outcome Qualification）**：事前明确未做多重比较校正的次要结果，只有在锁定 AnalysisFamily、假设层级、样本、效应判据、不确定性和解释政策，并经人工 Result Review 后，才可作为受限的 `supported_descriptive` 结果；它不能获得确认性主要结果同等启发式资格，需新实验将其作为主要假设验证。
_避免使用_：声明不校正即正式确认、描述性支持即启发式支持

**描述性支持标签（Supported Descriptive）**：`supported_descriptive` 是 Result Review 对未校正或仅具描述性解释资格结果施加的限制标签，不是新的 Outcome Evidence Strength 等级。它不能满足启发式支持单元、严格复现或范围扩张所需的确认性 `supported` 门槛，展示时不得省略 descriptive/unadjusted 限制。
_避免使用_：新证据等级、受限支持冒充确认性支持

**观察结果与探索结果边界（Observed vs Exploratory Outcome）**：目标用户真人结果在 Consent、原始数据、参与者范围、数据血缘和条件呈现均可核验，但缺少对照或确认性预注册判据时，可标记 `observed` 并作条件化描述；关键来源、呈现、数据或分析链不足时只能标记 `exploratory`。`observed` 不能声称因果、不能计入 Approved Design Heuristic 的确认性支持，升为 `supported` 仍需新的预注册确认性实验和人工 Result Review。
_避免使用_：真实观察即确认、方法缺口仍标 observed

**观察到启发式候选（Observed-to-Heuristic Candidate）**：单次 `observed` 结果只能形成 `Heuristic Observation`；`Heuristic Candidate` 必须由多个相关观察或较完整实验跨来源归纳，且共享明确结果假设、抽象变量和适用范围，并列出反例、混淆变量、限制和待验证边界。同一参与者、实验或数据源的拆分结果只能算一个观察来源，未经批准的候选不得进入 Next Design Prompt。
_避免使用_：单次观察即候选、同源拆分凑多案例

**混合观察的边界型候选（Mixed-Observation Boundary Candidate）**：多个独立 `observed` 来源方向混合或无清晰差异时，可以形成条件性/边界型 Heuristic Candidate，但不能形成稳定正向启发式。候选必须保留 `mixed/no_clear_difference`、调节变量和竞争解释，在边界验证前只能 `validation-only`，不得计入确认性支持或前瞻性批准门槛。
_避免使用_：混合结果包装稳定改善、方向冲突被平均

**条件性避免启发式（Conditional Avoidance Heuristic）**：多个独立、方法有效且达到确认性判据的负向结果，可以形成绑定明确用户/场景/变量范围的条件性避免启发式；它仍需两个独立 `supported`/更高支持单元和合格前瞻性检验，注入强度限于 `consider_avoiding` 或 `validation-only`，不能自动成为 `must_not`、`blocked` 或 Approved Risk Rule。高风险禁止须另行规则审批。
_避免使用_：负向结果即禁止、启发式替代风险规则

**冲突启发式并列处置（Conflicting Heuristics Coexistence）**：两条已批准启发式在同一声明范围内互相牵制时，保留各自结果、适用条件和证据，不平均、投票或自动合并；生成 Heuristic Tension，交由 DesignBrief 权衡、人工选择或新的验证任务处理。除非另有确定性风险规则，两条启发式都只能以 `consider_as_option` 注入。
_避免使用_：启发式多数决、平均冲突证据

**用户变体异质性（User-Variation Heterogeneity）**：同一启发式在不同 User Variation 上方向相反时，结果必须分层保存并标记 `mixed`，不能用总体平均抹平差异。原启发式只能收窄为有支持的变体范围或转为边界型候选；未预注册的交互/异质性分析不能事后宣称因果或扩大启发式资格。
_避免使用_：总体平均掩盖变体冲突、事后子组因果

**事后边界信号（Post-hoc Boundary Signal）**：未预注册的用户变体分析若显示与总体结果不同，只能形成 `post_hoc_boundary_signal`，触发 Evidence Impact Analysis、受影响变体的临时暂停和前瞻性验证任务；它不能直接成为正式支持、有效反例或永久收窄启发式。正式收窄必须创建新 revision 并完成针对该变体的预注册前瞻性检验。
_避免使用_：事后子组直接改范围、临时暂停即证据确认

**退出与缺失不等于启发式反例（Missingness Is Not a Heuristic Counterexample）**：用户退出、任务未完成或结果缺失必须按预注册的 Missingness Type、Task Completion Outcome 和 Completion Cause Evidence 处理，不能直接解释为启发式失效。原因不明或处理不可审计时，相关变体结果降为 `inconclusive`/`needs_reanalysis`；安全停止可先触发风险审查，完成者结果与退出模式必须并列报告。
_避免使用_：退出即失败、只分析完成者、缺失即反例

**结果测量兼容性（Outcome Measure Compatibility）**：不同测量工具只有在实验开始前通过版本化映射，明确构念范围、方向、时间窗、效度证据、已知分歧和允许结论后，才可能支持同一假设的严格复现；仅名称相同不构成兼容。缺少映射时只能形成独立结果绑定或 `cross_measure_convergence_candidate`，冲突结果必须标记 `mixed`。
_避免使用_：构念同名即同测量、挑选有利指标

**测量兼容审批（Outcome Measure Compatibility Approval）**：Outcome Measure Compatibility 必须由人工 Result Reviewer 与测量/方法专家共同审阅，最低证据包括两工具的操作定义、量纲/方向/时间窗、覆盖与不覆盖范围、效度/信度或校准依据、潜在分歧与偏差、事前兼容判据及工具/评分脚本版本快照。仅理论相似性只能标记 `provisional_compatibility`，不能用于严格 `replicated` 或启发式批准；工具或脚本变化须新 revision。
_避免使用_：研究者单独认定兼容、工具改版仍沿用旧映射

**测量实施兼容（Measurement Implementation Compatibility）**：Outcome Measure 的实施方式、施测者在场、设备界面、提示语、隐私环境和完成时限均属于测量协议。相同题目或评分脚本不构成自动兼容；只有事前兼容审阅及等价性/校准证据支持时，才可标记 `implementation_compatible`，并保留实施差异。无法判断时按不同测量处理，不计入严格 `replicated`。
_避免使用_：题目相同即等价、实施差异隐藏

**测量情境限制（Measurement Context Limitation）**：兼容但实施方式不同的测量可以计入同一假设的严格复现，但必须保存 `measurement_context`，并将启发式措辞限制为已声明的实施条件。`replicated` 不表示效应量跨实施方式可交换；新的实施方式需单独验证，跨实施效应合并须事前预注册和方法审阅。
_避免使用_：兼容即工具无关、事后平均实施差异

**部分测量兼容（Partial Outcome-Measure Compatibility）**：两个测量只覆盖同一构念的部分重叠范围时，只能支持明确的共同子构念，不能复现更宽的原假设。必须创建新的 hypothesis revision，声明共同交集、主要指标和不覆盖范围；旧假设的证据状态不自动继承，原链最多标记 `partial_cross_measure_convergence`。
_避免使用_：子指标复现整体构念、收窄后继承全部证据

**子构念收窄不得回填确认性支持（Post-hoc Subconstruct Narrowing）**：从宽假设收窄出的新子构念不能通过事后拆分旧量表继承确认性 `supported`。子量表若事前锁定为独立假设、分析族、方向和解释政策，最多形成受限描述性证据；未锁定则为 `exploratory`。新子构念仍需自身的独立确认性实验和外部前瞻性检验。
_避免使用_：事后拆量表凑支持、收窄假设回填资格

**组合启发式独立性（Compositional Heuristic Independence）**：同一实验可以分别支持多个预注册独立假设，但同一参与者集合、条件呈现和正式运行不能凑成组合启发式的独立支持单元。组合启发式必须事前定义联合结果或组合判据，并由新的独立实验验证；同一实验的同时成功只能记录为 `compositional_observation`。
_避免使用_：同一批参与者拼组合复现、事后拼接多结果

**组合联合成功判据（Composite Joint Success Criterion）**：组合启发式必须在实验开始前锁定联合结果与判据；若语义为“同时改善”，所有必要结果都须达到各自预注册门槛。非对称组合须事前声明“不损害”容忍范围；任一必要结果未达标时只能标记 `partial_composite_support`，不能满足确认性启发式支持或范围扩张。
_避免使用_：至少一项成功即联合成功、事后放宽必要结果

**组合无损害判据（Composite Non-Inferiority Criterion）**：组合启发式的“无损害”必须在实验开始前声明等价/非劣效界限、方向、区间标准和分析方法；点估计在容忍范围内或“未显著恶化”不足以证明无损害。无法排除超过界限的恶化时，联合结果只能是 `inconclusive` 或 `partial_composite_support`，不能由其他结果成功抵消。
_避免使用_：点估计无损害、未显著即等价

**多主要结果联合统计逻辑（Joint Multiplicity Control for Composite Outcomes）**：组合启发式包含多个主要结果时，必须事前锁定联合判据、各结果阈值/区间、缺失处理和整体错误控制（如 gatekeeping、交集检验或序贯策略）。未锁定整体逻辑时，即使各结果分别达标，也最多是 `supported_descriptive`/`partial_composite_support`，不能形成确认性联合支持；事后选择联合逻辑无效。
_避免使用_：分别显著即联合确认、事后挑联合规则

**组合失败的子结果保留（Composite Failure Decomposition）**：组合联合判据失败时，联合启发式标记 `partial_composite_support` 或 `inconclusive`，但各子结果按自身预注册假设独立保留其 `supported`/其他状态。子结果不能互相覆盖、抵消或自动支持组合启发式；联合语义需修订并重新预注册验证。
_避免使用_：整体失败抹掉局部证据、局部成功挽救联合结论

**组合版本不得回填旧失败（No Backfilling Composite Revisions）**：旧组合启发式的 `partial_composite_support`、失败或“不显著损害”结果可以作为新窄化版本的历史来源、边界材料和先验信息，但不能直接计入新版本确认性 `supported`。只有旧实验开始前已锁定与新版本相同的联合判据时，旧结果才可能按兼容假设计入；否则必须通过新预注册实验验证。
_避免使用_：改写联合语义回填支持、旧失败变新成功

**旧证据用于规划但不提升新强度（Prior Evidence for Planning Only）**：既有 `observed`、`supported` 或 `partial_composite_support` 结果可以作为新实验的样本量、效应范围、最小实际重要性、混淆变量、停止规则或冻结 Bayesian 先验的规划依据，但不能直接增加新版本 Outcome Evidence Strength。先验必须在实验开始前锁定并进行预注册敏感性分析；新版本资格只由新数据自身满足判据后产生，冲突按独立证据链审阅。
_避免使用_：旧证据重复计入、先验替代新数据

**先验依赖结果限制（Prior-Dependent Outcome Limitation）**：使用旧证据形成的信息 Bayesian 先验时，必须区分先验与新数据的贡献，并预注册弱信息/怀疑性先验敏感性分析。只有在不依赖旧证据推动的分析下主要判据仍成立，才可支持新实验的 `supported`；仅信息先验下成功标记 `prior-dependent`/`inconclusive`，不能计入 `replicated` 或启发式独立支持。
_避免使用_：先验推动后验即复现、后验替代新数据证据

**未预注册的中途查看与停止（Unplanned Interim Look and Stopping）**：实验中途查看结果并因达到成功判据而提前停止，若未事前锁定中期分析时点、停止边界、错误率控制和样本量重估规则，则不能按原确认性判据标记 `supported`/`replicated`，只能作 `exploratory` 或经方法审阅进入 `needs_reanalysis`。事后补写规则无效；预注册序贯设计和盲法样本量重估可保留确认性资格。
_避免使用_：看到成功即停、事后补停止规则

**完成样本量不消除未计划查看（Full Sample Does Not Cure an Interim Look）**：未预注册地查看中期主要结果，即使没有提前停止并最终完成原计划样本量，也必须标记 `unplanned_interim_look`，不能自动恢复确认性资格或计入严格 `replicated`/启发式支持。只有事前允许的盲法查看、独立数据监测或不影响研究决策的技术监控不构成该偏离。
_避免使用_：招满样本即消除窥视、未停招募即无偏

**独立监测边界（Independent Monitoring Boundary）**：独立数据监测或盲法中期查看必须事前锁定人员边界、可见/禁止字段、允许动作、每次查看审计和揭盲规则。组间方向或成功状态泄露并影响招募、排除、测量或分析时标记 `monitoring_contamination`，触发证据影响审查；安全暂停始终允许并须单独记录。
_避免使用_：监测者可看全部结果、为保资格延迟安全暂停

**监测污染不能由独立重分析修复（Monitoring Contamination Is Not Cured by Reanalysis）**：未接触泄露结果的独立分析者可以降低分析阶段偏差，但不能消除数据收集阶段的 `monitoring_contamination`。只有审计证明泄露后未改变招募、互动、排除、技术处理、测量或停止行为时，结果才可标记 `supported_with_monitoring_limitation`；它不能计入严格 `replicated` 或启发式独立支持。无法证明无影响时只能是 `exploratory/inconclusive`，恢复严格资格需要新的未污染实验。
_避免使用_：换分析者即洗净污染、重算恢复独立性

**受限反例信号（Counterexample Signal）**：达到相反方向但数据生成链受 `monitoring_contamination` 或类似确认性限制的结果，只能形成 `counterexample_signal`，触发 Evidence Impact Analysis 和新的独立验证，不能计为有效反例。普通体验信号暂停范围扩张和资格累积；安全、隐私或控制权信号可预防性临时暂停受影响范围，但正式反例仍需未污染实验确认。
_避免使用_：受限反向结果即有效反例、临时暂停即证实

**反例信号确认实验（Counterexample-Signal Confirmation Experiment）**：针对 `counterexample_signal` 的新实验必须引用信号来源、范围与污染限制，预注册“原启发式成立、真实边界/反例、方法偏差”竞争假设以及双向判据、最小重要性、样本和停止规则。新团队仅接收设计所需最小信息，不查看受污染精确效应值；任何方向的结果都须进入 Result Review。
_避免使用_：只检验恢复方向、选择性报告反例验证

**无结论反例验证处置（Inconclusive Counterexample Confirmation）**：反例信号确认实验为 `inconclusive` 时，不自动解除暂停，也不升级为有效反例。普通体验启发式可经新 revision 维持暂停、降为 `validation-only` 或收窄至明确支持范围；安全、隐私或控制权范围默认继续暂停。成本只影响治理选择，不构成恢复证据，历史记录不回写。
_避免使用_：无结论即恢复、成本高即解除暂停

**仅验证用途（Validation Only）**：标记 `validation-only` 的启发式只能用于生成明确隔离的研究候选或对照条件，并绑定竞争假设、Validation Task 和风险限制；它不能进入普通推进型 Next Design Prompt、Preferred 或正式采用路径。涉及安全、隐私或控制权暂停时，进入真人实验还必须通过相应伦理和风险审批。
_避免使用_：先用于真实设计再补验证、探索候选当正式候选

**启发式自我支持隔离（Heuristic Self-Support Isolation）**：由启发式生成并经人工筛选的候选，其良好结果不能直接反向支持该启发式。只有冻结单一候选、记录生成/筛选过程，以启发式所指变量为主要差异建立对照，并在新的独立样本上完成预注册确认性验证后，结果才可能计入启发式支持；无对照结果最多为 `observed`。
_避免使用_：启发式挑成功案例证明自己、无对照良好即有效

**候选筛选试点与确认性样本隔离（Pilot Selection Data Separation）**：用于候选筛选的试点参与者和结果不得与确认性样本事后合并；试点只能用于可行性、方差估计、故障发现、样本规划或探索性结果。只有在实验开始前已预注册纳入试点、且试点结果不影响候选选择、协议、样本或判据时，试点数据才可按预注册计划计入确认性分析；一旦结果影响选择，必须隔离。
_避免使用_：筛选试点混入正式样本、先看结果再合并

**试点结果可见性门槛（Pilot Visibility Gate）**：试点能否计入确认性分析取决于结果可见性与预注册查看规则，而不只取决于候选是否改变。未盲化组间结果或效应方向被查看时标记 `unblinded_pilot_look`；只有预注册允许该查看并锁定统计处理、错误率控制、样本追加和停止边界时才可保留确认性资格。未经允许的组间查看要求将试点从确认性主分析隔离；仅查看预先允许的盲化质量指标可按计划纳入。
_避免使用_：候选没变即无窥视、质量查看掩盖组间查看

**被隔离试点不可回纳（Isolated Pilot Cannot Re-enter Confirmatory Sample）**：因候选筛选或 `unblinded_pilot_look` 被隔离的试点数据，不能通过新的预注册重新纳入确认性样本或独立复现计数；它只能作为冻结先验、方差/样本规划、竞争假设或探索性资料。新确认性样本从新预注册生效后的未污染参与者开始；包含试点信息的合并模型须标记 `prior-dependent`。
_避免使用_：新预注册洗回试点、试点加新样本冒充独立复现

**外部检验的先验依赖分离（External Test Prior Dependence Separation）**：外部团队使用旧证据进行样本规划不损害执行独立性，使用事前冻结先验也不自动损害执行独立性，但若新数据只有信息先验下达到判据，结果标记 `prior-dependent`，不能满足启发式外部独立准入。只有弱信息或怀疑性先验分析在新数据自身达到 `supported`，外部检验才具准入资格；报告分开记录 `execution_independence` 与 `inferential_prior_dependence`。
_避免使用_：外部团队独立即推断独立、信息先验成功即外部支持

**共享基础设施依赖（Shared Infrastructure Dependency）**：外部独立检验可以复用相同招募供应商、设备型号、实验脚本或培训材料；只要人员、参与者、数据保管和揭盲分析独立，它仍可满足执行独立性。但这些共同来源必须标记 `shared_infrastructure_dependency`，并限制 `scope_generalizability` 和范围扩张解释。
_避免使用_：基础设施相同即不独立、执行独立即可泛化

**共享基础设施依赖等级（Shared Infrastructure Dependency Level）**：外部检验的共享基础设施依赖分为 `minimal_shared_dependency`、`moderate_shared_dependency` 和 `high_shared_dependency`。仅共享测量工具、公开协议或分析脚本通常为 minimal；共享设备型号、实验脚本或培训材料为 moderate；共享招募渠道、设备批次、场地流程、培训人员或关键操作环境为 high。高共享依赖只能作为受限外部支持，不能证明跨基础设施泛化。
_避免使用_：外部独立二元化、高共享依赖当完全外部支持

**共享依赖准入影响事前锁定（Prelocked Impact of Shared Dependency）**：共享依赖的事实可在实验后补充或纠正，但依赖等级如何影响外部准入和泛化必须在实验开始前声明。未事前锁定时，结果只能标记 `external_independence_unclassified` 或 `limited_external_support`，不能直接满足启发式外部独立准入；事后把高依赖降级不能追认资格。证明实际无共享依赖时须创建事实修订并执行影响分析。
_避免使用_：事后降级依赖洗资格、结果后定义外部独立

**共享依赖事实纠正（Shared-Dependency Fact Correction）**：若新证据证明原判定的共享基础设施事实错误，可创建 correction revision，执行 Evidence/Heuristic Impact Analysis 并重新判定外部独立资格；历史 `limited_external_support` 保留，不原地改写。纠正证据不可复现或来源受限时，资格维持 `independence_status_uncertain`。
_避免使用_：原地改独立性、纠正即自动恢复

**独立性纠正证据包（Independence Correction Evidence Packet）**：外部独立性事实纠正至少需要两类相互独立、可验证的来源，覆盖实际呈现使用的设备、软件、脚本、场地和关键培训人员，并保存时间、版本、来源、内容哈希和定位。纠正须由未参与实验执行或启发式归纳的人确认；单一来源、口头说明或部分组件证明不能恢复整体资格，且恢复前仍须检查其他共享依赖。
_避免使用_：两个文件即两份证据、部分不同推断整体独立

**证据来源独立性（Evidence Source Independence）**：独立性纠正按独立上游计数，而非文件数量。同一供应商、系统、数据库或复制链的多份记录只能算一个来源；至少还需不同上游的可验证证据。来源只能证明其覆盖字段，无法证明实际批次、呈现对象或关键组件时，不能推断整体独立性，资格维持 `independence_status_uncertain`。
_避免使用_：多份同源文件凑证据、证明型号即证明批次

**独立性覆盖闭包（Independence Coverage Closure）**：整体外部独立资格要求关键依赖字段覆盖闭包：设备、软件、脚本、场地、培训、招募、数据保管和揭盲分析等字段均需可验证来源，或有事前批准的“不影响独立性”理由。未覆盖字段标记 `independence_coverage_gap`；若缺口可能驱动结果，只能 `limited_external_support`，必须补证或完成独立敏感性/反例检验。多来源拼接须保存字段级来源映射。
_避免使用_：部分证据推断整体独立、证据包通过即覆盖全部

**独立性字段关键性（Independence Field Criticality）**：独立性字段只有在实验开始前由方法审阅者确认其不影响主要操纵、测量、参与者行为、条件呈现或风险边界时，才可标记为非关键；执行团队不能单独排除。说明/提示、反馈解释、无响应处理、招募筛选、数据清洗和安全处置等字段默认关键；事后发现影响可能时创建 `criticality_reclassification` 并触发影响分析，无法证明不影响时形成 `independence_coverage_gap`。
_避免使用_：执行团队自定非关键、记录困难即排除

**非关键字段重分类影响（Noncritical-Field Reclassification Impact）**：事前标记为非关键的字段若后来被发现可能调节结果，必须创建 `criticality_reclassification` 并执行 Evidence/Heuristic Impact Analysis。历史结果保留，但 `replicated` 暂时收窄为已使用的实施条件，启发式暂停受影响变体的新注入和范围扩张；共享该字段的多次实验不能证明跨该字段泛化，恢复资格需要新的预注册交互或边界实验。
_避免使用_：历史复现自动证明跨调节变量泛化、重分类后仍沿用原范围

**事后分层一致性（Retrospective Consistency）**：新实验确认调节变量后，对旧实验未预注册分层的重算只能标记 `retrospective_consistency` 或 `retrospective_conflict`，不能回填确认性支持或复现计数。新条件假设须创建独立 revision，以新的预注册分层实验建立 `supported`，并至少再经一次独立确认性实验才能标记 `replicated`。
_避免使用_：事后子组回填复现、与新结果一致即追认

**启发式族与条件分支（Heuristic Family and Conditional Branches）**：经预注册交互确认、对不同用户变体产生相反建议时，必须拆成资格、反例和生命周期独立的条件性 heuristic branches，各自绑定变体、结果、证据、适用/排除条件和注入指令。Heuristic Family 只关联共同调节证据和 lineage，不可直接注入；调节变量未知时标记 `unknown_applicability`，不得任选分支。
_避免使用_：一条启发式隐藏相反建议、未知变体默认套用

**条件启发式冲突（Conditional Heuristic Conflict）**：候选同时匹配多个建议冲突的启发式分支时，系统保留各分支的条件、结果、证据和代价，不按数量、具体性或版本新旧自动覆盖；由 DesignBrief 权衡和人工选择决定采用、并列验证或探索。Brief 缺少裁决依据时，候选进入 `explore`；只有确定性 Approved Risk Rule 可按既有优先级压过启发式建议。
_避免使用_：具体分支自动覆盖、启发式多数决

**启发式作用域充分性审阅（Heuristic Scope Adequacy Review）**：高频且结构化的 Conditional Heuristic Conflict 表明现有分支作用域可能不足，必须审阅未建模调节变量、交互、风险边界或测量差异，不能无限依赖逐案人工裁决。审阅期间相关重叠范围暂停自动注入，仅可 `validation-only` 或显式人工选择；若新调节变量得到证据支持，创建新的 Heuristic Family/branch revision，不能原地修改旧分支。
_避免使用_：反复人工裁决即充分、修改旧文本掩盖作用域缺口

**作用域冲突触发阈值（Scope Conflict Trigger Threshold）**：Heuristic Scope Adequacy Review 的“高频且结构化”阈值必须在启发式批准时预先声明，并按合法候选、已确认分支匹配和独立 Brief/场景计数。任一条件满足即可触发：连续两个 DesignIteration 中相关冲突占合法候选 ≥20%；至少 3 个独立 Brief/场景重复相同分支组合和冲突方向；同一重叠范围连续 ≥3 次需要同类人工覆盖；或发生一次确认的安全/隐私/控制权冲突。生成无效、未决事实冲突或无法判断候选不计入分母，历史计数只能在新 revision 中修订。
_避免使用_：事后调阈值、选择性计数冲突

**冲突计数审计投影（Conflict Counting Audit Projection）**：冲突阈值由确定性审计投影从全部合法候选、确认匹配和人工决策生成，分母成员逐项标记未匹配、单分支、多分支无冲突、多分支冲突、事实未决、生成无效或无法判断。覆盖必须引用冲突、分支、Brief、候选 revision 和理由；计数窗口、阈值版本、过滤规则与脚本冻结并带哈希，维护者不能手改分母或计数。漏记/误分类只能通过 correction revision 重算，历史触发保留。
_避免使用_：手工填报冲突率、删除分母案例降阈值

**触发快照与后续监测窗口（Trigger Snapshot and Post-Trigger Window）**：作用域审阅触发瞬间冻结 `Scope Review Trigger Snapshot`，后续新候选不回溯加入或改变触发事实；审阅期间另设 `post_trigger_monitoring_window`，其起止时间、纳入规则、分母和指标在审阅开始时锁定。受影响范围继续限制为 `validation-only`/人工选择；监测冲突下降不自动恢复，新增高风险冲突可扩大暂停，触发快照与监测窗口分开报告。
_避免使用_：后续数据洗掉触发、冲突下降即自动解封

**监测窗口结束建议（Post-Trigger Window Closure Recommendation）**：监测窗口结束条件必须在审阅开始时锁定，至少包括最小合法候选/独立 Brief 或场景数、关键用户变体/任务/风险覆盖、分支匹配与冲突完整记录、冲突持续率和新高风险事件检查。窗口只可产生 `maintain_suspension`、`narrowed_scope_candidate` 或 `revalidation_ready` 建议；后者仅表示可启动新预注册验证，不自动恢复。覆盖不足或 unknown 过多标记 `insufficient_monitoring`。
_避免使用_：不利结果提前结束窗口、监测完成即解封

**监测证据与确认性验证隔离（Monitoring Evidence Isolation）**：`post_trigger_monitoring_window` 的候选和结果只能作为新预注册验证的设计、边界、方差和反例输入，统一标记 `monitoring_evidence`，不得直接计入确认性样本或启发式支持。监测候选/条件与验证候选/条件使用独立 revision；窗口结果若改变变量范围、候选选择或判据，必须新建预注册 revision。监测参与者不能直接并入验证样本；重复参与须按学习/重复任务规则处理。
_避免使用_：监测试错后包装确认、监测样本凑复现

**监测参与者重复参与限制（Monitoring Participant Re-entry Limit）**：监测窗口参与者再次参加确认性验证时，默认不计入独立确认性样本；重复参与必须预注册记录身份关联、学习/顺序/期待效应、洗脱或替代任务、participant-level clustering 及纳入规则。重复比例超阈值时结果降为 `needs_reanalysis`/`inconclusive`，知悉启发式或反例信号还需标记 `expectation_contamination`；重复参与不能满足外部独立准入。
_避免使用_：换阶段标签伪造新样本、重复参与冒充独立验证

**参与者独立性随真实暴露历史（Participant Independence Follows Exposure History）**：参与者独立性不由 participant_id、同意版本或研究阶段标签决定；新 ID、重新同意或跨项目迁移不能重置既有暴露、学习和期待效应。系统应通过受控身份映射识别重复参与而不向普通分析暴露身份；无法核验时标记 `participant_independence_uncertain`，不得计入严格复现或外部支持。故意换 ID 隐藏重复是数据血缘/审计异常。
_避免使用_：新 ID 即新样本、重新同意洗掉学习效应

**跨项目参与者独立性不确定（Cross-Project Participant Independence Uncertainty）**：跨项目无法共享身份映射时，不得默认参与者独立；预注册必须声明可检测边界，并使用研究专属 token、受控哈希校验或第三方匹配等最小化去重信号。确认重复者按同一参与者处理；无法确认且重复风险较高时标记 `participant_independence_uncertain`，按独立/非独立边界做敏感性分析，无法排除影响则不计入严格 `replicated` 或启发式外部准入。
_避免使用_：跨项目即新参与者、无法匹配即独立

**概率去重边界分析（Probabilistic Deduplication Bounds）**：跨项目概率匹配只能记录 `match_probability`、依据和不可判定范围，不能按最可能匹配作单一判断。预注册必须分析全部独立、可能重复者剔除和最保守重复等合理边界；只有所有边界下独立样本、主要判据和方向仍满足要求，才可计入严格 `replicated`。结论依赖匹配假设时标记 `participant_independence_uncertain`，后续确定性证据须 correction revision。
_避免使用_：加权半个参与者、最可能匹配即独立

**复现对独立性边界的敏感性（Replication Sensitivity to Independence Bounds）**：若任一合理的参与者独立性边界使结果不满足 `replicated`，则不得升级为 `replicated`；新实验自身仍可保留 `supported + replication_sensitivity`，并展示全部边界结果。该受限结果不能满足启发式外部独立准入或新资格累积；受影响范围暂停扩张，直至补足去重证据或完成身份独立性可确认的新实验。
_避免使用_：多数边界通过即复现、受限支持凑启发式资格

**受限支持单元分级（Qualified Support Unit Classes）**：`supported + replication_sensitivity` 等受限结果可以保留为经验支持，但启发式资格计数必须与 `supported_clean` 分开。只有 `supported_clean` 才能计入 Approved Design Heuristic 的确认性支持和外部准入；受限支持仅用于 Heuristic Candidate、边界/反例分析和新实验规划。关键支持单元变为受限时，必须触发 Evidence Impact Analysis，不能把多个受限结果相加抵消限制。
_避免使用_：受限支持等同干净支持、堆叠限制结果洗资格

**启发式资格风险状态（Heuristic Qualification at Risk）**：已批准启发式的关键 `supported_clean` 单元变为受限并导致批准门槛暂不满足时，创建新 revision 标记 `qualification_at_risk`，停止范围扩张和资格累积；仅在依赖链证明未受影响的范围内继续 `consider_as_option`，边界不明则暂停。必须声明补证窗口与恢复条件；到期仍不足时转为 `evidence_insufficient` 或 `deprecated`，历史提示、候选和结果保留。
_避免使用_：受限后仍称完整批准、立即删除历史启发式

**资格风险补证窗口（Qualification-at-Risk Remediation Window）**：进入 `qualification_at_risk` 时必须由人工声明具体证据缺口、补证类型、最小完成条件、不可接受替代方案、负责人、期限、期间允许/禁止用途和逾期降级状态。时间仅是治理期限，不自动恢复或废弃；延期须新 revision，缺口长期不可得时转 `evidence_insufficient`，高风险缺口期间默认暂停受影响范围。
_避免使用_：固定天数自动恢复、无条件续期

**部分补证恢复（Partial Remediation Restoration）**：补证必须逐项对照事前声明的恢复条件。部分修复只标记 `remediation_partial`，不能自动恢复原 Approved 范围；若核心门槛恢复但仅覆盖较窄范围，创建新的窄范围 Approved revision 并明确排除未修复范围；关键门槛仍缺失则维持 `qualification_at_risk`，若证明原范围不可维持则收窄为条件分支或 `evidence_insufficient`。旧高范围 revision 保留。
_避免使用_：修复一项即恢复全范围、原地改批准范围

**窄范围前瞻性覆盖继承（Inherited Prospective Coverage）**：窄范围 heuristic revision 若严格属于旧范围子集，且变量、结果、协议、实施条件和用户定义兼容，可经人工 Result Review 引用旧合格前瞻性检验并标记 `inherited_prospective_coverage`；该引用不增加新支持计数。改变假设、主要指标、协议、实施或用户定义时必须重新进行前瞻性检验，不能通过收窄重包装失败结果。
_避免使用_：子集自动继承资格、旧失败收窄后变成功

**继承覆盖与外部独立分离（Inherited Coverage vs External Independence）**：`inherited_prospective_coverage` 只证明旧检验覆盖窄范围，不自动继承外部独立资格；旧检验的 `limited_independence`、`shared_infrastructure_dependency`、`prior-dependent` 等限制必须原样保留。旧检验若无合格外部/结果盲法资格，窄范围 revision 仍需追加新检验；资格记录分别列出覆盖、执行独立性和推断限制。
_避免使用_：继承覆盖即继承独立、收窄消除旧限制

**启发式分支共享检验血缘（Shared Lineage Across Heuristic Branches）**：同一外部检验可为多个 heuristic branches 产生各自结果证据，但共享参与者、正式运行、团队或数据生成链只能计为一条外部独立支持 lineage。分支必须分别记录结果状态、判据和限制；共享 lineage 不得按 hypothesis_id 拆分凑独立外部支持，家族联合成功也不自动传递分支资格。
_避免使用_：按分支复制同一检验、家族成功覆盖分支

**多分支共享实验前瞻性资格（Multi-Branch Shared Experiment Qualification）**：预注册可将同一外部实验中的多个分支锁定为独立主要假设，分别产生 `supported` 结果和前瞻性覆盖，但共享实验只提供一条外部独立 lineage。预注册必须锁定分支范围、主要指标、判据、非劣效界限、共享依赖与多重比较逻辑；每个分支仍需自身独立支持单元，家族联合验证不能由分支同时成功替代。任一分支污染、偏离或冲突须按分支与共享 lineage 分别影响分析。
_避免使用_：多分支同实验凑独立计数、分支成功即家族复现

**多分支整体错误控制（Multi-Branch Familywise Control）**：共享实验的多个主要分支必须在实验开始前锁定 AnalysisFamily、整体错误控制和 gatekeeping/层级/交集逻辑。缺少整体逻辑时，分支结果最多为 `supported_descriptive` 或 `partial_branch_support`，不能逐分支获得确认性 `supported` 或计入启发式资格；预注册策略未通过的下游分支按其预设层级处理，不能事后改解释。
_避免使用_：各分支独立显著即全确认、结果后挑多重比较规则

**Gatekeeping 下游受限结果（Downstream Outcome Under Failed Gate）**：当事前预注册的 gatekeeping 上游分支未达标时，下游分支即使自身指标达标，也只能标记 `supported_descriptive` 或 `exploratory_secondary_under_failed_gate`，不能获得确认性 `supported`、`replicated`、启发式支持或外部准入。下游原始结果和效应仍保留，并明确记录门控未通过；重新确认须新预注册主要假设或独立实验。
_避免使用_：下游成功绕过门控、上游失败被下游抵消

**Gatekeeping 上游完整性失败（Gate Integrity Failure）**：上游 gate 因技术故障、条件呈现未验证或数据不可用而未通过时，下游确认性资格同样关闭，但必须区别于效果未达标：效果失败使用 `supported_descriptive`/`exploratory_secondary_under_failed_gate`，完整性失败使用 `gate_inconclusive_due_to_upstream_integrity`。下游完整且可复现的结果只能作受限描述和规划，不能因技术失败改写 gate 逻辑；共享条件/样本/数据链受影响时，下游也不得计入外部独立支持或启发式资格。
_避免使用_：技术失败绕过门控、共享故障只影响上游

**共享故障的分支级隔离（Branch-Level Isolation of Shared Failures）**：共享条件、设备、环境、脚本或分配流程发生故障时，默认视为影响全部分支。只有字段级日志、校准或暴露证据证明某分支的条件、参与者暴露、测量和数据链完全独立，才能将其标记为未受影响并继续 Result Review；受影响分支标记 `gate_inconclusive_due_to_upstream_integrity`。局部保留 `supported` 不增加外部独立 lineage，边界不明时整体关闭确认性资格。
_避免使用_：好结果即未受影响、共享故障乐观拆分

**共享故障后分支隔离结果（Branch Isolation After Shared Failure）**：共享故障后，剩余分支只有在字段级影响分析证明条件呈现、参与者暴露、测量、数据链和门控逻辑未受影响时，才可保留 `supported`，并标记 `branch_isolated_after_shared_failure`。该结果不能满足启发式外部准入或增加外部独立 lineage，只能作为 `limited_external_support`、范围/反例分析和新实验规划材料；被排除分支的故障不自动成为剩余分支反例。
_避免使用_：事后隔离即外部确认、故障分支失败替代反例

**受限反例信号（Limited Counterexample Signal）**：共享故障后受限分支的反向结果只能标记 `limited_counterexample_signal`，不能直接成为有效反例、永久收窄或废弃启发式，也不计入正式反例次数。普通体验范围可暂停该分支扩张和新注入并触发影响分析；安全、隐私或控制权范围可预防性临时暂停。正式反例需无共享故障、事前分支隔离的确认性实验；旧启发式仅在可证明未受影响范围继续使用。
_避免使用_：受限反向结果即正式反例、故障隔离后立即废弃

**受限反例信号累积阈值（Limited Counterexample Signal Threshold）**：受限反例信号可触发 Heuristic Scope Adequacy Review 或暂停，但不能累积成正式反例。阈值须在启发式批准时预先声明，按独立数据生成链、独立 Brief/场景和受影响分支计数；至少 3 个独立信号指向同一范围、2 个独立 Brief/场景重复同一反向方向、连续两个监测窗口重复，或一次安全/隐私/控制权信号即可触发。触发后相关范围至少 `validation-only`/人工选择，正式反例仍需无故障且事前分支隔离的确认性实验。
_避免使用_：受限信号凑正式反例、忽略高风险单次信号

**受限反例信号先完整性后验证（Integrity Before Counterexample Confirmation）**：受限反例信号必须按顺序经历事实/lineage、测量/协议和实施完整性审查；可修复缺口先创建 correction/reanalysis revision，只有数据生成链足够完整后才启动预注册双向反例验证。缺口未关闭不能升级正式反例；修复后反向结果消失时仅记录方法问题，不计入反例；仍反向时还需新的无故障确认性实验。高风险范围可并行维持临时暂停。
_避免使用_：完整性未审即归因、修复和验证混在一条记录

**完整性修复后的启发式恢复（Heuristic Restoration After Integrity Fix）**：受限反向信号因事实、测量或实施修复而消失时，标记 `counterexample_signal_resolved_by_integrity_fix`，仍须完成 Evidence/Heuristic Impact Analysis 和新 heuristic revision，才能按实际证据覆盖范围恢复；不得原地解封或把该实验计入正式反例/新增独立支持。修复改变假设、条件或主要指标时必须重新确认性实验；高风险范围解除临时暂停还需风险审阅。
_避免使用_：修复后自动恢复全范围、修复结果凑支持

**修复后支持继承（Support Inheritance After Correction）**：完整性修复后的新 heuristic revision 只有在逐项证明原支持单元的候选、操纵变量、主要结果、协议语义、独立参与者/运行和分析可复现性未改变，且用户变体、测量实施和共享依赖限制重新评估后，才可标记 `inherited_clean_support_after_correction` 并经人工 Result Review 重新批准。受限、污染或不确定支持不能直接恢复为 `supported_clean`；改变假设、结果定义、变量映射或范围时必须新建支持链，外部/盲法前瞻性检验不可跳过。
_避免使用_：修复即洗成干净支持、继承后跳过外部检验

**候选选择执行者变更（Candidate Selection Executor Change）**：更换候选筛选执行者、生成模型或模型版本时，默认标记 `selection_executor_change` 并切断旧支持继承。只有候选池、筛选规则、排序依据、人工覆盖权限、随机性控制和可选范围均冻结且经人工证明执行等价，才可在新 revision 中有限继承；最终选中相同候选不构成过程等价证明，无法验证时必须建立新选择链和前瞻性验证。
_避免使用_：同一结果即同一选择过程、换模型后自动继承证据

**随机种子与选择链（Random Seed and Selection Lineage）**：随机种子变化不自动切断候选选择链，但必须在预注册中声明允许性，记录每次 seed、候选池差异和筛选轨迹，并完成多 seed 稳定性分析。若 seed 改变可选范围、筛选顺序或人工决策机会，标记 `stochastic_selection_shift` 并切断支持继承；频繁不同结果只能作为受限证据。
_避免使用_：同候选即同随机过程、选择性报告 seed

**候选结果支持与选择流程支持分离（Candidate Outcome vs Selection-Process Support）**：多 seed 产生不稳定候选但随后冻结单一候选并完成合规实验时，结果可支持该冻结候选的结果假设，但不能证明启发式选择流程稳定有效。两者分别记录为 `candidate_outcome_support` 与 `selection_process_support`；从多个 seed 挑选最佳候选还须标记 `selection_enrichment`，需多 seed/多候选预注册对照和独立样本才能支持选择流程。
_避免使用_：冻结候选好结果证明生成流程、挑最佳 seed 掩盖不稳定

**选择流程支持实验（Selection-Process Support Experiment）**：要声称 `selection_process_support`，必须将启发式驱动的生成/筛选流程作为独立实验条件，与事前锁定的无辅助、通用 LLM 或既有人工基线比较，并预注册多 seed、候选池、筛选规则、流程结果和选择偏差指标。仅证明被选候选表现良好只能是 `candidate_outcome_support`；流程级结果需新的独立样本和人工 Result Review，不能自动升级 Approved Heuristic。
_避免使用_：最佳候选结果代替流程比较、无基线即流程有效

**选择流程收益与成本联合判据（Selection-Process Benefit–Cost Criterion）**：选择流程支持必须事前同时锁定候选结果改善的主要指标/最小实际重要性、人工时间/负担/冲突处理量/错误率等成本指标及可接受上限或权衡规则。收益达标但成本超限时只能标记 `selection_process_support_with_cost` 并作为条件性流程建议；联合判据未达标时不能称为流程支持。流程成本测量的工具、时间窗、盲法和缺失处理也须预先声明，且不改变候选结果证据等级。
_避免使用_：结果收益抵消未预注册成本、流程支持等同候选支持

**选择流程权衡（Selection-Process Tradeoff）**：收益与人工成本若存在权衡，且实验开始前没有统一的 Pareto、分层或门槛式决策规则，结果只能分别报告为 `selection_process_tradeoff`，不能由人工事后判定总体“值得”并升级 `selection_process_support`。权衡结论必须绑定流程版本、团队背景、Brief 和任务范围；不可比较时保持 `explore` 并生成 Validation Task，不自动泛化。
_避免使用_：事后总体判定值得、收益成本压成单分数

**候选选择机制变化（Candidate Selection Process Change）**：候选生成池、筛选顺序、纳入/排除规则、人工覆盖、排序依据或选择机会集发生变化时，标记 `selection_process_change`，即使最终选中候选相同也切断旧支持继承。新流程必须记录选择链并重新进行前瞻性验证；旧结果只能作为历史材料或 `prior_observation`。
_避免使用_：最终候选相同即过程相同、换筛选机制仍继承支持

**事后分层一致性（Retrospective Stratified Consistency）**：调节变量经新实验确认后，旧实验中未预注册的分层结果只能标记 `retrospective_consistency`，不能回填为确认性支持单元或独立复现计数。新条件假设必须创建独立 hypothesis/heuristic revision，并由预注册分层实验建立自身证据；旧分层结果只能用于边界说明、规划和反例搜索，冲突须显式保留。
_避免使用_：事后分层凑复现、重算子组即预注册证据

**可选启发式建议（Heuristic Option）**：Approved Design Heuristic 在 Next Design Prompt 中的应用形式，带适用条件、不适用条件、证据和 `consider_as_option` 指令。生成器可以采用、部分采用或不采用，但必须返回处理说明。
_避免使用_：必须遵守、自动配方

**启发式不采用理由（Heuristic Non-Adoption Rationale）**：设计生成器或人工说明为什么当前候选没有采用某条可选启发式，必须指向 Brief 权衡、适用条件、冲突约束或新的证据。
_避免使用_：忽略经验、模型没听话

**不可信候选数据（Untrusted Candidate Data）**：外部生成器提供的文本、OCR、图片元数据、交互故事和声明内容。它们是评审对象，不是系统指令，不能改变 DesignBrief、规则、权限或阶段门。
_避免使用_：候选 prompt、模型指令

**提示注入标记（Prompt Injection Flag）**：候选数据中出现试图改变系统规则、忽略审查或操纵排序的指令性内容时追加的审计标记。标记本身不等于体验风险或 blocked。
_避免使用_：自动安全阻断、模型违规

**安全派生资产（Safe Derived Asset）**：由原始媒体经格式、大小、内容和元数据校验后重新编码生成的、供浏览器和视觉模型使用的副本。它与原始资产保留父子关系，不改变原始证据。
_避免使用_：清洗后覆盖原图、可信原件

**资产无效（Asset Invalid）**：文件格式、大小、解码、脚本或压缩安全检查失败，不能进入候选事实确认的状态。
_避免使用_：图片不清晰、评审失败

**提示投影（Prompt Projection）**：从完整项目数据中按当前设计任务筛选出发送给外部生成器的最小必要字段的过程。投影默认去除个人身份、原始用户研究、未确认推理和与当前反馈无关的审计信息。
_避免使用_：复制报告到 prompt、全文回灌

**发送前预览（Pre-Transfer Preview）**：外部生成器调用前展示实际将发送的提示字段、派生资产、脱敏结果、provider 和模型的人工确认阶段。
_避免使用_：隐私弹窗、一次性全局授权

**审批密度（Approval Density）**：根据风险、不可逆性、数据传输和知识影响程度，为不同工作流步骤决定逐条确认、批量确认或自动留痕的策略。
_避免使用_：所有步骤都点确认、全自动化

**高风险阶段（High-Risk Gate）**：涉及改变设计目标/约束、解除阻断、发送私人数据、批准实验、修改知识或最终选择的步骤，必须具备明确的人工确认和审计记录。
_避免使用_：重要页面、最后一步

**审阅负担（Review Burden）**：人完成一个候选批次的事实确认、关键 ReviewItem 审阅和决策覆盖所需的时间、修改量、冲突处理量和未解决项数量。它用于评估系统是否把值得判断的内容升级给人。
_避免使用_：点击次数、自动化比例

**升级质量（Escalation Quality）**：被系统要求人工判断的项目，实际需要人作出有价值判断的比例；低价值、重复或可由确定性规则解决的项目不应频繁升级。
_避免使用_：人工介入率、少让人看

**评审项预算（Review Item Budget）**：每个候选默认生成 4–6 个核心 ReviewItem，并优先保留高风险、影响主要权衡、可独立验证和影响下一轮变量修复的内容。预算不是安全项上限。
_避免使用_：模型输出长度、固定六条意见

**延后观察（Deferred Observation）**：因评审项预算未进入当前核心评审、但仍保留来源和潜在影响的低优先级内容。人可以手动展开为新的 ReviewItem。
_避免使用_：删除细节、忽略项

**介入事件（Intervention Event）**：在指定触发、事件紧急等级、用户任务和情境下，AI 设备以某种模态、时机和强度介入，并提供确认、纠正、撤销或延后路径的一次设计行为。它是 V1 ReviewItem 的主要组织单位。
_避免使用_：设备功能、硬件部件

**介入事件序列（Intervention Event Sequence）**：按时间顺序描述一次介入从 trigger、context inference、permission decision、feedback、user response 到 follow-up/recovery/termination 的设计行为链。它表达候选如何处理分支，不代表用户一定按预期回应。
_避免使用_：静态提醒字段、理想路径

**事件终止条件（Event Termination Condition）**：一次介入在用户接受、拒绝、延后、纠正、无响应、超时或达到安全上限后停止/转入恢复的明确条件。
_避免使用_：提醒结束、模型自动收尾

**受限事件状态机（Bounded Event State Machine）**：V1 用于表达 InterventionEvent Sequence 的有限状态模板，限制反馈步骤、响应分支、升级次数和循环，要求所有路径到达 termination 或 recovery。
_避免使用_：任意流程图、无限 Agent loop

**事件序列复杂度超限（Event Sequence Complexity Exceeded）**：候选事件序列超过 V1 的节点、步骤、分支或升级预算，保留草案但不能进入正式事实冻结后的候选比较。
_避免使用_：模型太聪明、运行失败

**无响应（No Response）**：设计序列在规定窗口内没有观察到用户接受、拒绝、延后或纠正动作的分支。它不表示同意、拒绝、专注或情境成立，必须有独立的降级、延后、升级或终止策略。
_避免使用_：默认同意、用户忽略

**反馈不可发现（Feedback Not Detectable）**：由于模态、强度、环境或设备状态无法确认用户是否感知到反馈的状态。它与用户有意识的 no_response 不同，通常要求补充发现性验证。
_避免使用_：用户无响应、提醒没用

**用户拒绝（User Rejected）**：用户明确表示当前介入或该类介入不应继续的响应。除非新的授权、事件类别或用户主动触发改变，系统不得把它解释为暂时延后或再次主动升级的许可。
_避免使用_：无响应、稍后处理

**用户延后（User Snoozed）**：用户明确表示当前不处理、但允许在指定条件或时间窗口再次出现的响应。延后不是同意，也不是永久拒绝，必须携带恢复条件和最大重试策略。
_避免使用_：忽略、默认稍后

**用户响应范围（User Response Scope）**：User Rejected 或 User Snoozed 作用的事件、事件类型、设备模式或全局偏好范围，以及过期/恢复条件。响应范围必须由用户动作或人工声明确定，不能由模型扩大。
_避免使用_：全局偏好猜测、自动记住一切

**有限重试（Bounded Retry）**：User Snoozed 后在指定条件满足时允许的有限再次介入次数和最大强度。V1 默认最多一次，不自动累加。
_避免使用_：持续追问、无限提醒

**用户纠正（User Correction）**：用户明确指出设备当前情境、事件、偏好或反馈解释不正确的响应。纠正立即影响当前事件，但一次纠正不自动更新长期模型或全局偏好。
_避免使用_：用户反馈即真理、自动学习

**即时纠正（Immediate Event Correction）**：User Correction 对当前 InterventionEvent 的立即处理结果，包括停止、撤销、切换路径或重新请求确认。它不改变已冻结 Brief 或历史候选。
_避免使用_：实时改需求、修改设计约束

**情境模式候选（Context Pattern Candidate）**：从多次用户纠正信号中归纳的长期情境/偏好模式草案，需复盘、用户控制和人工确认后才能影响未来设计。
_避免使用_：自动用户画像、一次纠正记忆

**目标用户群（Target Segment）**：DesignBrief 为一轮设计明确声明的主要用户群，必须可描述、可招募或可模拟，不使用“所有用户/普通人”等空泛标签。
_避免使用_：平均用户、泛用户

**用户变体（User Variation）**：在同一 Target Segment 内，对设备使用或体验有明确影响的最多三个差异条件，例如佩戴/不佩戴耳机或对公开反馈的敏感性。变体分别评审，不平均成一个体验分。
_避免使用_：个人画像、偏好标签

**研究可行性检查（Researchability Check）**：在 DesignBrief 冻结前检查 Target Segment 和 User Variation 是否可描述、可招募或可合理模拟，是否有可观察差异、样本路径和伦理边界。检查通过不等于用户研究已经完成。
_避免使用_：用户定义完成、代表真实用户

**模拟行为证据（Simulated Behavior Evidence）**：由模拟用户或合成角色产生的流程、分支和规则执行记录，只能证明系统路径可运行，不能证明真人体验或用户偏好。
_避免使用_：虚拟用户结果、合成体验证据

**流程已验证（Pipeline Validated）**：模拟行为和确定性测试已证明状态机、Schema、阶段门或反馈契约可执行的状态，不属于 Outcome Evidence。
_避免使用_：用户验证、体验已验证

**专家判断证据（Expert Judgement Evidence）**：由具备产品、心理或人因经验的标注者对设计一致性、机制合理性、风险、反馈可执行性或实验方案作出的判断。它不能单独证明真人体验结果。
_避免使用_：用户结果、实验真值

**真人结果证据（Real-User Outcome Evidence）**：来自目标用户的观察、行为测量、自报告或访谈，并绑定样本、情境、方法和原始数据的结果证据。它才可推进 Outcome Evidence Strength。
_避免使用_：专家意见、模拟结果

**结果观察（Outcome Observation）**：绑定候选 revision、Brief/场景快照、任务、实验条件、测量方法、样本、原始数据和同意状态的一条真人研究结果记录。它可以是行为测量、自报告、访谈编码或现场观察。
_避免使用_：用户喜欢、研究总结句

**不可用结果（Unusable Result）**：真人研究结果缺少候选/场景/任务/条件/测量/原始数据等关键字段，或无法确认同意与收集方法，不能推进 Outcome Evidence Strength 的状态。
_避免使用_：弱证据、暂时结果

**去标识结果（De-identified Outcome）**：只引用 pseudonymous participant_id、分群和研究条件，不包含姓名、联系方式、地址、可识别照片或身份映射的研究结果。它仍受研究同意和撤回规则约束。
_避免使用_：匿名即无隐私、公开用户数据

**身份映射（Identity Mapping）**：将 pseudonymous participant_id 连接到真实身份的受限记录，与 OutcomeObservation 分开保存，不进入普通分析、模型输入或展示包。
_避免使用_：用户主表、参与者画像

**同意范围（Consent Scope）**：参与者对数据收集、原始数据保存、去标识聚合、模型处理、公开展示、方法研究和知识增长等具体用途的授权集合。用途变化必须重新取得同意或停止对应处理。
_避免使用_：一次性总同意、默认研究授权

**证据影响分析（Evidence Impact Analysis）**：参与者撤回、数据删除、来源限制或方法纠正后，重新检查 Outcome Evidence、启发式和相关设计结论是否仍满足证据门槛的过程。
_避免使用_：自动删除贡献、忽略撤回影响

**同意记录（Consent Record）**：记录某位参与者在某一版本说明下，对各用途 Consent Scope 的授权、拒绝、变更和撤回时间及确认方式的不可变记录。
_避免使用_：勾选框状态、永久同意

**参与者数据控制（Participant Data Control）**：参与者查看已收集数据、了解用途、修改可修改信息、撤回某一用途或请求删除/限制处理的能力。
_避免使用_：用户设置、研究者决定

**参与者数据请求（Participant Data Request）**：参与者针对自己的研究数据提出 view、correct、withdraw_scope、delete_raw_data 或 restrict_processing 的可审计请求，带用途范围、验证状态和处理结果。
_避免使用_：普通客服单、删除按钮

**受控参与者验证（Controlled Participant Verification）**：在不向普通工作台暴露身份映射的前提下，确认数据请求者有权操作某个 pseudonymous participant_id 的受控流程。V1 使用一次性验证 token 或线下核对，不建立完整账号体系。
_避免使用_：直接输入 participant_id、公开身份映射

**请求验证状态（Request Verification Status）**：Participant Data Request 的身份验证结果，包括 pending、verified、failed、expired 或 manually_verified。验证失败/过期时不泄露 participant_id 是否存在。
_避免使用_：登录状态、找回账号

**请求处理状态（Request Fulfillment Status）**：数据请求从 received、under_review、partially_fulfilled、fulfilled、rejected 到 cancelled 的版本化状态，包含处理范围、理由、通知和证据影响分析。
_避免使用_：工单状态、删除完成即结束

**请求通知（Request Notification）**：向参与者说明数据请求处理范围、未完成部分、理由、保留聚合和证据影响的脱敏通知记录。V1 可手动发送，但必须保存时间和内容摘要。
_避免使用_：普通成功提示、内部日志

**传输受限（Transfer Restricted）**：资产已发送给远程 provider 后，参与者撤回授权、请求删除或 provider 无法取消处理时的状态。系统停止重试/再发送，并记录 provider 取消或删除能力及结果。
_避免使用_：远程已删除、撤回成功

**提示撤回（Prompt Revocation）**：尚未发送的 Next Design Prompt 因同意、资产、规则或人工决策变化而禁止发送的状态。已发送提示不可被修改，只能标记影响并请求 provider 处理。
_避免使用_：删除已发送 prompt、取消历史生成

**用途级撤回影响（Purpose-Scoped Withdrawal Impact）**：某一 Consent Scope 撤回后，按用途定位哪些提示、候选、评审、展示或知识增长流程需停止/限制，而不把单用途撤回扩大为全项目删除。
_避免使用_：全部撤回、全量删库

**聚合研究洞察（Aggregated Research Insight）**：由多个参与者的去标识结果汇总形成、无法直接回溯单个人的设计相关观察，可在满足同意、最小样本和重识别检查后作为下一轮提示的可选参考。
_避免使用_：用户原话拼接、匿名即安全

**最小聚合样本（Minimum Aggregation Sample）**：允许将研究结果形成 Aggregated Research Insight 或远程 prompt 参考所需的最低参与者数量/组合门槛。低于门槛只能留在当前研究分析。
_避免使用_：样本够大、隐私阈值随意

**隐私聚合门槛（Privacy Aggregation Threshold）**：按最小分组的参与者数量、敏感性和重识别风险判断结果能否被汇总或发送的门槛。它与 Outcome Evidence 的统计/研究支持强度独立。
_避免使用_：统计显著门槛、样本足够证明

**最小分组（Minimum Cell）**：由 target segment、user variation、scenario、condition 和时间窗口等字段共同定义的最细聚合单元。总样本量不能掩盖某个最小分组样本不足。
_避免使用_：总参与者数、平均用户

**聚合研究洞察（Aggregated Research Insight）**：满足隐私聚合门槛的去标识结果汇总，使用条件化、描述性方向表达体验/行为差异，并明确样本、测量、不确定性、替代解释和允许用途；不等于普遍偏好或因果结论。
_避免使用_：用户都喜欢、体验规律

**描述性方向（Descriptive Direction）**：由确定性分析计算的 higher、lower、mixed 或 no_clear_difference 等结果方向，只描述当前样本和条件下的观察，不自动代表效果、偏好或机制成立。
_避免使用_：效果方向、显著提升

**分析结果（Analysis Result）**：由版本化确定性脚本根据预注册指标计算的数值、方向、区间、样本、阈值状态、缺失和限制标记。它是自然语言摘要和结果审阅的唯一数值来源。
_避免使用_：模型统计、报告数字

**受限结果摘要（Constrained Result Summary）**：基于 Analysis Result 使用白名单表达生成的自然语言说明，不能新增数字、因果、显著性或普遍化表述。摘要校验失败时不得进入正式报告或提示包。
_避免使用_：LLM 自由解读、结果润色

**分析挑战（Analysis Challenge）**：人对数据、分析脚本、预注册偏差、结果解释或缺失上下文提出的结构化异议。它不能直接修改摘要，必须通过新分析输入/脚本/预注册 revision 解决。
_避免使用_：改报告、个人不同意

**编辑摘要修订（Editorial Summary Revision）**：只改变 Constrained Result Summary 的表达、不改变 Analysis Result、证据等级或判据的文字版本。它必须绑定原分析版本并通过字段一致性检查。
_避免使用_：改结论、重算结果

**分析运行（Analysis Run）**：绑定预注册、原始数据哈希、分析脚本版本、依赖锁、运行时、Schema 和参数的一次确定性分析执行。新脚本、数据清洗、参数或环境变化必须创建新运行。
_避免使用_：重新导出、覆盖统计

**可复现失败（Reproducibility Failed）**：同一 Analysis Run 无法在声明容差内重现结果，或缺少脚本、依赖、数据/参数等必要快照的状态。结果不能自动作为新证据使用。
_避免使用_：小数误差、运行失败

**原始数据（Raw Data）**：从用户研究、样机、传感器、问卷或访谈直接采集并经内容寻址保存的最初记录，不被清洗或模型覆盖。
_避免使用_：数据库当前数据、研究结果

**派生数据集（Derived Dataset）**：由 Raw Data 经去标识、清洗、排除、编码或聚合生成的不可变版本，保存转换脚本、参数、来源哈希和处理记录。
_避免使用_：清洗后的原始数据、临时表

**数据血缘（Data Lineage）**：从 Raw Data 到 Derived Dataset、Analysis Run、Result Review 和启发式的来源哈希、脚本、参数、版本和用途关系。
_避免使用_：数据来源备注、文件名链

**可回溯派生数据（Linkable Derived Data）**：仍能通过 participant_id、时间、罕见组合、身份映射或其他辅助数据回到单个参与者的派生数据，需要按个人数据处理。
_避免使用_：去掉姓名即匿名

**不可回溯聚合（Irreversibly Aggregated Data）**：经过最小分组、抑制罕见组合和重识别检查后，无法合理回溯到单个参与者的聚合结果。它仍受 Consent Scope 和用途限制。
_避免使用_：匿名数据、绝对安全数据

**重识别风险等级（Re-identification Risk Level）**：Derived Dataset 或聚合洞察在当前项目和可用辅助数据下被回溯到参与者的风险，取 low、medium、high 或 unresolved。它决定是否允许外传、展示和知识增长。
_避免使用_：匿名等级、隐私分数

**重识别检查（Re-identification Check）**：使用规则和人工复核检查直接身份、准标识符、小分组、罕见组合、时间地点、自由文本和外部联结的过程，不等于严格匿名化证明。
_避免使用_：匿名认证、LLM 隐私判断

**Provider 政策记录（Provider Policy Record）**：provider 某版本关于留存、训练使用、处理区域、删除能力和子处理方的可核验政策快照，带来源、哈希、检查人和时间。
_避免使用_：配置备注、服务商口头承诺

**政策状态（Provider Policy Status）**：Provider Policy Record 的 verified、self_declared、expired、rejected 或 unknown 状态，用于决定资产传输资格。
_避免使用_：安全等级、默认可信

**政策影响分析（Provider Policy Impact Analysis）**：provider 政策版本、留存/训练/区域/删除能力变化或违规发现后，定位受影响授权、Data Transfer Manifest、Job、结果、Prompt、候选和知识的过程。
_避免使用_：自动撤回数据、服务商评价分

**政策快照陈旧（Provider Policy Stale）**：已完成运行所引用的 provider policy revision 不再是当前可接受政策的状态。结果保留但新用途和新知识使用需要重新审阅。
_避免使用_：模型结果无效、历史删除

**Provider 请求快照（Provider Request Snapshot）**：一次远程模型请求实际发送的角色、provider/policy revision、Prompt Package、文本字段、资产/派生 hash、脱敏版本、Consent Scope 和 fingerprint 的不可变记录。
_避免使用_：上传日志、完整审计原文

**受限请求内容（Restricted Request Content）**：按资产隐私和 Consent Scope 受限保存的完整 prompt 或字段原文；审计默认只保存摘要/hash，复现导出需逐项授权。
_避免使用_：日志全文、默认公开 prompt

**Provider 派生资产（Provider-Derived Asset）**：远程或本地 provider 返回的图片、裁剪、标注、OCR、render、mask 或 embedding，带 parent_asset_ids、provider_run_id、输出类型、内容哈希、provenance、隐私等级和留存策略的新资产。
_避免使用_：覆盖原图、模型附属文件

**Provider 结构化输出（Provider Structured Output）**：provider 返回的 JSON/Schema 结果草案，包括观察、事件、变量、ReviewItem 或应用声明。它必须经过确定性校验和人工阶段门，不能直接成为领域事实。
_避免使用_：模型真值、已确认对象

**语义一致性检查（Semantic Consistency Check）**：在 Schema 合法之后，使用确定性规则检查 Provider Structured Output 内部字段、跨字段、与声明/观察资产的冲突。检查发现的冲突不能由 LLM 静默修复。
_避免使用_：模型自审、格式校验

**语义冲突（Semantic Conflict）**：Provider Structured Output 在能力、事件、变量、情境或来源之间同时声明互斥内容的状态，例如 supports_critical=false 但事件标记 critical。
_避免使用_：格式错误、普通未知

**语义冲突候选（Semantic Conflict Candidate）**：LLM 辅助检查提出的、尚未被确定性规则编码或人工确认的潜在冲突。它只能进入 explore/人工审查，不改变正式状态。
_避免使用_：自动语义阻断、模型发现即事实

**冲突规则升级（Conflict Rule Promotion）**：将重复出现且经人工确认的 Semantic Conflict Candidate 转换为版本化 Variable Compatibility Rule、Risk Rule 或输入校验规则的过程。
_避免使用_：自动加规则、模型自我改进

**规则升级门槛（Rule Promotion Gate）**：Semantic Conflict Candidate 成为确定性规则前必须满足的独立案例数、可形式化、证据链、人工确认、反例检查、Development/Validation 回归、影响评估和解除条件要求。
_避免使用_：模型自信、重复一次就规则

**新规则默认范围（New Rule Default Scope）**：新批准规则默认只适用于批准后的新 Job 和明确 re-evaluation，不静默改写历史候选、已完成实验或旧 Prompt。
_避免使用_：全库热更新、历史自动重算

**旁路规则运行（Shadow Rule Run）**：已批准但尚未强制执行的规则在不改变正式状态的旁路中运行，记录潜在命中、预期影响、误报/漏报和样本，但不参与正式偏序、阻断或评测真值。
_避免使用_：半生效规则、隐藏阻断

**强制规则运行（Enforced Rule Run）**：通过 shadow 和 Validation 后，经人工批准进入正式状态机、候选偏序和阶段门的规则版本。
_避免使用_：模型规则已启用、默认热更新

**规则发布证据（Rule Promotion Evidence）**：由 Shadow Rule Run、误报/漏报分析、Validation 回归和人工审查组成的规则升级证据包。它支持规则发布决策，但不作为模型训练或正式业务知识本身。
_避免使用_：测试分数、自动批准依据

**规则回滚修订（Rule Rollback Revision）**：对已 Enforced 规则通过新版本执行 supersede、收窄作用域、提高证据门槛或紧急暂停的修订。旧版本和历史命中保留，新版本按发布策略生效。
_避免使用_：改回旧文件、删除误报

**反事实比较（Counterfactual Comparison）**：在不改变 current 状态的副本上，移除或替换一个明确依赖（准则、规则、场景参数或 VariablePatch），重新计算候选评估和偏序，以解释结果敏感性。
_避免使用_：重新设计、任意假设实验

**反事实敏感性（Counterfactual Sensitivity）**：某个单依赖变化导致 Candidate Evaluation Record、tier、Reason Set 或选择上下文变化的可审计记录。
_避免使用_：因果证明、最佳规则搜索

**反事实解释（Counterfactual Explanation）**：基于结构化反事实差异，对候选偏序或设计权衡变化进行的受限说明。它必须标记 counterfactual_only，不是实际运行结果或因果证明。
_避免使用_：因果解释、替代现实结论

**反事实运行（Counterfactual Run）**：在只读副本和独立 fingerprint 上执行的单依赖反事实计算。它不能改变 current、正式评测、Consent Scope 或 Next Prompt。
_避免使用_：重新评审、试运行正式规则

**反事实缓存（Counterfactual Cache）**：按独立 fingerprint 保存反事实运行复用和重算产物的缓存，标记 reused 与 recomputed 资产，不可自动被正式 Job 消费。
_避免使用_：正式结果缓存、共享 current 缓存

**反事实预算（Counterfactual Budget）**：独立于正式评审的反事实运行调用/时延预算。V1 默认每候选最多 3 次、每 Brief 最多 10 次，结构化差异优先确定性计算，LLM 解释单独计费。
_避免使用_：免费搜索、无限敏感性分析

**反事实预算耗尽（Counterfactual Budget Exhausted）**：达到反事实运行次数或时延预算但仍有未执行请求的状态。它不表示没有敏感性，也不改变正式评审。
_避免使用_：敏感性为零、反事实完成

**反事实依赖选择（Counterfactual Dependency Selection）**：人从 Candidate Evaluation Record、Reason Set 和 Dependency Snapshot 中明确选择一个要移除/替换的依赖；系统可建议但不能自动穷举。
_避免使用_：自动敏感性搜索、模型自己试规则

**探索性反事实（Exploratory Counterfactual）**：人选择不在当前 Reason Set 中、但有明确研究理由的单依赖反事实，结果只作为研究材料，不改变正式解释集合。
_避免使用_：隐藏关键因素、正式评审补丁

**反事实预览（Counterfactual Preview）**：反事实执行前展示 baseline、依赖 revision、移除/替换操作、影响候选、预期失效/重算产物、安全/隐私影响、远程调用、成本和剩余预算的确认界面。
_避免使用_：确认弹窗、直接运行

**预期反事实差异（Expected Counterfactual Diff）**：基于依赖图和确定性规则预测哪些产物会失效或重算的结构化影响，不预测 LLM 最终解释或候选必然 tier 变化。
_避免使用_：预先知道结果、模型猜排名

**实际反事实差异（Actual Counterfactual Diff）**：Counterfactual Run 完成后由确定性重算和受限评审得到的实际产物、tier、Reason Set、事件覆盖和解释变化。它必须与 Expected Diff 分开比较。
_避免使用_：因果效果、反事实真相

**预期外依赖影响（Unexpected Dependency Effect）**：实际受影响对象超出 Expected Diff 或出现未声明的状态变化时的审计状态，需要检查依赖图或实现错误。
_避免使用_：模型惊喜、自动发现因果

**反事实决策支持（Counterfactual Decision Support）**：将 Actual Counterfactual Diff 与正式偏序、Reason Set、权衡和未决问题并列展示，帮助人决定是否创建新选择、验证任务或 Brief revision。它不改变原决策。
_避免使用_：自动重排、反事实替代现实

**反事实依据选择（Counterfactual-Based Decision）**：人基于反事实结果创建的新 Selection Decision、Validation Task 或 Brief revision，必须引用反事实 run_id 和说明其局限。
_避免使用_：反事实直接生效、伪实验结论

**反事实时间线记录（Counterfactual Timeline Record）**：记录反事实创建、确认、完成、取消和人工采纳的依赖、运行、差异、风险与后续决策。它区分领域变化和单纯预览行为。
_避免使用_：临时试算、隐藏分析

**受限反事实（Source-Restricted Counterfactual）**：反事实结构化记录仍保留，但其资产、原始模型内容或远程证据因删除、撤回或政策变化不可再访问的状态。它可用于审计，但不能宣称完整复现。
_避免使用_：已删除反事实、仍可复现

**反事实缓存清理（Counterfactual Cache Purge）**：清理未被决策、报告或研究引用的反事实派生缓存/原始响应，同时保留运行 ID、hash、状态和删除事件的操作。清理缓存不能删除时间线事实。
_避免使用_：删除反事实、撤销运行

**稳定对象 ID（Stable Object ID）**：领域对象在整个 revision 生命周期中不变的 UUID 标识。revision_id、revision_number 和 content_hash 不替代它。
_避免使用_：数据库自增 ID、版本就是 ID

**修订号（Revision Number）**：同一领域对象从 1 开始单调递增的整数顺序，用于 expected_revision 并发检查和版本排序，不能重用。
_避免使用_：数据库行号、时间排序

**注入式时钟（Injected Clock）**：由 application service 提供给领域操作的 UTC 时间来源，生产和测试可替换；领域对象不直接读取系统当前时间。
_避免使用_：datetime.now、前端时间

**内容哈希（Content Hash）**：对规范化不可变 payload 计算的完整性指纹，用于复现、去重检查和导出校验；它不是稳定对象 ID。
_避免使用_：哈希当主键、相同内容必然同一对象

**命令事务（Command Transaction）**：以一个 Domain Command 为边界，原子保存新 revision、current 指针、Domain/Audit Event、依赖记录和必要状态投影的事务。远程/长耗时调用不在其中执行。
_避免使用_：HTTP 请求事务、模型调用事务

**外部调用快照（External Call Snapshot）**：远程或长耗时 Job 开始前固定的输入 revision、fingerprint、能力/政策/同意快照。调用完成后只能基于该快照提交新领域 revision。
_避免使用_：调用时读取 current、动态输入

**陈旧 Job 结果（Stale Job Result）**：Job 完成时其输入 fingerprint、目标 revision 或依赖版本不再匹配 current 的合法输出。它可查看、比较或人工采纳，但不更新 current、不触发后续 Domain Event。
_避免使用_：任务失败、自动合并结果

**结果提交命令（Result Commit Command）**：Job 完成后检查快照和 current revision，并将合法结果创建为新领域 revision 或标记 stale 的显式 Domain Command。
_避免使用_：worker 直接写数据库、完成即生效

**Outbox 事件（Outbox Event）**：与 Domain Event 在同一 Command Transaction 中写入、由本地 worker 异步投递后续副作用的可靠事件记录。它有独立 delivery 状态和 event_id 幂等键。
_避免使用_：内存回调、事务后直接发请求

**Outbox 投递状态（Outbox Delivery Status）**：Outbox Event 的 pending、processing、delivered、failed 或 dead_letter 状态，支持重试、超时恢复和人工处理。
_避免使用_：消息已发/未发二元状态

**评审依赖快照（Review Dependency Snapshot）**：Review 绑定的 candidate revision、facts snapshot、Brief/scenario、机制目录、风险规则和变量词汇版本集合。只有依赖完全匹配 current 的 Review 才能参与正式偏序。
_避免使用_：引用当前候选、最新评审

**陈旧评审（Stale Review）**：Review 的任一依赖快照已不再匹配 current，或其来源资产/规则/机制被限制、废弃或纠错的状态。它可查看和比较，但不能作为正式偏序或 Next Prompt 输入。
_避免使用_：旧报告、错误评审

**实验假设链（Experiment Hypothesis Chain）**：从 ExperienceHypothesis 回溯到 ReviewItem、候选 revision、事件序列、Brief/场景、机制和变量快照的完整来源链。ExperimentPlan 必须保存该链。
_避免使用_：实验只挂产品名、心理构念单点

**假设状态陈旧（Hypothesis Stale）**：ExperienceHypothesis 的事实、情境、机制、规则或候选依赖已变化/受限，未执行 ExperimentPlan 不能继续运行的状态。
_避免使用_：假设被删除、实验自动失败

**假设绑定（Hypothesis Binding）**：ExperimentPlan 中对某个 ExperienceHypothesis revision 的独立绑定，声明 primary/secondary、预测结果、指标、分析族和状态。共享实验数据不使多个假设共享结果状态。
_避免使用_：实验假设列表、一起验证

**协议级变化（Protocol-Level Change）**：改变实验操纵、样本、场景、主要指标、停止规则或分析结构的变化，需要创建整个 ExperimentPlan 新 revision，而不是只更新 HypothesisBinding。
_避免使用_：改一个假设、继续原实验

**分析族（Analysis Family）**：共享一组数据、条件或主要指标的假设和分析集合，包含 primary、secondary、exploratory 分层、多重比较策略和解释政策。
_避免使用_：一组结果、一起分析

**预注册假设层级（Preregistered Hypothesis Tier）**：在实验执行前锁定的 primary、secondary 或 exploratory 假设身份。执行后不能静默改类，改变必须创建预注册修订并说明时间与原因。
_避免使用_：结果出来再选主要假设

**撤回影响结果（Affected by Withdrawal）**：已完成模型或实验结果因其依赖的参与者授权/资产被撤回而需要重新检查适用性或证据强度的状态。结果保留但不能自动作为新的证据输入。
_避免使用_：结果作废、自动删除

**模拟用户（Simulated User）**：用于流程、Schema、分支和评审可用性测试的非真人角色或合成行为。模拟结果不能作为真实体验结果或用户偏好证据。
_避免使用_：虚拟用户证明、AI 用户研究

**最小介入事件集（Minimum Intervention Event Set）**：每个 V1 候选必须声明的正常介入、用户延后/拒绝、低置信度和误判恢复四类事件；具备 critical 能力的候选还必须声明紧急介入事件。
_避免使用_：理想用户旅程、Happy Path

**基准场景（Benchmark Scenario）**：所有候选必须共同覆盖、用于公平事实确认和候选偏序比较的冻结使用场景。V1 默认包含深度工作、公共通勤和面对面交谈。
_避免使用_：示例故事、候选自选场景

**候选自定义场景（Candidate-Specific Scenario）**：候选为表达独特价值额外提供的 1–2 个场景，只用于单候选探索；未被所有候选共同覆盖前不参与正式跨候选偏序。
_避免使用_：比较优势场景、基准场景

**核心基准场景集（Core Benchmark Set）**：系统级版本化的 V1 基准场景集合，用于不同候选和系统版本的共同回归。DesignBrief 可在冻结前补充参数或对整个批次有理由地标记某场景不适用，但不能为单个候选删除。
_避免使用_：永久固定测试、随任务任意场景

**结构化基准场景（Structured Benchmark Scenario）**：由人可读叙事和 attention_demand、mobility、social_visibility、ambient_noise、hands/visual attention availability、event_criticality、inference_confidence、privacy_sensitivity、interruption/recovery cost 等版本化字段共同定义的比较场景。
_避免使用_：一段场景文案、模型自由理解

**体验准则（Experience Criterion）**：DesignBrief 中经过操作化的目标体验，包含定义、期望方向、可观察/禁止指标、适用场景、证据要求、优先级和并列处理规则。候选偏序引用准则，而不是模糊体验词。
_避免使用_：体验标签、形容词目标

**禁止体验（Prohibited Experience）**：DesignBrief 中经过操作化的非目标体验，按 hard、strong_avoidance 或 watch 分级，并声明触发指标、适用场景、证据要求和解除条件。只有 hard 且绑定批准风险规则时可触发 blocked。
_避免使用_：所有负面体验、模型风险判断

**设计约束（Design Constraint）**：DesignBrief 中以字段路径、白名单运算符、值、单位、容差、证据要求、检查阶段和失败状态定义的非体验限制，例如重量、尺寸、成本、续航或单手操作。
_避免使用_：文本要求、模型理解的轻量

**声明符合（Declared Compliance）**：候选声明值满足 DesignConstraint，但尚未经过样机或实测验证的状态。它不同于 Verified Compliance。
_避免使用_：符合约束、已验证通过

**工程声明（Engineering Claim）**：候选关于成本、可制造性、续航、耐久或合规的结构化主张，状态为 declared、source_supported、measured、unverified 或 conflicted。AI 生成的工程声明默认未验证。
_避免使用_：工程结论、可制造事实

**实测符合（Verified Compliance）**：由适用的物理测量、工程分析或正式合规证据证明候选满足某项 DesignConstraint 的状态。
_避免使用_：模型判断通过、声明符合

**工程证据提供者（Engineering Evidence Provider）**：执行 CAD、仿真、BOM、续航计算或物理测量并返回结构化 Engineering Evidence 的外部工具接口。它不属于 psyteardown 的核心体验推理。
_避免使用_：内置工程模块、LLM 工程判断

**工程证据（Engineering Evidence）**：外部工程工具返回的带工具/版本、输入资产、参数、方法、结果、单位、不确定性、限制和运行 ID 的证据记录。
_避免使用_：工程结论文本、AI 总结

**领域命令（Domain Command）**：显式表达冻结简报、确认事实、确认评审、选择候选或生成提示等状态变化的 API 操作，并检查对象当前 revision 和阶段门。
_避免使用_：页面保存、大对象覆盖

**只读投影（Read Projection）**：为工作台页面组合多个领域对象的查询视图，不拥有状态转换或写入规则。
_避免使用_：后端页面模型、写接口 DTO

**修订冲突（Revision Conflict）**：写请求携带的 expected_revision 与当前 revision 不一致的状态。服务端拒绝写入并要求人比较差异，不能自动合并领域决策。
_避免使用_：最后写入覆盖、自动解决

**陈旧结果（Stale Result）**：后台任务基于已不再是 current 的输入快照生成的合法输出。它可以查看、比较或手动采纳，但不能自动成为当前 revision。
_避免使用_：失败结果、自动更新

**设计来源（Design Source）**：候选产生方式的记录，分为 external_model、human 或 hybrid，并包含生成器名称/版本、Design Prompt Package 和人工编辑信息。它用于追溯，不等于生成器质量结论。
_避免使用_：作者署名、模型排行榜

**混合候选（Hybrid Candidate）**：由 AI 生成候选经人工实质修改后形成的新 revision，不能把后续评审或改善单独归因于原始生成器。
_避免使用_：AI 候选、纯人工设计

**生成器行为观察（Generator Behavior Observation）**：在明确模型、prompt、Brief 和样本范围内，对生成候选中重复出现的可观察设计模式进行的统计描述。它不构成生成器能力或人格画像。
_避免使用_：模型不懂隐私、生成器评分

**生成器提示补丁（Generator Prompt Patch）**：针对经过多 Brief 重复验证的生成器输出模式所提出、并经人工批准的可选提示补充。V1 不自动创建或应用。
_避免使用_：自动纠偏、自适应系统 prompt

**无辅助评审基线（Unaided Review Baseline）**：参与者直接查看相同 DesignBrief 和候选，凭经验选择并写自由文本反馈的对照条件。
_避免使用_：没有 AI、低质量对照

**通用模型评审基线（Generic LLM Review Baseline）**：使用通用“评价并推荐最佳设计”提示对相同 Brief 和候选生成自由文本与排名的对照条件，不包含 psyteardown 的结构化阶段门和证据模型。
_避免使用_：弱模型基线、故意差提示

**形成性评测（Formative Evaluation）**：由少量跨背景协作者参与、用于修正术语、流程、界面和审阅负担的早期研究。它不支持统计显著或普遍有效的主张。
_避免使用_：正式验证、小样本证明

**外部对照评测（External Comparative Evaluation）**：由未参与系统开发的设计/产品、心理/人因和目标用户参与，对无辅助、通用 LLM 与 psyteardown 条件进行受控比较的小规模研究。
_避免使用_：用户访谈、内部试玩

**合成基准案例（Synthetic Benchmark Case）**：人为构造并预先标注设计事实、证据冲突、风险规则、体验权衡和跨轮变量变化的候选案例，用于可靠性与回归评测。
_避免使用_：真实设计效果、用户偏好案例

**开放设计项目（Open Design Project）**：围绕真实 DesignBrief 生成和迭代候选、没有唯一最佳答案的设计任务，用于观察评审、选择与反馈基础设施的实际效用。
_避免使用_：带标准答案的测试、可靠性基准

**硬真值（Hard Ground Truth）**：可由资产、声明字段或确定性规则客观核验的基准答案，例如部件是否存在、参数是否声明、规则是否命中或指定变量是否改变。
_避免使用_：专家偏好、模型判断

**审议判断（Adjudicated Judgement）**：需要专业解释、可能存在合理分歧，并经独立标注和分歧处置形成的评测判断。它必须报告一致性和不确定性。
_避免使用_：客观真值、唯一答案

**开放评测问题（Open Evaluation Question）**：当前证据不足以设定唯一答案、正确系统行为是保留竞争假设并进入 explore 的问题。
_避免使用_：未标完、缺失答案

**开发评测集（Development Set）**：允许开发者查看案例、答案和逐项错误，用于实现和调试的基准子集。
_避免使用_：正式发布成绩、隐藏测试

**验证评测集（Validation Set）**：用于阶段验收、可查看结果但不应逐例调整规则的基准子集。
_避免使用_：调试样本、最终盲测

**保留评测集（Holdout Set）**：在发布评测前不进入模型输入、检索库或人工调参过程的基准子集。详细错误被查看后即转为验证集，下一次发布需要新保留集。
_避免使用_：永久秘密测试、开发样本

**纵向切片（Vertical Slice）**：从 DesignBrief 冻结到第二轮变量修复追踪和导出的端到端最小实现，横跨核心领域状态而不是先完成某一个技术层。
_避免使用_：模型 Demo、单页面原型

**不可变领域快照（Immutable Domain Snapshot）**：DesignBrief、候选事实、ReviewItem、Critique 等领域对象在某一 revision 下的不可原地修改状态。任何领域变更都以新 revision 和审计事件表达。
_避免使用_：更新同一对象、可变当前记录

**领域命令（Domain Command）**：在满足阶段门和 revision 前置条件后，对不可变领域快照提出的显式状态变化请求。命令返回新 revision 和待写入审计事件，而不直接修改旧对象。
_避免使用_：对象 setter、页面保存

**领域快照模型（Domain Snapshot Model）**：使用 Pydantic frozen model 或等价不可变语义表达的正式领域对象，集合字段采用不可变语义。它与 API 请求、LLM 草案和持久化 DTO 分离。
_避免使用_：可变 Pydantic 模型、接口 DTO

**评审草案（Review Draft）**：LLM 或导入流程产生、尚未通过确定性校验和人工确认的可变边界对象。草案不是正式 ReviewItemRevision。
_避免使用_：已确认评审、领域事实

**领域事件（Domain Event）**：表达领域对象已经发生状态变化的不可变事实，例如 BriefFrozen、CandidateFactsFrozen、ReviewItemConfirmed、CandidateSelected 或 NextPromptConfirmed。它可驱动投影和后续流程，但不用于重放恢复状态。
_避免使用_：审计日志、调用记录

**审计事件（Audit Event）**：记录一次操作的操作者、时间、目标、expected_revision、理由、来源和摘要，用于责任追溯与人工覆盖分析。它不等同于领域状态变化。
_避免使用_：领域事件、文本日志

**核心领域事件集（Core Domain Event Set）**：V1 中会影响工作流、权限、传输、实验或知识状态的领域事件集合，包括 Brief、Candidate、Facts、ReviewItem、Comparison、Next Prompt、Variable Repair、Experiment、Heuristic、Remote Consent 和 Asset 可用性变化。纯 UI 行为不属于该集合。
_避免使用_：所有操作日志、前端事件

**任务输入指纹（Job Input Fingerprint）**：由模型角色、冻结输入快照、Brief/事实/机制/规则版本、提示版本、provider/model/采样参数和资产哈希组成的稳定标识，用于确定 Job 是否可复用。
_避免使用_：请求 ID、页面点击次数

**探索性重跑（Exploratory Rerun）**：用户显式要求对相同 Job Input Fingerprint 再次执行的独立运行，用于观察模型稳定性。它不覆盖首次合法输出或当前结果。
_避免使用_：刷新结果、重新取最好答案

**稳定性评测（Stability Evaluation）**：对相同模型相关输入按冻结配置重复运行，报告结果一致率、均值和范围的评测过程。它不通过选择最佳一次输出掩盖模型方差。
_避免使用_：多跑取平均、最佳采样

**局部降级（Role-Local Degradation）**：单个模型角色或 provider 不可用时，只暂停该角色对应阶段，保留已确认事实和历史，并允许人工或稍后重试；不能把失败解释成无风险或自动跳过阶段门。
_避免使用_：全流程回退、静默换模型

**人工替代步骤（Manual Fallback Step）**：人在自动角色不可用时手动完成观察、ReviewItem 或审查动作的显式记录，带来源、理由、作者和时间，不伪装成模型输出。
_避免使用_：人工兜底、自动结果

**工作流恢复（Workflow Recovery）**：从最近 current revision 和持久化 Job 状态继续执行，只重试未完成、失败、过期或等待授权的当前步骤，成功步骤不重复执行。输入版本改变的旧结果标记 stale_result。
_避免使用_：重新跑全流程、内存队列恢复

**孤立任务（Orphaned Job）**：worker 心跳超时但未明确成功或失败的 Job。它必须先标记 orphaned，再由恢复操作重新排队或取消，不能直接假设失败或成功。
_避免使用_：后台丢失、自动重启任务

**反向修订（Reversal Revision）**：针对已确认选择、blocked、Next Prompt 或知识批准创建的显式撤销/解除/废弃新版本。它改变 current 状态，但不抹除原始决策。
_避免使用_：回滚覆盖、删除历史

**撤销依赖结果（Dependent-on-Revoked Result）**：基于后来被撤销的决策、提示或规则生成的结果。结果保留供审计，但不能自动成为新 current。
_避免使用_：无效结果、自动删除

**依赖快照（Dependency Snapshot）**：领域产物生成时记录的上游对象类型、ID、revision 和内容哈希集合，用于判断结果能否复用、是否 stale 或需要局部重新生成。
_避免使用_：全项目版本号、隐式依赖

**局部失效（Scoped Invalidation）**：上游 revision 变化时，只将依赖该 revision 的 ReviewItem、聚合、排序、提示或实验分析标记为 stale，不影响无关产物和原始实验数据。
_避免使用_：全量清空、静默重跑

**依赖无环约束（Acyclic Dependency Constraint）**：体验领域产物之间必须形成有向无环图；反馈只能通过新 revision 或新对象创建下一轮输入，不能让对象直接依赖自己或其下游结果。
_避免使用_：循环反馈边、同轮自引用

**候选组合（Candidate Composition）**：人从多个候选中按设计变量选择并组合，创建新的 Hybrid Candidate。组合候选保存多个 parent_candidate_ids、每个变量的来源和冲突处理，不继承父候选的已确认评审结论。
_避免使用_：拼贴方案、直接合并结果

**组合事实重审（Composition Re-review）**：Hybrid Candidate 重新生成 Candidate Facts Snapshot 后，对事件集、约束、冲突、风险和 ReviewItem 重新确认的阶段。父候选的事实和评审只能作为草案参考。
_避免使用_：复用父评审、继承通过

**规范设计变量（Canonical Design Variable）**：带稳定 variable_id、值类型、允许值/单位、来源要求、适用场景和风险相关性的 V1 设计变量词汇项。自由文本必须绑定到现有变量或形成待审变量候选。
_避免使用_：同义标签、模型自定义字段

**结构化变量值（Typed Design Variable Value）**：按规范变量的 value_type 表达、带 normalized_value、display_value、单位/范围、来源和 certainty 的值。缺失状态区分 not_declared、not_observable、not_measured 和 conflicted。
_避免使用_：自由字符串参数、模型认为的数值

**变量兼容性（Variable Compatibility）**：两个或多个设计变量值能否在同一候选和介入事件中同时成立的约束关系。未知或冲突的兼容性不能被自动假设为成立。
_避免使用_：模型拼接可行、变量相关性

**变量兼容性规则（Variable Compatibility Rule）**：描述规范设计变量之间 requires、forbids、conflict 或 recommends_review 关系的声明式规则。只有 approved 版本可被确定性引擎执行。
_避免使用_：临时模型判断、隐式业务逻辑

**变量词汇演进（Variable Vocabulary Evolution）**：通过新版本、replacement ID 和显式映射增量修改 DesignVariable 词汇，不重写旧变量、枚举值或单位语义。无法映射的跨版本比较标记 uncomparable。
_避免使用_：重命名覆盖、自动迁移所有历史值

**机制适用映射（Mechanism Applicability Mapping）**：将规范设计变量与机制卡关联的版本化知识，声明适用/排除情境、观察线索、混淆变量、测量方式和最低证据要求。它表示值得检查的关系，不表示因果已成立。
_避免使用_：变量到心理结果的固定映射、设计配方

**机制检索结果（Mechanism Retrieval Result）**：针对冻结候选事实和情境，返回的机制卡/适用映射、命中理由、适用边界和证据要求集合。被检索不等于被 ReviewItem 采用。
_避免使用_：模型知识上下文、已确认机制

**候选机制（Candidate Mechanism）**：尚未有 approved MechanismApplicability 支持、但由模型或人提出值得检查的机制关系。它只能生成 explore 或待审映射，不能直接作为正式机制依据。
_避免使用_：心理结论、已批准机制

**机制覆盖（Mechanism Coverage）**：一个 InterventionEvent 在当前机制目录和适用映射版本下的覆盖状态，取 none、partial 或 approved。覆盖状态不表示体验好坏。
_避免使用_：心理安全、机制评分

**无机制覆盖（No Mechanism Coverage）**：当前没有 approved MechanismApplicability 能支持某个事件体验解释的状态。系统仍可执行事实、约束、隐私和实验评审，但相关体验结论只能是 unknown/explore。
_避免使用_：无法评审、设计失败

**事件覆盖结果（Event Coverage Result）**：针对每个必需 InterventionEvent 的结构化状态，取 covered、partial、unknown 或 blocked，并列出事实、ReviewItem、规则命中和缺失项。它是事件级完整性结果，不是心理体验分数。
_避免使用_：事件评分、整体通过

**事件覆盖聚合（Event Coverage Aggregation）**：将模型提出的事件覆盖、事实完整性、ReviewItem 关联、机制覆盖和确定性规则命中汇总为 covered、partial、unknown 或 blocked 的过程。LLM 不直接决定最终状态。
_避免使用_：模型事件评分、自动通过

**候选评估记录（Candidate Evaluation Record）**：在候选偏序前汇总风险结果、事件覆盖、Criterion Assessment、Outcome Evidence、未知/探索、机制冲突和 Brief 权重的不可变记录。它保存决定 tier 的最小原因集合。
_避免使用_：候选总分、模型总评

**偏序原因集（Partial-Order Reason Set）**：解释候选为何进入 Preferred、Viable Alternatives、Needs Evidence 或 Blocked 的最小引用集合，包括规则命中、准则、事件和证据 ID。
_避免使用_：解释性长报告、隐藏评分

**首选集合（Preferred Set）**：在同一 DesignBrief 和证据快照下，满足推进门槛且当前无法合理区分的一个或多个候选集合。它不是唯一最佳设计，成员可并行进入下一轮或实验。
_避免使用_：冠军候选、最终答案

**并列推进（Parallel Advancement）**：人选择多个 Preferred 候选分别进入下一轮或验证，而不通过伪精确排序强行合并成一个方案的动作。
_避免使用_：自动集成、同时选冠军

**并行分支预算（Parallel Branch Budget）**：一轮 DesignIteration 允许推进的候选方向上限。V1 默认最多 2 个；改变该上限必须显式修改迭代策略或 Brief 配置。
_避免使用_：候选数量、生成批次大小

**保留比较（Held for Comparison）**：进入 Preferred 但因并行分支预算、人工选择或等待区分实验而暂不推进的候选状态。它不是 rejected，可在新证据或新 revision 后重新选择。
_避免使用_：淘汰、失败候选

**探索选择（Selected for Exploration）**：人从 Needs Evidence 候选中明确选择继续研究的状态，必须绑定未解决问题、验证任务和暂不接受的风险，不得按 Preferred 方案回灌。
_避免使用_：例外通过、临时 Preferred

**选择覆盖（Selection Override）**：人工选择与系统候选偏序不一致时的结构化记录，保存原偏序、选择动作、理由和后续约束，不修改原偏序结果。
_避免使用_：手动改排名、模型排序错误

**选择决策（Selection Decision）**：人工对候选执行 select、explore_further、hold、compose、reject 或 override 的结构化记录，包含决策依据、接受/拒绝权衡、后续任务、自由解释、作者和时间。
_避免使用_：按钮点击、主观标签

**人类判断信号（Human Judgement Signal）**：从 Selection Decision、ReviewItem 覆盖和冲突处置中提取的、尚未批准为规则或启发式的经验信号。它用于评测和候选知识提议，不自动改变模型行为。
_避免使用_：训练标签、人工真理

**人类判断信号池（Human Judgement Signal Pool）**：集中保存人工选择、覆盖、冲突处置和实验解释的待分析信号集合，带 Brief、情境、候选、作者和证据范围。信号池不是生产知识库。
_避免使用_：用户偏好数据库、自动规则库

**跨案例复盘（Cross-Case Synthesis）**：在多个 Brief、候选、情境和参与者的 Human Judgement Signal 上进行聚类、反例检查和适用范围分析，提出不同类型候选知识的过程。
_避免使用_：简单统计偏好、自动学习规律

**评审运行预算（Review Run Budget）**：一次候选批次允许使用的模型调用次数、重试次数和目标时延。V1 约束为每候选 4–6 个核心 ReviewItem、批次最多 40 次模型调用、单候选目标 3 分钟、整批目标 10 分钟。
_避免使用_：模型无限思考、只看 token 成本

**预算耗尽（Review Budget Exhausted）**：达到调用或时延预算后仍有未完成评审的状态。系统保留高风险和主要权衡结果，低优先级内容标记延后，不将未完成解释成无风险。
_避免使用_：评审完成、自动降级通过

**变量补丁（Variable Patch）**：将 actionable change 结构化为针对 canonical DesignVariable 的 set、replace、add、remove、constrain 或 relax 操作，包含原值/目标值、适用范围、理由、证据、预期影响、风险和验证方式。
_避免使用_：自然语言修改建议、体验优化句子

**补丁采用追踪（Patch Adoption Trace）**：通过比较父子候选的结构化变量值，判断 Variable Patch 是 adopted、partially_adopted、not_adopted 还是 unverifiable 的跨轮记录。
_避免使用_：文本变相似、模型说已修改

**补丁冲突（Patch Conflict）**：同一作用域内两个或多个 VariablePatch 对同一变量提出互不兼容的目标值或约束的状态。冲突必须由人解决、拆分为变体或撤回，不由生成器自行折中。
_避免使用_：最后 patch 覆盖、模型折中

**补丁执行强度（Patch Enforcement）**：人工确认的 VariablePatch 约束等级：must、should 或 explore。它决定未采用时的候选状态和是否必须生成对照/验证方向。
_避免使用_：模型优先级、自动重要性

**补丁作用域（Patch Scope）**：VariablePatch 适用的场景、事件类型、用户分群、时间窗口、设备模式和排除条件集合。修复追踪和冲突检查都在作用域内执行。
_避免使用_：全局修改、当前页面范围

**全局补丁声明（Global Patch Declaration）**：明确声明对所有适用场景和事件生效的 VariablePatch。它仍需列出排除条件，不能仅靠缺省空 scope 表示全局。
_避免使用_：无作用域补丁、默认全局

**补丁优先级解析（Patch Precedence Resolution）**：按排除条件、作用域具体性、执行强度和同级冲突规则决定某个介入事件实际生效补丁的确定性过程。被覆盖补丁保留为 shadowed_in_scope。
_避免使用_：最后写入生效、模型选 patch

**补丁应用声明（Patch Application Declaration）**：生成器对每个确认 VariablePatch 回报的 intended、actual、partial、not_applied 或 unverifiable 处理结果及其理由，不等于系统已验证变量改变。
_避免使用_：模型说已采用、自动修复证明

**补丁采用状态（Patch Adoption Status）**：由 psyteardown 根据父子候选的 canonical 变量值和确认事实确定的 adopted、partially_adopted、not_adopted 或 unverifiable 状态，不接受生成器自报作为唯一依据。
_避免使用_：模型已采用、prompt 执行成功

**生成器应用声明（Generator Application Declaration）**：外部设计生成器对某个 VariablePatch 的 intended、applied、partially_applied、not_applied 或 unverifiable 自述。它是候选输入数据，必须与事实 diff 分开保存。
_避免使用_：采用事实、系统确认

**候选草案（Candidate Draft）**：通过表单或版本化 JSON 导入、尚未通过输入契约和事实确认的 DesignCandidate 状态。草案不能参与正式评审、偏序或反馈回灌。
_避免使用_：半成品候选、已确认候选

**候选输入契约版本（Candidate Contract Version）**：定义 DesignCandidate 必填字段、允许资产引用、事件集、变量值和不可信数据边界的 Schema 版本，随每个候选保存。
_避免使用_：当前表单版本、接口版本

**输入不完整（Input Incomplete）**：Candidate Draft 缺少最小事件集、必填字段、关键情境推断声明或合法资产引用的状态。它同时属于 generation_invalid，但草案仍可保存和修订。
_避免使用_：低质量、评审不通过

**事件集完整性（Event Set Completeness）**：候选是否声明正常介入、延后/拒绝、低置信度、误判恢复以及在声明 critical 能力时的紧急介入事件。缺少必需事件会阻止 facts freeze。
_避免使用_：Happy Path 完整、功能列表完整

**紧急能力声明（Critical Capability Declaration）**：候选是否支持 critical 事件、允许的人工批准事件类别以及对应的最低必要介入策略的结构化声明。只有完整且无冲突的声明才能使用 critical 权限。
_避免使用_：高优先级通知、模型紧急判断

**最低必要介入策略（Minimum Intervention Policy）**：对每个 critical 事件声明在指定情境、置信度和用户授权下允许使用的最小反馈模态、时机、强度、确认和降级路径。它限制 critical 通道，不能由模型临时扩大。
_避免使用_：紧急就最高强度、默认全量打断

**默认介入策略（Default Intervention Policy）**：针对 routine/important 事件的可选默认模态、时机、强度、确认、延后和降级行为，用于低打扰设计评审。它不能覆盖 critical 策略。
_避免使用_：所有通知策略、模型默认行为

**最大介入强度（Maximum Intervention Intensity）**：某个策略在指定场景、事件和用户授权下允许达到的最高反馈显著性/打断级别。它是约束上限，不是推荐每次使用的强度。
_避免使用_：提醒强度分数、越强越好

**介入强度属性（Intervention Intensity Attributes）**：描述某种反馈实际如何吸引注意和产生代价的模态内字段，包括 salience_level、duration、repetition、persistence、privacy_exposure、attention_capture、user_override_cost 和 fallback_level。
_避免使用_：跨模态强度总分、声音比触觉高两分

**反馈模态画像（Modality Profile）**：描述一种反馈模态在隐私暴露、注意捕获、可发现性、持久性、社交可见性、可打断性、可逆性和用户操作成本等影响维度上的结构化画像。它用于多目标比较，不等于实验结果或跨模态总强度。
_避免使用_：模态心理分数、声音比触觉更强

**规则命中（Rule Match）**：兼容性或风险规则的确定性匹配结果，包含参与匹配的变量值、来源、rule_id、版本、影响和解除条件。规则命中必须可重现。
_避免使用_：模型说冲突、隐形警告

**规则优先级合并（Rule Precedence Merge）**：按 Scope Exclusion、Safety/Privacy Blocking、Brief Hard Constraint、Conflict、Requires、Recommends Review 的固定顺序合并多个 Rule Match 的过程，风险结果单调，不由普通支持项抵消。
_避免使用_：规则平均分、最后一条覆盖

**规则证据门槛（Rule Evidence Threshold）**：规则声明触发判断所需的最低证据类型，例如 declared、confirmed_observation、source_supported、measured 或 multiple_sources。事实未达到门槛时不能普通化地触发 blocked。
_避免使用_：模型置信度、任意证据

**高风险缺失规则（High-Risk Missing-Evidence Rule）**：专门处理关键隐私/安全声明缺失或高风险冲突的批准规则，可在“无法确认是否安全”本身构成风险时触发 blocked，而不是把所有未知都阻断。
_避免使用_：未知即危险、默认阻断所有探索

**传输授权等待（Awaiting Consent）**：任务因尚未获得针对具体资产、provider、模型和用途的传输/操作授权而暂停的状态。它不表示候选设计违反规则。
_避免使用_：隐私阻断、用户拒绝

**设计阻断（Design Blocked）**：候选在确认事实后命中范围、Brief 硬约束或批准风险规则的状态；普通传输授权不能解除，必须修改设计、简报或满足解除条件。
_避免使用_：任务暂停、等待同意

**本地能力等待（Awaiting Local Capability）**：任务需要处理 local_only 资产或执行本地专属能力，但当前没有可用本地 provider/人工路径的暂停状态。它不等于设计 blocked。
_避免使用_：模型失败、允许远程替代

**离线处理路径（Offline Processing Path）**：不发送任何外部资产即可完成的 Fake、人工或本地 provider 流程，V1 纵向切片和敏感项目必须至少保留其中一种。
_避免使用_：无网络模式但仍远程调用

**能力清单（Capability Manifest）**：provider 版本化声明的角色、输入模态、结构化输出、资产大小、数据驻留、local_only 支持、采样控制和限制集合。Job 执行前据此检查可行性。
_避免使用_：模型名称推断能力、配置备注

**Provider 运行（Provider Run）**：某个角色、provider 版本和输入指纹的一次独立输出记录。多个 Provider Run 的一致性不等于事实真值。
_避免使用_：模型投票、最终答案

**跨 Provider 一致性（Cross-Provider Agreement）**：多个独立 provider 对同一观察或判断的相似输出信号，只能辅助人工排序观察草案，不能自动生成确认事实或 ground truth。
_避免使用_：多数即正确、模型共识真值

**观察合并决策（Observation Merge Decision）**：人将多个 Observation Draft 合并为 Confirmed Observation 时记录的接受、拒绝、未决声明、来源 provider runs、合并类型、理由、作者和时间。合并不会提升任何来源的证据等级。
_避免使用_：模型共识、自动去重

**事实修订（Facts Amendment）**：在 Candidate Facts Frozen 后新增不影响、影响性或纠错性事实的方式，创建新的事实快照并按依赖图局部使下游 ReviewItem/聚合/排序失效。
_避免使用_：解冻修改、补丁覆盖

**事实纠错（Fact Correction）**：证明既有冻结事实错误或证据冲突后创建的 correction revision。原事实和错误来源保留，受影响结果重新评审。
_避免使用_：改正原记录、静默修正

**实验影响分析（Experiment Impact Analysis）**：事实、简报、机制或规则修订后，判断已完成实验的操作条件、解释、适用范围和结论状态是否受影响的过程。原始数据不被改写。
_避免使用_：自动重算结论、删除实验

**结果降级（Result Downgrade）**：因事实纠错、方法偏离、证据不足或复现失败，将已审阅结果从 supported 降为 needs_reanalysis、needs_replication、inconclusive 或 invalidated_by_fact_correction 的新 revision。
_避免使用_：撤销数据、改成绩

**复现冲突处置（Replication Conflict Handling）**：独立复现实验有效但与既有结果方向相反或没有清晰差异时，创建新的 `mixed/inconclusive` 结果 revision，不标记 `replicated`；若复现实验因样本、条件呈现、协议偏离或分析不可复现而无法解释，则创建 `needs_replication` revision。既有 `supported` 结果保留，不被静默改写。
_避免使用_：覆盖旧结论、冲突即删除

**复现效应一致性（Replication Effect Consistency）**：独立复现除方向一致外，还必须满足预注册的最小实际重要性或效应容忍范围；效应大小无法与该范围相容时，即使方向相同也不能标记 `replicated`。
_避免使用_：方向相同即复现、统计显著即稳定

**启发式废弃（Heuristic Deprecation）**：已批准设计启发式因证据、适用范围或反例变化而不再进入新的 Next Design Prompt 的状态。历史提示和候选保留依赖关系，不自动判定为错误。
_避免使用_：删除经验、历史失效

**启发式恢复（Heuristic Restoration）**：对 deprecated 启发式基于新证据创建新 revision 并重新审批的过程，不直接恢复旧版本状态。
_避免使用_：撤销废弃、改回旧版本

**紧急规则暂停（Emergency Rule Suspension）**：批准风险规则因明显错误或安全问题被立即停止新评审使用的状态。它不自动解除历史 blocked，必须进行影响分析和显式解除。
_避免使用_：删除风险规则、自动解封

**规则影响分析（Rule Impact Analysis）**：风险规则版本或状态变化后，定位受影响候选、ReviewItem、实验和启发式，并决定哪些需要重新评审、通知或保持原状态的过程。
_避免使用_：全量重跑、静默更新

**规则快照（Rule Set Snapshot）**：Job 创建时固定的规则集合 ID、版本和哈希，Job 整个生命周期使用该快照，不读取运行中的 current 规则。
_避免使用_：实时规则、运行中热切换

**规则快照陈旧（Rule Snapshot Stale）**：Job 完成时其固定规则集已 deprecated、superseded 或 emergency_suspended 的结果状态。结果可保存，但不能自动成为 current。
_避免使用_：运行失败、历史删除

**机制快照（Mechanism Catalog Snapshot）**：Job 创建时固定的机制卡集合、版本和哈希，运行期间不热切换。ReviewItem 保存使用的机制卡 ID/版本/引用位置。
_避免使用_：实时知识库、当前机制自动替换

**机制快照陈旧（Mechanism Snapshot Stale）**：Job 完成时所用机制卡已 deprecated、superseded 或发生来源纠错的状态。结果保留但需影响分析，不能自动作为新知识依据。
_避免使用_：机制结果删除、自动重算

**准则修订（Criterion Revision）**：DesignBrief 中某个 ExperienceCriterion 的操作性定义、指标、适用场景或优先级变化形成的新版本。它使相关 Design Alignment、偏序、选择上下文和 Next Prompt 需要局部重算，但不重写事实和原始 ReviewItem。
_避免使用_：改标签、重新打分旧结果

**场景修订（Scenario Revision）**：BenchmarkScenario 的结构化核心字段或适用性变化形成的新版本。它使引用该场景的 InterventionEvent、ReviewItem、Criterion Assessment、偏序和实验计划按依赖范围局部失效。
_避免使用_：改叙事、全量重跑

**选择流程支持作用域（Selection-Process Support Scope）**：`selection_process_support` 成立时所绑定的流程版本、候选选择执行团队能力、DesignBrief/任务范围和候选选择机会集组合。跨越任一边界都必须创建新 revision 并进行相应的独立验证，旧支持不能自动继承。
_避免使用_：跨场景自动泛化、同一候选即同一流程

**执行能力等价（Executor Capability Equivalence）**：不同候选选择团队或执行者在预先声明的任务理解、筛选一致性、冲突处理、人工成本和错误率等可观察指标上，经独立校准任务证明达到规定标准的状态。职位、经验或培训经历本身不构成等价证明。
_避免使用_：资历等价、培训即等价

**部分执行等价（Partial Executor Equivalence）**：新执行团队仅在部分预先声明维度达到等价门槛的状态。关键维度失败时不得继承旧流程支持；非关键维度部分达标只能创建明确收窄且带限制的新 revision，不能用平均分恢复原范围支持。
_避免使用_：平均能力达标、部分通过即全量继承

**执行能力关键性（Executor Capability Criticality）**：人工方法审阅者在实验前依据某项执行能力是否可能改变候选纳入/排除、排序、风险处置、冲突解决、人工覆盖或选择机会集，对该项标记为关键或非关键并冻结在预注册中的判定。事后发现影响可能时必须重新分类并进行影响分析，不能降级关键性以挽救支持继承。
_避免使用_：执行团队自定非关键、事后降级关键性

**执行关键性重分类影响处置（Executor-Criticality Reclassification Impact Handling）**：发现原标记为非关键的执行能力实际可能改变筛选结果时，对受影响范围立即暂停新注入和资格累积，保留历史支持并标记 `qualification_at_risk` 或 `needs_reanalysis`，通过字段级影响分析隔离未受影响范围；修复或重分析完成后仍须创建新 revision 并经人工审阅，不自动恢复。
_避免使用_：发现后继续注入、修复即自动解封

**字段级影响闭合（Field-Level Impact Closure）**：对执行能力关键性重分类的影响分析，逐字段、逐阶段、逐候选选择链核验候选池、筛选规则、排序、人工覆盖、风险/隐私/冲突处置、暴露与测量、数据链及选择机会集；任一环节无法隔离即不能声明范围未受影响。
_避免使用_：最终候选相同即无影响、只核对结果字段

**独立影响复核（Independent Impact Review）**：由不承担相关启发式维护或候选选择执行责任的方法审阅者，对字段级影响闭合逐项核验并签署的复核。涉及安全、隐私、控制权或支持资格恢复时，必须双人复核并记录证据、异议和签名，维护者或受影响团队不得单独自证。
_避免使用_：维护者自证、看摘要即通过

**审阅者独立性最低标准（Reviewer Independence Minimum）**：独立方法审阅者必须与流程设计、执行、候选筛选、数据分析和启发式维护角色隔离，不对支持资格、上线或绩效承担直接利益；复核依据冻结清单和原始日志，并披露利益冲突。同团队复核若无法满足隔离，只能标记 `limited_independent_review`，不能恢复完整支持资格。
_避免使用_：同团队轮换即独立、无利益披露复核

**审阅独立性共享依赖评估（Shared-Dependency Review Independence Assessment）**：审阅者是否来自组织外部不是独立性的充分条件。无论同组织还是跨组织，工具、培训、管理链、数据管线和绩效目标等共享依赖都必须事前披露并评估；可能影响关键字段时仅可标记 `limited_independent_review`，除非证明不影响或由外部复核补足。
_避免使用_：外部身份即独立、同组织即不独立

**共享依赖降级修订（Shared-Dependency Downgrade Revision）**：共享依赖等级只有在创建事实修订、提交可核验的字段级证据并完成重新影响分析后才能改变；事后说明不能直接把 `high_shared_dependency` 降为较低等级。在修订完成前维持 `limited_independent_review` 或 `external_independence_unclassified`，降级也不能追认既往失去的资格。
_避免使用_：补充说明即降级、事后降级追认资格

**共享依赖无影响证据门槛（Shared-Dependency Non-Impact Evidence Threshold）**：要证明共享依赖不影响关键字段，至少提交两类来自可独立核验上游的证据，例如访问/操作日志与冻结协议或数据血缘记录，并逐字段覆盖。单一团队的回顾性声明不能降级依赖或恢复资格。
_避免使用_：一份声明即证明、只看总结报告

**证据独立上游血缘（Independent Upstream Evidence Lineage）**：多类证据是否独立按不可互相生成的上游来源计数，而非按文件格式、报告数量或字段数量计数。同一系统或团队导出的多份材料仅算一条 lineage；来源独立性无法证明时标记 `shared_evidence_lineage`，不得用于降级共享依赖或恢复资格。
_避免使用_：多文件即多证据、不同格式即独立

**关键字段闭合门槛（Critical-Field Closure Threshold）**：共享依赖无影响的独立性声明必须对每个预先列出的关键字段分别达到证据门槛；不同证据可按事前声明的字段分层分别判定，但不能用总体覆盖或字段数量抵消任一关键字段缺口。
_避免使用_：总体覆盖抵消缺口、字段越多越可信

**新增可观测性不追溯补资格（Prospective Observability Only）**：历史关键字段缺少日志或可核验证据时，形成 `independence_coverage_gap`；后来新增的日志、监控或数据链只能支持未来运行或新 revision，不能倒灌补足旧实验的独立性或资格。旧结果最多保持 `limited_external_support` 或 `needs_reanalysis`。
_避免使用_：补日志即补历史资格、事后可观测性追溯证明

**运行内可观测性分段（Within-Run Observability Segmentation）**：实验运行中途启用关键字段可观测性时，只有按预先定义的运行分段规则，并以逐参与者、逐候选、逐关键字段的可靠时间戳证明前后隔离，才能将后段作为受限分析单元；无法分段隔离时，整条运行 lineage 保持 `independence_coverage_gap`。
_避免使用_：中途开日志即全程合格、按报告章节切段

**可靠事件时间戳（Trusted Event Timestamp）**：用于运行内分段的时间戳必须由权威系统在事件发生时自动写入，关联参与者、候选、关键字段和运行 ID，并保留不可静默改写的原始审计链；时钟来源、漂移容忍度和跨系统对时规则须预先声明。人工补填、报告生成时间或可任意改写的客户端时间不构成可靠时间戳。
_避免使用_：人工时间、导出时间即事件时间

**时间戳完整性失败（Timestamp Integrity Failure）**：时钟漂移超出预先容忍度或事件顺序无法可靠重建时，受影响时段的时间戳完整性状态。该状态不得用于严格运行分段或独立资格；仅可依据预注册的独立时钟源、校准方法、最大误差和外部顺序证据创建 correction/reanalysis revision，不能用受污染时间戳自证校准。
_避免使用_：事后统一校时、同一日志自证校准

**事件顺序重建证据（Event-Order Reconstruction Evidence）**：当时间戳完整性失败而事件顺序影响候选筛选、暴露或资格判定时，至少需要两条独立上游证据共同覆盖同一关键顺序边界。单条证据只能标记 `order_reconstruction_signal`；证据冲突时标记 `order_inconclusive`，不得择一解释。
_避免使用_：单证据重建顺序、选择最合理时间线

**相关证据依赖（Correlated Evidence Dependency）**：不同系统的事件顺序证据若共享时钟源、同步服务、采集设备、操作人员或可能造成相同错误的上游故障模式，不能仅因系统边界不同而视为独立。此时标记 `correlated_evidence_dependency`，除非有不共享该依赖的额外证据或预注册独立校验。
_避免使用_：系统不同即独立、双份同源证据

**独立证据依赖图（Independent Evidence Dependency Graph）**：证据独立性通过逐关键字段/顺序边界的依赖图判定；至少一条证据路径不得与其他证据共享关键时钟、采集、同步或操作故障的共同因果祖先。允许共享不影响该字段的基础设施，但关键错误路径必须隔离并留痕；依赖图不完整时标记 `independence_dependency_unknown`，不满足恢复资格。
_避免使用_：来源名称即独立、依赖未知即无依赖

**回溯依赖图资格（Retrospective Dependency-Graph Qualification）**：证据依赖图可在实验后回溯绘制，但只有依据实验前已存在且不可静默修改的架构、配置、访问和故障记录，并经独立审阅者核验，才可用于资格判断。依赖回忆或事后解释补齐的节点维持 `independence_dependency_unknown`，不能恢复独立资格。
_避免使用_：事后访谈即依赖证明、回忆补图即合格

**依赖图变更修订（Dependency-Graph Change Revision）**：实验期间关键架构、配置、访问权限或故障依赖发生变化时，必须创建带时间边界的 dependency-graph revision 并按变更前后分段；不同 revision 不共用同一独立性结论。未及时记录的变化使受影响时段标记 `dependency_revision_unknown`，除非预注册允许且证明关键错误路径未改变，否则不得计入严格资格。
_避免使用_：依赖变更后继续沿用结论、事后合并分段

**迟记依赖变更重建（Late-Recorded Dependency Change Reconstruction）**：依赖变更未及时记录但可由独立外部日志精确还原时，只能通过 correction/reanalysis revision 重新分段。外部日志须定位变更时点和受影响字段，并证明各段关键错误路径稳定；重建不能追认原有严格资格，最多形成受限证据，除非其他事前条件本已满足。
_避免使用_：事后还原即追认资格、外部日志替代全部事前条件

**延迟写入外部日志（Delayed-Write External Log）**：仅当日志系统在事件发生时已自动采集原始数据、之后只是延迟传输或索引，并能核验采集时间、写入时间、不可变哈希/序列号、生成系统和传输链时，才可作为依赖变更重建证据。事故后汇总、人工回填或从受影响日志推导的记录只能作为线索。
_避免使用_：事故后汇总即原始日志、人工补录即事件证据

**事后完整性未验证（Posthoc Integrity Unverified）**：原始日志虽存在，但不可变哈希、签名或可信时间锚定仅在事故后生成，无法证明事件时版本未被改写的状态。此类记录标记 `posthoc_integrity_unverified`，只能作线索；资格恢复还需事件时/周期性锚定、追加式存储或独立备份及连续性核验。
_避免使用_：事后哈希即历史完整性、当前文件哈希即原始证明

**签名密钥妥协完整性不确定（Key-Compromise Integrity Uncertainty）**：事件时使用的签名密钥后来泄露或撤销，且无法以独立可信时间锚定、密钥控制证明、明确泄露边界和未改写的日志版本链确认签名有效性的状态。标记 `key_compromise_integrity_uncertain`，不得用于恢复资格；满足全部条件时也仅可有限保留泄露前签名。
_避免使用_：撤销后签名一律有效、事后轮换即覆盖历史

**密钥妥协保守时间窗（Conservative Key-Compromise Window）**：密钥泄露时间只能确定为区间时，从最后可独立证明密钥安全的时间点起，至完成轮换、吊销并验证新信任链路的时间点止，整段标记 `key_compromise_integrity_uncertain`。不得从发现时间起算或仅凭签名时间戳自行切分；只有独立证据才能缩小窗口。
_避免使用_：发现时刻才受影响、签名时间戳自证切段

**密钥过渡完整性不确定（Key-Transition Integrity Uncertainty）**：密钥轮换期间新旧密钥并行使用，但新钥缺少独立信任锚、明确生效时间、授权控制证明或轮换验证记录，或逐条日志的密钥/链路版本不清时的状态。整个重叠区间标记 `key_transition_integrity_uncertain`，不得用于恢复资格。
_避免使用_：新钥一启用即可信、轮换期间默认完整

**根信任锚妥协完整性不确定（Trust-Anchor Integrity Uncertainty）**：验证密钥链的根信任锚被妥协或妥协时间不明时，按妥协时间窗和依赖链影响分析，将依赖该根锚的记录标记 `trust_anchor_integrity_uncertain`；只有不共享该根锚或共同故障路径的独立外部锚定才可能保留，不能用同一根锚自证。
_避免使用_：根锚妥协前签名一律有效、同根证明自证安全

**相关信任锚依赖（Correlated Trust-Anchor Dependency）**：不同供应商的根信任锚若共享决定事件存在时间或签名有效边界的同一时间戳服务或其他关键祖先，不能自动视为独立，标记 `correlated_trust_anchor_dependency`。只有证明共享祖先不影响判断，或有不共享它的独立事件时间证据，才可合并恢复资格。
_避免使用_：供应商不同即锚定独立、双根链自动互证

**锚定汇合不确定（Anchor Convergence Inconclusive）**：根信任锚证据存在冲突时，按独立上游 lineage 而非证据数量计数；共享关键祖先的证据不能以多数压过独立反向证据。冲突标记 `anchor_convergence_inconclusive`，只有新的、事前允许的仲裁证据在新 revision 中解决后，才可重新判定。
_避免使用_：2 比 1 多数采信、相关证据压过独立冲突

**未预注册仲裁限制（Unregistered Arbitration Limitation）**：根锚冲突后临时引入、未预注册的第三方仲裁服务只能用于诊断、规划或生成新验证任务，不能追溯恢复当前资格。冲突解决必须创建新 revision，事前锁定仲裁来源、判据、独立性和失败处理，并重新验证受影响范围。
_避免使用_：冲突后临时找裁判、仲裁结果追认旧资格

**仲裁故障降级（Arbitration Failure Degradation）**：新 revision 中的仲裁服务不可用、超时或无法得出结论时，必须记录 `arbitration_unavailable`、`arbitration_timeout` 或 `arbitration_inconclusive`，并保持 `anchor_convergence_inconclusive`，暂停受影响范围的新资格累积与支持恢复。不得静默回退到多数投票、维护者判断或旧根锚；仅可切换到预先声明且同样独立的备用路径并记录切换。
_避免使用_：仲裁失败自动回退、维护者临时裁决

**仲裁路径选择偏差（Arbitration Path Selection Bias）**：备用仲裁的触发条件、优先顺序、重试次数和停止规则必须在新 revision 预先锁定，并只能由技术状态触发，不能按主仲裁结果是否满意来选择。主仲裁返回结论后才选择备用路径时，标记 `arbitration_selection_bias`，两者最多作探索性比较，不能恢复资格。
_避免使用_：结果不满意才换仲裁、事后挑选仲裁路径

**仲裁重试血缘（Arbitration Retry Lineage）**：相同仲裁服务、版本、输入和信任链的多次重试属于同一仲裁 lineage，只说明可重复性，不增加独立证据数量。提示、参数、输入裁剪或判据变化后的重试标记 `arbitration_specification_shift`，只能作探索性敏感性分析，不能择优恢复资格。
_避免使用_：多次重试即多份独立证据、改参数后挑最好结果

**相关仲裁血缘（Correlated Arbitration Lineage）**：不同供应商的仲裁服务是否独立，须追踪模型家族/版本、训练或微调快照、关键数据来源、运行基础设施、提示与判据、输入处理和信任链，而非仅看供应商名称。共享上游可能造成同方向错误时标记 `correlated_arbitration_lineage`；只有关键错误路径隔离才计为独立仲裁证据。
_避免使用_：供应商不同即独立、模型同源却算双证据

**仲裁血缘未知（Arbitration Lineage Unknown）**：仲裁服务的模型、训练/微调数据、关键基础设施或信任链等必要血缘字段未披露或无法核验的状态。未知不等于独立；该服务仅可用于诊断或探索性敏感性分析，不能计入独立仲裁证据、解决根锚冲突或恢复资格，除非获得可核验的最小血缘声明或独立验证路径。
_避免使用_：供应商保密即默认独立、未知即无共享

**仲裁血缘变更（Arbitration Lineage Change）**：同一 revision 内仲裁服务更换后端模型、训练/微调快照、运行基础设施或其他关键上游时的状态。必须从最后可验证声明起切断独立性继承，按变更前后建立新 lineage 和时间边界；时点不明时使用保守窗口并标记 `arbitration_lineage_unknown`，事后补发声明不能自动恢复旧结果。
_避免使用_：供应商补发说明即无缝继承、同 revision 内隐式换后端

**仲裁后端兼容新修订（Compatible Arbitration Backend Revision）**：仲裁后端模型或基础设施变化后，只有通过事前定义的等价性测试，证明关键字段输出、失败模式、时序和信任链均达到门槛，才能建立的兼容关系。它始终是新 revision、独立 lineage 的有限关联，不能因供应商声称语义兼容而自动继承旧支持。
_避免使用_：性能变更不算变更、语义兼容即同一 lineage

**仲裁决策语义兼容（Arbitration Decision-Semantic Compatibility）**：后端兼容性以事前冻结测试集中的关键顺序/完整性结论、冲突/缺失/超时状态、边界与反例决策、时序/重试和信任链是否保持为准，而非文本相似度。任一关键字段或安全相关失败模式改变即不兼容；措辞变化本身可接受。
_避免使用_：文本相似即兼容、平均相似度抵消关键变化

**兼容性测试污染风险（Compatibility Contamination Risk）**：仲裁后端兼容性测试集可能被供应商访问、泄露或进入训练/微调数据而无法排除的状态。兼容性验证必须包含供应商不可见的 holdout、未公开边界/反例和新鲜 canary，并记录访问、泄露与训练污染；污染无法排除时标记 `compatibility_contamination_risk`，只能作探索性证据，不能支持独立性继承。
_避免使用_：固定公开集即等价证明、可能见过也算盲测

**Canary 暴露退役（Canary Exposure Retirement）**：新鲜 canary 被供应商、其训练管线或可访问人员知悉后，标记 `canary_exposed` 并退出确认性兼容性证据；暴露后的成功不能证明持续兼容。后续验证必须使用新的、未暴露 canary，旧 canary 仅保留历史审计记录。
_避免使用_：暴露后重复计入、同一 canary 长期复用

**Canary 独立保管（Independent Canary Stewardship）**：不参与仲裁服务开发、供应商沟通或结果判定的独立 steward，以与被测后端无关的来源和秘密种子生成并保管未暴露 canary，直至执行时才揭示；生成、抽样、访问和销毁均须审计。被测模型生成、公开样例改写或同一供应商保管的 canary 标记 `canary_generation_contamination`，不能作确认性证据。
_避免使用_：供应商保管盲测、公开样例改写即 canary

**Canary 保管结果盲法（Canary Steward Outcome Blinding）**：canary steward 在执行后可查看必要审计信息，但在揭示前和结果判定前不得看到被测后端结果，也不能据结果调整抽样、替换 canary 或决定纳入。盲态被打破后，结果判定须由另一独立人员接管；否则标记 `canary_steward_outcome_contamination`，该轮不能形成确认性兼容性结论。
_避免使用_：保管者看结果再换题、同一人生成保管判定

**Canary 技术失败替换（Canary Technical-Failure Replacement）**：canary 只能在预先定义且与仲裁结论无关的技术失败条件（如请求未送达、响应损坏或基础设施故障）下替换；替换次数、抽样算法和停止规则须冻结，不得因结果不利或难判而换题。技术失败过多时标记 `canary_execution_integrity_failure`，不得静默删除失败样本后宣称兼容。
_避免使用_：结果不满意即换题、删失败样本

**Canary 失败分类复核（Canary Failure Classification Review）**：技术失败或仲裁失败的分类由与供应商、canary 保管和结果判定隔离的运行完整性审阅者，依据冻结的原始请求/响应、传输和基础设施日志判定。超时、拒答、解析失败或安全降级若可能源于服务行为，不得自动替换；分类不确定时标记 `canary_failure_classification_uncertain`，不替换、不剔除，并阻止确认性兼容结论。
_避免使用_：服务拒答一律技术失败、结果审阅者自行分类

**失败分类审阅者利益冲突（Failure-Classification Reviewer Conflict of Interest）**：运行完整性审阅者与运维团队共享管理链时，必须披露并评估其绩效、上线责任或事故归因是否会直接受失败分类影响；存在直接利益时标记 `reviewer_conflict_of_interest`，分类不得用于替换 canary 或恢复资格。无直接利益的关键争议仍须第二名隔离审阅者复核。
_避免使用_：同管理链即天然独立、无披露的内部复核

**失败分类争议（Failure-Classification Dispute）**：两名隔离审阅者对 canary 失败分类结论相反时的状态。标记 `failure_classification_disputed`，不得以多数投票替换或剔除 canary；仅可由预先声明且独立于双方和相关基础设施的裁决路径，结合原始证据在新 revision 中重新判定。裁决不可用时维持不确定并阻止确认性结论。
_避免使用_：第三人多数决、争议时挑选一方

**失败分类裁决后重新纳入（Post-Adjudication Canary Reinstatement）**：独立裁决推翻原失败分类时，只能在新分类与兼容性 revision 中重新纳入对应 canary，保留原审阅结论、裁决依据、证据链和裁决独立性记录。重新纳入仅影响该 canary，不抹除同批次其他失败、替换行为或污染标记；裁决路径存在依赖或盲法缺口时仍为受限证据。
_避免使用_：裁决后覆盖历史、单个翻案洗掉整批失败

**关键兼容失败不可补偿（Non-Compensatory Critical Compatibility Failure）**：兼容性测试中，安全、完整性、关键顺序或资格相关的决策语义任一变化即阻止兼容性结论；总体通过率、文本相似度或大量普通 canary 通过不能抵消。只有普通字段差异可按预先声明的容忍范围汇总分析。
_避免使用_：平均通过率掩盖关键失败、数量多数抵消安全差异

**关键 Canary 分类（Critical Canary Classification）**：兼容性 revision 开始前，由独立方法审阅者依据 canary 失败是否可能改变安全、完整性、关键顺序、资格或候选纳入/排除，将 canary 分类为关键或普通并冻结在预注册中。不得按测试结果事后降级关键性；普通 canary 后来被证明影响关键决策时，须触发 criticality reclassification 和影响分析。
_避免使用_：失败后降级关键、结果导向分类

**关键路径 Canary 覆盖（Critical-Path Canary Coverage）**：关键 canary 必须覆盖每条关键决策路径及其预先定义的边界/反例，包括正常通过、应阻断、证据缺失、冲突、超时/降级和资格拒绝等，不得以每类单题或总体数量替代。任一路径无覆盖时标记 `critical_path_coverage_gap`，不能声称后端兼容或恢复资格。
_避免使用_：每类一题即覆盖、总通过率代表路径覆盖

**关键交互 Canary 覆盖（Critical-Interaction Canary Coverage）**：无需穷举所有路径组合，但必须在 revision 开始前锁定风险驱动的关键交互矩阵，至少覆盖会共同影响同一决策的组合，如证据缺失×超时降级、冲突×资格拒绝、密钥过渡×时间戳异常。未覆盖的高风险交互标记 `critical_interaction_coverage_gap`，单路径通过不能外推交互兼容。
_避免使用_：单路径全通过即组合安全、事后挑交互组合

**关键交互事后发现重分类（Post-Discovery Critical-Interaction Reclassification）**：发现预注册矩阵未覆盖的高风险交互时，不得原地追加测试并沿用旧兼容结论。必须标记 `critical_interaction_reclassification`，暂停受影响范围的新资格累积并创建新的 canary/兼容性 revision；旧结论保留为未覆盖该交互的历史结果。
_避免使用_：事后补一题即原 revision 已覆盖、旧结论自动扩展

**关键交互重分类触发分级（Critical-Interaction Reclassification Trigger Tiers）**：一次确认的安全、隐私、控制权或完整性事件即可触发关键交互重分类；普通体验或性能交互按 revision 批准时冻结的重复次数、独立 Brief/场景和影响幅度阈值触发；无法确认、事实未决或技术噪声仅作信号，不直接扩大暂停范围。阈值不得事后调整。
_避免使用_：所有单次信号都阻断、看到结果再改阈值

**高风险交互暂停范围（High-Risk Interaction Suspension Scope）**：确认高风险交互后，按字段级依赖图暂停受影响交互、相关决策路径和共享上游的最小可证明范围；共享模型、规则、信任链或证据链可能传播风险，或影响边界无法闭合时，必须保守扩大至全局 `validation-only` 或人工选择，直至影响分析完成。
_避免使用_：边界不明仍局部放行、默认全局永久冻结

**暂停期间隔离路径（Isolated Path During Suspension）**：全局暂停期间，只有字段级依赖闭合证明某路径不共享受影响的模型、规则、信任链、数据链、选择机会集或关键故障模式时，才可继续运行并标记 `isolated_during_suspension`。功能名称、业务团队不同或历史未出问题不构成隔离证明；无法闭合时保持 `validation-only` 或人工选择。
_避免使用_：名字不同即无关、历史无事故即隔离

**暂停期间隔离路径的资格限制（Suspension-Isolated Path Qualification Limit）**：`isolated_during_suspension` 路径在全局暂停解除前只能产出运营性、描述性或验证规划数据，不能新增 `selection_process_support`、启发式资格、外部独立 lineage 或范围扩张；解除暂停须另行完成影响分析与显式恢复。
_避免使用_：隔离例外绕过暂停、暂停中累积资格

**全局暂停解除授权（Global Suspension Release Authority）**：全局暂停只能在预先冻结的恢复条件全部满足后，由独立方法审阅者与独立风险/完整性审阅者双签解除；高风险范围还需人工安全/隐私负责人确认。触发暂停的维护者、供应商或原执行团队不得单独解除。解除必须创建新 revision，列出缺口关闭、剩余限制、恢复范围和监测窗口。
_避免使用_：触发者自解封、修复即自动恢复

**暂停解除与资格恢复分离（Suspension Release vs Qualification Restoration）**：解除全局暂停只能进入 `revalidation_ready` 或新 revision 的候选范围，不自动恢复原完整支持。新的预注册验证、覆盖闭合和监测窗口须按具体交互、执行团队和 Brief 分范围完成；未覆盖部分继续暂停或 `validation-only`。
_避免使用_：解封即全量恢复、局部验证恢复全局资格

**恢复范围授权（Release Scope Grant）**：部分恢复必须生成机器可检查的结构化授权，逐项列明允许的交互、决策路径、Brief、执行团队、模型/规则/信任链 revision、排除条件、监测义务和失效条件。系统对授权外情境默认拒绝；口头说明、自由文本或人工记忆不构成恢复授权。
_避免使用_：恢复范围靠口头传递、未列排除条件即默认全局

**恢复授权冲突合并（Release Grant Conflict Merge）**：多个 `Release Scope Grant` 重叠或冲突时，按事前冻结规则确定生效授权：暂停/风险/失效条件优先；更具体的交互、Brief 或团队范围优先；同等具体度下仅明确 `supersede` 的较新 revision 取代旧授权；无法确定时标记 `grant_conflict` 并默认拒绝。
_避免使用_：最后写入生效、运行时挑授权

**恢复授权撤销收敛（Release Grant Revocation Convergence）**：发现新的高风险证据时，`Release Scope Grant` 必须通过不可变 `revoke` revision 失效，并立即传播到所有执行节点和缓存；授权校验默认 fail-closed。撤销不删除历史，离线缓存不得继续放行；传播状态不明时标记 `grant_revocation_pending`，相关路径暂停或转人工，直至确认收敛。
_避免使用_：只改中心状态、缓存继续放行、静默删除授权

**撤销收敛回执闭合（Revocation-Convergence Receipt Closure）**：撤销收敛须由每个预登记执行节点、缓存和离线代理确认已读取指定 `revoke` revision，并提供不可伪造的版本、时间和签名回执；回执集合必须与节点清单闭合。节点离线、回执缺失或版本落后时维持 `grant_revocation_pending`，不能因超时自动视为已撤销。
_避免使用_：中心写入即收敛、超时即默认撤销成功

**未登记执行面（Unregistered Execution Surface）**：发现未登记的执行节点、缓存或离线副本时的状态。标记 `unregistered_execution_surface`，不得假定其未持有或执行受影响授权；必须纳入节点清单并扩大撤销影响分析，无法证明未缓存或未执行时维持 `grant_revocation_pending`，必要时扩大暂停。
_避免使用_：不在清单即不影响、未登记面自动排除

**执行面清单闭合（Execution-Surface Inventory Closure）**：执行节点清单必须在 revision 开始前锁定多源发现渠道（部署编排、网络访问、缓存目录、密钥使用、离线同步和审计系统等），并定期对账；来源间无法解释的节点差异标记 `execution_inventory_gap`。清单未闭合时，撤销不能宣称已收敛。
_避免使用_：人工清单即完整、未解释差异仍视为收敛

**快照后执行面（Post-Snapshot Execution Surface）**：撤销传播期间在节点清单快照后新出现、但尚未收到指定 `revoke` revision 的节点或副本状态。标记 `post_snapshot_execution_surface`，立即禁止处理受影响授权；完成版本回执并纳入清单对账后才能解除隔离。快照时不存在不构成未受影响证明。
_避免使用_：快照后出现即安全、未收撤销仍可运行

**执行面监控缺口（Execution-Inventory Watch Gap）**：撤销传播期间持续 inventory watch 中断或漏报时，从中断开始至恢复并完成补偿扫描的未知区间。标记 `execution_inventory_watch_gap`，期间不得新增放行或解除 `grant_revocation_pending`；恢复后须以至少一条独立发现源回溯扫描并与其他来源对账，无法排除新节点时相关范围继续暂停。
_避免使用_：监控恢复即缺口关闭、漏报不影响收敛

**监控缺口保守回溯边界（Conservative Watch-Gap Backdating Boundary）**：inventory watch 缺口的影响窗口若起点清单完整性无法证明，必须回溯到最近一次经过多源对账闭合的 inventory snapshot；快照后至补偿扫描完成均标记未知。若最近闭合快照也无法确认，则从 revision 开始时间起暂停。
_避免使用_：从发现时刻起算、缺口前快照未经闭合也作为基线

**补偿扫描覆盖证明（Compensatory Scan Coverage Proof）**：补偿扫描只有在证明覆盖整个 watch 缺口窗口、所有登记资源类型及离线/缓存面，并核验扫描工具版本、时间戳和访问权限后，才能关闭 `execution_inventory_watch_gap`。扫描结果为空不等于完整；与原 watch 共享故障祖先时仅为受限证据，覆盖不足或依赖不明则维持缺口。
_避免使用_：空扫描即无节点、同源扫描自证完整

**补偿扫描相关依赖（Correlated Compensatory Scan Dependency）**：补偿扫描运行在受影响基础设施、权限系统或 watch 服务上，或与其共享关键故障祖先时的状态。标记 `compensatory_scan_correlated`，结果只能作受限线索；高风险范围至少须有一条不共享这些依赖的独立扫描路径。独立扫描与原 watch 冲突时维持缺口并启动影响分析，不能择优。
_避免使用_：同源扫描即独立复核、选择较完整结果

**授权使用历史闭合（Authorization-Usage History Closure）**：执行节点清单闭合不等于证明未使用受影响授权。撤销收敛还须核对独立的授权调用、缓存命中、密钥使用、离线队列和执行结果日志，确认缺口期间无受影响操作；使用日志缺失时标记 `authorization_usage_unknown`，不能恢复资格。
_避免使用_：无新节点即未执行、节点清单替代使用历史

**授权执行不确定（Authorization Execution Uncertainty）**：撤销窗口内存在授权调用，但无法确认请求是否真正到达执行面、命中缓存或产生下游输出时的状态。标记 `authorization_execution_uncertain`，相关候选、评审和资格结果暂停；只有独立证据证明未到达执行面、未命中缓存且无下游副作用，才能解除不确定。
_避免使用_：请求未完成即未执行、无输出即无副作用

**未授权输出隔离（Unauthorized Output Quarantine）**：潜在执行产生候选或评审草稿，即使未被人工查看，也不得作为正式结果或进入事实、ReviewItem、偏序、反馈及训练/案例库的状态。标记 `unauthorized_output_quarantined`，仅可作为事故调查材料保留，并记录访问控制、隔离/删除状态和影响分析。
_避免使用_：无人查看即无污染、未采用即可入库

**未授权输出污染传播（Unauthorized Output Contamination Propagation）**：未授权输出在隔离前被下游读取时，污染沿数据血缘传播到所有直接或间接依赖的候选、事实、ReviewItem、排序、反馈和实验结果，标记 `unauthorized_output_contaminated` 并暂停使用。只有独立访问日志证明对象未读取该输出，才可隔离保留；人工回忆或结果相同不能排除污染。
_避免使用_：只污染直接产物、看起来相同即未受影响

**干净重推导修订（Clean Rederivation Revision）**：污染对象使用未污染输入、独立执行环境、冻结参数和可复现日志重新生成并确认关键结果一致后，可在新 revision 标记 `clean_rederived` 恢复使用。旧 revision 保留 `unauthorized_output_contaminated`，不得洗白或作为资格证据。
_避免使用_：重跑覆盖污染历史、结果相同即原对象干净

**清洁输入闭包（Clean Input Closure）**：`clean rerun` 必须逐项核验直接输入、提示、缓存、检索索引、依赖数据、环境变量、模型上下文和输出存储，证明数据血缘不依赖任何 `unauthorized_output_quarantined` 或 `unauthorized_output_contaminated` 对象；运行使用新工作区并记录版本、哈希和清理证明。任一依赖无法闭合时标记 `clean_rerun_contamination_uncertain`，不能标记 `clean_rederived`。
_避免使用_：只清理主输入、旧缓存隐式复用

**干净重推导分歧（Clean Rederivation Divergence）**：`clean rerun` 输出与污染输出不一致时的状态。标记 `clean_rederivation_divergence`，保留两条结果及其血缘，暂停依赖旧结果的支持资格并开展差异影响分析；新输出须独立通过完整确认流程才可成为 current，旧污染输出仍不可用，差异本身不能单独证明旧结果错误。
_避免使用_：新结果更好即替换、差异即证明旧结果错误
