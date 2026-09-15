# 资产清理通过影响记录更新引用状态

## Status

accepted

反事实资产或缓存清理后，系统创建 Impact Record，定位 Showcase Export、Reproducible Bundle、Selection Decision、Validation Task 和 Heuristic 的引用，并更新 available、source_restricted、partially_reproducible 或 reproducibility_failed 状态。历史导出、人工决策和时间线不静默改写；新导出必须显式显示缺失资产、hash 和证据受限状态，不能伪装完整可复现。受影响的启发式执行 Evidence Impact Analysis，但不会自动删除或改判历史设计。
