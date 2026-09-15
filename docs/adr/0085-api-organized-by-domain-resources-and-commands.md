# API 按领域资源和显式命令组织

## Status

accepted

FastAPI `/api/v1` 按 Brief、Iteration、Candidate、Fact、ReviewItem、Job、Asset 和 Export 等领域资源组织；冻结、确认、选择、覆盖和生成提示使用显式 Domain Command endpoint。所有写请求带 expected_revision，耗时命令返回 202 + job_id，Domain State Error 使用稳定错误码。页面可使用只读组合投影，但投影不承载写逻辑；API Schema 不直接暴露数据库行。这样让前端变化不重塑领域边界，并防止旧页面状态覆盖新 revision。
