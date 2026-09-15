# 任务未完成不自动等于设计失败

## Status

accepted

正式任务使用 Task Completion Outcome 区分成功、辅助完成、参与者放弃、界面/硬件/协议阻塞、超时、安全停止和数据不可用，并绑定 Completion Cause Evidence。abandoned_by_participant 不等于设计失败；safety_stop 需要结合原因审阅；没有原因来源时标记 completion_outcome_unknown。完成率比较必须同任务、同停止规则和同缺失策略，未完成事实不能直接生成确定性 VariablePatch。
