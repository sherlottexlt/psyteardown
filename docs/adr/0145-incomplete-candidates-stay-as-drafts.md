# 缺少必需事件的候选保留为草案

## Status

accepted

Candidate Draft 缺少正常介入、延后/拒绝、低置信度、误判恢复，或声明 critical 能力却缺少紧急介入时，标记 input_incomplete/generation_invalid，允许保存和修订，但不能进入 Candidate Facts Frozen、正式评审或偏序。事件存在但字段值为 unknown 不属于输入缺失，候选可冻结，相关 Event Coverage 为 partial/unknown。系统不自动补写缺失事件，修复创建新候选 revision。
