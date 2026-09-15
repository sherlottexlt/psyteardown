# V1 使用最小事件日志验证条件呈现

## Status

accepted

V1 只记录与条件加载/切换、事件触发、反馈模态/强度/时机、用户确认/延后/拒绝/纠正、设备错误/延迟/丢包/重试、校准、任务边界和研究者干预直接相关的 EventLog；不默认采集无关屏幕行为、位置、通信内容、长期设备流或原始音视频。日志字段、频率、保留和同意范围预先声明，时间使用 Device Monotonic Time 并可选 UTC 对齐，payload 最小化并带 hash。日志缺失或改写影响 Condition Presentation Record，按 Protocol Deviation/Presentation Unverified 处理。
