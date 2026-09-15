# V1 反事实依赖由人指定

## Status

accepted

V1 不自动穷举反事实；人从 Dependency Snapshot、Candidate Evaluation Record 和 Partial-Order Reason Set 中指定一个移除/替换依赖，系统提供基于影响范围和成本的建议。涉及 Safety/Privacy Blocking、critical policy 或 emergency rule 的反事实必须人工明确授权；一次只改一个依赖。人可选择 Reason Set 外的依赖，标记 Exploratory Counterfactual，不自动加入正式解释或设计提示。
