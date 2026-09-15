# 反事实只在执行后记录实际评估差异

## Status

accepted

Expected Counterfactual Diff 只预测确定性依赖传播，不预测最终 tier、Reason Set、人工选择或因果结果。执行后生成 Actual Counterfactual Diff，分别记录候选 tier、Coverage、Reason Set、受影响产物和受限解释，再与预期 diff 比较；超出预期标记 Unexpected Dependency Effect 并检查依赖图/实现。没有 tier 变化仍是有效反事实结果，不影响正式状态，也不能解释为体验因果。
