# 反事实只更新决策支持，不自动改变选择

## Status

accepted

Counterfactual Result 只能生成 Counterfactual Decision Support：展示正式与反事实偏序、Reason Set、权衡和未决问题，不能自动改 Preferred Set、人工选择或 Next Prompt。人若采纳反事实启示，必须创建新的 Selection Decision、Validation Task 或 DesignBrief revision，引用 counterfactual run_id 并说明反事实局限；反事实不能成为 Outcome Evidence 或 Design Heuristic。
