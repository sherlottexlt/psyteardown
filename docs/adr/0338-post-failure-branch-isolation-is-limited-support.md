# 共享故障后的分支隔离只产生受限支持

## Status

accepted

共享故障后，剩余分支只有在字段级影响分析证明条件、暴露、测量、数据链和门控逻辑未受影响时，才可保留 `supported` 并标记 `branch_isolated_after_shared_failure`。它不能满足启发式外部准入或增加外部独立 lineage，只能作为 `limited_external_support`、范围/反例分析和新实验规划材料；被排除分支的故障不自动构成剩余分支反例。
