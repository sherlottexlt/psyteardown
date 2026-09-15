# 体验评审作为独立领域模块

## Status

accepted

新增 `experience` 领域模块，负责 DesignBrief、DesignCandidate、Observation、ExperienceHypothesis、Critique、DesignIteration 和实验规划；现有文本拆解 `pipeline` 保持兼容。两者共享心理学知识库、LLM provider 和证据基础设施，并通过只读适配器连接旧产物。这样避免新物理产品设计闭环破坏旧案例和测试，同时允许两种输入模式逐步汇合；代价是短期存在相邻但不同的领域模型。
