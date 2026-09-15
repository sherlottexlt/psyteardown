# Enforced 规则回滚使用新修订

## Status

accepted

Enforced 规则发现普通误报/漏报时创建新 Rule Rollback Revision，收窄作用域、提高证据门槛或调整条件，并先进入 shadow；明显安全错误立即将旧规则标为 emergency_suspended，停止新任务/发送并触发 Rule Impact Analysis。旧规则、历史 Rule Match、blocked 候选和结果保留，不能直接修改 current 或自动解封；后续恢复/回滚也创建新 revision，按发布策略重新验证。
