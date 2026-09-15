# V1 对体验评审设置调用和时延预算

## Status

accepted

V1 每候选约 4–6 个核心 ReviewItem（explore 最多 3 个），5 候选批次最多约 40 次模型调用，单候选目标 ≤3 分钟、整批目标 ≤10 分钟；重试计入预算。独立候选和普通 Judge 可有限并行，高风险项逐条优先。达到预算仍未完成时标记 Review Budget Exhausted，保留高风险/主要权衡，低优先级内容转 Deferred Observation，不把未完成解释成无风险；预算配置进入运行 fingerprint。
