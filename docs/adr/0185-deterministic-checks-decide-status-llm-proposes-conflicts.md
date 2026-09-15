# 语义一致性由确定性规则决定状态，LLM 只提出冲突候选

## Status

accepted

Semantic Consistency Check 采用双层模式：确定性规则检查字段互斥、依赖、事件完整性、变量/单位、Brief 约束、批准风险规则和图文冲突，并唯一决定阶段门与状态；LLM 可独立提出 Semantic Conflict Candidate、解释可能影响和建议人工确认，但不能直接 blocked、修改 JSON 或覆盖确定性失败。候选冲突经重复案例、证据和人工审查后，才可通过 Conflict Rule Promotion 进入版本化规则。
