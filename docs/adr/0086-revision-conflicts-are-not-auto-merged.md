# 修订冲突拒绝写入且陈旧后台结果不自动生效

## Status

accepted

所有领域写命令检查 expected_revision，不一致时返回 HTTP 409 revision_conflict 并展示客户端版本、当前版本和差异，不自动合并。后台 Job 基于固定输入快照执行；完成时若目标已有新 revision，输出标记 stale_result，只能查看、比较或由人显式采纳到新 revision。UI 折叠等非领域状态不参与 revision。这样避免后台任务或旧标签覆盖已确认决策；代价是冲突需要人工处理。
