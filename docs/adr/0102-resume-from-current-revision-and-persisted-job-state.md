# 工作流从 current revision 和持久化 Job 恢复

## Status

accepted

工作流中断后读取最近 current revision 和 Jobs：queued 继续，running 心跳超时先变为 orphaned，succeeded 复用，failed/expired 新增 attempt，awaiting_consent 等待授权，cancelled 不自动恢复，stale_result 只能查看/比较/手动采纳。成功步骤不重复执行；Brief、事实、机制、规则或模型配置变化会使旧 Job stale 并创建新 fingerprint。这样避免页面刷新或 worker 重启重跑整轮，也不覆盖已确认状态。
