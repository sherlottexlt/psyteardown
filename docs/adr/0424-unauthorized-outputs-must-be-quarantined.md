# 未授权输出必须隔离

## Status

accepted

撤销窗口内潜在执行产生的候选或评审草稿，即使未被人工查看，也必须标记 `unauthorized_output_quarantined`，不得进入候选事实、ReviewItem、偏序、反馈或训练/案例库。输出只能作为事故调查材料保留，并需记录访问控制、隔离/删除状态和影响分析。
