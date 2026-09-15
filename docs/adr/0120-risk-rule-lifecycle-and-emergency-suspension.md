# 风险规则拥有保守生命周期和紧急暂停状态

## Status

accepted

Approved Risk Rule 支持 candidate、approved、deprecated、superseded 和 emergency_suspended。deprecated/superseded 停止新评审使用但历史结果保留；emergency_suspended 因明显错误或安全问题立即停止新评审，并触发 Rule Impact Analysis，定位受影响候选、ReviewItem、实验和启发式。任何状态变化都不自动解除历史 blocked；只有人工审阅影响并创建显式 unblock revision 才能解除。
