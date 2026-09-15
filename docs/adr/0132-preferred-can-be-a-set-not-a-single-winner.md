# Preferred 允许候选集合而非唯一冠军

## Status

accepted

Candidate Partial Order 的 Preferred 可以包含多个候选，表示在当前 Brief、共同基准场景和证据下都满足推进门槛且关键维度不可合理区分。系统显示 preferred_set_id、不可比较维度和推荐实验，不继续强排唯一冠军；人可以选择一个、多个或要求增加证据。若 Brief 要求唯一方案，系统提示需要区分实验，不凭空打破并列。这样保留真实设计探索的分支；代价是下一轮可能有多个并行分支。
