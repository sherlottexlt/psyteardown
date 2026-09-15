# DesignBrief 在每轮生成前由人确认并冻结

## Status

accepted

DesignBrief 由设计者或产品负责人提出，psyteardown 可检查完整性和冲突，但不能擅自决定目标。每轮候选生成前，必须由人确认并形成不可静默修改的 brief snapshot；目标、用户、情境、硬约束或权衡优先级变化时创建新的 brief revision。评审、排序和跨轮比较只能引用对应快照。这样保证系统的判断基准稳定、可审计；代价是设计需求变化需要显式创建版本。
