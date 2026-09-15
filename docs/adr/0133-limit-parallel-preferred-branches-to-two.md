# V1 限制 Preferred 并行推进分支

## Status

accepted

Preferred Set 可以包含多个候选，但 V1 每个 DesignIteration 默认最多推进 2 个方向。超过上限时，人必须选择、组合成 Hybrid Candidate 或先做区分实验；未推进候选标记 Held for Comparison，保留历史和证据，不视为 rejected。并行预算写入 iteration policy，若 DesignBrief 需要不同上限，必须在冻结前声明并版本化。这样保留并列判断，同时防止候选树失控。
