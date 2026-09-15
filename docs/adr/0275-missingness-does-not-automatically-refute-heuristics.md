# 缺失和退出不自动推翻启发式

## Status

accepted

用户退出、任务未完成或测量缺失必须按预注册的 Missingness Type、Task Completion Outcome 和 Completion Cause Evidence 处理，不能直接作为启发式反例。原因不明或处理不可审计时，结果降为 `inconclusive/needs_reanalysis`；安全停止可先触发风险审查，完成者结果与退出模式并列报告。
