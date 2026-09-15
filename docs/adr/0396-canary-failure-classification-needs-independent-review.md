# Canary 失败分类须独立复核

## Status

accepted

Canary 的技术失败与仲裁失败分类必须由隔离的运行完整性审阅者，根据冻结的原始请求/响应、传输与基础设施日志判定。超时、拒答、解析失败或安全降级不得自动归为可替换技术失败；分类不确定时标记 `canary_failure_classification_uncertain`，不替换、不剔除并阻止确认性兼容结论。
