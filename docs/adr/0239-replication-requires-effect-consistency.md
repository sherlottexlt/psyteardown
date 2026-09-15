# replicated 要求效应一致而非仅方向一致

## Status

accepted

独立复现除方向一致外，还必须满足预注册的最小实际重要性或效应容忍范围。效应大小无法与该范围相容时，即使方向相同也不能标记 `replicated`，而应保持 `supported` 或进入 `needs_replication`。
