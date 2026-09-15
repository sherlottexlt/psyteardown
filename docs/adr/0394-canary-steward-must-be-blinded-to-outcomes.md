# Canary 保管者须对结果保持盲法

## Status

accepted

Canary steward 在执行后可查看必要审计信息，但在揭示前和结果判定前不得看到仲裁结果，也不能据结果调整抽样、替换 canary 或决定纳入。盲态被打破后须由另一独立人员判定结果；否则标记 `canary_steward_outcome_contamination`，该轮不能形成确认性兼容性结论。
