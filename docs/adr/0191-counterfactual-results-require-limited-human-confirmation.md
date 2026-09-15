# 反事实结果与正式状态隔离

## Status

accepted

结构化 Counterfactual Run 可由确定性代码自动生成并展示；LLM 对差异的解释，以及涉及安全/隐私、critical policy 或 blocking rule 的反事实，必须经过人工确认。所有结果标记 counterfactual_only，明确不是实际运行结果、因果证明或正式评测；反事实使用独立 fingerprint 和 dependency snapshot，不修改 current、Consent Scope、正式偏序、历史结果或 Next Design Prompt，也不自动进入 Human Judgement Signal Pool。人确认后最多作为解释材料或后续研究问题保存。
