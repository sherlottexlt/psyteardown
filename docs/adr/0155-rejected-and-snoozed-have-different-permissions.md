# user_rejected 与 user_snoozed 使用不同权限语义

## Status

accepted

User Rejected 表示当前作用域内停止主动介入；除非用户重新触发、明确修改偏好或出现经批准的 critical 事件，普通事件不得换模态继续逼近。User Snoozed 表示带 resume_condition/时间窗口的有限延后，V1 默认最多一次受限重试，重试仍遵守原最大强度；再次拒绝转为 rejected。两者均保存 User Response Scope，不由模型扩大或互相改写。
