# V1 使用规则化重识别风险检查

## Status

accepted

V1 对派生数据和聚合洞察执行 Re-identification Check，检查直接身份、准标识符、Minimum Cell、罕见组合、时间/地点、自由文本唯一性、Identity Mapping 和外部数据联结，输出 low/medium/high/unresolved 并经人工复核。high/unresolved 默认禁止外部 prompt、公开展示和知识增长；medium 需要降粒度/抑制或人工批准，low 仍受 Consent Scope 和 k 门槛限制。仅 hash 不算匿名，系统不宣称绝对匿名；检查规则/脚本版本进入 Data Lineage。
