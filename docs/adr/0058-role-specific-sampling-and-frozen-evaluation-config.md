# 模型随机性按角色配置并冻结正式评测参数

## Status

accepted

VisionObserver 和 ClaimJudge 使用 provider 支持的低随机性配置，ReviewReasoner 允许受限发散但仍受 Schema、机制白名单和项目上限约束。所有参数随 Model Step Attempt 保存；provider 不支持 temperature 或 seed 时显式记录 unsupported。正式评测冻结模型、prompt、参数、机制库和规则库版本，探索运行不与正式评测混用。系统不承诺 LLM 完全可重复，只承诺配置、输出和差异可追溯。
