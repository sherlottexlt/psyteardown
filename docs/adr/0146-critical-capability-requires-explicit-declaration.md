# Critical 能力必须由显式声明或人工确认确定

## Status

accepted

只有候选的结构化 supports_critical 声明或人工确认，才能把候选视为支持 critical 能力。受控词扫描（如“安全警报”“立即通知”）只能生成 critical_capability_candidate，不能自动升级、阻断或创建事件类别。显式支持 critical 却缺少人工批准的 critical_event_classes 和最低必要介入策略时，候选属于 input_incomplete/generation_invalid 或 explore；声明冲突进入 Evidence Conflict。这样防止通过换词绕过紧急通道约束。
