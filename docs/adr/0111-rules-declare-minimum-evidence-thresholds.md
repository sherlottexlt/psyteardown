# 规则声明最低证据门槛

## Status

accepted

每条 Variable Compatibility Rule、Approved Risk Rule 和 Blocking Rule 必须声明最低证据类型。仅有 declared 的候选不能证明 measured 或 confirmed_observation；证据不足通常进入 explore/conflicted。只有专门的 High-Risk Missing-Evidence Rule 才能在关键隐私/安全声明缺失或高风险冲突本身构成风险时触发 blocked。这样避免未知被普遍等同于危险，同时保留对关键缺失安全声明的保守处理。
