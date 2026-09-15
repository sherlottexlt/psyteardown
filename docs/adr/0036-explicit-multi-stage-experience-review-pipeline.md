# 正式评审采用显式多阶段流水线

## Status

accepted

体验评审从冻结事实开始，分为 Context Binding、Mechanism Retrieval、ReviewItem Generation、Claim Judge、Feedback Generation、Candidate Synthesis 和 Cross-Candidate Comparison。确定性代码负责状态、证据定位、版本、Schema、硬约束和权限；LLM 只生成情境解释、心理假设、替代解释、权衡和修改建议草案。各步独立保存、校验和重试，禁止一次模型调用直接决定完整评审与排序。这样提高可诊断性和可评测性；代价是调用次数和编排复杂度增加。
