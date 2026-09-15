# 新规则先 shadow 再强制执行

## Status

accepted

新批准规则默认进入 Approved Shadow，只记录潜在 Rule Match、预期状态、误报/漏报和样本，不改变 generation_invalid、blocked、偏序、Prompt 或正式评测结果。达到预定样本、完成误报/漏报检查、通过 Validation 回归并确认解除条件后，人工创建 Approved Enforced revision；该版本才进入状态机和 Job fingerprint。Emergency Suspended 可立即停止新任务，不受 shadow 等待限制。
