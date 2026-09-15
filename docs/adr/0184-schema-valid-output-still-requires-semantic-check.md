# Schema 合法不等于语义一致

## Status

accepted

Provider Structured Output 即使通过 Pydantic/JSON Schema，也必须经过 Semantic Consistency Check，检查内部互斥字段、跨字段依赖、与候选声明/Confirmed Observation 的冲突和事件完整性。发现 Semantic Conflict 时不能进入 Candidate Facts Frozen 或正式评审，不能由 LLM 静默挑选/置空/修正；原始 JSON、校验报告和处理状态保留，人工修订创建新 draft revision。缺非关键字段可 input_incomplete，影响事件完整性 generation_invalid，高风险冲突按批准规则或人工审查处理。
