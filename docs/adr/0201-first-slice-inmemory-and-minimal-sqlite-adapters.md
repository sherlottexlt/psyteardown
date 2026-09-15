# 首条纵向切片同时提供内存和最小 SQLite 适配器

## Status

accepted

第一条 experience 纵向切片的领域测试使用 InMemory repositories，端到端 Fake provider 测试使用临时 SQLite 数据库；二者调用同一 application service 和 domain command。SQLite 只实现新 experience schema、不可变 revision、current projection、Domain/Audit Event 与必要索引，不先迁移旧 pipeline 或建立完整兼容体系；旧 pipeline 表和新 experience 表分开。
