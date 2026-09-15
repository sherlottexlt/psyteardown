# 非关键字段被重分类后收窄证据范围

## Status

accepted

事前标记为非关键的字段若后来被发现可能调节结果，必须创建 `criticality_reclassification` 并执行 Evidence/Heuristic Impact Analysis。历史结果保留，但 `replicated` 暂时收窄为已使用的实施条件，启发式暂停受影响变体的新注入和范围扩张；共享该字段的多次实验不能证明跨该字段泛化，恢复资格需要新的预注册交互或边界实验。
