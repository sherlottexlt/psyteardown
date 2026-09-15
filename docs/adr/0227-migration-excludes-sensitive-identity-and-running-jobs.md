# V1 项目迁移默认排除身份映射和运行中 Job

## Status

accepted

V1 支持离线手工迁移完整结构化研究项目；经授权的资产和受保护日志可选迁移。Identity Mapping、真实联系方式、未授权原始媒体、API key 和 running Job 默认不迁移；running Job 在新设备上按 orphaned/cancelled 重新创建。迁移生成新的 local project_id，保留 origin_project_id，验证 manifest/hash、删除限制和恢复密钥；provider 授权不自动继承。
