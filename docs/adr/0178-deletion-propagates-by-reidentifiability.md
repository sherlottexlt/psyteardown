# 派生数据删除按可回溯性传播

## Status

accepted

参与者删除/限制请求先执行重识别风险检查：可通过 participant_id、时间、罕见组合、身份映射或辅助数据回溯的 Linkable Derived Data 必须删除/限制，并创建新 Derived Dataset revision；满足最小分组、抑制稀有组合且无法合理回溯的 Irreversibly Aggregated Data，可在 Consent Scope 允许且证据门槛仍满足时保留。受影响 Analysis/Insight/Heuristic 做新 revision 和 Evidence Impact Analysis；旧数据和报告保留审计状态，不静默覆盖。
