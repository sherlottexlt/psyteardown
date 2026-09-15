# 冻结事实通过新快照修订和纠错

## Status

accepted

Candidate Facts Frozen 后允许新增事实，但不解冻或原地修改旧快照。不影响现有评审的补充可作为附加观察；影响性补充和 Fact Correction 创建新 facts revision，保留原事实、来源和错误原因，并按依赖图局部使受影响 ReviewItem、聚合、排序和 Next Prompt stale。新资产经历同样隐私与确认流程；事实修订不自动改变人工选择，已发送提示和实验原始数据保持不变。
