# VariablePatch 使用 must、should、explore 执行强度

## Status

accepted

人工确认的 VariablePatch 必须带执行强度：must、should 或 explore。must 用于修复硬约束、解除 blocked 或满足 Brief 明确要求，未满足时不能进入普通 Preferred；should 用于可权衡的 revise 建议，未采用必须解释；explore 用于竞争假设和证据不足方向，应生成对照或验证任务。生成器必须返回实际采用状态，执行强度只能由人工确认并通过新 revision 改变。
