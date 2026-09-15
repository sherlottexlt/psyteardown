# 远程模型调用使用资产级传输策略和清单

## Status

accepted

每个资产拥有 remote_allowed、confirm_each_run 或 local_only 的传输策略。远程 VisionObserver/LLM 任务执行前生成不可变 Data Transfer Manifest，列出 provider、model、asset_id/派生资产、文本字段、用途和脱敏状态；project_private 默认逐运行确认，sensitive 默认禁止远程。用户未授权时 Job 状态为 awaiting_consent，不上传也不伪装失败；相同内容和 provider 的重试可复用授权，内容变化需重新确认。这样把本地存储和远程传输分开控制；代价是远程任务增加授权步骤。
