# 分离传输授权等待与设计阻断

## Status

accepted

Awaiting Consent 是具体资产/provider/model/用途尚未获得用户授权的任务状态；授权后 Job 可以继续，候选评审状态不改变。Design Blocked 是候选事实命中 Scope Exclusion、Brief Hard Constraint 或 Approved Risk Rule 的设计状态；用户授权不能解除，必须修改候选/Brief 或满足 unblock condition。两者同时存在时任务层显示 awaiting_consent，设计层保留 blocked，授权后仍不得继续正式评审或回灌。
