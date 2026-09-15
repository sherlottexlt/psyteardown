# 项目日志使用设备安全存储和版本化密钥

## Status

accepted

V1 由 OS Keychain、Secure Enclave 或 TPM 管理每个项目独立的 Project Log Key，事件日志使用 AEAD 加密；密钥和 key_version 不写入日志、SQLite 或默认导出包。密钥轮换产生新 Key Version，旧日志保留原版本，不覆盖重加密。Key Unavailable 时保留受保护本地日志、停止上传并标记状态，不使用固定默认密钥或明文降级；设备无安全存储能力时不采集敏感持久化事件。
