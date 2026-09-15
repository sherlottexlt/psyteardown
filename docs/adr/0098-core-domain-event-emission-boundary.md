# 仅为影响领域与流程的变化发出 Domain Event

## Status

accepted

V1 只为影响领域状态、后续流程、权限、数据传输、实验或知识库的变化发出 Domain Event，包括 Brief 冻结/替换、候选导入/事实冻结/评审确认/阻断/选择、ReviewItem 确认/覆盖/延后、发散缺口、比较、Next Prompt、反馈回灌、变量修复、实验、启发式、远程同意和资产来源可用性。Job 创建/完成/失败也是领域事件，模型细节保存在 ModelStepAttempt。页面导航、展开、筛选、草稿未提交等纯 UI 行为不进入领域事件流。
