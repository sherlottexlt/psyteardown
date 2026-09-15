# 只有确定性批准规则可以触发 blocked

## Status

accepted

正式 blocked 只能由确认事实与三类明确规则的确定性匹配触发：V1 Scope Exclusion、冻结 DesignBrief 的 Hard Constraint、或带稳定 rule_id 的 Approved Risk Rule。LLM 只能生成 Risk Candidate，普通心理机制风险默认进入 revise 或 explore，不能直接阻断。范围排除在 V1 内不可覆盖，简报硬约束只能通过新 revision 改变，批准风险规则按解除条件重新评审。这样阻断可复现、可审计；代价是需要维护风险规则生命周期。
