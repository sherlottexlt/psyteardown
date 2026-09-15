# 首条纵向切片使用结构化文本和 Fake provider

## Status

accepted

第一条 Vertical Slice 使用结构化文本候选与 FakeDesignGenerator/FakeReviewReasoner/FakeClaimJudge，跑通 Brief 冻结、5 候选导入、发散/事件校验、事实冻结、ReviewItem 人工确认、确定性准则聚合、候选偏序、人工选择、Next Design Prompt、第二轮 3 候选、Variable Repair Trace 和 Showcase 导出。它必须实现不可变 revision 和阶段门，但暂不接真实视觉/设计模型、材料文档抽取、实验执行或完整视觉设计。这样先验证核心领域闭环，而不是被模型和界面问题掩盖。
