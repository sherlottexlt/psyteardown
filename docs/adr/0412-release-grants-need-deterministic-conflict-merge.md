# 恢复授权冲突须确定性合并

## Status

accepted

多个 `Release Scope Grant` 重叠或冲突时，暂停/风险/失效条件优先，更具体范围优先；同等具体度下只有明确 `supersede` 的较新 revision 才取代旧授权。无法确定优先级时标记 `grant_conflict` 并默认拒绝，不能由运行时或最后写入顺序选择。
