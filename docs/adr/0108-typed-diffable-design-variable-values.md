# 设计变量值类型化并支持差异追踪

## Status

accepted

V1 的 DesignVariableValue 按变量定义的 value_type 表达，保存 normalized_value、display_value、单位/范围、来源和 certainty；枚举使用 canonical value_id，数值必须带单位和测量条件，文本标记 unstructured。缺失状态区分 not_declared、not_observable、not_measured 和 conflicted；跨轮 diff 比较 normalized value。候选组合遇到类型不兼容或变量兼容性未知时进入人工处理，不自动拼接。
