# 视觉观察经人工确认后才能进入正式评审

## Status

accepted

视觉模型提取的 Observed Fact 首先保存为 Observation Draft，必须经人接受、修改、驳回或标记 not_observable 后，才能成为 Confirmed Observation 并进入正式 ReviewItem。未经确认的观察最多生成 explore 或澄清请求，不能触发 blocked 或确定性设计修改。这样降低图像误识别对设计决策的影响；代价是每个候选需要一个事实确认步骤。
