# Review 绑定不可变候选和知识依赖快照

## Status

accepted

Review aggregate 不引用动态 current Candidate，而绑定 candidate_revision_id、Candidate Facts Snapshot、Brief Snapshot、Benchmark Scenario Snapshot、Mechanism Catalog Snapshot、Rule Set Snapshot 和变量词汇版本。Candidate、Brief、场景、机制、规则、变量或来源资产变化时，旧 Review 标记 Stale Review 并保留；新的评审创建新 revision。Candidate Partial Order 只使用依赖完全匹配 current 的 Review，陈旧评审不能进入正式偏序或 Next Prompt。
