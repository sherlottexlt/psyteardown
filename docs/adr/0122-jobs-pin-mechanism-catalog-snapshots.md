# Job 固定机制目录快照

## Status

accepted

每个 ReviewReasoner/ClaimJudge Job 创建时固定 Mechanism Catalog Snapshot，ReviewItem 保存机制卡 ID、版本和引用位置；运行期间不热切换。机制卡 deprecated、superseded 或来源纠错后，已完成结果标记 mechanism_snapshot_stale 并执行 Mechanism Impact Analysis，必要时重新审阅 ReviewItem 和启发式；一般不自动 blocked，也不修改 Brief 或实验原始数据。只有人工批准的新机制版本影响后续 Job。
