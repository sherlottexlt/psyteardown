# 实验优先采用最小差异，组合变化不做单变量归因

## Status

accepted

V1 的主要假设优先使用 Minimal-Difference Experiment：指定一个 primary DesignVariable，尽量保持文案、时机、频率、设备、任务、用户和场景一致。若 VariablePatch 或实际候选导致多个变量同时变化，预注册必须列出共同变化、控制不了的变量和分析边界，结果降级为组合/探索性结论，不得声称其中某一变量造成体验结果。多因素设计可作为后续扩展，但需预注册交互项和分析族。
