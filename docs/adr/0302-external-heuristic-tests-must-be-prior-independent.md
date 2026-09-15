# 外部启发式检验须证明推断不依赖旧先验

## Status

accepted

外部团队可使用旧证据进行样本规划，冻结先验也不自动破坏执行独立性；但若新数据只有信息先验下达到成功判据，结果标记 `prior-dependent`，不能满足启发式外部独立准入。只有弱信息或怀疑性先验分析在新数据自身达到 `supported`，外部检验才具准入资格；`execution_independence` 与 `inferential_prior_dependence` 分开记录。
