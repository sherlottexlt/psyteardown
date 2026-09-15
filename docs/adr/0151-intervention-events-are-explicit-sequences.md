# InterventionEvent 使用显式时序序列

## Status

accepted

每个 Minimum Intervention Event Set 事件使用 Intervention Event Sequence，至少描述 trigger、context_snapshot/inference、permission decision、feedback steps、预期用户响应、无响应/超时行为、纠正路径、恢复路径和终止条件。缺少用户拒绝、无响应或终止条件时候选输入不完整；步骤可标记 not_applicable，但不能被省略。序列描述设计行为，不等于真实用户结果；统一基准场景比较要求覆盖相同阶段。
