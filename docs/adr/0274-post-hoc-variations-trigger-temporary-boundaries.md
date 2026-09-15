# 事后用户变体只能触发临时边界

## Status

accepted

未预注册的用户变体分析即使数据和呈现有效，也只能形成 `post_hoc_boundary_signal`，触发 Evidence Impact Analysis、受影响变体的临时暂停和验证任务；它不能直接成为正式支持、有效反例或永久收窄启发式。正式收窄必须创建新 revision，并完成针对该变体的预注册前瞻性检验；高风险信号可先采取临时更窄处置。
