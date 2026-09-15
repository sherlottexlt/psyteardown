# 每个候选必须覆盖失败和恢复事件

## Status

accepted

V1 DesignCandidate 至少声明四类 InterventionEvent：正常介入、用户延后/拒绝、低置信度降级和误判恢复；声明 critical 能力时再增加紧急介入，说明最低必要介入和紧急通道约束。只描述设备正确理解用户并自然帮助的 happy path，属于候选输入不完整并标记 generation_invalid。这样迫使 AI 设计同时处理拒绝、不确定性和失败恢复，而不只呈现理想交互。
