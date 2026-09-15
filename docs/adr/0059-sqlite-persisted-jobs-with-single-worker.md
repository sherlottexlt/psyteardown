# V1 使用 SQLite 持久化任务和单进程 worker

## Status

accepted

FastAPI 为视觉观察、ReviewItem 生成和 Claim Judge 等耗时步骤创建 SQLite 持久化 Job，由单进程后台 worker 执行；前端通过轮询或 SSE 获取进度。任务使用 idempotency_key 防重复，崩溃后可恢复超时 running 任务，取消不删除已完成尝试，任务结果和状态机转换在事务中写入。V1 不引入 Redis、Celery 或消息总线，以控制本地部署复杂度；未来多人部署再替换执行层。
