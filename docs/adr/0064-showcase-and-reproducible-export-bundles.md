# V1 区分展示包和可复现项目包

## Status

accepted

V1 提供 Showcase Export 和 Reproducible Project Bundle。展示包面向作品集，默认排除私人原始资产、完整 prompt、原始模型响应和审计；复现包通过 manifest.json、Schema 版本、稳定 ID、相对路径和 SHA-256 打包经授权资产、修订、评审、规则/机制版本、模型尝试、人工决策与评测配置。API key、.env 和绝对路径永不导出；敏感资产逐项确认。导入生成新的本地 project_id，并保留 origin_bundle_id。这样同时支持公开表达和工程复现。
