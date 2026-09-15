# VariablePatch 冲突必须显式解决

## Status

accepted

同一作用域内对同一变量的互不兼容 VariablePatch 创建 Patch Conflict。两个 must 冲突时必须人工解决、撤回一个或拆分为不同候选变体；must 优先于 should；两个 should 可由人选择或拆成 A/B；explore 冲突只进入探索分支。未解决冲突的候选标记 patch_conflict，不能进入普通 Preferred；生成器不得按顺序覆盖或自行折中。解决创建新 patch revision，原冲突保留。
