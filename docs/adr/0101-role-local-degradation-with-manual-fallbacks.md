# 模型失败采用角色级局部降级和显式人工替代

## Status

accepted

VisionObserver、ReviewReasoner、ClaimJudge 或远程 provider 不可用时，只暂停对应阶段，保留已冻结事实、历史 revision 和已完成结果；可稍后重试或由人执行 Manual Fallback Step，记录来源、理由、作者、时间和证据。未授权/不可用 provider 不自动切换或重新发送资产；规则/机制库缺失时不能生成正式评审或偏序。系统不得把模型失败解释为无风险、通过或“没有观察到问题”，不满足阶段门时停留在草案/探索状态。
