# 使用 SQLite Outbox 保证领域事件与异步副作用一致

## Status

accepted

需要触发后续 Job 或其他异步副作用的 Domain Event，与新 revision、current 指针和 Audit Event 在同一 SQLite Command Transaction 中写入 Outbox Event。单进程 worker 只处理已提交 outbox，按 event_id 幂等创建/唤醒 Job；重复投递不创建重复任务。状态为 pending/processing/delivered/failed/dead_letter，processing 超时可恢复，重试超限进入 dead_letter。只读事件可不进 outbox，纯 Audit Event 不触发副作用；V1 不引入外部消息总线。
