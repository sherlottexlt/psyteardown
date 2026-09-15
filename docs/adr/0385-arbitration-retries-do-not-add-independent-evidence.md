# 仲裁重试不增加独立证据

## Status

accepted

相同仲裁服务、版本、输入和信任链的多次重试属于同一仲裁 lineage，只能说明可重复性，不能增加独立证据数量。变更提示、参数、输入裁剪或判据后的重试必须标记 `arbitration_specification_shift`，仅可作探索性敏感性分析，不能择优恢复资格。
