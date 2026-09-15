# Patch 采用状态由候选事实差异确定

## Status

accepted

DesignGenerator 必须回报 Generator Application Declaration，但 psyteardown 不把它当作事实。系统解析候选的 canonical DesignVariable 值，在事实确认后与父候选和确认 VariablePatch 比较，确定 Patch Adoption Status（adopted、partially_adopted、not_adopted 或 unverifiable）；L0/L1 仍只能证明声明层采用。生成器声称 applied 而变量未变时，以 not_adopted 或 unverifiable 为准；must 未满足的候选不能进入普通 Preferred。
