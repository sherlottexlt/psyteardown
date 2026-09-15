# 反事实只复用未受影响的不可变产物

## Status

accepted

Counterfactual Run 可以只读复用 Brief、Candidate Facts、Confirmed Observation、机制检索、原始 ReviewItem、AnalysisResult 和资产哈希等未受影响的不可变产物；被移除/替换依赖及其下游 Criterion Assessment、Rule Match、Event Coverage、Candidate Evaluation、Partial Order 和 Reason Set 必须重算。反事实拥有独立 fingerprint/cache，保存 reused/recomputed artifact IDs，不能自动成为正式 Job 输入；如需新远程调用，重新执行 Consent/Provider Policy 检查。
