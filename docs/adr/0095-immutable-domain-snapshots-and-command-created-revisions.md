# 领域对象使用不可变快照，命令创建新修订

## Status

accepted

DesignBriefSnapshot、CandidateFactsSnapshot、ReviewItemRevision、CritiqueRevision 等领域对象采用不可变语义，禁止原地修改已确认对象。领域状态变化只能通过 Domain Command 和 policy 函数创建新 revision；应用服务在同一事务中持久化新版本、更新 current 指针并写入 AuditEvent，repository 不悄悄改写领域状态。UI 临时状态不属于领域对象，可保持可变。这样让版本链、并发冲突和审计在代码层保持一致。
