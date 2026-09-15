# 规则命中使用固定优先级和单调风险合并

## Status

accepted

规则结果按固定优先级合并：Scope Exclusion → Safety/Privacy Blocking → DesignBrief Hard Constraint → Variable Conflict → Requires/Missing Dependency → Recommends Review。Scope Exclusion 和批准的安全/隐私阻断不能被普通 support 抵消；同级规则全部保留，解除条件不一致时维持 blocked/revise 并要求人工处理。规则版本变化触发受影响候选重新评审。这样保证风险判断不受文件顺序、LLM 偏好或支持项数量影响。
