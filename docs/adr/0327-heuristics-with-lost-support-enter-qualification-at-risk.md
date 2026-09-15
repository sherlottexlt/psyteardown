# 关键支持受限后启发式进入资格风险状态

## Status

accepted

已批准启发式的关键 `supported_clean` 单元变为受限并导致门槛暂不满足时，创建新 revision 标记 `qualification_at_risk`，停止范围扩张和资格累积；仅在依赖链证明未受影响的范围内继续 `consider_as_option`，边界不明则暂停。必须声明补证窗口与恢复条件，到期仍不足时转为 `evidence_insufficient` 或 `deprecated`；历史记录保留。
