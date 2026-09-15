# V1 使用受限事件状态机

## Status

accepted

InterventionEvent Sequence 使用 Bounded Event State Machine：每个事件最多 3 个反馈步骤、每节点最多 5 个用户响应分支、critical 升级最多 1 次，禁止隐式循环，所有分支必须到达 termination 或 recovery。分支必须引用 DesignVariable 或 Context 条件；无法映射的分支进入 explore。超过预算标记 event_sequence_complexity_exceeded，候选可保存为草案但不能进入正式比较。
