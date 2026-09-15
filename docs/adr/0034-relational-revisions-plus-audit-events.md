# SQLite 关系模型配合不可变修订和审计事件

## Status

accepted

MVP 使用 SQLite 关系表保存当前业务对象和不可变 revision，并以追加式 audit_events 记录人工确认、评审、覆盖和生成提示等动作；当前状态通过 current_revision_id 等投影字段读取。系统不采用完整 Event Sourcing，也不要求重放事件恢复状态。这样满足版本比较、审计和本地可用性，同时控制实现复杂度；代价是状态投影和审计事件需要在同一事务中保持一致。
