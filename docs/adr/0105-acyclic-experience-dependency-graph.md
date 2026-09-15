# 体验领域依赖图保持有向无环

## Status

accepted

V1 的 Brief、场景、候选、事实、机制、ReviewItem、声明审查、准则聚合、偏序、人工选择、Next Prompt、实验和知识对象形成 DAG。新增依赖时执行 cycle detection，检测到循环返回 dependency_cycle。实验结果只能创建新的 Hypothesis/Heuristic Candidate 或 Brief/Prompt revision；Next Prompt 可引用上一轮评审但不能成为自身输入；任何反馈不得直接改写上游快照或在同一轮自引用。这样让局部失效、复用和两轮比较有明确边界。
