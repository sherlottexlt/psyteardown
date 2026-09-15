# 人工选择使用结构化动作、依据和后续任务

## Status

accepted

SelectionDecision 固定 action（select、explore_further、hold、compose、reject、override）、候选 ID、decision_basis、被覆盖判断、接受/拒绝权衡、required_followups、rationale_text、actor、时间和 revision。个人判断可作为依据但不得伪装证据；override/compose/explore/reject 必须说明原因，验证后续关联 Validation Task。Human Judgement Signal 只用于评测和提出候选知识，不自动训练模型或修改规则。
