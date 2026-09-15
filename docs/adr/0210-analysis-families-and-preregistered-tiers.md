# 共享实验数据使用分析族和预注册层级

## Status

accepted

ExperimentPlan 的 AnalysisFamily 必须在执行前锁定 HypothesisBinding 的 primary、secondary、exploratory 层级、主要指标、分析族、多重比较校正/未校正状态和解释政策。执行后不能按结果改类或从 exploratory 升为 primary；若确有设计/伦理变化，创建新的预注册 revision 并记录原因与时间。结果摘要和 Result Review 显示层级与校正状态，LLM 不得挑选有利结果。
