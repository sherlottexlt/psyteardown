# Critical 能力必须声明事件类别和最低介入策略

## Status

accepted

支持 critical 的候选必须同时声明 supports_critical、人工批准的 critical_event_classes、事件到类别的映射和 Minimum Intervention Policy。缺少类别或事件映射属于 input_incomplete/generation_invalid；类别与事件冲突创建 Evidence Conflict；缺少最低必要介入策略时最多 facts 可冻结但评审为 explore，不能使用 critical 权限。普通“重要/紧急/不能错过”文本不能创建类别，新类别必须通过 Brief/分类表 revision；每个 critical 事件还需说明最低模态、时机、强度、确认和降级路径。
