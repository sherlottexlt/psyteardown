# AnalysisResult 绑定冻结的分析运行环境

## Status

accepted

正式 AnalysisResult 必须绑定 AnalysisRun，包括 preregistration_id、raw_data_hash、分析脚本 commit、依赖锁哈希、运行时、输入/输出 Schema、清洗/排除/缺失规则和参数；随机分析保存 seed，provider 不支持时标记不可完全复现。任何脚本、数据清洗、参数或环境变化创建新 AnalysisRun，旧结果不覆盖；无法在声明容差内重现或缺少快照时标记 reproducibility_failed，不能自动作为新证据。
