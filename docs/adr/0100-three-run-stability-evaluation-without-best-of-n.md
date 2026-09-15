# 正式模型评测三次重复并报告方差

## Status

accepted

确定性逻辑单次评测即可；模型相关的 Development、Validation 和 Holdout 案例按冻结配置各运行 3 次，报告事实 precision/recall、机制重合、ReviewItem 状态、数量范围和候选 tier 的均值/范围与一致率，不选择最佳一次。高风险确认事实 + 规则引擎结果必须 100% 一致；建议 Confirmed Fact 引用一致率 ≥0.90，blocked/revise/explore 和候选 tier 一致率 ≥0.80。稳定性不达标时追查事实冻结、检索、prompt 和合并规则，不用平均掩盖。
