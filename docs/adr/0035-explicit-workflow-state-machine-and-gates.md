# 使用显式状态机保护人工阶段门

## Status

accepted

DesignBrief、DesignCandidate、ReviewItem 和 DesignIteration 使用显式状态机。Brief 未冻结不能开始该轮候选；Facts 未冻结不能生成正式 ReviewItem；评审未确认不能参与正式排序；未完成人工选择和 Next Design Prompt 确认不能回灌下一轮；blocked 候选必须通过新 revision 解除阻断后才能被选择。非法跳转返回 Domain State Error，不自动补齐前序状态。这样让权责边界在代码中可执行；代价是操作流程更严格，需要清晰的 UI 状态提示。
