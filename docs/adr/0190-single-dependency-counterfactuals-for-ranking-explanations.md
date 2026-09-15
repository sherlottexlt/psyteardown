# V1 支持单依赖反事实解释候选偏序

## Status

accepted

V1 支持 Counterfactual Comparison：在只读副本中一次移除/替换一个 ExperienceCriterion、Risk Rule、tradeoff priority、Benchmark Scenario 参数或 VariablePatch，重新计算 Candidate Evaluation Record、Partial Order 和 Reason Set，记录 tier 变化、受影响候选、版本和 fingerprint。反事实不修改 current、不自动进入正式评审或 Next Prompt；emergency_suspended 规则的反事实只用于影响分析，不能自动解封。V1 不做多变量组合搜索。
