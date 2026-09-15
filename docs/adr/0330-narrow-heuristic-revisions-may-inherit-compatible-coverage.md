# 窄范围启发式可有条件继承前瞻覆盖

## Status

accepted

严格属于旧范围子集且变量、结果、协议、实施条件和用户定义兼容时，窄范围 revision 可经人工 Result Review 引用旧合格前瞻性检验并标记 `inherited_prospective_coverage`，但不增加新支持计数。改变假设、指标、协议、实施或用户定义必须重新前瞻检验，不能借收窄重包装失败。
