# 风险规则使用受限声明式模型和人工审批

## Status

accepted

Approved Risk Rule 采用声明式 Schema，只允许 equals、not_equals、contains、missing、greater_than、less_than、all_of 和 any_of 等白名单运算符；AI 不得生成可执行代码。规则候选经过 Schema 校验、去重和人工审批后版本化生效，被驳回的 rule_id 保留。新规则不静默改写历史评审，对旧候选的应用通过显式 Re-evaluation 创建新 revision。这样保持规则执行安全、可重复和可审计；代价是复杂风险需要拆成多个受限条件或转为人工评审。
