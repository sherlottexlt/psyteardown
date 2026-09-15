# 共享依赖对准入的影响必须事前锁定

## Status

accepted

共享依赖事实可在实验后补充或纠正，但其等级如何影响外部独立准入和泛化必须在实验开始前声明。未事前锁定时，结果只能是 `external_independence_unclassified` 或 `limited_external_support`，不能直接满足启发式外部准入；事后降低依赖等级不能追认资格。证明实际无共享依赖时需创建事实修订并执行影响分析。
