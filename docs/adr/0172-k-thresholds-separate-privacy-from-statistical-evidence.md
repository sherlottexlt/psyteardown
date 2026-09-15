# 聚合样本门槛与统计证据门槛分离

## Status

accepted

V1 的 Privacy Aggregation Threshold 按 Minimum Cell 检查：普通内部 Aggregated Research Insight 最低 k=5，外部设计 prompt 参考最低 k=10；敏感属性、罕见行为或高风险情境至少 k=10 且可因重识别风险直接禁止。Minimum Cell 由 segment、variation、scenario、condition 和时间窗口等字段确定，总样本不能掩盖小分组不足。k 只表示隐私聚合资格，不代表统计显著、体验假设支持或可外推性。
