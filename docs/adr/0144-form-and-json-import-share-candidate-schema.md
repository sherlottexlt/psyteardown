# 表单和 JSON 导入共享候选 Schema

## Status

accepted

V1 同时提供 Review Workspace 表单和版本化 JSON 导入，两者都创建 Candidate Draft 并记录 Candidate Contract Version、Design Source 和资产引用，经过同一套字段、资产、提示注入、Generation Constraint 和 Minimum Intervention Event Set 检查。任何导入都不能直接写入 facts_frozen、正式评审或 Next Prompt；缺失/非法字段返回字段级错误，不静默补全，资产只能引用登记的 asset_id。
