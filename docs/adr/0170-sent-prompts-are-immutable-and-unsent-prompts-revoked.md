# Prompt Package 按发送状态处理撤回

## Status

accepted

已发送的 Next Design Prompt 不可修改或伪装撤回，只能按 provider 能力请求取消/删除并标记 Transfer Restricted/Affected by Withdrawal，保留发送 hash、资产 ID、授权范围和影响分析；基于它生成的候选保留并标记依赖。未发送提示立即 Prompt Revocation，不能再发送；新提示必须重新 Prompt Projection、脱敏和 Consent 检查。用途级撤回只影响对应 remote processing、showcase 或 knowledge growth 流程，不自动扩大为全项目删除。
