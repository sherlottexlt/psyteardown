# 候选比较采用分层偏序而非完整排名

## Status

accepted

候选比较不强制输出 1–N 名次。系统先隔离 blocked，再依据 DesignBrief 的权衡优先级和带证据的序数体验维度判断，将候选分为 Preferred、Viable Alternatives、Needs Evidence 和 Blocked。不同候选代表合理但不同的权衡时允许并列，关键维度证据不足时标记不可比较并生成 explore。这样避免用隐含总分制造伪确定性；代价是结果可能没有唯一“第一名”。
