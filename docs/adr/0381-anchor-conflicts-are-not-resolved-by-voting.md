# 根锚冲突不能靠多数投票解决

## Status

accepted

根信任锚证据按独立上游 lineage 而非数量计数；共享时间戳或其他关键祖先的多条证据只能算一条相关 lineage。独立证据冲突时标记 `anchor_convergence_inconclusive`，不得以相关证据多数压过独立反向证据；冲突处理需新的、事前允许的仲裁证据和新 revision。
