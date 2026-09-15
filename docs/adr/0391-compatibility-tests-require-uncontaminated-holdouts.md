# 兼容性测试须包含未污染保留集

## Status

accepted

仲裁后端兼容性不能仅用供应商可能见过的固定测试集。验证必须包含供应商不可见的 holdout、未公开边界/反例和新鲜 canary，并记录测试访问、泄露和训练/微调污染状态；污染无法排除时标记 `compatibility_contamination_risk`，仅可作探索性证据，不能支持独立性继承。
