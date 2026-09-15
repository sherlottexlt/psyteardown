# 触发快照与后续监测窗口分开

## Status

accepted

作用域审阅触发瞬间冻结 `Scope Review Trigger Snapshot`，后续候选不得回溯改写触发事实；审阅期间另设 `post_trigger_monitoring_window`，其起止时间、纳入规则、分母和指标事前锁定。受影响范围只能 `validation-only`/人工选择，冲突下降不自动恢复，高风险新增冲突可扩大暂停，两个窗口分开报告。
