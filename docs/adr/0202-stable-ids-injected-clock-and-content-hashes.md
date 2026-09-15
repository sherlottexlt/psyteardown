# 使用稳定 ID、注入式 UTC 时钟和内容哈希

## Status

accepted

第一条 experience 纵向切片中，领域对象和事件创建时生成稳定 UUID；对象后续 revision 不改变稳定 ID。每个对象的 revision_number 从 1 开始单调递增，用于 expected_revision 并发检查，不能重用；revision_id 与 revision_number 分开。时间由 application service 注入 UTC Clock，测试使用 FrozenClock，领域模型不直接读取系统时间。对规范化不可变 payload 计算 content_hash，用于完整性、复现和导出校验，但不作为主键或对象身份。生产时间统一 UTC，展示层再转换时区。
