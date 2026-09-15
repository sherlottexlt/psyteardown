# 相反条件建议拆成独立启发式分支

## Status

accepted

经预注册交互确认、对不同用户变体产生相反建议时，必须拆成资格、反例和生命周期独立的条件性 heuristic branches，各自绑定变体、结果、证据、适用/排除条件和注入指令。Heuristic Family 只用于关联共同调节证据和 lineage，不可直接注入；调节变量未知时标记 `unknown_applicability`，不得任选分支。负向分支仍只能以 `consider_avoiding` 使用。
