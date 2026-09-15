# 工程工具作为外部证据提供者接入

## Status

accepted

CAD、CAE、BOM、续航计算、合规检查和物理测量等通过 EngineeringEvidenceProvider 协议接入，返回带工具版本、输入资产/参数、方法、结果、单位、不确定性、限制和 run_id 的 EngineeringEvidence。psyteardown 不内置这些工具、不润色原始结果，也不在工具失败时由 LLM 补结论；证据只能支持其能力范围内的 EngineeringClaim。V1 只定义协议与 Fake provider，真实工具留待后续适配。
