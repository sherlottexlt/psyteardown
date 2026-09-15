# 执行面监控缺口阻止撤销闭合

## Status

accepted

撤销传播期间 inventory watch 中断或漏报时，必须标记 `execution_inventory_watch_gap`；从中断至恢复并完成补偿扫描期间不得新增放行或解除 `grant_revocation_pending`。恢复后须用至少一条独立发现源回溯扫描并对账；无法排除新节点时相关范围继续暂停。
