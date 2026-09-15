# 远程资产处理需要可核验 Provider Policy Record

## Status

accepted

远程 provider 必须保存版本化 Provider Policy Record：provider/model 版本、政策来源和文档哈希、retention、training_use、region、deletion capability、subprocessors、检查人/时间和 status。verified 可按 Consent Scope 处理对应资产；self_declared 只允许 public；expired/rejected/unknown 禁止 project_private/sensitive。Provider 政策变化需新记录和重新检查，不自动沿用旧授权；Data Transfer Manifest 引用具体 policy revision。本地 provider 也需声明 local_only 和数据驻留。
