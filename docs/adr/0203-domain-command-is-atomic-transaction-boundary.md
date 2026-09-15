# Domain Command 是最小原子事务边界

## Status

accepted

一个 Domain Command 在单个 SQLite 事务中原子保存新 revision、current_revision_id、Domain Event、Audit Event、Dependency Snapshot 和必要投影，并检查 expected_revision。LLM、远程 provider、长分析和文件处理在事务外执行；Job 创建事务只记录固定 External Call Snapshot，完成后通过新命令提交结果。外部调用失败不回滚已提交 Job，领域命令失败不产生 Domain Event 但可写失败审计；远程调用不持有数据库事务。
