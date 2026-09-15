# 多候选组合创建 Hybrid Candidate 并重新评审

## Status

accepted

Human Selection 支持 Select As-Is 和 Compose Revision。组合时创建新的 Hybrid Candidate，保存多个 parent_candidate_ids、每个设计变量的来源、冲突处理和人工理由，不修改父候选；组合候选必须重新生成事实快照，检查 Generation Constraint、Evidence Conflict、Minimum Intervention Event Set、发散矩阵和风险规则，并重新进行 ReviewItem 确认。父候选的已确认事实和评审只作为 draft 参考，不能直接继承。这样支持真实的综合设计过程且保持证据独立。
