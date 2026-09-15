# 参与者数据请求采用可审计处理生命周期

## Status

accepted

每个 Participant Data Request 生成 request_id，并经历 received、under_review、partially_fulfilled、fulfilled、rejected 或 cancelled；验证状态单独记录。处理删除、撤回、限制或更正时必须说明范围、理由、无法完成的部分、保留聚合和 Evidence Impact Analysis，并向参与者发送脱敏 Request Notification；通知时间和摘要写入审计。V1 可手动通知，不接邮件系统，不泄露其他参与者、prompt 或身份映射。
