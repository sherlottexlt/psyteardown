# 多 Provider 输出独立保存且不自动投票

## Status

accepted

同一输入可以运行多个 VisionObserver、ReviewReasoner 或 ClaimJudge provider，但每次作为独立 Provider Run 保存。观察一致只产生 Cross-Provider Agreement 辅助信号，不自动成为事实；不一致形成 Evidence Conflict/Provider Disagreement。ReviewReasoner 只能读取人冻结后的 Confirmed Observation，ClaimJudge 不能用多数模型同意替代证据。人可以从多个草案创建新的人工确认 Observation，保存来源列表、合并理由和作者。
