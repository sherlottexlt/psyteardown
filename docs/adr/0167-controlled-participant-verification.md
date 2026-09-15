# 参与者请求使用受控验证而非 participant_id 登录

## Status

accepted

V1 使用一次性高熵 token 或研究者线下核对完成 Controlled Participant Verification；token 不携带 participant_id、姓名或可推断身份的信息，只允许声明的请求 action scope。验证失败/过期不泄露 participant_id 存在性，使用、重置、作废和线下核对均写入审计。Participant Data Request 的验证状态与处理状态分开记录，研究者不能在普通工作台直接访问 Identity Mapping。
