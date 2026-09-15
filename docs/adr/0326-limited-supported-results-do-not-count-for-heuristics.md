# 受限 supported 不计入确认性启发式资格

## Status

accepted

`supported + replication_sensitivity` 等受限结果可以保留，但必须与 `supported_clean` 分开计数。只有 `supported_clean` 才能满足 Approved Design Heuristic 的确认性支持和外部准入；受限结果仅用于候选、边界/反例分析和规划。关键支持单元变为受限时触发 Evidence Impact Analysis，不能通过多个受限结果相加抵消限制。
