# 事实纠错触发实验影响分析而不改原始数据

## Status

accepted

事实纠错或相关 Brief/机制/规则修订后，对依赖它的已完成实验执行 Experiment Impact Analysis：若不影响操作条件，结果保持；若影响解释或适用范围，创建新的 Result Review 并可降级为 needs_reanalysis/needs_replication/inconclusive；若预注册条件实际未被满足，标记 invalidated_by_fact_correction。原始数据、原报告和历史 Result Review 保留，相关 Design Heuristic 标记 stale/deprecated，不静默删除或改写。
