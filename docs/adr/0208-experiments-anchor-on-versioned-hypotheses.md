# ExperimentPlan 以版本化 ExperienceHypothesis 为核心

## Status

accepted

ExperimentPlan 必须绑定具体 hypothesis_id/revision，并保存完整 Experiment Hypothesis Chain：ReviewItem revision、candidate revision、Candidate Facts、InterventionEventSequence、Brief/Benchmark Scenario、Mechanism/Risk/Variable 快照和 outcome measures。不能只引用产品或单一心理构念；假设依赖变化使未执行计划 Hypothesis Stale，已完成实验保留原始数据并在 Result Review 中检查适用性。实验结果不回写原 ReviewItem，只创建结果审阅和知识候选。
