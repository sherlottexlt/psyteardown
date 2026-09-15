# V1 记录生成器行为模式但不自动适配提示

## Status

accepted

V1 可以在明确模型/版本、prompt package、Brief 和样本范围内统计 Generator Behavior Observation，例如候选缺少误判恢复或材料参数，但不把它表述为生成器能力画像，也不自动创建或应用永久 prompt 补丁。Hybrid Candidate 不归因给原模型。未来 Generator Prompt Patch 必须跨多个 Brief、包含重复运行、排除人工编辑影响并经人工批准；新模型版本重新评测。这样保留改进信号而避免过度归因和自我强化。
