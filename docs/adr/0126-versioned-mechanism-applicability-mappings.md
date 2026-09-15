# 机制卡与设计变量通过适用映射连接

## Status

accepted

MechanismApplicability 将 Canonical DesignVariable 与 MechanismCard 关联，并保存 applicable/excluded contexts、observation clues、confounds、suggested measures、evidence requirements、strength 和 status。LLM 可提出 candidate mapping，但只有 approved 版本进入默认检索；映射只表示值得检查的机制关系，不构成因果结论、固定设计配方或 blocked 规则。变量/机制版本变化触发映射影响分析，历史 ReviewItem 保留原映射版本。
