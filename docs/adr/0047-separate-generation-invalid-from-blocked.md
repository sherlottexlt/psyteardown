# 分离 generation_invalid 与 blocked 的状态语义

## Status

accepted

generation_invalid 只表示候选在评审前缺少输入契约、资产损坏、与冻结 brief 不匹配，或违反可直接检查的 Generation Constraint；它通过补输入或重新生成修复。blocked 只在事实冻结后，由确认事实命中 Experience/Safety Constraint 或 Approved Risk Rule 产生，并通过候选 revision 和解除条件重新评审。两者不互相替代。这样避免输入校验失败被误写成心理风险，也避免高风险候选绕过正式评审。
