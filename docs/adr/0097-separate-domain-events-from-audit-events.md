# 区分领域事件与审计事件但不采用事件溯源

## Status

accepted

系统在 SQLite 关系状态与 revision 之外追加保存 Domain Event 和 Audit Event。Domain Event 表达已发生的领域变化，用于只读投影、后续 Job 和导出时间线；Audit Event 记录操作者、时间、expected_revision、理由、来源和摘要，用于审计和覆盖分析。一个命令通常产生一个主要 Domain Event 和一个或多个 Audit Event；失败命令不产生 Domain Event，但可写失败审计。二者不保存完整私人资产或原始模型内容，也不用于重放恢复业务状态。
