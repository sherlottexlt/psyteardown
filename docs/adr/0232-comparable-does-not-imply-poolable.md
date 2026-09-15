# 跨实例比较和统计合并分离

## Status

accepted

comparable 只允许实例间描述性比较；只有通过独立 Pooling Compatibility，满足 Consent Scope、相同/兼容协议、条件和测量定义、样本/缺失处理、设备运行和分析计划，并声明/控制 Instance Effect，结果才标记 poolable。合并创建新的 Derived Dataset 和 AnalysisRun，保留每个 instance_id 和批次来源；未预注册的合并只能 exploratory，不提高 Outcome Evidence Strength。撤回或策略变化后执行 Evidence Impact Analysis，LLM 不决定 poolable。
