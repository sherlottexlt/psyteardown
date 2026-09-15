# 禁止体验按 hard、strong avoidance 和 watch 分级

## Status

accepted

DesignBrief 中的 Prohibited Experience 必须操作化并分为 hard、strong_avoidance 和 watch。只有 hard 且绑定 Approved Risk Rule 的条件在确认事实满足时触发 blocked；strong_avoidance 形成 risk/strong_risk 和 revise；watch 形成 explore 和验证任务。严重级别在 Brief 冻结前由人确认，LLM 不能在评审时自行升级，改变等级需新 Brief revision 或风险规则审批。这样避免把所有负面体验都硬阻断。
