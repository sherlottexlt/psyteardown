# local_only 资产必须有离线处理路径

## Status

accepted

V1 必须支持 Fake provider、人工观察/评审或未来本地模型中的至少一种 Offline Processing Path；`local_only` 资产禁止远程 VisionObserver/LLM 读取。当前无本地能力时 Job 进入 Awaiting Local Capability，允许用户人工处理或配置本地 provider，不自动换发远程，也不把看不到的资产判为无风险。缺失观察通常进入 explore；只有 High-Risk Missing-Evidence Rule 适用时才可 blocked。
