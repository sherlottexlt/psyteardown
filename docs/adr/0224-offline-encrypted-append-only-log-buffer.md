# V1 使用离线加密追加式事件日志缓冲

## Status

accepted

设备离线时将最小 EventLog 写入本地加密 append-only buffer，每条记录带 participant/condition/sequence、前一条 hash 和 Device Monotonic Time；网络恢复后按 sequence 有序幂等上传，服务端校验 hash/sequence。缓冲满时按预注册策略优先保留关键条件/安全事件，普通事件丢弃需记录 overflow，不覆盖旧日志；撤回远程处理后停止未上传内容。sequence 缺口、hash 冲突、溢出或时钟质量不足标记 Log Integrity Uncertain，Condition Presentation/Outcome Evidence 降级，不能猜补或作为主要证据。
