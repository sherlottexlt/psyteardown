# 使用声明式变量兼容性规则

## Status

accepted

V1 建立 Variable Compatibility Rule，使用 requires、forbids、conflict 和 recommends_review 等白名单关系描述规范设计变量组合；确定性引擎只执行 approved 规则，LLM 只能提出候选。Rule Match 保存参与变量值、来源、rule_id/版本、影响、证据要求和解除条件；未知关系进入 explore，多个冲突规则全部保留并交由确定性优先级/人工处理，不由 LLM 选择性隐藏。这样让材料、介入、情境和隐私约束可审计地联动。
