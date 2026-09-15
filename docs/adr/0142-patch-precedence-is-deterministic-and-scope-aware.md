# VariablePatch 按作用域和执行强度确定性解析

## Status

accepted

对同一 InterventionEvent，先应用 exclusions，再按作用域具体性选择，随后按 must/should/explore 强度处理；同一具体度和强度的互斥 patch 进入 patch_conflict，交由人解决或拆分变体。routine patch 不能覆盖 critical 作用域；被覆盖 patch 标记 shadowed_in_scope 并保留。生成器还要返回 Patch Application Declaration（intended/actual/partial/not_applied/unverifiable），系统通过变量 diff 另行确认实际采用。
