# 人工合并观察创建新来源链

## Status

accepted

多个 provider 的 Observation Draft 由人合并时，创建新的 Confirmed Observation，并保存 source_observation_ids、provider runs、merge_type、accepted/rejected/unresolved claims、merge rationale、actor 和时间；原始草案不可修改。合并只保留各来源共同或人工明确确认的内容，不提升 declared/observed/measured 证据等级。这样保证人工责任和证据边界可追溯。
