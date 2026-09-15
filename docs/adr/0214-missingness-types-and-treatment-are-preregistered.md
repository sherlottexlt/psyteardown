# 缺失类型和处理策略必须预注册

## Status

accepted

OutcomeObservation 分开记录 participant_withdrawal、task_abandonment、technical_failure、skipped_by_protocol、no_response 和 not_applicable；这些状态不自动等于拒绝、不喜欢或体验失败。预注册必须锁定各类型的分析处理、分母、阈值和敏感性分析；缺失率超阈值可将结果降为 inconclusive/needs_reanalysis，事后改变策略创建新的 Analysis/Preregistration revision。LLM 只能辅助归类，最终由规则/人工确认。
