# 本地保留运行记录并显式处理已删除证据

## Status

accepted

V1 默认在本地长期保存原始资产、Data Transfer Manifest、prompt、结构化输出和 ModelStepAttempt，以支持审计和复现；远程 provider 的保留/训练政策单独声明，不由系统臆测。用户删除原始资产时不静默删除历史评审，而将相关 Evidence 标记 source_unavailable 并降低可验证性。敏感资产只允许发送给数据政策满足要求的 provider。审计事件仅保存 ID 和摘要，导出不包含 API key。这样兼顾可追溯和用户删除权；代价是删除后部分历史结果无法重新核验。
