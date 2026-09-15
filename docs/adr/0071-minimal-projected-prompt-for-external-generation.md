# 外部设计生成使用最小投影提示包

## Status

accepted

Next Design Prompt 通过 Prompt Projection 从完整项目数据生成最小必要字段，默认去除用户身份、原始访谈/日志/媒体、未确认模型推理、内部评审者信息、被驳回候选和无关实验数据。投影后的提示包必须经过本地脱敏和 Pre-Transfer Preview，由人确认具体字段、派生资产、provider 与模型后才能发送；提示版本和哈希保存，敏感字段检测失败进入 awaiting_redaction。这样把下一轮设计反馈和隐私数据解耦。
