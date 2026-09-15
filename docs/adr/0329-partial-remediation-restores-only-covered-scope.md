# 部分补证只恢复已覆盖范围

## Status

accepted

补证按事前声明的恢复条件逐项判定，部分修复标记 `remediation_partial`，不能自动恢复原 Approved 范围。核心门槛恢复但仅覆盖较窄范围时，创建新的窄范围 Approved revision 并排除未修复范围；关键门槛仍缺失则维持 `qualification_at_risk`，原高范围 revision 保留。
