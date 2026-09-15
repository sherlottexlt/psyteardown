# VariablePatch 必须声明作用域

## Status

accepted

每个 VariablePatch 都必须声明 Patch Scope（场景、事件、用户、时间/设备模式和排除条件）；无作用域只能作为 explore，不能成为 must。Global Patch Declaration 必须显式标记并列出例外/排除。作用域重叠执行冲突检查，critical 事件不被 routine patch 覆盖；生成器回报实际应用范围，Variable Repair Trace 按作用域比较，作用域变化创建新 patch revision。
