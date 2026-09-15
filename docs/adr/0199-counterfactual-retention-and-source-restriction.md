# 反事实记录长期保留，内容按来源策略清理

## Status

accepted

Counterfactual Run 的结构化记录、Expected/Actual Diff、依赖快照、fingerprint、人工决策和引用关系长期保留。原始/派生资产及模型响应遵守 Consent Scope、隐私等级、Provider Policy 和删除请求；不可访问时标记 Source-Restricted Counterfactual，不能宣称完整复现。未被决策、报告或研究引用的反事实缓存/原始响应可执行 Counterfactual Cache Purge，但必须保留 run_id、hash、状态和删除事件，不能删除时间线事实；重新运行创建新 Run。
