# 模型步骤保存不可变尝试并限制自动重试

## Status

accepted

每次 VisionObserver、ReviewReasoner 或 ClaimJudge 调用保存独立 Model Step Attempt，包括输入快照哈希、provider、model、prompt 版本、参数、原始/解析输出、校验错误和状态。Schema 或确定性引用校验失败时最多自动重试两次，采用首次合法输出；合法输出之间的冲突作为稳定性数据保留，不由模型自选。全部失败时只标记当前步骤 failed 并允许单步重跑，不回退事实确认或覆盖历史结果。这样支持诊断和复现；代价是保存更多调用记录。
