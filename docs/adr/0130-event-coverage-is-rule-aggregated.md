# Event Coverage Result 由规则聚合并允许人工覆盖

## Status

accepted

ReviewReasoner 可以提出事件覆盖和缺失字段，确定性引擎检查必需事件、字段、ReviewItem 关联、机制覆盖和 blocked 规则，生成 covered、partial、unknown 或 blocked；人工可对结果创建新 revision。blocked 只能由确定性规则触发，covered 仅表示事件评审覆盖完整，不表示体验结果已验证。这样把模型提议与流程完整性、风险状态分开。
