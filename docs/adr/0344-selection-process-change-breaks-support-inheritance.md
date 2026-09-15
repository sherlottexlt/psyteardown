# 候选选择机制变化切断支持继承

## Status

accepted

候选生成池、筛选顺序、纳入/排除规则、人工覆盖、排序依据或选择机会集发生变化时，即使最终选中候选相同，也标记 `selection_process_change` 并切断旧支持继承。新流程必须记录选择链并重新前瞻验证；旧结果只能作为历史材料或 `prior_observation`。
