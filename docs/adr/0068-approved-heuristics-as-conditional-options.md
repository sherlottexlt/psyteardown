# 已批准设计启发式以条件性可选建议应用

## Status

accepted

Approved Design Heuristic 以 Heuristic Option 进入 Next Design Prompt，包含适用/不适用条件、支持证据、反例和 `consider_as_option` 指令；它不成为硬约束、不能触发 blocked 或替代 DesignBrief。生成器可以采用、部分采用或不采用，但必须返回处理说明；不采用理由要指向权衡、适用条件、冲突约束或新证据。这样保留经验的参考价值，避免知识库固化成设计配方。
