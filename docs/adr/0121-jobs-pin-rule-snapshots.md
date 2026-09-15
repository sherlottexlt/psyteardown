# Job 固定规则快照且不运行中热切换

## Status

accepted

每个评审 Job 创建时固定 Rule Set Snapshot（ID、版本、哈希），整个运行使用同一规则集。deprecated/superseded 的规则允许已启动 Job 完成但结果标记 rule_snapshot_stale，并建议显式 re-evaluation；emergency_suspended 阻止未开始/queued Job，running Job 可安全终止或完成后强制 stale，具体动作记录审计。规则变化不修改冻结事实/ReviewItem，也不在一个 Job 中混用版本。
