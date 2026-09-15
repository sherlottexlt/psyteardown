# 冲突复现与不可解释复现分开处置

## Status

accepted

方法有效的独立复现若方向相反或没有清晰差异，创建新的 `mixed/inconclusive` revision，不标记 `replicated`；因样本、条件呈现、协议偏离或分析不可复现而无法解释时，创建 `needs_replication` revision。既有 `supported` 记录保留，不静默改写。
