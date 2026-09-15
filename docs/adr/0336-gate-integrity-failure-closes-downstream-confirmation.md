# Gate 完整性失败关闭下游确认性资格

## Status

accepted

上游 gate 因技术故障、条件呈现未验证或数据不可用而未通过时，下游确认性资格同样关闭，但使用独立状态 `gate_inconclusive_due_to_upstream_integrity`，与效果未达标区分。下游完整结果只能作受限描述和规划，不能改写 gate 逻辑；共享条件、样本或数据链受影响时，下游不得计入外部独立支持或启发式资格。
