# 必需介入事件必须有事件级覆盖结果

## Status

accepted

每个 V1 候选的 Minimum Intervention Event Set 都必须生成 Event Coverage Result（covered、partial、unknown 或 blocked），再按预算拆分核心 ReviewItem。缺少必需事件属于 generation_invalid；事件存在但机制不足仍保留并标记 none/unknown；高风险和 critical 事件不能被评审预算合并隐藏。候选偏序只引用共同基准事件的覆盖结果，候选自定义事件只用于探索。
