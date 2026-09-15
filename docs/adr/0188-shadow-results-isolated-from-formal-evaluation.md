# Shadow 结果与正式评测/知识隔离

## Status

accepted

Shadow Rule Run 只用于 Rule Promotion Evidence：统计命中、误报/漏报、作用域和解除条件，不改变候选正式状态、系统分数、评测真值、知识增长或模型训练。Development/Validation 可单独显示 shadow 列但不能当正式结果；Holdout 不暴露 shadow 命中，基于 shadow 重新标注的数据不能充当独立真值。规则转 Enforced 后必须重新执行正式评测，只有 enforced 结果进入系统分数。
