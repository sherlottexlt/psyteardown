# 撤销使用反向修订而不删除历史

## Status

accepted

撤销人工选择、解除 blocked、撤回 Next Prompt 或废弃知识时创建 Reversal Revision，保留原决策、作者、时间、理由和证据；已有下游结果标记 Dependent-on-Revoked Result，保留用于审计但不能自动成为 current。新的下游流程必须从新的 current revision 重新生成，不修改旧结果或伪装成决策从未发生。
