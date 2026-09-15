# Gatekeeping 上游失败限制下游确认

## Status

accepted

事前 gatekeeping 上游分支未达标时，下游即使自身指标达标，也只能是 `supported_descriptive` 或 `exploratory_secondary_under_failed_gate`，不能获得确认性 `supported`/`replicated`、启发式支持或外部准入。下游结果和效应保留并标记门控未通过；重新确认需新预注册主要假设或独立实验。
