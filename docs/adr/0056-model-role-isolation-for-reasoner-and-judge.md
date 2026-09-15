# Reasoner 与 Judge 复用模型时保持调用隔离

## Status

accepted

V1 允许 ReviewReasoner 和 ClaimJudge 复用同一个底层模型，但必须使用不同 system prompt、独立请求、无共享对话历史，并让 Judge 只读取原始冻结事实、机制卡和单条 ReviewItem，不接收 Reasoner 的隐藏思考、候选排名或自我辩护。Claim Judgement 只作人工审阅信号，不自动删除、批准、阻断或作为评测真值；正式评测使用人工标注集。这样控制 MVP 成本，同时避免明显的自我审查耦合。
