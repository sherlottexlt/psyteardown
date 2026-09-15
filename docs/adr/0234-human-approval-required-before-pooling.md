# 跨实例池化必须人工审批

## Status

accepted

Pooling Compatibility、Instance Effect 和 Consent Scope 通过后，创建 Pooling Proposal，列出 instance/dataset/protocol/condition/measure、样本、同意、缺失、分析计划、收益和风险；未经 Human Pooling Approval 不创建 pooled dataset。人可选择 full_pool、stratified_pool、exploratory_only 或 reject；批准后创建新的 Derived Dataset/AnalysisRun，不改写源实例。Stratified Pooling 保留各实例结果，拒绝提案保存理由且不自动重复提交；池化不等于知识/启发式批准。
