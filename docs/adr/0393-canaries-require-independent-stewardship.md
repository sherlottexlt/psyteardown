# Canary 须由独立人员生成并保管

## Status

accepted

未暴露 canary 必须由不参与仲裁服务开发、供应商沟通或结果判定的独立 steward，以与被测后端无关的来源和秘密种子生成、保管并在执行时揭示；生成、抽样、访问和销毁均须审计。由被测模型生成、公开样例改写或同一供应商保管的 canary 标记 `canary_generation_contamination`，不能作为确认性证据。
