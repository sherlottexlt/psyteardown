# 以依赖快照支持局部失效和结果复用

## Status

accepted

Brief Snapshot、Candidate Facts Snapshot、Benchmark Scenario、Mechanism Catalog、Risk Rule、ReviewItem、Criterion Assessment、Candidate Partial Order、Next Prompt 和 Experiment Plan/Analysis 都保存 Dependency Snapshot，包含上游对象 ID、revision 和 content hash。上游变化时只对依赖它的产物执行 Scoped Invalidation；无关产物可复用，原始实验数据不失效。局部重新生成创建新 revision，旧结果保留并标 stale。这样避免全量重跑和无条件继承；代价是需要维护依赖关系和失效检查。
