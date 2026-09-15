# 组合失败拆分保留子结果

## Status

accepted

组合联合判据失败时，联合启发式只能标记 `partial_composite_support`/`inconclusive`，各子结果仍按自身预注册假设独立保留。子结果不能互相覆盖、抵消或自动支持组合启发式；联合语义必须修订并重新预注册验证。
