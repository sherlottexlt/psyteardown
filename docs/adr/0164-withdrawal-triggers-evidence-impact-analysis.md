# 参与者撤回触发证据影响分析

## Status

accepted

参与者撤回同意后，对其 OutcomeObservation、分析、启发式和相关报告执行 Evidence Impact Analysis。若移除/限制该参与者数据后，剩余独立证据仍满足样本、来源和适用范围门槛，可保留去标识聚合并创建新启发式 revision；若不满足，启发式标记 evidence_insufficient，停止新的 Next Design Prompt 回灌，历史提示、候选和结果保留并显示依赖。原始和可关联数据按同意协议删除/限制，不能静默判定历史设计错误，也不能继续把被撤回数据作为新增支持。
