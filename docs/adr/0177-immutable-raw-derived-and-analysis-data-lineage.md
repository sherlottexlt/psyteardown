# Raw、Derived 和 Analysis 数据分层并保留血缘

## Status

accepted

Raw Data、Derived Dataset 和 Analysis Result 三层不可变保存，使用 raw_data_hash、处理脚本/参数、derived_dataset_hash 和 AnalysisRun 形成 Data Lineage。清洗、去标识、排除、编码或聚合变化创建新派生版本并局部使下游分析 stale；原始数据不被模型或分析脚本覆盖，任何数字变化只能通过新 AnalysisRun 产生。
