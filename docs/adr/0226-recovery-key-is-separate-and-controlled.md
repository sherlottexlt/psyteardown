# 恢复密钥独立于项目包并受控迁移

## Status

accepted

V1 可由人显式导出 Project Recovery Key，用另一个用户密码或公钥包裹，单独保存，不进入 Showcase 或 Reproducible Bundle，明文不落盘/不进剪贴板。迁移时验证项目 manifest、内容 hash、日志 sequence 和删除/限制状态，在新设备创建本地绑定并保留旧 key_version；没有恢复密钥只导出结构化数据，受保护日志标 decrypt_unavailable。密钥导出/导入/轮换/吊销均审计，恢复密钥不能绕过参与者删除请求。
