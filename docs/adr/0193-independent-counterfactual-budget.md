# V1 为反事实设置独立预算

## Status

accepted

Counterfactual Run 使用独立于正式评审的资源预算：V1 默认每候选最多 3 次、每个 Brief 最多 10 次；结构化 tier/Reason Set diff 优先确定性重算，LLM 解释单独计入预算。超过调用/时延预算标记 counterfactual_budget_exhausted，不解释为没有敏感性，不影响正式评审、current 或 Next Prompt；相同 fingerprint 默认复用 Counterfactual Cache。
