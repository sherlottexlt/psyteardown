# Provider 政策变化触发影响分析和重新授权

## Status

accepted

Provider Policy Record 版本变化时，新 Job 使用新政策；留存、训练、区域、删除能力等实质变化使旧授权不自动扩展，尚未发送任务进入 awaiting_consent。政策不满足或违规发现时 provider 变为 rejected/emergency_suspended，停止新 project_private/sensitive 发送，queued 任务取消或等待替代，running 任务按传输阶段停止/限制；已完成结果标 provider_policy_stale，并执行 Provider Policy Impact Analysis。历史授权、Prompt、候选和结果保留原 policy revision，不假装远程内容已收回。
