# 多假设 ExperimentPlan 使用独立 HypothesisBinding

## Status

accepted

一个 ExperimentPlan 可以绑定多个 ExperienceHypothesis，但每个通过 HypothesisBinding 独立记录 hypothesis revision、primary/secondary、预测结果、measure_ids、analysis_family 和状态。单个假设变化且不影响协议时只使 binding stale；改变操纵、样本、场景、主要指标、停止规则或分析结构属于 Protocol-Level Change，创建整个 ExperimentPlan 新 revision。Result Review 按 binding 分别决定 supported/rejected/inconclusive，不能由一个假设结果替代其他假设。
