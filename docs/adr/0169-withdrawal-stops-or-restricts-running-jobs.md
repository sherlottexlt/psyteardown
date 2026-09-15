# 撤回/删除按 Job 阶段停止或限制处理

## Status

accepted

参与者撤回远程处理或删除资产时，queued/awaiting_consent 且未发送的 Job 取消；running 但未发送相关资产的 Job 停止；已发送的 Job 尝试 provider 取消并标记 Transfer Restricted，停止重试/再发送，明确记录 provider 能力，不能假装已收回；已完成结果标记 Affected by Withdrawal，触发 Evidence Impact Analysis。仅撤回公开展示时停止相关 Showcase Export，不必取消不相关模型 Job；系统不自动换 provider。
