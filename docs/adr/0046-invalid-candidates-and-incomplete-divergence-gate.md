# 生成无效候选和发散缺口使用不同阶段门

## Status

accepted

候选在导入时违反 DesignBrief 硬约束或缺少必填输入契约，标记 generation_invalid 并拒绝进入事实确认。候选本身合法但整个批次未满足 Candidate Divergence Matrix 时，保留候选，批次标记 divergence_incomplete，暂停正式跨候选比较，并生成 Divergence Gap Report 和补充设计提示；只有人工确认后才交给外部生成器补齐。这样区分单个候选无效与批次探索不足，避免系统自行补生成。
