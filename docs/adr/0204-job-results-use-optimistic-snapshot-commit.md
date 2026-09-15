# Job 结果通过快照和 revision 检查提交

## Status

accepted

Job 开始时固定 External Call Snapshot 和 target expected_revision；完成时 Result Commit Command 检查 Brief、Candidate Facts、机制/规则/变量词汇、资产和当前目标 revision 是否匹配。全部匹配才创建新结果 revision、更新 current 并发出后续 Domain Event；任一不匹配则保存结果并标记 Stale Job Result，不更新 current、不触发后续状态。人工可查看、重跑或显式采纳到新 revision，禁止自动三方合并。
