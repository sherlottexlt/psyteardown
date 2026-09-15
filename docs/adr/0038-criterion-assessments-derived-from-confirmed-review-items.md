# 体验维度判断由已确认 ReviewItem 确定性聚合

## Status

accepted

Criterion Assessment 不由 LLM 直接给出，而从人工确认的 ReviewItem 及其维度映射中按规则聚合。未解除硬风险产生 strong_risk；未解决 explore 或关键证据缺失产生 unknown；支持与风险并存时保留机制冲突，不强行平均。LLM 只能建议 ReviewItem 属于哪个体验维度，映射随评审项一起确认；人可以版本化覆盖聚合结果。这样使候选偏序可复现和可诊断；代价是需要维护明确的聚合规则。
