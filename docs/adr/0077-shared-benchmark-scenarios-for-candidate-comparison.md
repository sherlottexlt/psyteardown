# 跨候选比较使用共同基准场景

## Status

accepted

V1 默认要求所有候选覆盖三个 Benchmark Scenario：深度工作中的 routine 提醒、公共通勤中的 important 非 critical 提醒、面对面交谈且情境推断仅中等置信度。每个场景均包含正常介入、延后/拒绝、低置信度和误判恢复。候选可添加 1–2 个 Candidate-Specific Scenario，但未共同覆盖时只用于探索，不参与正式偏序。这样防止生成器只选择对自身有利的故事，同时保留设计差异。
