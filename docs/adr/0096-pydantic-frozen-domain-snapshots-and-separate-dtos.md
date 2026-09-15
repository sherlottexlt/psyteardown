# 使用 Pydantic 冻结领域快照并分离边界 DTO

## Status

accepted

项目继续使用 Pydantic，但正式领域对象采用 frozen snapshot 语义，集合字段不可变；API request/response、LLM structured output、导入对象和持久化 DTO 与领域快照分离。LLM 的 Review Draft 先经 Schema、证据和人工确认，再转换为 ReviewItemRevision；repository 读取数据后重建不可变对象。这样复用现有 Pydantic 生态，同时不让可变 DTO 绕过 revision 和阶段门。
