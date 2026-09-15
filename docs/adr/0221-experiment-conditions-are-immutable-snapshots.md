# 实验条件使用不可变 Condition Snapshot

## Status

accepted

ExperimentPlan 预注册时创建 Condition Snapshot，绑定 candidate revision、DesignVariable 值、InterventionEventSequence、Scenario Snapshot、asset/prototype hash、说明版本、环境、随机化角色、Consent Scope 和 content_hash；正式参与者使用后不可原地修改。反馈模态、时机、材料、文案、任务说明、环境或 provider 变化创建新条件 revision；实际参与者数据引用 Actual Presented Condition。预注册与实际不一致记录 Protocol Deviation，结果不能只按条件名称归属。
