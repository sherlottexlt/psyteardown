# 干净重跑分歧须经影响分析

## Status

accepted

`clean rerun` 与污染输出不一致时，必须标记 `clean_rederivation_divergence`，保留两条结果及血缘，暂停依赖旧结果的支持资格并进行差异影响分析。新输出只有独立通过完整确认流程后才能成为 current；旧污染输出仍不可用，分歧本身不能单独证明旧结果错误。
