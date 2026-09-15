# Semantic Conflict Candidate 需独立案例和回归后升级

## Status

accepted

潜在语义冲突至少在 3 个独立候选/运行中重复出现，能够形式化为字段/运算符/作用域条件，具有逐次证据链，经人工确认、反例检查、Development/Validation 回归和影响评估，才可通过 Rule Promotion Gate 升级为版本化确定性规则。新规则默认只影响批准后的新 Job 或明确 Re-evaluation，历史结果不热更新；被拒绝候选保留。
