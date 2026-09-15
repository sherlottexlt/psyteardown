# 多主要结果的组合启发式须控制整体错误

## Status

accepted

组合启发式的多个主要结果必须事前锁定联合判据、阈值/区间、缺失处理和整体错误控制策略。未锁定整体逻辑时，即使各结果分别达标，也最多是 `supported_descriptive`/`partial_composite_support`，不能形成确认性联合支持；事后选择联合规则无效。
