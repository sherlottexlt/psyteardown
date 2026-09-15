# 关键事件顺序重建须有独立证据汇合

## Status

accepted

时间戳完整性失败后，若事件顺序影响候选筛选、参与者暴露或资格判定，至少需要两条独立上游证据共同覆盖同一关键顺序边界。单条证据只能形成 `order_reconstruction_signal`；独立证据冲突时标记 `order_inconclusive`，不得择一解释或恢复资格。
