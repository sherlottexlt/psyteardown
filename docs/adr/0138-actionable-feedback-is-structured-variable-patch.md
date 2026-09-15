# 可操作反馈必须结构化为 VariablePatch

## Status

accepted

ReviewItem 的 actionable_changes 必须转换为 VariablePatch，绑定 canonical variable_id 和 set/replace/add/remove/constrain/relax 操作，记录 from_value、to_value、scope、理由、证据、预期影响、风险和验证方式；自然语言只作为解释。下一轮设计只消费经人工确认的 patch，Patch Adoption Trace 通过父子候选变量值比较确认 adopted、partially_adopted、not_adopted 或 unverifiable，不依赖文本相似度或模型自评。
