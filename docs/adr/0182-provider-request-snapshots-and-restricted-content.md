# Provider 请求保存不可变快照并限制原文留存

## Status

accepted

每次远程 provider 请求保存 Provider Request Snapshot，包含 role、provider/model/policy revision、Prompt Package、实际文本字段、asset_id/派生 hash、redaction revision、Consent Scope 和 fingerprint；重试创建新快照并与 ModelStepAttempt 一一对应。Audit Event 默认只存摘要和 hash，完整 prompt/私人字段按资产隐私和授权受限保存；Showcase 不包含完整请求，Reproducible Bundle 按授权导出。
