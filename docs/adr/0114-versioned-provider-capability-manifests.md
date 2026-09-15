# Provider 能力以版本化清单声明

## Status

accepted

每个 DesignGenerator、VisionObserver、ReviewReasoner、ClaimJudge 和工程证据 provider 必须提供版本化 Capability Manifest，声明 locality、supported_roles、input_modalities、max_asset_size、structured_output/schema validation、data_retention_policy、supports_local_only、采样控制和限制。Job 创建前按角色、资产隐私和模态检查；local_only 只能匹配本地且支持该能力的 provider，不支持 seed/temperature 必须标记 unsupported；能力或版本变化产生新 fingerprint。系统不按 provider 名称猜能力，也不自动切换 provider，替代方案由人选择。
