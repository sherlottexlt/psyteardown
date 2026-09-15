# 区分 critical 最低策略与普通默认策略

## Status

accepted

Critical 事件必须声明 Minimum Intervention Policy，包含允许模态、最大强度、时机、确认和降级；routine/important 可声明 Default Intervention Policy，用于低打扰默认行为。所有策略带作用域和 Maximum Intervention Intensity；routine/important 默认策略不能覆盖 critical 策略。候选覆盖策略需要新 revision，评审比较实际强度与允许上限；缺少普通默认策略可继续但相关事件可能 explore。
