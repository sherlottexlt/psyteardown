# 视觉观察、评审推理和声明审查使用独立角色接口

## Status

accepted

系统分别定义 VisionObserver、ReviewReasoner 和 ClaimJudge provider 接口，三者使用独立提示词、Schema、运行记录、评测集和 Fake 实现。MVP 底层可以配置同一个实际多模态模型承担多个角色，但 ReviewReasoner 不能补充未经确认的视觉事实，ClaimJudge 只能审查、不能改写或批准评审项。这样避免一个万能模型同时观察、解释和证明自己正确，也允许后续独立替换各角色实现。
