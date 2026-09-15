# 首条 experience 切片使用五类聚合根

## Status

accepted

V1 主要聚合根为 DesignBrief、DesignIteration、DesignCandidate、Review 和 Experiment。Brief 负责冻结/supersede；Iteration 负责候选批次、发散、并行预算和人工选择；Candidate 负责 revision、事实快照和 InterventionEventSequence；Review 负责 ReviewItem、ClaimJudgement、Event Coverage 和 Candidate Evaluation；Experiment 负责预注册、分析和结果审阅。跨聚合操作由 application service、Domain Event 和 Outbox 协调，不建立全项目大聚合或跨聚合长事务。
