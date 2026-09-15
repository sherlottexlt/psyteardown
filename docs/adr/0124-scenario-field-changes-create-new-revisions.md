# 核心场景字段变化创建新场景修订

## Status

accepted

仅修改叙事且结构字段不变可创建展示层修订；改变 attention_demand、mobility、social_visibility、event_criticality、inference_confidence、privacy_sensitivity、interruption/recovery cost 等核心字段，必须创建 Scenario Revision，并让引用它的 InterventionEvent、ReviewItem、Criterion Assessment、Candidate Partial Order 和 Experiment Plan 局部 stale。Brief 级整体排除场景只在冻结前生效。场景变化不自动解除历史 blocked，历史评测基准版本保留。
