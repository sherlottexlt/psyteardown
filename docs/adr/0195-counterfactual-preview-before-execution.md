# 反事实运行前展示结构化预览

## Status

accepted

所有 Counterfactual Run 前展示 Counterfactual Preview：baseline、依赖 ID/revision、remove/replace 操作、replacement、受影响候选、Expected Counterfactual Diff、重算产物、隐私/安全影响、是否远程调用、预计成本和剩余预算。普通反事实可批量确认但仍一次一依赖；blocking/critical/privacy/Consent/provider policy 相关逐条确认，远程调用重新走 Data Transfer Manifest/Consent。取消预览不产生领域事件，执行后比较预期与实际 diff。
