# 用户纠正立即生效但不自动学习

## Status

accepted

User Correction 立即停止、撤销或切换当前 InterventionEvent，并将原推断标记 corrected_by_user；当前事件不能继续使用原推断授权。一次纠正不修改冻结 DesignBrief、候选事实、历史评审或长期偏好，只进入 Human Judgement Signal Pool。多次相似信号可形成 Context Pattern Candidate，经跨事件复盘、用户控制和人工确认后才影响未来设计；敏感状态纠正不得用于人格/健康推断。
